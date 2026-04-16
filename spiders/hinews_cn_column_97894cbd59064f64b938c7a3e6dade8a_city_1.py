import hashlib
import json
import re
import time
from typing import Any

from scrapling.fetchers import FetcherSession
from scrapling.spiders import Request, Spider


ACCOUNT = "15_STWZ_YNTVCN_02_530000"
BASE_URL = "https://www.hinews.cn"
SOURCE_URL = "https://www.hinews.cn/column/97894cbd59064f64b938c7a3e6dade8a?city=1"
LIST_API = f"{BASE_URL}/open-service/content/getNewsIndexManyLevelByUuidSplit"
COLUMN = "海口"
UUID = "97894cbd59064f64b938c7a3e6dade8a"
SITE_ID = 12
PAGE_NO = 1
PAGE_SIZE = 20
DEFAULT_DETAIL_SECTION = "1044"


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


def api_json(response) -> dict[str, Any]:
    try:
        return json.loads(response.body.decode("utf-8", errors="ignore"))
    except Exception:
        return {}


def article_text(response, title: str) -> str:
    parts = [node_text(node) for node in response.css("#bs_content p, #bs_content div p, #bs_content .formatted")]
    parts = [part for part in parts if part]
    if parts and clean(parts[0]) == clean(title):
        parts = parts[1:]
    return clean(" ".join(parts)) or first_text(response, "#bs_content")


def text_item(response, project: str) -> dict[str, Any]:
    title = clean(response.meta.get("title")) or first_text(response, "h2.page_h2")
    publish_time = clean(response.meta.get("publish_time")) or extract_publish_time(response)
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
        "spidertime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "content": article_text(response, title),
        "createtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "type": "t_social_web",
        "tags": "textmessage",
        "commentnum": 0,
        "browsenum": 0,
        "forwardnum": 0,
        "likenum": 0,
        "root_column_name": COLUMN,
        "column_name": COLUMN,
    }


def extract_publish_time(response) -> str:
    meta_text = clean(first_text(response, "ul.page_brief"))
    match = re.search(r"(\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2}:\d{2})?)", meta_text)
    return clean(match.group(1)) if match else ""


def nested_get(data: dict[str, Any], path: str) -> str:
    value: Any = data
    for key in path.split("."):
        if not isinstance(value, dict):
            return ""
        value = value.get(key)
    return clean(value)


def detail_url(wrapper: dict[str, Any], content: dict[str, Any]) -> str:
    for candidate in (
        nested_get(content, "url"),
        nested_get(content, "href"),
        nested_get(content, "pageUrl"),
        nested_get(content, "shareUrl"),
        nested_get(wrapper, "url"),
        nested_get(wrapper, "href"),
        nested_get(wrapper, "pageUrl"),
    ):
        if not candidate:
            continue
        return candidate if candidate.startswith("http") else f"{BASE_URL}{candidate}"

    news_id = ""
    for key in ("id", "newsId", "contentId", "contentNewsId", "n"):
        news_id = clean(content.get(key))
        if news_id:
            break
    section = ""
    for key in ("siteSectionId", "sectionId", "columnId", "channelId", "s"):
        section = clean(content.get(key) or wrapper.get(key))
        if section:
            break
    if news_id:
        return f"{BASE_URL}/page?n={news_id}&m=1&s={section or DEFAULT_DETAIL_SECTION}"
    return ""


class HinewsCnColumn97894cbd59064f64b938c7a3e6dade8aCity1Spider(Spider):
    name = "hinews-cn-column-97894cbd59064f64b938c7a3e6dade8a-city-1"
    project_name = name
    allowed_domains = {"www.hinews.cn", "hinews.cn"}
    concurrent_requests = 4
    download_delay = 0.1

    def configure_sessions(self, manager) -> None:
        manager.add(
            "http",
            FetcherSession(
                timeout=30,
                headers={
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "Origin": BASE_URL,
                    "Referer": SOURCE_URL,
                },
            ),
            default=True,
        )

    async def start_requests(self):
        yield Request(
            LIST_API,
            sid="http",
            callback=self.parse,
            dont_filter=True,
            method="POST",
            data={"uuid": UUID, "pageNo": PAGE_NO, "siteId": SITE_ID},
        )

    async def parse(self, response):
        rows = api_json(response).get("data", {}).get("list", []) or []
        for row in rows[:PAGE_SIZE]:
            wrapper = row.get("moduleNewsDataBO") or {}
            content = wrapper.get("contentNewsBO") or {}
            url = detail_url(wrapper, content)
            if not url:
                continue
            publish_time = clean(content.get("timeStamp"))
            if re.fullmatch(r"\d{10,13}", publish_time):
                try:
                    stamp = int(publish_time[:10])
                    publish_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stamp))
                except Exception:
                    pass
            yield Request(
                url,
                sid="http",
                callback=self.parse_detail,
                meta={
                    "title": clean(content.get("title")),
                    "publish_time": publish_time,
                },
            )

    async def parse_detail(self, response):
        yield text_item(response, self.project_name)


if __name__ == "__main__":
    for item in HinewsCnColumn97894cbd59064f64b938c7a3e6dade8aCity1Spider().start().items:
        print(json.dumps(item, ensure_ascii=False))
