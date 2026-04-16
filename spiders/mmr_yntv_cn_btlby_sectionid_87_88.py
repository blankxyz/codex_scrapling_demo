import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urljoin

from scrapling.fetchers import AsyncDynamicSession, AsyncStealthySession
from scrapling.spiders import Request, Spider


ACCOUNT = "15_STWZ_YNTVCN_02_530000"
COLUMN = "အရေးကြီးသတင်း"
BASE = "https://www.yntv.cn"


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def node_text(node) -> str:
    try:
        return clean(node.get_all_text(separator=" ", strip=True)) if node is not None else ""
    except Exception:
        return clean(getattr(node, "text", ""))


def first_text(response, selector: str) -> str:
    try:
        return node_text(response.css(selector).first)
    except Exception:
        return ""


def md5(value: str) -> str:
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def fmt_ts(value: Any) -> str:
    try:
        dt = datetime.fromtimestamp(int(value), timezone(timedelta(hours=8)))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


def article_text(response, title: str, fallback: str = "") -> str:
    parts = []
    for node in response.css("#page_details_text_wrap .content_left > p"):
        text = node_text(node)
        if text and text != title and not text.lower().startswith("requestid"):
            parts.append(text)
    return clean(" ".join(parts)) or clean(fallback)


def html_text(response) -> str:
    body = getattr(response, "body", b"") or b""
    if isinstance(body, bytes):
        return body.decode(getattr(response, "encoding", "utf-8") or "utf-8", errors="ignore")
    return str(body)


def script_url(response, pattern: str) -> str:
    match = re.search(pattern, html_text(response), re.I | re.S)
    if not match:
        return ""
    value = next((group for group in match.groups() if group), "")
    return urljoin(response.url, clean(value).replace("\\/", "/"))


def video_url(response) -> str:
    url = clean(response.meta.get("content_url"))
    return urljoin(response.url, url) if url else script_url(
        response, r'"source"\s*:\s*"([^"]+)"|<source[^>]+src=["\']([^"\']+)["\']|<video[^>]+src=["\']([^"\']+)["\']'
    )


def text_item(response, project: str) -> dict[str, Any]:
    title = clean(response.meta.get("title")) or first_text(response, "#page_details_text_wrap .text_title")
    publish = clean(response.meta.get("publish_time"))
    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    return {
        "url": response.url,
        "project": project,
        "accountcode": ACCOUNT,
        "tbid": md5(response.url),
        "spiderid": project,
        "author": "",
        "title": title,
        "publishdate": publish,
        "publishtime": publish,
        "spidertime": now,
        "content": article_text(response, title, response.meta.get("description", "")),
        "createtime": now,
        "type": "t_social_web",
        "tags": "textmessage",
        "commentnum": 0,
        "browsenum": 0,
        "forwardnum": 0,
        "likenum": 0,
        "root_column_name": clean(response.meta.get("column_name")) or COLUMN,
        "column_name": clean(response.meta.get("column_name")) or COLUMN,
    }


def video_item(response, project: str) -> dict[str, Any]:
    now = int(time.time())
    title = clean(response.meta.get("title")) or first_text(response, "#page_details_text_wrap .text_title")
    column = clean(response.meta.get("column_name")) or COLUMN
    poster = clean(response.meta.get("image")) or script_url(response, r'"cover"\s*:\s*"([^"]+)"')
    return {
        "url": response.url,
        "project": project,
        "program_name": title,
        "content": article_text(response, title, response.meta.get("description", "")) or title,
        "actor": "",
        "spider_time": now,
        "poster": poster,
        "create_time": now,
        "publish_time": clean(response.meta.get("publish_time")),
        "director": "",
        "author": "",
        "source": "吉祥网",
        "accountcode": ACCOUNT,
        "video_url": video_url(response),
        "root_column_name": column,
        "root_column_id": "",
        "column_id": clean(response.meta.get("section_id")),
        "column_name": column,
        "program_id": clean(response.meta.get("content_id")),
        "tags": column,
        "episode": 1,
        "commentnum": 0,
        "browsenum": 0,
        "forwardnum": 0,
        "likenum": 0,
    }


