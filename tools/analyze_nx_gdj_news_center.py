import argparse
import asyncio
import json
import re
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright


DATE_RE = re.compile(r"20\d{2}-\d{2}-\d{2}")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Analyze Ningxia Radio and TV Bureau news-center subcolumns with a local browser."
    )
    parser.add_argument(
        "--root-url",
        default="https://gdj.nx.gov.cn/xwzx/gzdt/",
        help="A news-center page used to discover subcolumns.",
    )
    parser.add_argument(
        "--out-json",
        required=True,
        help="Output JSON path.",
    )
    parser.add_argument(
        "--out-md",
        required=True,
        help="Output markdown path.",
    )
    parser.add_argument(
        "--wait-ms",
        type=int,
        default=5000,
        help="Extra wait after load.",
    )
    return parser


async def wait_page(page, wait_ms):
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    if wait_ms > 0:
        await page.wait_for_timeout(wait_ms)


async def collect_root(page):
    return await page.evaluate(
        """() => {
            const norm = value => (value || '').replace(/\\s+/g, ' ').trim();
            const items = [...document.querySelectorAll('a')]
              .map(a => ({
                text: norm(a.innerText || a.textContent || ''),
                href: a.href || a.getAttribute('href') || '',
                className: a.className || ''
              }))
              .filter(x => x.href && x.href.includes('/xwzx/'));
            const seen = new Set();
            const subcolumns = [];
            for (const item of items) {
              if (!item.text || item.text === '新闻中心') continue;
              if (item.href.includes('/xwzx/') && !seen.has(item.href)) {
                seen.add(item.href);
                subcolumns.push(item);
              }
            }
            return {
              url: location.href,
              title: document.title,
              bodyText: norm(document.body?.innerText || '').slice(0, 3000),
              subcolumns
            };
        }"""
    )


async def collect_list_page(page):
    return await page.evaluate(
        """() => {
            const norm = value => (value || '').replace(/\\s+/g, ' ').trim();
            const cssPath = el => {
              if (!el) return '';
              if (el.id) return `#${el.id}`;
              const parts = [];
              let node = el;
              let depth = 0;
              while (node && node.nodeType === 1 && depth < 4) {
                let part = node.tagName.toLowerCase();
                const classes = [...(node.classList || [])].slice(0, 2);
                if (classes.length) part += '.' + classes.join('.');
                parts.unshift(part);
                node = node.parentElement;
                depth += 1;
              }
              return parts.join(' > ');
            };
            const current = location.href;
            const sameHost = location.host;
            const anchors = [...document.querySelectorAll('a')];
            const detailCandidates = anchors.map(a => {
              const href = a.href || a.getAttribute('href') || '';
              const text = norm(a.innerText || a.textContent || '');
              const row = a.closest('li, tr, article, .item, .news, .list, div');
              const rowText = norm(row?.innerText || '');
              const rowHtml = row?.innerHTML || '';
              const dateMatch = rowText.match(/20\\d{2}-\\d{2}-\\d{2}/);
              const isHtmlDetail = href.includes('.html') && !href.includes('index');
              const isSameHost = href.startsWith('http') ? (new URL(href)).host === sameHost : true;
              const looksDetail = isHtmlDetail && text.length >= 6 && !['首页','上一页','下一页','尾页'].includes(text);
              return {
                text,
                href,
                rowText: rowText.slice(0, 300),
                rowSelector: cssPath(row),
                anchorSelector: cssPath(a),
                date: dateMatch ? dateMatch[0] : '',
                isSameHost,
                looksDetail,
                hasImage: /<img/i.test(rowHtml),
              };
            }).filter(x => x.looksDetail);

            const parentCounts = {};
            for (const item of detailCandidates) {
              parentCounts[item.rowSelector] = (parentCounts[item.rowSelector] || 0) + 1;
            }
            const topRowSelector = Object.entries(parentCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || '';

            const pagination = anchors.map(a => ({
              text: norm(a.innerText || a.textContent || ''),
              href: a.href || a.getAttribute('href') || ''
            })).filter(x => x.href && (['首页', '上一页', '下一页', '尾页'].includes(x.text) || /^\\d+$/.test(x.text)));

            const headingTexts = [...document.querySelectorAll('h1,h2,h3,.tit,.title,[class*=title]')]
              .map(el => norm(el.innerText || el.textContent || ''))
              .filter(Boolean)
              .slice(0, 20);

            return {
              url: location.href,
              title: document.title,
              bodyText: norm(document.body?.innerText || '').slice(0, 6000),
              metaColumnName: document.querySelector('meta[name=\"ColumnName\"]')?.content || '',
              detailCandidates: detailCandidates.slice(0, 20),
              topRowSelector,
              pagination,
              headings: headingTexts
            };
        }"""
    )


