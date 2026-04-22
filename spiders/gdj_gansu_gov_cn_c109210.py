import hashlib
import json
import os
import re
import time
from typing import Any
from urllib.parse import urljoin

from scrapling.fetchers import AsyncStealthySession
from scrapling.spiders import Request, Spider


ACCOUNT = "15_STWZ_YNTVCN_02_530000"
BASE_URL = "https://gdj.gansu.gov.cn"
SOURCE_URL = "https://gdj.gansu.gov.cn/gdj/c109210/xwzxcdh.shtml"
COLUMN = "本局消息"
CHANNEL_ID = "da0a67b533e44b5db010364acd9ee7bb"
SITE_NAME = "甘肃省广播电视局"

TEXT_ITEM_KEYS = [
    "url",
    "project",
    "accountcode",
    "tbid",
    "spiderid",
    "author",
    "title",
    "publishdate",
    "publishtime",
    "spidertime",
    "content",
    "createtime",
    "type",
    "tags",
    "commentnum",
    "browsenum",
    "forwardnum",
    "likenum",
    "root_column_name",
    "column_name",
]

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


def file_name_md5(value: str) -> str:
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def node_text(node) -> str:
    try:
        return clean_text(node.get_all_text(separator=" ", strip=True)) if node is not None else ""
    except Exception:
        return clean_text(getattr(node, "text", ""))


def first_text(response, selector: str) -> str:
    try:
        return node_text(response.css(selector).first)
    except Exception:
        return ""


def all_text(response, selector: str) -> str:
    try:
        return clean_text(" ".join(node_text(node) for node in response.css(selector)))
    except Exception:
        return ""


def response_html(response) -> str:
    body = getattr(response, "body", b"") or b""
    if isinstance(body, bytes):
        return body.decode(getattr(response, "encoding", "utf-8") or "utf-8", errors="ignore")
    return str(body)


def page_title(response) -> str:
    return first_text(response, "title")


def extract_meta_value(domain_meta_list: list[dict[str, Any]], key: str) -> str:
    for group in domain_meta_list or []:
        for item in group.get("resultList") or []:
            if item.get("key") == key:
                return clean_text(item.get("value"))
    return ""


def extract_publish_time(text: str, fallback: str = "") -> str:
    match = re.search(r"发布时间[:：]\s*(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?)", text or "")
    if match:
        return clean_text(match.group(1))
    match = re.search(r"20\d{2}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?", text or "")
    return clean_text(match.group(0)) if match else fallback


