import hashlib
import json
import re
import time
from typing import Any
from urllib.parse import urlparse

from scrapling.fetchers import AsyncStealthySession
from scrapling.spiders import Request, Spider


ACCOUNT = "15_STWZ_YNTVCN_02_530000"
BASE_URL = "https://www.nxnews.net"
SOURCE_URL = "https://www.nxnews.net/sh/jjcz/"
COLUMN = "警界传真"
SITE_NAME = "宁夏新闻网"
PAGE_SIZE = 20


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


def response_html(response) -> str:
    body = getattr(response, "body", b"") or b""
    if isinstance(body, bytes):
        return body.decode(getattr(response, "encoding", "utf-8") or "utf-8", errors="ignore")
    return str(body)


def article_text(response) -> str:
    article = response.css(".article").first
    return node_text(article) or first_text(response, "body")


def extract_publish_time(response) -> str:
    text = first_text(response, ".zmm6")
    match = re.search(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}", text)
    return clean(match.group(0)) if match else ""


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
            return response.urljoin(clean(match.group(1)).replace("\\/", "/"))
    return ""


def extract_poster(response) -> str:
    html = response_html(response)
    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'"cover"\s*:\s*"([^"]+)"',
        r'"poster"\s*:\s*"([^"]+)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.I | re.S)
        if match:
            return response.urljoin(clean(match.group(1)).replace("\\/", "/"))
    return clean(response.meta.get("image"))


def resolve_detail_type(response) -> str:
    carried = clean(response.meta.get("content_type")).lower()
    if carried in {"video", "vod", "live"}:
        return "video"
    if "/video/" in response.url.lower():
        return "video"
    if extract_video_url(response):
        return "video"
    return "text"


def text_item(response, project: str) -> dict[str, Any]:
    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    title = clean(response.meta.get("title")) or first_text(response, ".zwbt")
    publish_time = clean(response.meta.get("publish_time")) or extract_publish_time(response)
    column = clean(response.meta.get("column_name")) or COLUMN
    return {
        "url": response.url,
        "project": project,
        "accountcode": ACCOUNT,
        "tbid": md5(response.url),
        "spiderid": project,
        "author": "",
        "title": title,
        "publishdate": publish_time,
        "publishtime": publish_time,
        "spidertime": now,
        "content": article_text(response),
        "createtime": now,
        "type": "t_social_web",
        "tags": "textmessage",
        "commentnum": 0,
        "browsenum": 0,
        "forwardnum": 0,
        "likenum": 0,
        "root_column_name": column,
        "column_name": column,
    }


def video_item(response, project: str) -> dict[str, Any]:
    now = int(time.time())
    title = clean(response.meta.get("title")) or first_text(response, ".zwbt")
    publish_time = clean(response.meta.get("publish_time")) or extract_publish_time(response)
    column = clean(response.meta.get("column_name")) or COLUMN
    return {
        "url": response.url,
        "project": project,
        "program_name": title,
        "content": article_text(response) or title,
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
        "root_column_name": column,
        "root_column_id": "",
        "column_id": "",
        "column_name": column,
        "program_id": md5(response.url),
        "tags": column,
        "episode": 1,
        "commentnum": 0,
        "browsenum": 0,
        "forwardnum": 0,
        "likenum": 0,
    }


class WwwNxnewsNetShJjczSpider(Spider):
    name = "www-nxnews-net-sh-jjcz"
    project_name = name
    allowed_domains = {"www.nxnews.net", "nxnews.net"}
    concurrent_requests = 2
    download_delay = 0.2

    def configure_sessions(self, manager) -> None:
        manager.add(
            "browser",
            AsyncStealthySession(
                google_search=False,
                real_chrome=True,
                network_idle=False,
                wait=3000,
                timeout=60000,
                max_pages=2,
                extra_headers={"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
            ),
            default=True,
        )

    async def start_requests(self):
        yield Request(
            SOURCE_URL,
            sid="browser",
            callback=self.parse,
            dont_filter=True,
            wait_selector="#list",
            meta={"column_name": COLUMN},
        )

    async def parse(self, response):
        seen = set()
        for link in response.css("#list a[href]"):
            href = clean(link.attrib.get("href"))
            url = response.urljoin(href) if href else ""
            if not url or url in seen:
                continue
            parsed = urlparse(url)
            if parsed.netloc and parsed.netloc not in self.allowed_domains:
                continue
            seen.add(url)
            yield Request(
                url,
                sid="browser",
                callback=self.parse_detail,
                meta={
                    "title": node_text(link.css("p").first) or node_text(link),
                    "publish_time": node_text(link.css("span#time").first),
                    "column_name": clean(response.meta.get("column_name")) or COLUMN,
                },
                wait_selector=".zwbt, .article",
            )
            if len(seen) >= PAGE_SIZE:
                break

    async def parse_detail(self, response):
        if resolve_detail_type(response) == "video":
            yield video_item(response, self.project_name)
        else:
            yield text_item(response, self.project_name)


if __name__ == "__main__":
    for item in WwwNxnewsNetShJjczSpider().start().items:
        print(json.dumps(item, ensure_ascii=False))