async def collect_detail_page(page):
    return await page.evaluate(
        """() => {
            const norm = value => (value || '').replace(/\\s+/g, ' ').trim();
            const cssPath = el => {
              if (!el) return '';
              if (el.id) return `#${el.id}`;
              const parts = [];
              let node = el;
              let depth = 0;
              while (node && node.nodeType === 1 && depth < 4) {
                let part = node.tagName.toLowerCase();
                const classes = [...(node.classList || [])].slice(0, 2);
                if (classes.length) part += '.' + classes.join('.');
                parts.unshift(part);
                node = node.parentElement;
                depth += 1;
              }
              return parts.join(' > ');
            };
            const titleEls = [...document.querySelectorAll('h1,h2,.title,[class*=title],[class*=Tit]')];
            const titleCandidates = titleEls
              .map(el => ({text: norm(el.innerText || el.textContent || ''), selector: cssPath(el)}))
              .filter(x => x.text.length >= 6)
              .slice(0, 10);
            const contentEls = [...document.querySelectorAll('article, main, .content, .TRS_Editor, [class*=content], [class*=article], [class*=detail], [class*=正文]')];
            const contentCandidates = contentEls
              .map(el => ({text: norm(el.innerText || el.textContent || '').slice(0, 1000), selector: cssPath(el)}))
              .filter(x => x.text.length >= 80)
              .slice(0, 10);
            const textBody = norm(document.body?.innerText || '');
            return {
              url: location.href,
              title: document.title,
              metaColumnName: document.querySelector('meta[name=\"ColumnName\"]')?.content || '',
              titleCandidates,
              contentCandidates,
              hasVideo: document.querySelectorAll('video, source, iframe').length > 0 || /mp4|m3u8|player|视频/.test(document.documentElement.innerHTML),
              publishDate: (textBody.match(/20\\d{2}[-年]\\d{1,2}[-月]\\d{1,2}/) || [''])[0],
              bodyText: textBody.slice(0, 4000)
            };
        }"""
    )


def choose_sample_detail(items):
    same_host = [item for item in items if item.get("isSameHost")]
    if same_host:
        return same_host[0]
    return items[0] if items else None


def summarize_network(records):
    filtered = []
    for rec in records:
        url = rec.get("url", "")
        if any(part in url for part in (".css", ".js", ".png", ".jpg", ".svg", ".woff", ".ico")):
            continue
        filtered.append(
            {
                "url": url,
                "status": rec.get("status"),
                "method": rec.get("method"),
                "resource_type": rec.get("resource_type"),
            }
        )
    return filtered[:20]


async def analyze_column(context, column, wait_ms):
    page = await context.new_page()
    list_network = []

    async def on_response(resp):
        req = resp.request
        if req.resource_type not in {"document", "xhr", "fetch"}:
            return
        list_network.append(
            {
                "url": resp.url,
                "status": resp.status,
                "method": req.method,
                "resource_type": req.resource_type,
            }
        )

    page.on("response", lambda resp: asyncio.create_task(on_response(resp)))
    list_error = ""
    try:
        await page.goto(column["href"], wait_until="domcontentloaded", timeout=25000)
        await wait_page(page, wait_ms)
        list_data = await collect_list_page(page)
    except Exception as exc:
        list_error = str(exc)
        list_data = {
            "url": column["href"],
            "title": "",
            "bodyText": "",
            "metaColumnName": "",
            "detailCandidates": [],
            "topRowSelector": "",
            "pagination": [],
            "headings": [],
        }

    detail_data = {}
    detail_network = []
    sample = choose_sample_detail(list_data.get("detailCandidates", []))
    if sample and sample.get("href"):
        dpage = await context.new_page()

        async def on_detail_response(resp):
            req = resp.request
            if req.resource_type not in {"document", "xhr", "fetch"}:
                return
            detail_network.append(
                {
                    "url": resp.url,
                    "status": resp.status,
                    "method": req.method,
                    "resource_type": req.resource_type,
                }
            )

        dpage.on("response", lambda resp: asyncio.create_task(on_detail_response(resp)))
        try:
            await dpage.goto(sample["href"], wait_until="domcontentloaded", timeout=25000)
            await wait_page(dpage, min(wait_ms, 2500))
            detail_data = await collect_detail_page(dpage)
        except Exception as exc:
            detail_data = {
                "url": sample["href"],
                "title": "",
                "metaColumnName": "",
                "titleCandidates": [],
                "contentCandidates": [],
                "hasVideo": False,
                "publishDate": "",
                "bodyText": "",
                "error": str(exc),
            }
        await dpage.close()

    await page.close()
    return {
        "column_name": column["text"],
        "column_url": column["href"],
        "list": list_data,
        "list_error": list_error,
        "list_network": summarize_network(list_network),
        "sample_detail": sample,
        "detail": detail_data,
        "detail_network": summarize_network(detail_network),
    }


