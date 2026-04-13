from __future__ import annotations

import html as html_lib
import json
import logging
import os
import re
from contextlib import contextmanager
from typing import Any
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

from scrapling.fetchers import DynamicFetcher, Fetcher
from scrapling.parser import Adaptor, Selector

logger = logging.getLogger(__name__)


class YntvCnSpider:
    SITE_SLUG = "yntv-cn"
    SITE_NAME = "云南广播电视台"
    LIST_URL = "https://mmr.yntv.cn/mmr/tplby.html?sectionid=89&page=1"
    REQUIRES_DYNAMIC = True

    # Marker primary selector first, then robust fallbacks.
    LIST_LINK_SELECTORS = [
        "#page_list_video > div.special_section2.row a",
        "#page_list_video a",
        "#page_list_video li a",
        ".page_list_video a",
        "a[href*='/video/']",
    ]

    TITLE_SELECTORS = [
        "h1",
        ".video-title",
        ".article-title",
        "meta[property='og:title']",
        "meta[name='Title']",
        "title",
    ]

    TIME_SELECTORS = [
        ".video-info .time",
        ".article-info .time",
        ".publish-time",
        "time",
        "meta[property='article:published_time']",
        "meta[name='publishdate']",
        "meta[name='PubDate']",
    ]

    CONTENT_SELECTORS = [
        ".video-intro",
        ".article-content",
        ".TRS_Editor",
        "#content",
        "article",
        ".content",
        "body",
    ]

    SOURCE_SELECTORS = [
        ".source",
        ".video-source",
        "meta[name='source']",
    ]

    AUTHOR_SELECTORS = [
        ".author",
        "meta[name='author']",
    ]

    REQUIRED_FIELDS = ["url", "title", "publish_time", "content_html", "content_text", "source"]
    ARTICLE_URL_PATTERN = re.compile(r"/video/\d{8}/\d+\.html(?:$|[?#])", re.I)
    LIST_URL_PATH_PATTERN = re.compile(r"/mmr/tplby\.html$", re.I)
    DATE_PATTERN = re.compile(
        r"(20\d{2}[-/.年]\s*\d{1,2}[-/.月]\s*\d{1,2}(?:[日\s]+\d{1,2}:\d{2}(?::\d{2})?)?)"
    )
    ATTACHMENT_PATTERN = re.compile(r"\.(pdf|doc|docx|xls|xlsx|zip|rar|txt)(?:$|[?#])", re.I)

    @classmethod
    @contextmanager
    def _without_proxy_env(cls):
        proxy_keys = [
            "http_proxy",
            "https_proxy",
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "all_proxy",
            "ALL_PROXY",
        ]
        backups = {k: os.environ.get(k) for k in proxy_keys}
        for key in proxy_keys:
            os.environ.pop(key, None)
        try:
            yield
        finally:
            for key, value in backups.items():
                if value is not None:
                    os.environ[key] = value

    @classmethod
    def _clean_text(cls, value: str) -> str:
        return re.sub(r"\s+", " ", value or "").strip()

    @classmethod
    def _normalize_url(cls, href: str, base_url: str) -> str:
        if not href:
            return ""
        abs_url = urljoin(base_url, href.strip())
        parsed = urlparse(abs_url)
        if not parsed.scheme or not parsed.netloc:
            return ""
        if parsed.netloc.endswith("yntv.cn") and parsed.scheme == "http":
            parsed = parsed._replace(scheme="https")
            return urlunparse(parsed)
        return abs_url

    @classmethod
    def _fetch_html(cls, url: str, dynamic: bool | None = None) -> str:
        use_dynamic = cls.REQUIRES_DYNAMIC if dynamic is None else dynamic
        with cls._without_proxy_env():
            if use_dynamic:
                try:
                    page = DynamicFetcher.fetch(url, headless=True, network_idle=True)
                    engine = "DynamicFetcher"
                except Exception as exc:
                    logger.warning(
                        "DynamicFetcher failed, fallback to Fetcher for %s: %s",
                        url,
                        exc,
                    )
                    page = Fetcher.get(url, impersonate="chrome")
                    engine = "Fetcher(fallback)"
            else:
                page = Fetcher.get(url, impersonate="chrome")
                engine = "Fetcher"

        html = getattr(page, "text", None) or getattr(page, "body", b"")
        if isinstance(html, bytes):
            html = html.decode("utf-8", errors="ignore")
        logger.info("Fetched URL via %s: %s", engine, url)
        return html

    @classmethod
    def _validate_required_fields(cls, item: dict[str, Any]) -> None:
        for field in cls.REQUIRED_FIELDS:
            value = item.get(field, "")
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"missing required field: {field}")

    @classmethod
    def _normalize_time(cls, raw: str) -> str:
        value = cls._clean_text(raw)
        value = value.replace("年", "-").replace("月", "-").replace("日", " ")
        value = value.replace("/", "-").replace(".", "-")
        value = re.sub(r"\s+", " ", value).strip()
        return value

    @classmethod
    def _parse_source_and_time_meta(cls, doc: Adaptor) -> tuple[str, str]:
        text = cls._clean_text(doc.get_all_text())
        source = ""
        publish_time = ""

        source_match = re.search(r"来源[:：]\s*([^\s|｜]+)", text)
        if source_match:
            source = cls._clean_text(source_match.group(1))

        time_match = cls.DATE_PATTERN.search(text)
        if time_match:
            publish_time = cls._normalize_time(time_match.group(1))

        return source, publish_time

    @classmethod
    def _get_first_text(cls, doc: Adaptor, selectors: list[str], from_meta: bool = False) -> str:
        for selector in selectors:
            nodes = doc.css(selector)
            if not nodes:
                continue
            node = nodes[0]
            if from_meta and node.tag == "meta":
                value = cls._clean_text(node.attrib.get("content", ""))
            else:
                value = cls._clean_text(node.get_all_text())
            if value:
                return value
        return ""

    @classmethod
    def _extract_publish_time(cls, doc: Adaptor) -> str:
        for selector in cls.TIME_SELECTORS:
            for node in doc.css(selector):
                raw = node.attrib.get("content", "") if node.tag == "meta" else node.get_all_text()
                raw = cls._clean_text(raw)
                if not raw:
                    continue
                match = cls.DATE_PATTERN.search(raw)
                if match:
                    return cls._normalize_time(match.group(1))
                if re.search(r"20\d{2}-\d{1,2}-\d{1,2}", raw):
                    return cls._normalize_time(raw)

        _, publish_time = cls._parse_source_and_time_meta(doc)
        return publish_time

    @classmethod
    def _extract_content(cls, doc: Adaptor, url: str) -> tuple[str, str, list[str], list[str]]:
        for selector in cls.CONTENT_SELECTORS:
            nodes = doc.css(selector)
            if not nodes:
                continue
            node = nodes[0]

            content_html = node.get()
            content_text = cls._clean_text(node.get_all_text())

            images: list[str] = []
            for img in node.css("img[src]"):
                src = cls._normalize_url(img.attrib.get("src", ""), url)
                if src and src not in images:
                    images.append(src)

            attachments: list[str] = []
            for a in node.css("a[href]"):
                href = cls._normalize_url(a.attrib.get("href", ""), url)
                if href and cls.ATTACHMENT_PATTERN.search(href) and href not in attachments:
                    attachments.append(href)

            if content_text:
                return content_html, content_text, images, attachments

        return "", "", [], []

    @classmethod
    def parse_list_html(cls, html: str, base_url: str | None = None) -> list[str]:
        doc = Adaptor(html, url=base_url or cls.LIST_URL)
        base = base_url or cls.LIST_URL
        links: list[str] = []
        seen: set[str] = set()

        for selector in cls.LIST_LINK_SELECTORS:
            nodes = doc.css(selector)
            for node in nodes:
                anchors: list[Selector] = [node] if node.tag == "a" else list(node.css("a[href]"))
                for anchor in anchors:
                    href = anchor.attrib.get("href", "")
                    normalized = cls._normalize_url(href, base)
                    if not normalized:
                        continue
                    parsed = urlparse(normalized)
                    if not parsed.netloc.endswith("yntv.cn"):
                        continue
                    if not cls.ARTICLE_URL_PATTERN.search(parsed.path):
                        continue
                    if normalized in seen:
                        continue
                    seen.add(normalized)
                    links.append(normalized)

            if links:
                logger.info("List selector matched: %s (%d links)", selector, len(links))
                break

        if not links:
            logger.warning("No links extracted from list page %s", base)
        return links

    @classmethod
    def _extract_list_page_urls(cls, html: str, base_url: str) -> list[str]:
        doc = Adaptor(html, url=base_url)
        page_urls: list[str] = []
        seen: set[str] = set()

        for a in doc.css("a[href]"):
            href = a.attrib.get("href", "")
            url = cls._normalize_url(href, base_url)
            if not url:
                continue
            parsed = urlparse(url)
            if parsed.netloc != "mmr.yntv.cn":
                continue
            if not cls.LIST_URL_PATH_PATTERN.search(parsed.path):
                continue
            query = parse_qs(parsed.query)
            if query.get("sectionid", [""])[0] != "89":
                continue
            page_value = query.get("page", [""])[0]
            if page_value and not page_value.isdigit():
                continue
            normalized_query = urlencode({"sectionid": "89", "page": page_value or "1"})
            normalized_page = urlunparse(parsed._replace(query=normalized_query, fragment=""))
            if normalized_page in seen:
                continue
            seen.add(normalized_page)
            page_urls.append(normalized_page)

        if cls.LIST_URL not in seen:
            page_urls.insert(0, cls.LIST_URL)
        return page_urls

    @classmethod
    def parse_list_page(cls, url: str | None = None, dynamic: bool | None = None) -> list[str]:
        list_url = url or cls.LIST_URL
        html = cls._fetch_html(list_url, dynamic=dynamic)
        links = cls.parse_list_html(html, base_url=list_url)
        use_dynamic = cls.REQUIRES_DYNAMIC if dynamic is None else dynamic
        if links or use_dynamic:
            return links

        logger.info("Retry list page with DynamicFetcher because static parse returned no links: %s", list_url)
        html = cls._fetch_html(list_url, dynamic=True)
        return cls.parse_list_html(html, base_url=list_url)

    @classmethod
    def parse_detail_html(cls, html: str, url: str) -> dict[str, Any]:
        doc = Adaptor(html, url=url)

        title = cls._get_first_text(doc, cls.TITLE_SELECTORS, from_meta=True)
        if title and "|" in title:
            title = cls._clean_text(title.split("|")[0])

        publish_time = cls._extract_publish_time(doc)
        content_html, content_text, images, attachments = cls._extract_content(doc, url=url)

        source = cls._get_first_text(doc, cls.SOURCE_SELECTORS, from_meta=True)
        if source:
            source = re.sub(r"^来源[:：]\s*", "", source).strip()
        if not source or len(source) > 50:
            parsed_source, parsed_time = cls._parse_source_and_time_meta(doc)
            source = parsed_source or cls.SITE_NAME
            if not publish_time:
                publish_time = parsed_time

        author = cls._get_first_text(doc, cls.AUTHOR_SELECTORS, from_meta=True)
        if not content_text:
            desc_nodes = doc.css("meta[name='description']")
            if desc_nodes:
                content_text = cls._clean_text(desc_nodes[0].attrib.get("content", ""))
        if not content_html and content_text:
            content_html = f"<p>{html_lib.escape(content_text)}</p>"

        return {
            "url": url,
            "title": title,
            "publish_time": publish_time,
            "content_html": content_html,
            "content_text": content_text,
            "source": source or cls.SITE_NAME,
            "author": author,
            "images": images,
            "attachments": attachments,
        }

    @classmethod
    def parse_detail_page(cls, url: str, dynamic: bool | None = None) -> dict[str, Any]:
        html = cls._fetch_html(url, dynamic=dynamic)
        item = cls.parse_detail_html(html, url=url)
        use_dynamic = cls.REQUIRES_DYNAMIC if dynamic is None else dynamic
        if (item.get("title") and item.get("content_text")) or use_dynamic:
            return item

        logger.info("Retry detail page with DynamicFetcher because static parse looked incomplete: %s", url)
        html = cls._fetch_html(url, dynamic=True)
        return cls.parse_detail_html(html, url=url)

    @classmethod
    def _collect_full_list_links(cls, dynamic: bool | None = None) -> list[str]:
        seen_pages: set[str] = set()
        pending_pages: list[str] = [cls.LIST_URL]
        links: list[str] = []
        link_seen: set[str] = set()

        while pending_pages:
            page_url = pending_pages.pop(0)
            if page_url in seen_pages:
                continue
            seen_pages.add(page_url)

            html = cls._fetch_html(page_url, dynamic=dynamic)

            page_links = cls.parse_list_html(html, base_url=page_url)
            for link in page_links:
                if link not in link_seen:
                    link_seen.add(link)
                    links.append(link)

            list_pages = cls._extract_list_page_urls(html, base_url=page_url)
            for list_page in list_pages:
                if list_page not in seen_pages and list_page not in pending_pages:
                    pending_pages.append(list_page)

        logger.info("Collected list pages=%d, links=%d", len(seen_pages), len(links))
        return links

    @classmethod
    def crawl_all(cls, dynamic: bool | None = None) -> dict[str, Any]:
        errors: list[dict[str, str]] = []
        items: list[dict[str, Any]] = []
        use_dynamic = cls.REQUIRES_DYNAMIC if dynamic is None else dynamic

        try:
            links = cls._collect_full_list_links(dynamic=use_dynamic)
            if not links and not use_dynamic:
                logger.info("Retry crawl link collection with DynamicFetcher due to empty static result")
                links = cls._collect_full_list_links(dynamic=True)
        except Exception as exc:
            logger.exception("Failed collecting list links")
            return {
                "site_slug": cls.SITE_SLUG,
                "list_url": cls.LIST_URL,
                "total_links": 0,
                "success_count": 0,
                "error_count": 1,
                "items": [],
                "errors": [{"url": cls.LIST_URL, "error": f"collect_links_failed: {exc}"}],
            }

        for idx, url in enumerate(links, start=1):
            try:
                item = cls.parse_detail_page(url, dynamic=use_dynamic)
                cls._validate_required_fields(item)
                items.append(item)
                logger.info("Parsed %d/%d: %s", idx, len(links), url)
            except Exception as exc:
                logger.exception("Failed parsing detail page: %s", url)
                errors.append({"url": url, "error": str(exc)})

        return {
            "site_slug": cls.SITE_SLUG,
            "list_url": cls.LIST_URL,
            "total_links": len(links),
            "success_count": len(items),
            "error_count": len(errors),
            "items": items,
            "errors": errors,
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = YntvCnSpider.crawl_all(dynamic=True)
    output_path = "out/yntv-cn/crawl_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"total_links={result['total_links']}")
    print(f"success_count={result['success_count']}")
    print(f"error_count={result['error_count']}")
    print(f"output_file={output_path}")
