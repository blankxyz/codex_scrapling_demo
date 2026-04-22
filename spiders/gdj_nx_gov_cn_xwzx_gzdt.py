import hashlib
import json
import re
import time
from typing import Any
from urllib.parse import urlparse

from scrapling.fetchers import AsyncDynamicSession
from scrapling.spiders import Request, Spider


ACCOUNT = "15_STWZ_YNTVCN_02_530000"
COLUMN = "工作动态"
SITE_NAME = "宁夏回族自治区广播电视局"
SOURCE_URL = "https://gdj.nx.gov.cn/xwzx/gzdt/"


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
    match = re.search(r"20\d{2}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}(?::\d{2})?)?", text or "")
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
        r'<video[^>]+poster=["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.I | re.S)
        if match:
            return response.urljoin(clean(match.group(1)).replace("\\/", "/"))
    return ""


def resolve_detail_type(response) -> str:
    carried = clean(response.meta.get("content_type")).lower()
    if carried in {"video", "vod", "live"}:
        return "video"
    if "/video/" in response.url.lower():
        return "video"
    host = (urlparse(response.url).netloc or "").lower()
    if "nxtv.com.cn" in host:
        return "video"
    if extract_video_url(response):
        return "video"
    return "text"


def article_text(response, title: str) -> str:
    text = first_text(response, "div.gk-artcle-con > div.view.TRS_UEDITOR.trs_paper_default.trs_word")
    if text:
        return text
    text = first_text(response, "article, .article, .content, .TRS_Editor")
    if text:
        return text
    lines = [node_text(p) for p in response.css("p")]
    merged = clean(" ".join(line for line in lines if line and line != title))
    return merged or first_text(response, "body")


def text_item(response, project: str) -> dict[str, Any]:
    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    title = clean(response.meta.get("title")) or first_text(response, "div.gk-xl.mt20 > h1.gk-xl-t") or first_text(response, "h1")
    publish_time = clean(response.meta.get("publish_time")) or extract_publish_time(response_html(response))
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
    title = clean(response.meta.get("title")) or first_text(response, "h1") or first_text(response, "title")
    publish_time = clean(response.meta.get("publish_time")) or extract_publish_time(response_html(response))
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


class GdjNxGovCnXwzxGzdtSpider(Spider):
    name = "gdj-nx-gov-cn-xwzx-gzdt"
    project_name = name
    allowed_domains = {"gdj.nx.gov.cn", "www.nxtv.com.cn", "nxtv.com.cn"}
    concurrent_requests = 2
    download_delay = 0.2

    def configure_sessions(self, manager) -> None:
        manager.add(
            "browser",
            AsyncDynamicSession(
                google_search=False,
                network_idle=False,
                wait=3000,
                timeout=60000,
                max_pages=2,
                real_chrome=True,
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
            wait_selector="div.gl-con.rt > ul.gl-list > li > a",
            meta={"column_name": COLUMN},
        )

    async def parse(self, response):
        seen = set()
        for row in response.css("div.gl-con.rt > ul.gl-list > li"):
            link = row.css("a").first
            href = clean(link.attrib.get("href") if link is not None else "")
            detail_url = response.urljoin(href) if href else ""
            if not detail_url or detail_url in seen:
                continue
            seen.add(detail_url)
            yield Request(
                detail_url,
                sid="browser",
                callback=self.parse_detail,
                wait_selector="body",
                meta={
                    "title": node_text(link),
                    "publish_time": node_text(row.css("span").first),
                    "column_name": clean(response.meta.get("column_name")) or COLUMN,
                    "content_type": "video" if "nxtv.com.cn" in (urlparse(detail_url).netloc or "").lower() else "news",
                },
            )

    async def parse_detail(self, response):
        if resolve_detail_type(response) == "video":
            yield video_item(response, self.project_name)
        else:
            yield text_item(response, self.project_name)


if __name__ == "__main__":
    for item in GdjNxGovCnXwzxGzdtSpider().start().items:
        print(json.dumps(item, ensure_ascii=False))
