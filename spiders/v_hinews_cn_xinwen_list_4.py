import hashlib
import json
import re
import time
from typing import Any
from urllib.parse import parse_qs, urlparse

from scrapling.fetchers import FetcherSession
from scrapling.spiders import Request, Spider


ACCOUNT = "15_STWZ_YNTVCN_02_530000"
SECTIONS = [
    {
        "column_name": "椰现场",
        "column_id": "4",
        "url": "https://v.hinews.cn/xinwen/list-4.html",
    }
]


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def first_text(response, selector: str) -> str:
    try:
        node = response.css(selector).first
        return clean(node.get_all_text(separator=" ", strip=True)) if node is not None else ""
    except Exception:
        return ""


def md5(value: str) -> str:
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def page_number(url: str) -> int:
    query = parse_qs(urlparse(url).query)
    try:
        return int((query.get("page") or ["1"])[0])
    except Exception:
        return 1


def video_url(response) -> str:
    html = response.body.decode("utf-8", errors="ignore") if getattr(response, "body", None) else ""
    for pattern in (
        r"video\s*:\s*['\"]([^'\"]+\.mp4[^'\"]*)['\"]",
        r'<video[^>]+src=["\']([^"\']+)["\']',
        r'<source[^>]+src=["\']([^"\']+)["\']',
    ):
        match = re.search(pattern, html, re.I)
        if match:
            return response.urljoin(match.group(1))
    return ""


def poster_url(response) -> str:
    html = response.body.decode("utf-8", errors="ignore") if getattr(response, "body", None) else ""
    for pattern in (
        r"poster\s*:\s*['\"]([^'\"]+)['\"]",
        r'<video[^>]+poster=["\']([^"\']+)["\']',
    ):
        match = re.search(pattern, html, re.I)
        if match:
            return response.urljoin(match.group(1))
    return clean(response.meta.get("image"))


def content_text(response) -> str:
    parts = [clean(node.get_all_text(separator=" ", strip=True)) for node in response.css("p.formatted")]
    parts = [part for part in parts if part]
    return clean(" ".join(parts))


def meta_text(response) -> str:
    return first_text(response, ".v_word")


def publish_time(response) -> str:
    value = clean(response.meta.get("publish_time"))
    if value:
        return value
    match = re.search(r"(\d{4}年\d{2}月\d{2}日 \d{2}:\d{2})", meta_text(response))
    return clean(match.group(1)) if match else ""


def source_text(response) -> str:
    value = clean(response.meta.get("source"))
    if value:
        return value
    match = re.search(r"来源：\s*(.+?)\s*编辑：", meta_text(response))
    return clean(match.group(1)) if match else ""


def program_id(url: str) -> str:
    match = re.search(r"show-(\d+)\.html", url)
    return clean(match.group(1)) if match else ""


def video_item(response, project: str) -> dict[str, Any]:
    now = int(time.time())
    title = clean(response.meta.get("title")) or first_text(response, ".v_brief a")
    column_name = clean(response.meta.get("column_name"))
    column_id = clean(response.meta.get("column_id"))
    return {
        "url": response.url,
        "project": project,
        "program_name": title,
        "content": content_text(response) or title,
        "actor": "",
        "spider_time": now,
        "poster": poster_url(response),
        "create_time": now,
        "publish_time": publish_time(response),
        "director": "",
        "author": "",
        "source": source_text(response),
        "accountcode": ACCOUNT,
        "video_url": video_url(response),
        "root_column_name": column_name,
        "root_column_id": column_id,
        "column_id": column_id,
        "column_name": column_name,
        "program_id": program_id(response.url),
        "tags": column_name,
        "episode": 1,
        "commentnum": 0,
        "browsenum": 0,
        "forwardnum": 0,
        "likenum": 0,
    }


class VHinewsCnXinwenList4Spider(Spider):
    name = "v-hinews-cn-xinwen-list-4"
    project_name = name
    allowed_domains = {"v.hinews.cn", "v-data.hinews.cn"}
    concurrent_requests = 4
    download_delay = 0.1

    def configure_sessions(self, manager) -> None:
        manager.add(
            "http",
            FetcherSession(
                timeout=30,
                headers={"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
            ),
            default=True,
        )

    async def start_requests(self):
        for section in SECTIONS:
            yield Request(
                section["url"],
                sid="http",
                callback=self.parse,
                dont_filter=True,
                meta=section,
            )

    async def parse(self, response):
        seen = set()
        for link in response.css('.ysp06 a[href*="/xinwen/show-"]'):
            href = clean(link.attrib.get("href"))
            title = clean(link.get_all_text(separator=" ", strip=True))
            if not href or not title or href in seen:
                continue
            seen.add(href)
            item = link.parent
            image = ""
            if item is not None:
                image_node = item.css("img").first
                image = clean(image_node.attrib.get("src")) if image_node is not None else ""
            yield Request(
                response.urljoin(href),
                sid="http",
                callback=self.parse_detail,
                meta={
                    "title": title,
                    "image": response.urljoin(image) if image else "",
                    "column_name": response.meta.get("column_name"),
                    "column_id": response.meta.get("column_id"),
                },
            )

        current_page = page_number(response.url)
        for link in response.css('a[href*="/xinwen/list-4.html?page="]'):
            href = clean(link.attrib.get("href"))
            if not href:
                continue
            next_url = response.urljoin(href)
            next_page = page_number(next_url)
            if next_page <= current_page:
                continue
            yield Request(
                next_url,
                sid="http",
                callback=self.parse,
                meta=response.meta,
            )
            break

    async def parse_detail(self, response):
        yield video_item(response, self.project_name)


if __name__ == "__main__":
    for item in VHinewsCnXinwenList4Spider().start().items:
        print(json.dumps(item, ensure_ascii=False))
