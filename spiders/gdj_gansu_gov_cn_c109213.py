import hashlib
import json
import os
import re
import time
from typing import Any
from urllib.parse import urljoin

from scrapling.fetchers import AsyncStealthySession
from scrapling.spiders import Request, Spider


def file_name_md5(value: str) -> str:
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def node_text(node) -> str:
    try:
        return clean_text(str(node.get_all_text(separator=" ", strip=True)))
    except Exception:
        return clean_text(str(getattr(node, "text", "") or ""))


def first_text(response, selector: str) -> str:
    try:
        node = response.css(selector).first
        return node_text(node) if node is not None else ""
    except Exception:
        return ""


def all_text(response, selector: str) -> str:
    try:
        return clean_text(" ".join(node_text(node) for node in response.css(selector)))
    except Exception:
        return ""


def response_text(response) -> str:
    try:
        return response.body.decode("utf-8", errors="ignore")
    except Exception:
        return all_text(response, "body")


def page_title(response) -> str:
    return first_text(response, "title")


def extract_meta_value(domain_meta_list: list[dict[str, Any]], key: str) -> str:
    for group in domain_meta_list or []:
        for item in group.get("resultList") or []:
            if item.get("key") == key:
                return clean_text(item.get("value"))
    return ""


def extract_publish_time(text: str, fallback: str = "") -> str:
    match = re.search(r"发布时间[:：]\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", text or "")
    if match:
        return match.group(1)
    return fallback


def make_text_item(response, project_name: str) -> dict[str, Any]:
    html_or_text = response_text(response)
    publish_time = response.meta.get("publish_time") or extract_publish_time(html_or_text, "")
    column_name = response.meta.get("column_name") or "行业动态"
    title = response.meta.get("title") or first_text(response, "h6.text_title_f") or page_title(response)
    content = first_text(response, ".notice_content") or all_text(response, "p")
    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))

    return {
        "url": response.url,
        "project": project_name,
        "accountcode": "15_STWZ_YNTVCN_02_530000",
        "tbid": file_name_md5(response.url),
        "spiderid": project_name,
        "author": "",
        "title": title,
        "publishdate": publish_time,
        "publishtime": publish_time,
        "spidertime": now,
        "content": content,
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


class GdjGansuGovCnC109213Spider(Spider):
    name = "gdj-gansu-gov-cn-c109213"
    project_name = name
    allowed_domains = {"gdj.gansu.gov.cn"}
    start_urls = ["https://gdj.gansu.gov.cn/gdj/c109213/xwzxcdh.shtml"]

    base_url = "https://gdj.gansu.gov.cn"
    column_name = "行业动态"
    real_chrome = os.getenv("SCRAPLING_REAL_CHROME", "1") != "0"

    concurrent_requests = 2
    download_delay = 0.2

    def configure_sessions(self, manager) -> None:
        manager.add(
            "browser",
            AsyncStealthySession(
                capture_xhr="/common/search/",
                google_search=False,
                real_chrome=self.real_chrome,
                extra_headers={"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
                network_idle=False,
                wait=3000,
                timeout=60000,
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
            wait_selector=".pagelist a[href*='/gdj/c109213/'][href$='.shtml']",
            meta={"column_name": self.column_name},
        )

    async def parse(self, response):
        list_data = self._extract_first_page_json(response)
        if list_data:
            for row in list_data.get("data", {}).get("results", []) or []:
                detail_url = urljoin(self.base_url, row.get("url") or "")
                if not detail_url:
                    continue
                yield Request(
                    detail_url,
                    sid="browser",
                    callback=self.parse_detail,
                    meta={
                        "title": clean_text(row.get("title")),
                        "publish_time": clean_text(row.get("publishedTimeStr")),
                        "column_name": row.get("channelName") or self.column_name,
                        "source": extract_meta_value(row.get("domainMetaList") or [], "source"),
                    },
                    wait_selector=".notice_content",
                )
            return

        # Fallback: use the rendered first-page DOM if XHR capture is unavailable.
        for link in response.css(".pagelist a[href*='/gdj/c109213/'][href$='.shtml']"):
            href = link.attrib.get("href") or ""
            title = node_text(link.css(".left p").first) or clean_text(link.attrib.get("title"))
            publish_time = node_text(link.css("em").first)
            if not href:
                continue
            yield Request(
                urljoin(self.base_url, href),
                sid="browser",
                callback=self.parse_detail,
                meta={
                    "title": title,
                    "publish_time": publish_time,
                    "column_name": self.column_name,
                },
                wait_selector=".notice_content",
            )

    async def parse_detail(self, response):
        yield make_text_item(response, self.project_name)

    def _extract_first_page_json(self, response) -> dict[str, Any] | None:
        for xhr in response.captured_xhr or []:
            if "/common/search/" not in getattr(xhr, "url", ""):
                continue
            try:
                data = json.loads(xhr.body.decode("utf-8", errors="ignore"))
            except Exception:
                continue
            if data.get("data", {}).get("page") == 1:
                return data
        return None


if __name__ == "__main__":
    result = GdjGansuGovCnC109213Spider().start()
    for item in result.items:
        print(json.dumps(item, ensure_ascii=False))
