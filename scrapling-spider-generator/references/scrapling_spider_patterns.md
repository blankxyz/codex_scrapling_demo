# Scrapling Spider Patterns

## Session Pattern

Use `AsyncStealthySession` for protected dynamic pages:

```python
from scrapling.fetchers import AsyncStealthySession

def configure_sessions(self, manager) -> None:
    manager.add(
        "browser",
        AsyncStealthySession(
            capture_xhr="/common/search/",
            google_search=False,
            real_chrome=True,
            extra_headers={"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
            network_idle=False,
            wait=3000,
            timeout=60000,
            max_pages=2,
        ),
        default=True,
    )
```

Make `real_chrome` configurable only when useful:

```python
real_chrome = os.getenv("SCRAPLING_REAL_CHROME", "1") != "0"
```

Do not include `cdp_url` in generated production spiders.

## Text Helpers

Scrapling selectors expose `.first`, `.attrib`, and node `.get_all_text(...)`.
Do not use `response.doc(...)` unless the local project already wraps responses that way.

```python
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
```

## Mixed Detail-Type Detection

Do not hardcode a section as text-only from local sampling. Every generated spider should be able to inspect each detail page and decide whether it is a text article or a video page.

```python
def response_html(response) -> str:
    body = getattr(response, "body", b"") or b""
    if isinstance(body, bytes):
        return body.decode(getattr(response, "encoding", "utf-8") or "utf-8", errors="ignore")
    return str(body)


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
            return response.urljoin(clean_text(match.group(1)).replace("\\/", "/"))
    return ""


def resolve_detail_type(response) -> str:
    carried = clean_text(response.meta.get("content_type")).lower()
    if carried in {"video", "vod", "live"}:
        return "video"
    if "/video/" in response.url.lower():
        return "video"
    if extract_video_url(response):
        return "video"
    return "text"
```

## Captured XHR Parsing

```python
def extract_first_page_json(response) -> dict[str, Any] | None:
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
```

Use the fields found in analysis, for example:

```python
for row in data.get("data", {}).get("results", []) or []:
    detail_url = urljoin(self.base_url, row.get("url") or "")
    yield Request(
        detail_url,
        sid="browser",
        callback=self.parse_detail,
        meta={
            "title": clean_text(row.get("title")),
            "publish_time": clean_text(row.get("publishedTimeStr")),
            "column_name": row.get("channelName") or self.column_name,
        },
        wait_selector=".notice_content",
    )
```

## Output Item Patterns

Preserve the user's schema exactly. The key order is part of the schema. Do not add, remove, rename, or reorder fields. When a site has mixed text and video details, generate separate builders and branch in `parse_detail` with runtime detection from metadata, URL hints, and full-page media signals.

Use these exact key lists for the user's current YNTV-style spiders:

```python
TEXT_ITEM_KEYS = [
    "url",
    "project",
    "accountcode",
    "tbid",
    "spiderid",
    "author",
    "title",
    "publishdate",
    "publishtime",
    "spidertime",
    "content",
    "createtime",
    "type",
    "tags",
    "commentnum",
    "browsenum",
    "forwardnum",
    "likenum",
    "root_column_name",
    "column_name",
]

VIDEO_ITEM_KEYS = [
    "url",
    "project",
    "program_name",
    "content",
    "actor",
    "spider_time",
    "poster",
    "create_time",
    "publish_time",
    "director",
    "author",
    "source",
    "accountcode",
    "video_url",
    "root_column_name",
    "root_column_id",
    "column_id",
    "column_name",
    "program_id",
    "tags",
    "episode",
    "commentnum",
    "browsenum",
    "forwardnum",
    "likenum",
]
```

For text-message details:

