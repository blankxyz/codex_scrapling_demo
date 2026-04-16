import asyncio
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright


URL = "https://hkbtv.cn/#/common1858408493966991361?type=1858408493966991361"
OUT = Path("analysis_outputs/_hkbtv_probe.json")


async def response_body(resp):
    try:
        headers = await resp.all_headers()
        ctype = headers.get("content-type", "")
        if not any(part in ctype for part in ("json", "text", "javascript", "html")):
            return ""
        text = await resp.text()
        return text[:250000]
    except Exception:
        return ""


async def main():
    records = []
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await context.new_page()

        async def on_response(resp):
            req = resp.request
            if req.resource_type not in {"xhr", "fetch", "document"}:
                return
            body = await response_body(resp)
            records.append(
                {
                    "url": resp.url,
                    "status": resp.status,
                    "method": req.method,
                    "resource_type": req.resource_type,
                    "request_headers": await req.all_headers(),
                    "response_headers": await resp.all_headers(),
                    "body": body,
                }
            )

        page.on("response", lambda resp: asyncio.create_task(on_response(resp)))
        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        await page.wait_for_timeout(5000)

        dom = await page.evaluate(
            """() => {
                const text = el => (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
                const compact = el => ({
                  tag: el.tagName.toLowerCase(),
                  className: el.className || '',
                  id: el.id || '',
                  href: el.href || el.getAttribute('href') || '',
                  src: el.src || el.getAttribute('src') || '',
                  text: text(el).slice(0, 500),
                  childCount: el.children.length
                });
                const anchors = [...document.querySelectorAll('a')].slice(0, 200).map(compact);
                const likely = [...document.querySelectorAll('li, article, .item, .news, .list, .card, [class*=item], [class*=list], [class*=news], [class*=title]')]
                  .map(compact).filter(x => x.text.length > 8).slice(0, 300);
                const headings = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6,.title,[class*=title],[class*=name]')]
                  .map(compact).filter(x => x.text).slice(0, 150);
                return {
                  url: location.href,
                  title: document.title,
                  bodyText: text(document.body).slice(0, 8000),
                  anchors,
                  likely,
                  headings,
                  html: document.documentElement.outerHTML.slice(0, 200000)
                };
            }"""
        )

        # Try opening the first visible article-like link in a new tab for detail selectors.
        detail = {}
        hrefs = [a["href"] for a in dom["anchors"] if a.get("href")]
        candidates = [
            href
            for href in hrefs
            if "hkbtv.cn" in href and href != URL and not href.endswith("#") and "common1858408493966991361" not in href
        ]
        if candidates:
            detail_url = candidates[0]
            dpage = await context.new_page()
            detail_records = []

            async def on_detail_response(resp):
                req = resp.request
                if req.resource_type in {"xhr", "fetch", "document"}:
                    detail_records.append(
                        {
                            "url": resp.url,
                            "status": resp.status,
                            "method": req.method,
                            "resource_type": req.resource_type,
                            "body": await response_body(resp),
                        }
                    )

            dpage.on("response", lambda resp: asyncio.create_task(on_detail_response(resp)))
            await dpage.goto(detail_url, wait_until="domcontentloaded", timeout=60000)
            try:
                await dpage.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            await dpage.wait_for_timeout(4000)
            detail = await dpage.evaluate(
                """() => {
                    const text = el => (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
                    const compact = el => ({
                      tag: el.tagName.toLowerCase(),
                      className: el.className || '',
                      id: el.id || '',
                      text: text(el).slice(0, 1000)
                    });
                    return {
                      url: location.href,
                      title: document.title,
                      bodyText: text(document.body).slice(0, 8000),
                      headings: [...document.querySelectorAll('h1,h2,h3,h4,h5,h6,.title,[class*=title]')].map(compact).filter(x => x.text).slice(0, 100),
                      contentCandidates: [...document.querySelectorAll('article, main, .content, [class*=content], [class*=article], [class*=detail], p')].map(compact).filter(x => x.text.length > 20).slice(0, 200),
                      html: document.documentElement.outerHTML.slice(0, 200000)
                    };
                }"""
            )
            detail["network"] = detail_records
            await dpage.close()

        await page.close()
        await browser.close()

    OUT.write_text(
        json.dumps(
            {
                "source_url": URL,
                "saved_at": int(time.time()),
                "dom": dom,
                "network": records,
                "detail": detail,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(OUT)


if __name__ == "__main__":
    asyncio.run(main())
