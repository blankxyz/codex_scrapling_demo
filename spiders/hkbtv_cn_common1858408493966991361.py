import hashlib
import html
import json
import re
import time
from typing import Any

from scrapling.fetchers import FetcherSession
from scrapling.parser import Selector
from scrapling.spiders import Request, Spider


ACCOUNT = "15_STWZ_YNTVCN_02_530000"
LIST_API = "https://hkbtv.cn/tv-station/api/article/list"
DETAIL_API = "https://hkbtv.cn/tv-station/api/details/article"
SECTIONS = [
    {"column_name": "要闻", "classify_code": "1858408493966991361"},
    {"column_name": "时政", "classify_code": "1858408519833264130"},
    {"column_name": "海南", "classify_code": "1858408574329856001"},
]


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def md5(value: str) -> str:
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def api_json(response) -> dict[str, Any]:
    try:
        return json.loads(response.body.decode("utf-8", errors="ignore"))
    except Exception:
        return {}


def content_text(value: str) -> str:
    doc = Selector(content=html.unescape(value or ""))
    parts = [clean(node.get_all_text(separator=" ", strip=True)) for node in doc.css("p")]
    parts = [part for part in parts if part]
    return clean(" ".join(parts)) or clean(doc.get_all_text(separator=" ", strip=True))


def text_item(data: dict[str, Any], meta: dict[str, Any], project: str) -> dict[str, Any]:
    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    url = meta["url"]
    root_column = clean(meta.get("root_column_name"))
    module = clean(meta.get("column_name")) or root_column
    return {
        "url": url,
        "project": project,
        "accountcode": ACCOUNT,
        "tbid": md5(url),
        "spiderid": project,
        "author": "",
        "title": clean(data.get("title")) or clean(meta.get("title")),
        "publishdate": clean(data.get("releaseTime")) or clean(meta.get("publish_time")),
        "publishtime": clean(data.get("releaseTime")) or clean(meta.get("publish_time")),
        "spidertime": now,
        "content": content_text(data.get("content", "")) or clean(data.get("summary")) or clean(meta.get("summary")),
        "createtime": now,
        "type": "t_social_web",
        "tags": "textmessage",
        "commentnum": 0,
        "browsenum": 0,
        "forwardnum": 0,
        "likenum": 0,
        "root_column_name": root_column,
        "column_name": module,
    }


class HkbtvCnCommon1858408493966991361Spider(Spider):
    name = "hkbtv-cn-common1858408493966991361"
    project_name = name
    allowed_domains = {"hkbtv.cn"}
    concurrent_requests = 4
    download_delay = 0.1

    def configure_sessions(self, manager) -> None:
        manager.add(
            "api",
            FetcherSession(
                timeout=30,
                headers={
                    "Accept": "application/json, text/plain, */*",
                    "Content-Type": "application/json;charset=UTF-8",
                    "operator-type": "4",
                    "Referer": "",
                },
            ),
            default=True,
        )

    async def start_requests(self):
        yield self.section_request(0)

    def section_request(self, index: int) -> Request:
        section = SECTIONS[index]
        return Request(
            LIST_API,
            sid="api",
            callback=self.parse,
            dont_filter=True,
            method="POST",
            json={
                "page": 1,
                "limit": 20,
                "publishingPath": 3,
                "classifyCode": section["classify_code"],
                "classifyLevel": 1,
            },
            meta={**section, "section_index": index},
        )

    async def parse(self, response):
        index = int(response.meta.get("section_index", 0))
        root_column = clean(response.meta.get("column_name"))
        seen = set()
        for record in api_json(response).get("data", {}).get("records", []) or []:
            module = clean(record.get("newsColumnName")) or clean(record.get("locationType")) or "文章"
            for article in record.get("articles") or []:
                article_id = clean(article.get("articleId"))
                article_type = article.get("articleType", 0)
                if not article_id or article_id in seen:
                    continue
                seen.add(article_id)
                yield Request(
                    DETAIL_API,
                    sid="api",
                    callback=self.parse_detail,
                    dont_filter=True,
                    method="POST",
                    json={"articleId": article_id, "articleType": str(article_type)},
                    meta={
                        "url": f"https://hkbtv.cn/#/article?type=article&id={article_id}&articleType={article_type}",
                        "title": clean(article.get("title")),
                        "publish_time": clean(article.get("releaseTime")),
                        "summary": clean(article.get("summary")),
                        "root_column_name": root_column,
                        "column_name": module,
                        "article_id": article_id,
                        "article_type": article_type,
                        "image": clean(article.get("coverMapAddress")),
                        "source": clean(article.get("sourceArticle")),
                    },
                )
        if index + 1 < len(SECTIONS):
            yield self.section_request(index + 1)

    async def parse_detail(self, response):
        data = api_json(response).get("data") or {}
        yield text_item(data, response.meta, self.project_name)


if __name__ == "__main__":
    for item in HkbtvCnCommon1858408493966991361Spider().start().items:
        print(json.dumps(item, ensure_ascii=False))