```python
def make_text_item(response, project_name: str) -> dict[str, Any]:
    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
    return {
        "url": response.url,
        "project": project_name,
        "accountcode": "15_STWZ_YNTVCN_02_530000",
        "tbid": file_name_md5(response.url),
        "spiderid": project_name,
        "author": "",
        "title": response.meta.get("title") or first_text(response, "h1, h6"),
        "publishdate": response.meta.get("publish_time") or "",
        "publishtime": response.meta.get("publish_time") or "",
        "spidertime": now,
        "content": first_text(response, ".article, .notice_content") or all_text(response, "p"),
        "createtime": now,
        "type": "t_social_web",
        "tags": "textmessage",
        "commentnum": 0,
        "browsenum": 0,
        "forwardnum": 0,
        "likenum": 0,
        "root_column_name": response.meta.get("column_name") or "",
        "column_name": response.meta.get("column_name") or "",
    }
```

For video details:

```python
def extract_video_url(response) -> str:
    html = response_html(response)
    patterns = [
        r'"source"\s*:\s*"([^"]+)"',
        r'"mp4"\s*:\s*"([^"]+)"',
        r"source\s*:\s*'([^']+)'",
        r'<source[^>]+src=["\']([^"\']+)["\']',
        r'<video[^>]+src=["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.I | re.S)
        if match:
            return response.urljoin(clean_text(match.group(1)).replace("\\/", "/"))
    return ""


def make_video_item(response, project_name: str) -> dict[str, Any]:
    now = int(time.time())
    title = response.meta.get("title") or first_text(response, "h1, .text_title")
    column_name = response.meta.get("column_name") or ""
    return {
        "url": response.url,
        "project": project_name,
        "program_name": title,
        "content": title,
        "actor": "",
        "spider_time": now,
        "poster": response.meta.get("img") or response.meta.get("image") or "",
        "create_time": now,
        "publish_time": response.meta.get("publish_time") or "",
        "director": "",
        "author": "",
        "source": "吉祥网",
        "accountcode": "15_STWZ_YNTVCN_02_530000",
        "video_url": extract_video_url(response),
        "root_column_name": column_name,
        "root_column_id": "",
        "column_id": "",
        "column_name": column_name,
        "program_id": "",
        "tags": column_name,
        "episode": 1,
        "commentnum": 0,
        "browsenum": 0,
        "forwardnum": 0,
        "likenum": 0,
}
```

Use runtime branching in `parse_detail`:

```python
async def parse_detail(self, response):
    if resolve_detail_type(response) == "video":
        yield make_video_item(response, self.project_name)
    else:
        yield make_text_item(response, self.project_name)
```

Validate generated items with exact key order and constant/type checks:

```python
def validate_text_item_schema(item: dict[str, Any]) -> None:
    assert list(item.keys()) == TEXT_ITEM_KEYS
    assert item["accountcode"] == "15_STWZ_YNTVCN_02_530000"
    assert item["author"] == ""
    assert item["type"] == "t_social_web"
    assert item["tags"] == "textmessage"
    for key in ("commentnum", "browsenum", "forwardnum", "likenum"):
        assert item[key] == 0
    assert isinstance(item["spidertime"], str)
    assert isinstance(item["createtime"], str)


def validate_video_item_schema(item: dict[str, Any]) -> None:
    assert list(item.keys()) == VIDEO_ITEM_KEYS
    assert item["actor"] == ""
    assert item["director"] == ""
    assert item["author"] == ""
    assert item["source"] == "吉祥网"
    assert item["accountcode"] == "15_STWZ_YNTVCN_02_530000"
    assert item["root_column_id"] == ""
    assert item["column_id"] == ""
    assert item["program_id"] == ""
    assert item["episode"] == 1
    for key in ("commentnum", "browsenum", "forwardnum", "likenum"):
        assert item[key] == 0
    assert isinstance(item["spider_time"], int)
    assert isinstance(item["create_time"], int)
```

Branch detail output:

```python
async def parse_detail(self, response):
    content_type = (response.meta.get("content_type") or "").lower()
    if content_type == "video" or "/video/" in response.url:
        yield make_video_item(response, self.project_name)
        return
    yield make_text_item(response, self.project_name)
```

## Validation Notes

- `py_compile` catches syntax and import mistakes cheaply.
- If `AsyncDynamicSession` returns `400` while CDP/manual browser analysis works, use `AsyncStealthySession`.
- Successful validation should show list page `200`, captured API/XHR `200`, and detail page `200`.
