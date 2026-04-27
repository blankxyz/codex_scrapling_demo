import hashlib
import json
import re
import time
from typing import Any
from urllib.parse import urlparse

from scrapling.fetchers import FetcherSession
from scrapling.spiders import Request, Spider


ACCOUNT = "15_STWZ_YNTVCN_02_530000"
BASE_URL = "http://www.hngrrb.cn"
SOURCE_URL = f"{BASE_URL}/shizheng/"
COLUMN = "时政"
SITE_NAME = "河南工人日报"


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def md5(value: str) -> str:
    return hashlib.md5(value.encode("utf-8")).hexdigest()


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


def all_text(response, selector: str) -> str:
    try:
        return clean(" ".join(node_text(node) for node in response.css(selector)))
    except Exception:
        return ""


def response_html(response) -> str:
    body = getattr(response, "body", b"") or b""
    if isinstance(body, bytes):
        return body.decode(getattr(response, "encoding", "utf-8") or "utf-8", errors="ignore")
    return str(body)


def extract_publish_time(text: str) -> str:
    match = re.search(r"(\d{4}年\d{2}月\d{2}日\d{2}:\d{2}|\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)", text or "")
    return clean(match.group(1)) if match else ""


def extract_source(text: str) -> str:
    match = re.search(r"来源[:：]\s*([^\s]+)", text or "")
    return clean(match.group(1)) if match else ""


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
        r'"poster"\s*:\s*"([^"]+)"',
        r'"cover"\s*:\s*"([^"]+)"',
        r'<video[^>]+poster=["\']([^"\']+)["\']',
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


def article_text(response, title: str) -> str:
    text = first_text(response, "main.post-page .post-main .post-text")
    if text:
        return text
    paragraphs = [node_text(node) for node in response.css("main.post-page .post-main .post-text p")]
    merged = clean(" ".join(part for part in paragraphs if part and clean(part) != clean(title)))
    return merged or all_text(response, "p")


def text_item(response, project: str) -> dict[str, Any]:
    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    meta_text = first_text(response, "main.post-page .post-main .post-share > span.left")
    title = clean(response.meta.get("title")) or first_text(response, "main.post-page .post-main > h2") or first_text(response, "title")
    publish_time = clean(response.meta.get("publish_time")) or extract_publish_time(meta_text or response_html(response))
    column = clean(response.meta.get("column_name")) or COLUMN
    return {
        "url": response.url,
        "project": project,
        "accountcode": ACCOUNT,
        "tbid": md5(response.url),
        "spiderid": project,
        "author": extract_source(meta_text),
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
        "root_column_name": column,
        "column_name": column,
    }


def video_item(response, project: str) -> dict[str, Any]:
    now = int(time.time())
    meta_text = first_text(response, "main.post-page .post-main .post-share > span.left")
    title = clean(response.meta.get("title")) or first_text(response, "main.post-page .post-main > h2") or first_text(response, "title")
    publish_time = clean(response.meta.get("publish_time")) or extract_publish_time(meta_text or response_html(response))
    column = clean(response.meta.get("column_name")) or COLUMN
    return {
        "url": response.url,
        "project": project,
        "program_name": title,
        "content": article_text(response, title) or title,
        "actor": "",
        "spider_time": now,
        "poster": extract_poster(response),
        "create_time": now,
        "publish_time": publish_time,
        "director": "",
        "author": extract_source(meta_text),
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


class WwwHngrrbCnShizhengSpider(Spider):
    name = "www-hngrrb-cn-shizheng"
    project_name = name
    allowed_domains = {"www.hngrrb.cn", "hngrrb.cn"}
    concurrent_requests = 4
    download_delay = 0.1

    def configure_sessions(self, manager) -> None:
        manager.add(
            "http",
            FetcherSession(
                timeout=30,
                headers={
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Referer": BASE_URL,
                },
            ),
            default=True,
        )

    async def start_requests(self):
        yield Request(
            SOURCE_URL,
            sid="http",
            callback=self.parse,
            dont_filter=True,
            meta={"column_name": COLUMN},
        )

    async def parse(self, response):
        seen = set()
        featured_link = response.css("main.list-page .row > .col-8 > .row > .col-8 > a[href]").first
        featured = response.css("main.list-page .first-news").first
        if featured_link is not None and featured is not None:
            href = clean(featured_link.attrib.get("href"))
            detail_url = response.urljoin(href) if href else ""
            if detail_url:
                seen.add(detail_url)
                yield Request(
                    detail_url,
                    sid="http",
                    callback=self.parse_detail,
                    meta={
                        "title": node_text(featured.css(".news-ds p").first),
                        "publish_time": "",
                        "column_name": clean(response.meta.get("column_name")) or COLUMN,
                        "content_type": "",
                        "image": clean(featured.css("img").first.attrib.get("src")) if featured.css("img").first is not None else "",
                    },
                )

        for row in response.css("main.list-page .list-page-box .news-page > .media"):
            link = row.css(".media-body > a[href]").first
            href = clean(link.attrib.get("href") if link is not None else "")
            detail_url = response.urljoin(href) if href else ""
            if not detail_url or detail_url in seen:
                continue
            parsed = urlparse(detail_url)
            if parsed.netloc and parsed.netloc not in self.allowed_domains:
                continue
            seen.add(detail_url)
            yield Request(
                detail_url,
                sid="http",
                callback=self.parse_detail,
                meta={
                    "title": node_text(row.css(".media-heading").first),
                    "publish_time": extract_publish_time(node_text(row.css(".clear > span.left").first)),
                    "column_name": clean(response.meta.get("column_name")) or COLUMN,
                    "content_type": "",
                    "image": "",
                },
            )

    async def parse_detail(self, response):
        if resolve_detail_type(response) == "video":
            yield video_item(response, self.project_name)
        else:
            yield text_item(response, self.project_name)


if __name__ == "__main__":
    for item in WwwHngrrbCnShizhengSpider().start().items:
        print(json.dumps(item, ensure_ascii=False))
