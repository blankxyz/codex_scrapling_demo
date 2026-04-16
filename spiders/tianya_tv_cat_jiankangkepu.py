import hashlib
import json
import re
import time
from typing import Any

from scrapling.fetchers import FetcherSession
from scrapling.spiders import Request, Spider


ACCOUNT = "15_STWZ_YNTVCN_02_530000"
SOURCE = "海南丽声"
SECTIONS = [
    {
        "column_name": "健康科普",
        "column_id": "69",
        "url": "https://www.tianya.tv/cat/%e5%81%a5%e5%ba%b7%e7%a7%91%e6%99%ae",
    },
    {
        "column_name": "网络电影",
        "column_id": "59",
        "url": "https://www.tianya.tv/cat/%e4%bc%98%e7%a7%80%e7%bd%91%e7%bb%9c%e8%a7%86%e5%90%ac%e8%8a%82%e7%9b%ae%e5%b1%95%e6%92%ad/%e7%bd%91%e7%bb%9c%e7%94%b5%e5%bd%b1",
    },
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


def video_url(response) -> str:
    for selector in ("video source", "video"):
        node = response.css(selector).first
        if node is not None:
            url = node.attrib.get("src") or ""
            if url:
                return response.urljoin(url)
    html = getattr(response, "text", "") or ""
    match = re.search(r'<source[^>]+src=["\\\']([^"\\\']+)', html, re.I)
    return response.urljoin(match.group(1)) if match else ""


def video_item(response, project: str) -> dict[str, Any]:
    now = int(time.time())
    title = response.meta.get("title") or first_text(response, "h1.entry-title")
    publish_time = response.meta.get("publish_time") or first_text(response, ".entry-date")
    column_name = clean(response.meta.get("column_name"))
    column_id = clean(response.meta.get("column_id"))
    poster = (
        response.meta.get("image")
        or clean(response.css(".entry-content img.wp-post-image").first.attrib.get("src"))
        if response.css(".entry-content img.wp-post-image").first
        else ""
    )
    return {
        "url": response.url,
        "project": project,
        "program_name": title,
        "content": title,
        "actor": "",
        "spider_time": now,
        "poster": response.urljoin(poster) if poster else "",
        "create_time": now,
        "publish_time": publish_time,
        "director": "",
        "author": "",
        "source": SOURCE,
        "accountcode": ACCOUNT,
        "video_url": video_url(response),
        "root_column_name": column_name,
        "root_column_id": column_id,
        "column_id": column_id,
        "column_name": column_name,
        "program_id": response.meta.get("post_id") or "",
        "tags": column_name,
        "episode": 1,
        "commentnum": 0,
        "browsenum": 0,
        "forwardnum": 0,
        "likenum": 0,
    }


class TianyaTvCatJiankangkepuSpider(Spider):
    name = "tianya-tv-cat-jiankangkepu"
    project_name = name
    allowed_domains = {"www.tianya.tv", "tianya.tv"}
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
        for post in response.css('#recent-content > div[id^="post-"]'):
            title_link = post.css("h2.entry-title a").first
            thumb_link = post.css("a.thumbnail-link").first
            href = ""
            if title_link is not None:
                href = title_link.attrib.get("href") or ""
            if not href and thumb_link is not None:
                href = thumb_link.attrib.get("href") or ""
            if not href:
                continue
            image = clean(post.css("img").first.attrib.get("src")) if post.css("img").first else ""
            yield Request(
                response.urljoin(href),
                sid="http",
                callback=self.parse_detail,
                meta={
                    "title": clean(title_link.get_all_text(separator=" ", strip=True)) if title_link is not None else "",
                    "publish_time": "",
                    "post_id": clean((post.attrib.get("id") or "").replace("post-", "")),
                    "image": image,
                    "column_name": response.meta.get("column_name"),
                    "column_id": response.meta.get("column_id"),
                },
            )

    async def parse_detail(self, response):
        yield video_item(response, self.project_name)


if __name__ == "__main__":
    for item in TianyaTvCatJiankangkepuSpider().start().items:
        print(json.dumps(item, ensure_ascii=False))
