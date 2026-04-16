import hashlib
import json
import re
import time
from typing import Any

from scrapling.fetchers import FetcherSession
from scrapling.spiders import Request, Spider


ACCOUNT = "15_STWZ_YNTVCN_02_530000"
SOURCE_URL = "https://www.hinews.cn/module/b0ba0a6167674227932bbeca1cc20e77"
COLUMN = "时政"


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


def article_text(response, title: str) -> str:
    parts = [node_text(node) for node in response.css("#bs_content p.formatted")]
    parts = [part for part in parts if part]
    if parts and parts[0] == title:
        parts = parts[1:]
    return clean(" ".join(parts)) or first_text(response, "#bs_content")


def text_item(response, project: str) -> dict[str, Any]:
    title = response.meta.get("title") or first_text(response, "h2.page_h2")
    publish_time = response.meta.get("publish_time") or clean(first_text(response, "ul.page_brief li:last-child")).replace(
        "时间：", ""
    )
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


class HinewsCnModuleB0ba0a6167674227932bbeca1cc20e77Spider(Spider):
    name = "hinews-cn-module-b0ba0a6167674227932bbeca1cc20e77"
    project_name = name
    allowed_domains = {"www.hinews.cn", "hinews.cn"}
    start_urls = [SOURCE_URL]
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
        yield Request(self.start_urls[0], sid="http", callback=self.parse, dont_filter=True)

    async def parse(self, response):
        for item in response.css("ul.l_list > li"):
            link = item.css("h3 a").first
            href = link.attrib.get("href") if link is not None else ""
            if not href:
                continue
            publish = clean(node_text(item.css("ul.brief_box li:last-child").first)).replace("来源：", "")
            yield Request(
                response.urljoin(href),
                sid="http",
                callback=self.parse_detail,
                meta={
                    "title": node_text(link),
                    "publish_time": clean(node_text(item.css("ul.brief_box li:first-child").first)).replace("发布时间：", ""),
                    "source": publish,
                },
            )

    async def parse_detail(self, response):
        yield text_item(response, self.project_name)


if __name__ == "__main__":
    for item in HinewsCnModuleB0ba0a6167674227932bbeca1cc20e77Spider().start().items:
        print(json.dumps(item, ensure_ascii=False))