def extract_video_url(response) -> str:
    html = response_html(response)
    patterns = [
        r'"source"\s*:\s*"([^"]+)"',
        r'"mp4"\s*:\s*"([^"]+)"',
        r"source\s*:\s*'([^']+)'",
        r'<source[^>]+src=["\']([^"\']+)["\']',
        r'<video[^>]+src=["\']([^"\']+)["\']',
        r'<iframe[^>]+src=["\']([^"\']*(?:player|video)[^"\']*)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.I | re.S)
        if match:
            return response.urljoin(clean_text(match.group(1)).replace("\\/", "/"))
    return ""


def extract_poster(response) -> str:
    html = response_html(response)
    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'"cover"\s*:\s*"([^"]+)"',
        r'"poster"\s*:\s*"([^"]+)"',
        r'<video[^>]+poster=["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.I | re.S)
        if match:
            return response.urljoin(clean_text(match.group(1)).replace("\\/", "/"))
    return clean_text(response.meta.get("image"))


def resolve_detail_type(response) -> str:
    carried = clean_text(response.meta.get("content_type")).lower()
    if carried in {"video", "vod", "live"}:
        return "video"
    if "/video/" in response.url.lower():
        return "video"
    if extract_video_url(response):
        return "video"
    return "text"


def article_text(response, title: str = "") -> str:
    content = first_text(response, ".notice_content")
    if content:
        return content
    content = first_text(response, ".content.mcont.w1200")
    if content:
        return clean_text(content.replace(title, "", 1)) if title and content.startswith(title) else content
    lines = [node_text(node) for node in response.css("p")]
    merged = clean_text(" ".join(line for line in lines if line and line != title))
    return merged or first_text(response, "body")


def make_text_item(response, project_name: str) -> dict[str, Any]:
    html_or_text = response_html(response)
    publish_time = clean_text(response.meta.get("publish_time")) or extract_publish_time(html_or_text, "")
    column_name = clean_text(response.meta.get("column_name")) or COLUMN
    title = clean_text(response.meta.get("title")) or first_text(response, "h6.text_title_f") or page_title(response)
    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
    item = {
        "url": response.url,
        "project": project_name,
        "accountcode": ACCOUNT,
        "tbid": file_name_md5(response.url),
        "spiderid": project_name,
        "author": "",
        "title": title,
        "publishdate": publish_time,
        "publishtime": publish_time,
        "spidertime": now,
        "content": article_text(response, title),
        "createtime": now,
        "type": "t_social_web",
        "tags": "textmessage",
        "commentnum": 0,
        "browsenum": 0,
        "forwardnum": 0,
        "likenum": 0,
        "root_column_name": column_name,
        "column_name": column_name,
    }
    assert list(item.keys()) == TEXT_ITEM_KEYS
    return item


def make_video_item(response, project_name: str) -> dict[str, Any]:
    now = int(time.time())
    title = clean_text(response.meta.get("title")) or first_text(response, "h6.text_title_f") or page_title(response)
    publish_time = clean_text(response.meta.get("publish_time")) or extract_publish_time(response_html(response), "")
    column_name = clean_text(response.meta.get("column_name")) or COLUMN
    item = {
        "url": response.url,
        "project": project_name,
        "program_name": title,
        "content": article_text(response, title) or title,
        "actor": "",
        "spider_time": now,
        "poster": extract_poster(response),
        "create_time": now,
        "publish_time": publish_time,
        "director": "",
        "author": "",
        "source": SITE_NAME,
        "accountcode": ACCOUNT,
        "video_url": extract_video_url(response),
        "root_column_name": column_name,
        "root_column_id": "",
        "column_id": "",
        "column_name": column_name,
        "program_id": file_name_md5(response.url),
        "tags": column_name,
        "episode": 1,
        "commentnum": 0,
        "browsenum": 0,
        "forwardnum": 0,
        "likenum": 0,
    }
    assert list(item.keys()) == VIDEO_ITEM_KEYS
    return item


class GdjGansuGovCnC109210Spider(Spider):
    name = "gdj-gansu-gov-cn-c109210"
    project_name = name
    allowed_domains = {"gdj.gansu.gov.cn"}
    start_urls = [SOURCE_URL]

    base_url = BASE_URL
    column_name = COLUMN
    real_chrome = os.getenv("SCRAPLING_REAL_CHROME", "1") != "0"

    concurrent_requests = 2
    download_delay = 0.2

    def configure_sessions(self, manager) -> None:
        manager.add(
            "browser",
            AsyncStealthySession(
                capture_xhr="/common/search/",
                google_search=False,
                # real_chrome=self.real_chrome,
                extra_headers={"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
                network_idle=False,
                wait=8000,
                timeout=12000,
                max_pages=2,
            ),
            default=True,
        )

    async def start_requests(self):
        yield Request(
            self.start_urls[0],
            sid="browser",
            callback=self.parse,
            dont_filter=True,
            wait_selector=".newList ul li .left p a[href*='/gdj/c109210/']",
            meta={"column_name": self.column_name},
        )

    async def parse(self, response):
        seen = set()
        list_data = self._extract_first_page_json(response)
        if list_data:
            for row in list_data.get("data", {}).get("results", []) or []:
                detail_url = urljoin(self.base_url, row.get("url") or "")
                if not detail_url or detail_url in seen:
                    continue
                seen.add(detail_url)
                yield Request(
                    detail_url,
                    sid="browser",
                    callback=self.parse_detail,
                    meta={
                        "title": clean_text(row.get("title")),
                        "publish_time": clean_text(row.get("publishedTimeStr")),
                        "column_name": row.get("channelName") or self.column_name,
                        "source": extract_meta_value(row.get("domainMetaList") or [], "source"),
                        "content_type": clean_text(row.get("contentType") or row.get("type") or "news"),
                    },
                    wait_selector=".notice_content, h6.text_title_f, video, iframe",
                )
            return

        for row in response.css(".newList ul li"):
            link = row.css(".left p a[href*='/gdj/c109210/'][href$='.shtml']").first or row.css("a[href*='/gdj/c109210/'][href$='.shtml']").first
            href = clean_text(link.attrib.get("href") if link is not None else "")
            detail_url = response.urljoin(href) if href else ""
            if not detail_url or detail_url in seen:
                continue
            seen.add(detail_url)
            yield Request(
                detail_url,
                sid="browser",
                callback=self.parse_detail,
                meta={
                    "title": node_text(link),
                    "publish_time": node_text(row.css("em").first),
                    "column_name": clean_text(response.meta.get("column_name")) or self.column_name,
                    "content_type": "news",
                },
                wait_selector=".notice_content, h6.text_title_f, video, iframe",
            )

    async def parse_detail(self, response):
        if resolve_detail_type(response) == "video":
            yield make_video_item(response, self.project_name)
        else:
            yield make_text_item(response, self.project_name)

    def _extract_first_page_json(self, response) -> dict[str, Any] | None:
        for xhr in response.captured_xhr or []:
            if f"/common/search/{CHANNEL_ID}" not in getattr(xhr, "url", ""):
                continue
            try:
                data = json.loads(xhr.body.decode("utf-8", errors="ignore"))
            except Exception:
                continue
            if data.get("data", {}).get("page") == 1:
                return data
        return None


if __name__ == "__main__":
    result = GdjGansuGovCnC109210Spider().start()
    for item in result.items:
        print(json.dumps(item, ensure_ascii=False))
