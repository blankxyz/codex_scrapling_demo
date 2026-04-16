import hashlib
import json
import re
import time
from typing import Any

from scrapling.fetchers import FetcherSession
from scrapling.spiders import Request, Spider


ACCOUNT = "15_STWZ_YNTVCN_02_530000"
BASE_URL = "https://www.hinews.cn"
API_BASE_URL = "https://rm-comapi-pc.hinews.cn"
SOURCE_URL = "https://www.hinews.cn/column/97894cbd59064f64b938c7a3e6dade8a?city=1"
LIST_API = f"{API_BASE_URL}/open-service/content/getNewsIndexManyLevelByUuidSplit"
COLUMN = "海口频道"
UUID = "97894cbd59064f64b938c7a3e6dade8a"
SITE_ID = 12
PAGE_NO = 1
PAGE_SIZE = 20
DEFAULT_DETAIL_STYLE = "1044"


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


def normalize_publish_time(value: Any) -> str:
    text = clean(value)
    if re.fullmatch(r"\d{10,13}", text):
        try:
            stamp = int(text[:10]) if len(text) >= 10 else int(text)
            return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stamp))
        except Exception:
            return text
    return text


def extract_publish_time(response) -> str:
    text = clean(first_text(response, "ul.page_brief li:last-child"))
    match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", text)
    return clean(match.group(1)) if match else ""


def article_text(response) -> str:
    article = response.css("#bs_content > div:first-child").first
    return node_text(article) or first_text(response, "#bs_content")


def detail_url(wrapper: dict[str, Any], content: dict[str, Any]) -> str:
    for candidate in (
        clean(content.get("url")),
        clean(content.get("href")),
        clean(content.get("pageUrl")),
        clean(content.get("shareUrl")),
        clean(wrapper.get("url")),
        clean(wrapper.get("href")),
        clean(wrapper.get("pageUrl")),
    ):
        if candidate:
            return candidate if candidate.startswith("http") else f"{BASE_URL}{candidate}"

    news_id = clean(content.get("id"))
    style_id = clean(content.get("siteLayoutModuleArticleStyleId") or content.get("styleId")) or DEFAULT_DETAIL_STYLE
    return f"{BASE_URL}/page?n={news_id}&m=1&s={style_id}" if news_id else ""


def text_item(response, project: str) -> dict[str, Any]:
    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    column_name = clean(response.meta.get("column_name")) or COLUMN
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
        "spidertime": now,
        "content": article_text(response),
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


class WwwHinewsCnColumn97894cbd59064f64b938c7a3e6dade8aSpider(Spider):
    name = "www-hinews-cn-column-97894cbd59064f64b938c7a3e6dade8a"
    project_name = name
    allowed_domains = {"www.hinews.cn", "hinews.cn", "rm-comapi-pc.hinews.cn"}
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
            meta={"column_name": COLUMN},
        )

    async def parse(self, response):
        rows = api_json(response).get("data", {}).get("list", []) or []
        if not rows:
            yield Request(
                SOURCE_URL,
                sid="http",
                callback=self.parse_dom,
                dont_filter=True,
                meta={"column_name": clean(response.meta.get("column_name")) or COLUMN},
            )
            return

        for row in rows[:PAGE_SIZE]:
            wrapper = row.get("moduleNewsDataBO") or {}
            content = wrapper.get("contentNewsBO") or {}
            url = detail_url(wrapper, content)
            if not url:
                continue
            yield Request(
                url,
                sid="http",
                callback=self.parse_detail,
                meta={
                    "title": clean(content.get("title")),
                    "publish_time": normalize_publish_time(content.get("publishTime") or content.get("timeStamp")),
                    "column_name": clean(response.meta.get("column_name")) or COLUMN,
                },
            )

    async def parse_dom(self, response):
        seen = set()
        for item in response.css("ul.l_list > li"):
            link = item.css("h3 > a").first
            href = clean(link.attrib.get("href") if link is not None else "")
            url = response.urljoin(href) if href else ""
            if not url or url in seen:
                continue
            seen.add(url)
            yield Request(
                url,
                sid="http",
                callback=self.parse_detail,
                meta={
                    "title": node_text(link),
                    "publish_time": normalize_publish_time(
                        clean(node_text(item.css("ul.brief_box > li:first-child").first)).replace("发布时间：", "")
                    ),
                    "column_name": clean(response.meta.get("column_name")) or COLUMN,
                },
            )
            if len(seen) >= PAGE_SIZE:
                break

    async def parse_detail(self, response):
        yield text_item(response, self.project_name)


if __name__ == "__main__":
    for item in WwwHinewsCnColumn97894cbd59064f64b938c7a3e6dade8aSpider().start().items:
        print(json.dumps(item, ensure_ascii=False))
