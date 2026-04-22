import argparse
import asyncio
import json
import time
from pathlib import Path

from playwright.async_api import async_playwright


def build_parser():
    parser = argparse.ArgumentParser(
        description="Probe a page with a locally launched browser and save DOM evidence."
    )
    parser.add_argument("--url", required=True, help="Page URL to analyze.")
    parser.add_argument("--out", required=True, help="Output JSON path.")
    parser.add_argument(
        "--wait-ms",
        type=int,
        default=5000,
        help="Extra wait after initial page load.",
    )
    parser.add_argument(
        "--max-html-chars",
        type=int,
        default=200000,
        help="Maximum serialized HTML characters captured per page.",
    )
    return parser


async def collect_page_dom(page, max_html_chars):
    return await page.evaluate(
        """(maxHtmlChars) => {
            const text = value => (value || '').replace(/\\s+/g, ' ').trim();
            const compact = el => ({
              tag: el.tagName.toLowerCase(),
              className: el.className || '',
              id: el.id || '',
              href: el.href || el.getAttribute('href') || '',
              text: text(el.innerText || el.textContent || '').slice(0, 500)
            });
            return {
              url: location.href,
              title: document.title,
              bodyText: text(document.body?.innerText || '').slice(0, 12000),
              anchors: [...document.querySelectorAll('a')].map(compact).filter(x => x.text || x.href).slice(0, 500),
              headings: [...document.querySelectorAll('h1,h2,h3,h4,h5,h6,.title,[class*=title],[class*=name]')]
                .map(compact).filter(x => x.text).slice(0, 300),
              html: document.documentElement.outerHTML.slice(0, maxHtmlChars)
            };
        }""",
        max_html_chars,
    )


async def main():
    args = build_parser().parse_args()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        if args.wait_ms > 0:
            await page.wait_for_timeout(args.wait_ms)
        dom = await collect_page_dom(page, args.max_html_chars)
        await browser.close()

    payload = {
        "source_url": args.url,
        "saved_at": int(time.time()),
        "dom": dom,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    asyncio.run(main())

# 172.17.28.164