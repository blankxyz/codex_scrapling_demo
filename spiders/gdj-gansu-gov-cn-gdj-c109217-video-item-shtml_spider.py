from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
from typing import Any
from urllib.parse import urljoin

try:
    from prefect import flow, get_run_logger, task
except Exception:  # pragma: no cover - local fallback when prefect is unavailable
    _fallback_logger = logging.getLogger("gdj_gansu_gov_cn_gdj_c109217_video_item_shtml_spider")
    if not _fallback_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        _fallback_logger.addHandler(handler)
    _fallback_logger.setLevel(logging.INFO)

    def get_run_logger():
        return _fallback_logger

    def task(*_args, **_kwargs):
        def _decorator(fn):
            return fn

        return _decorator

    def flow(*_args, **_kwargs):
        def _decorator(fn):
            return fn

        return _decorator

try:
    from patchright.async_api import async_playwright
except ImportError:  # pragma: no cover - fallback for local/dev environments
    from playwright.async_api import async_playwright

from common.clickhouse_sink import filter_new_items_by_url
from common.result_sink import save_items_to_sinks

ACCOUNT_CODE = "15_STWZ_GANSUGOVCN_00_620000"
BASE_URL = "https://gdj.gansu.gov.cn"
LIST_URL = "https://gdj.gansu.gov.cn/gdj/c109217/video_item.shtml"
SITE_NAME = "甘肃省广播电视局"
SPIDER_NAME = "gdj-gansu-gov-cn-gdj-c109217-video-item-shtml-spider"
KAFKA_BOOTSTRAP_SERVERS = ["59.110.20.108:19092", "59.110.21.25:19092", "47.93.84.177:19092"]
KAFKA_TOPIC = "bh_website_620000"
REQUEST_TIMEOUT_MS = 20000
LIST_WAIT_SELECTOR = ".news_list-item ul.pagelist > li > a[href*='/gdj/c109217/'][href$='.shtml']"
DETAIL_WAIT_SELECTOR = ".newsDetails #content video[src], .newsDetails #content source[src$='.mp4'], .newsDetails #content"
FIRST_PAGE_LIMIT = 20
DEFAULT_COLUMN = "本土纪录片"

VIDEO_ITEM_KEYS = [
    "url",
    "project",
    "program_name",
    "content",
    "actor",
    "spider_time",
    "poster",
    "create_time",
    "publish_time",
    "director",
    "author",
    "source",
    "accountcode",
    "video_url",
    "root_column_name",
    "root_column_id",
    "column_id",
    "column_name",
    "program_id",
    "tags",
    "episode",
    "commentnum",
    "browsenum",
    "forwardnum",
    "likenum",
]

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def file_name_md5(value: str) -> str:
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def extract_publish_time(text: str, fallback: str = "") -> str:
    match = re.search(r"发布时间[:：]\s*(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?)", text or "")
    if match:
        return clean_text(match.group(1))
    match = re.search(r"20\d{2}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?", text or "")
    return clean_text(match.group(0)) if match else fallback


def extract_source(text: str, fallback: str = "") -> str:
    match = re.search(r"来源[:：]\s*([^\s【]+)", text or "")
    return clean_text(match.group(1)) if match else fallback


def extract_views(text: str) -> int:
    match = re.search(r"浏览次数[:：]\s*(\d+)", text or "")
    return int(match.group(1)) if match else 0


def extract_video_url_from_html(html: str, page_url: str) -> str:
    patterns = [
        r'<source[^>]+src=["\']([^"\']+\.mp4[^"\']*)["\']',
        r'<video[^>]+src=["\']([^"\']+\.mp4[^"\']*)["\']',
        r'"source"\s*:\s*"([^"]+\.mp4[^"]*)"',
        r'"mp4"\s*:\s*"([^"]+\.mp4[^"]*)"',
        r"source\s*:\s*'([^']+\.mp4[^']*)'",
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.I | re.S)
        if match:
            return urljoin(page_url, clean_text(match.group(1)).replace("\\/", "/"))
    return ""


def extract_poster_from_html(html: str, page_url: str) -> str:
    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'"poster"\s*:\s*"([^"]+)"',
        r'"cover"\s*:\s*"([^"]+)"',
        r'<video[^>]+poster=["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.I | re.S)
        if match:
            return urljoin(page_url, clean_text(match.group(1)).replace("\\/", "/"))
    return ""


def make_video_item(entry: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any]:
    title = clean_text(entry.get("title")) or clean_text(detail.get("title"))
    publish_time = clean_text(entry.get("publish_time")) or clean_text(detail.get("publish_time"))
    column_name = clean_text(entry.get("column_name")) or DEFAULT_COLUMN
    now = int(time.time())
    item = {
        "url": detail["url"],
        "project": SPIDER_NAME,
        "program_name": title,
        "content": clean_text(detail.get("content") or detail.get("body_text") or title),
        "actor": "",
        "spider_time": now,
        "poster": clean_text(detail.get("poster")),
        "create_time": now,
        "publish_time": publish_time,
        "director": "",
        "author": "",
        "source": clean_text(detail.get("source")) or SITE_NAME,
        "accountcode": ACCOUNT_CODE,
        "video_url": clean_text(detail.get("video_url")),
        "root_column_name": column_name,
        "root_column_id": "c109217",
        "column_id": "c109217",
        "column_name": column_name,
        "program_id": file_name_md5(detail["url"]),
        "tags": column_name,
        "episode": 1,
        "commentnum": 0,
        "browsenum": int(detail.get("views") or 0),
        "forwardnum": 0,
        "likenum": 0,
    }
    assert list(item.keys()) == VIDEO_ITEM_KEYS
    return item


