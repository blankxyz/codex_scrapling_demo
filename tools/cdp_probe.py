import argparse
import asyncio
import json
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright


def build_parser():
    parser = argparse.ArgumentParser(
        description="Probe a list page through an existing Chrome CDP session and save DOM/network/detail evidence."
    )
    parser.add_argument("--url", required=True, help="List page URL to analyze.")
    parser.add_argument("--out", required=True, help="Output JSON path.")
    parser.add_argument(
        "--cdp-url",
        default="http://127.0.0.1:9222",
        help="Chrome CDP endpoint. Default: http://127.0.0.1:9222",
    )
    parser.add_argument(
        "--list-wait-ms",
        type=int,
        default=5000,
        help="Extra wait after initial list-page load.",
    )
    parser.add_argument(
        "--detail-wait-ms",
        type=int,
        default=4000,
        help="Extra wait after initial detail-page load.",
    )
    parser.add_argument(
        "--max-body-chars",
        type=int,
        default=250000,
        help="Maximum response body characters captured per response.",
    )
    parser.add_argument(
        "--max-html-chars",
        type=int,
        default=200000,
        help="Maximum serialized HTML characters captured per page.",
    )
    parser.add_argument(
        "--no-detail",
        action="store_true",
        help="Skip opening and probing one detail page.",
    )
    return parser


async def response_body(resp, max_chars):
    try:
        headers = await resp.all_headers()
        ctype = headers.get("content-type", "")
        if not any(part in ctype for part in ("json", "text", "javascript", "html")):
            return ""
        text = await resp.text()
        return text[:max_chars]
    except Exception:
        return ""


async def collect_page_dom(page, max_html_chars):
    return await page.evaluate(
        """(maxHtmlChars) => {
            const text = el => (el?.innerText || el?.textContent || '').replace(/\\s+/g, ' ').trim();
            const compact = el => ({
              tag: el.tagName.toLowerCase(),
              className: el.className || '',
              id: el.id || '',
              href: el.href || el.getAttribute('href') || '',
              src: el.src || el.getAttribute('src') || '',
              text: text(el).slice(0, 500),
              childCount: el.children.length
            });
            const anchors = [...document.querySelectorAll('a')].slice(0, 300).map(compact);
            const likely = [...document.querySelectorAll('li, article, .item, .news, .list, .card, [class*=item], [class*=list], [class*=news], [class*=title]')]
              .map(compact).filter(x => x.text.length > 8).slice(0, 400);
            const headings = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6,.title,[class*=title],[class*=name]')]
              .map(compact).filter(x => x.text).slice(0, 200);
            return {
              url: location.href,
              title: document.title,
              bodyText: text(document.body).slice(0, 12000),
              anchors,
              likely,
              headings,
              html: document.documentElement.outerHTML.slice(0, maxHtmlChars)
            };
        }""",
        max_html_chars,
    )


async def collect_detail_dom(page, max_html_chars):
    return await page.evaluate(
        """(maxHtmlChars) => {
            const text = el => (el?.innerText || el?.textContent || '').replace(/\\s+/g, ' ').trim();
            const compact = el => ({
              tag: el.tagName.toLowerCase(),
              className: el.className || '',
              id: el.id || '',
              text: text(el).slice(0, 1000)
            });
            return {
              url: location.href,
              title: document.title,
              bodyText: text(document.body).slice(0, 12000),
              headings: [...document.querySelectorAll('h1,h2,h3,h4,h5,h6,.title,[class*=title]')]
                .map(compact).filter(x => x.text).slice(0, 150),
              contentCandidates: [...document.querySelectorAll('article, main, .content, [class*=content], [class*=article], [class*=detail], p')]
                .map(compact).filter(x => x.text.length > 20).slice(0, 250),
              html: document.documentElement.outerHTML.slice(0, maxHtmlChars)
            };
        }""",
        max_html_chars,
    )


def pick_detail_candidate(anchors, source_url):
    source = urlparse(source_url)
    source_host = source.netloc
    candidates = []
    for anchor in anchors:
        href = anchor.get("href") or ""
        text = (anchor.get("text") or "").strip()
        if not href or href.endswith("#") or href.startswith("javascript:"):
            continue
        try:
            target = urlparse(href)
        except Exception:
            continue
        if target.scheme not in {"http", "https"}:
            continue
        if target.netloc and target.netloc != source_host:
            continue
        if href == source_url:
            continue
        if len(text) < 6:
            continue
        candidates.append(href)
    return candidates[0] if candidates else ""


async def main():
    args = build_parser().parse_args()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    records = []
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(args.cdp_url)
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await context.new_page()

        async def on_response(resp):
            req = resp.request
            if req.resource_type not in {"xhr", "fetch", "document"}:
                return
            records.append(
                {
                    "url": resp.url,
                    "status": resp.status,
                    "method": req.method,
                    "resource_type": req.resource_type,
                    "request_headers": await req.all_headers(),
                    "response_headers": await resp.all_headers(),
                    "body": await response_body(resp, args.max_body_chars),
                }
            )

        page.on("response", lambda resp: asyncio.create_task(on_response(resp)))
        await page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        if args.list_wait_ms > 0:
            await page.wait_for_timeout(args.list_wait_ms)

        dom = await collect_page_dom(page, args.max_html_chars)

        detail = {}
        if not args.no_detail:
            detail_url = pick_detail_candidate(dom.get("anchors", []), args.url)
            if detail_url:
                dpage = await context.new_page()
                detail_records = []

                async def on_detail_response(resp):
                    req = resp.request
                    if req.resource_type not in {"xhr", "fetch", "document"}:
                        return
                    detail_records.append(
                        {
                            "url": resp.url,
                            "status": resp.status,
                            "method": req.method,
                            "resource_type": req.resource_type,
                            "request_headers": await req.all_headers(),
                            "response_headers": await resp.all_headers(),
                            "body": await response_body(resp, args.max_body_chars),
                        }
                    )

                dpage.on("response", lambda resp: asyncio.create_task(on_detail_response(resp)))
                await dpage.goto(detail_url, wait_until="domcontentloaded", timeout=60000)
                try:
                    await dpage.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass
                if args.detail_wait_ms > 0:
                    await dpage.wait_for_timeout(args.detail_wait_ms)
                detail = await collect_detail_dom(dpage, args.max_html_chars)
                detail["network"] = detail_records
                await dpage.close()

        await page.close()
        await browser.close()

    payload = {
        "source_url": args.url,
        "cdp_url": args.cdp_url,
        "saved_at": int(time.time()),
        "dom": dom,
        "network": records,
        "detail": detail,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    asyncio.run(main())