class MmrYntvCnBtlbySectionid8788Spider(Spider):
    name = "mmr-yntv-cn-btlby-sectionid-87-88"
    project_name = name
    allowed_domains = {"mmr.yntv.cn", "www.yntv.cn", "yntv-api.yntv.cn", "video.yntv.cn"}
    start_urls = [
        "https://mmr.yntv.cn/mmr/btlby.html?sectionid=87,88&page=1&title=%E1%80%A1%E1%80%9B%E1%80%B1%E1%80%B8%E1%80%80%E1%80%BC%E1%80%AE%E1%80%B8%E1%80%9E%E1%80%90%E1%80%84%E1%80%BA%E1%80%B8"
    ]

    section_id = "87,88"
    page_size = 30
    concurrent_requests = 2
    download_delay = 0.2

    def configure_sessions(self, manager) -> None:
        session_cls = AsyncStealthySession if os.getenv("SCRAPLING_STEALTH") == "1" else AsyncDynamicSession
        manager.add(
            "browser",
            session_cls(
                capture_xhr="/api/cms/getsection",
                google_search=False,
                real_chrome=os.getenv("SCRAPLING_REAL_CHROME", "1") != "0",
                network_idle=False,
                wait=3000,
                timeout=60000,
                max_pages=2,
                extra_headers={"Accept-Language": "my,zh-CN;q=0.9,en;q=0.8"},
            ),
            default=True,
        )

    async def start_requests(self):
        yield Request(
            self.start_urls[0],
            sid="browser",
            callback=self.parse,
            dont_filter=True,
            wait_selector='li.sec2_right_item a[href^="https://www.yntv.cn/"]',
        )

    async def parse(self, response):
        data = self.first_page_json(response)
        if data:
            for row in (data.get("data") or [])[: self.page_size]:
                url = clean(row.get("url"))
                if url:
                    yield Request(
                        url,
                        sid="browser",
                        callback=self.parse_detail,
                        meta={
                            "title": clean(row.get("title")),
                            "publish_time": fmt_ts(row.get("createtime")),
                            "column_name": COLUMN,
                            "section_id": self.section_id,
                            "content_type": clean(row.get("type")).lower(),
                            "image": urljoin(BASE, clean(row.get("image"))),
                            "description": clean(row.get("description")),
                            "content_id": clean(row.get("content_id")),
                            "content_url": clean(row.get("content_url")),
                        },
                        wait_selector="#page_details_text_wrap .content_left .text_title",
                    )
            return

        seen = set()
        for item in response.css("li.sec2_right_item"):
            link = item.css('a[href^="https://www.yntv.cn/"]').first
            url = clean(link.attrib.get("href") if link is not None else "")
            if not url or url in seen or len(seen) >= self.page_size:
                continue
            seen.add(url)
            yield Request(
                url,
                sid="browser",
                callback=self.parse_detail,
                meta={
                    "title": node_text(item.css(".sec2_right_item_title").first),
                    "column_name": COLUMN,
                    "section_id": self.section_id,
                    "content_type": "video" if "/video/" in url else "news",
                },
                wait_selector="#page_details_text_wrap .content_left .text_title",
            )

    async def parse_detail(self, response):
        if clean(response.meta.get("content_type")) == "video" or "/video/" in response.url:
            yield video_item(response, self.project_name)
        else:
            yield text_item(response, self.project_name)

    def first_page_json(self, response) -> dict[str, Any] | None:
        for xhr in response.captured_xhr or []:
            url = getattr(xhr, "url", "")
            if "/api/cms/getsection" not in url or "page=1" not in url:
                continue
            try:
                data = json.loads(xhr.body.decode("utf-8", errors="ignore"))
            except Exception:
                continue
            if isinstance(data.get("data"), list):
                return data
        return None


if __name__ == "__main__":
    for item in MmrYntvCnBtlbySectionid8788Spider().start().items:
        print(json.dumps(item, ensure_ascii=False))