def infer_notes(columns):
    notes = []
    same_host_counts = sum(
        1
        for column in columns
        if column.get("sample_detail", {}).get("isSameHost")
    )
    if same_host_counts >= 1:
        notes.append("大部分栏目详情链接为静态 HTML 页面，可直接做 list-to-detail 抓取。")
    external = [
        column["column_name"]
        for column in columns
        if column.get("sample_detail")
        and not column["sample_detail"].get("isSameHost")
    ]
    if external:
        notes.append(f"存在站外详情或媒体页栏目：{', '.join(external)}。")
    if any(column.get("detail", {}).get("hasVideo") for column in columns):
        notes.append("至少一个栏目详情页存在视频或播放器信号，需要运行时区分文本与视频详情。")
    return notes


def build_markdown(root_url, cdp_error, columns, notes):
    lines = [
        f"# 宁夏广电局新闻中心栏目分析",
        "",
        f"- 根页面: {root_url}",
        f"- 分析时间戳: {int(time.time())}",
        f"- CDP 状态: 失败，改用本地浏览器渲染。错误: {cdp_error}",
        f"- 子栏目数量: {len(columns)}",
        "",
        "## 子栏目清单",
        "",
    ]
    for column in columns:
        list_data = column["list"]
        detail_items = list_data.get("detailCandidates", [])
        titles = [item["text"] for item in detail_items[:5]]
        sample_detail = column.get("detail", {})
        content_selector = ""
        if sample_detail.get("contentCandidates"):
            content_selector = sample_detail["contentCandidates"][0]["selector"]
        title_selector = ""
        if sample_detail.get("titleCandidates"):
            title_selector = sample_detail["titleCandidates"][0]["selector"]
        lines.extend(
            [
                f"### {column['column_name']}",
                "",
                f"- 列表页: {column['column_url']}",
                f"- 页面标题: {list_data.get('title', '')}",
                f"- Meta 栏目名: {list_data.get('metaColumnName', '')}",
                f"- 首屏条目数: {len(detail_items)}",
                f"- 推测列表行选择器: {list_data.get('topRowSelector', '')}",
                f"- 抽样详情: {column.get('sample_detail', {}).get('href', '')}",
                f"- 详情标题选择器候选: {title_selector}",
                f"- 正文容器候选: {content_selector}",
                f"- 视频信号: {sample_detail.get('hasVideo', False)}",
                "- 首屏标题:",
            ]
        )
        for title in titles:
            lines.append(f"  - {title}")
        if list_data.get("pagination"):
            pages = ", ".join(
                f"{item['text']}={item['href']}" for item in list_data["pagination"][:6]
            )
            lines.append(f"- 分页链接: {pages}")
        if column.get("list_network"):
            docs = ", ".join(item["url"] for item in column["list_network"][:5])
            lines.append(f"- 列表网络: {docs}")
        if column.get("detail_network"):
            docs = ", ".join(item["url"] for item in column["detail_network"][:5])
            lines.append(f"- 详情网络: {docs}")
        lines.append("")

    lines.extend(["## 结论", ""])
    for note in notes:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


async def main():
    args = build_parser().parse_args()
    out_json = Path(args.out_json)
    out_md = Path(args.out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    cdp_error = ""
    async with async_playwright() as p:
        try:
            browser_over_cdp = await asyncio.wait_for(
                p.chromium.connect_over_cdp("http://172.17.142.220:9222"),
                timeout=5,
            )
            await browser_over_cdp.close()
        except Exception as exc:
            cdp_error = str(exc)

        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        root_page = await context.new_page()
        await root_page.goto(args.root_url, wait_until="domcontentloaded", timeout=60000)
        await wait_page(root_page, args.wait_ms)
        root = await collect_root(root_page)
        await root_page.close()

        preferred_names = [
            "通知公告",
            "工作动态",
            "图片新闻",
            "视频展示",
            "总局信息",
            "央网动态",
            "头条推荐",
            "纪录片",
        ]
        name_to_column = {}
        for item in root.get("subcolumns", []):
            text = item.get("text", "")
            href = item.get("href", "")
            if text in preferred_names and href:
                name_to_column[text] = {"text": text, "href": href}
        if "工作动态" not in name_to_column:
            name_to_column["工作动态"] = {
                "text": "工作动态",
                "href": args.root_url,
            }
        columns = []
        for name in preferred_names:
            column = name_to_column.get(name)
            if column:
                columns.append(await analyze_column(context, column, args.wait_ms))

        await browser.close()

    notes = infer_notes(columns)
    payload = {
        "source_url": args.root_url,
        "slug": "gdj-nx-gov-cn-xwzx-news-center",
        "analyzed_at": int(time.time()),
        "analysis_method": {
            "requested_cdp_url": "http://172.17.142.220:9222",
            "cdp_available": False,
            "cdp_error": cdp_error,
            "fallback": "local_playwright_browser",
        },
        "site": {
            "domain": urlparse(args.root_url).netloc,
            "base_url": "https://gdj.nx.gov.cn",
            "root_title": root.get("title", ""),
            "root_body_excerpt": root.get("bodyText", ""),
        },
        "subcolumns": columns,
        "notes": notes,
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(build_markdown(args.root_url, cdp_error, columns, notes), encoding="utf-8")
    print(out_json)
    print(out_md)


if __name__ == "__main__":
    asyncio.run(main())