async def _new_context(browser):
    return await browser.new_context(
        viewport={"width": 1440, "height": 2200},
        user_agent=UA,
        ignore_https_errors=True,
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
    )


async def _fetch_list_entries() -> list[dict[str, Any]]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-dev-shm-usage"])
        context = await _new_context(browser)
        page = await context.new_page()
        page.set_default_timeout(REQUEST_TIMEOUT_MS)
        try:
            await page.goto(LIST_URL, wait_until="domcontentloaded")
            await page.wait_for_selector(LIST_WAIT_SELECTOR, timeout=REQUEST_TIMEOUT_MS)
            await page.wait_for_timeout(1500)
            items = await page.locator(".news_list-item ul.pagelist > li").evaluate_all(
                """
                (els) => els.map((li) => {
                  const anchor = li.querySelector("a[href*='/gdj/c109217/'][href$='.shtml']");
                  if (!anchor) return null;
                  const titleNode = anchor.querySelector("p");
                  const timeNode = anchor.querySelector("p span");
                  const titleText = (titleNode?.innerText || titleNode?.textContent || "").replace(/\\s+/g, " ").trim();
                  const publishTime = (timeNode?.innerText || timeNode?.textContent || "").replace(/\\s+/g, " ").trim();
                  const title = titleText.replace(publishTime, "").replace(/\\s+/g, " ").trim();
                  return {
                    url: anchor.href || "",
                    title,
                    publish_time: publishTime,
                  };
                }).filter(Boolean)
                """
            )
        finally:
            await context.close()
            await browser.close()

    entries: list[dict[str, Any]] = []
    for item in items[:FIRST_PAGE_LIMIT]:
        url = clean_text(item.get("url"))
        title = clean_text(item.get("title"))
        if not url or not title:
            continue
        entries.append(
            {
                "url": url,
                "title": title,
                "publish_time": clean_text(item.get("publish_time")),
                "column_name": DEFAULT_COLUMN,
            }
        )
    return entries


async def _fetch_video_items(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not entries:
        return []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-dev-shm-usage"])
        context = await _new_context(browser)
        page = await context.new_page()
        page.set_default_timeout(REQUEST_TIMEOUT_MS)

        items: list[dict[str, Any]] = []
        try:
            for entry in entries:
                await page.goto(entry["url"], wait_until="domcontentloaded")
                await page.wait_for_selector(DETAIL_WAIT_SELECTOR, timeout=REQUEST_TIMEOUT_MS)
                await page.wait_for_timeout(1200)

                title = clean_text(
                    await page.locator(".newsDetails #title_f, .newsDetails #title_mm, h6.text_title_f#title_f").first.text_content()
                ) or clean_text(entry.get("title"))
                meta_text = clean_text(
                    await page.locator(".newsDetails .notice, .titles").first.text_content()
                )
                content_text = clean_text(
                    await page.locator(".newsDetails #content").first.text_content()
                )
                content_html = await page.locator(".newsDetails #content").first.inner_html()
                page_html = await page.content()

                detail = {
                    "url": entry["url"],
                    "title": title,
                    "content": content_text or title,
                    "body_text": clean_text(" ".join(part for part in [meta_text, content_text] if part)),
                    "publish_time": extract_publish_time(meta_text or page_html, entry.get("publish_time", "")),
                    "source": extract_source(meta_text or page_html, SITE_NAME),
                    "views": extract_views(meta_text or page_html),
                    "video_url": extract_video_url_from_html(content_html or page_html, entry["url"]),
                    "poster": extract_poster_from_html(content_html or page_html, entry["url"]),
                }
                items.append(make_video_item(entry, detail))
        finally:
            await context.close()
            await browser.close()

    return items


@task(retries=2, retry_delay_seconds=5, name="抓取甘肃广电局本土纪录片列表")
def fetch_list_entries() -> list[dict[str, Any]]:
    logger = get_run_logger()
    entries = asyncio.run(_fetch_list_entries())
    logger.info("列表页抓到 %s 条，按第一页处理，保留前 %s 条", len(entries), FIRST_PAGE_LIMIT)
    return entries


@task(retries=2, retry_delay_seconds=5, name="抓取甘肃广电局本土纪录片详情")
def fetch_video_items(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    logger = get_run_logger()
    items = asyncio.run(_fetch_video_items(entries))
    logger.info("详情页抓取完成，共生成 %s 条视频记录", len(items))
    return items


@task(name="打印甘肃广电局本土纪录片样例")
def print_results(items: list[dict[str, Any]]) -> None:
    for item in items[:8]:
        print(
            f"{item.get('publish_time') or '未知时间'} | "
            f"{item.get('program_name')} | "
            f"{item.get('video_url') or item.get('url')}"
        )
    print(f"--- 共 {len(items)} 条 ---")


@flow(name="甘肃广电局_本土纪录片_第一页抓取", log_prints=True)
def gdj_gansu_gov_cn_gdj_c109217_video_item_shtml_flow() -> list[dict[str, Any]]:
    entries = fetch_list_entries()
    new_entries = filter_new_items_by_url(entries, site_name=ACCOUNT_CODE)
    items = fetch_video_items(new_entries)

    if items:
        saved = save_items_to_sinks(
            items,
            site_name=ACCOUNT_CODE,
            topic=KAFKA_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        )
        get_run_logger().info("已写入通用表 %s 条", saved)
        print_results(items)

    return items


gdj_gansu_gov_cn_gdj_c109217_video_item_shtml_flow.interval = 86400


if __name__ == "__main__":
    gdj_gansu_gov_cn_gdj_c109217_video_item_shtml_flow()
