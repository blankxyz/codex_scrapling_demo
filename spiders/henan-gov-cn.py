from __future__ import annotations

import logging
import json
import re
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
from scrapling.fetchers import DynamicFetcher, Fetcher

logger = logging.getLogger(__name__)


class HenanGovCnSpider:
    SITE_NAME = "河南省广播电视局"
    LIST_URL = "https://gd.henan.gov.cn/sy/tz/"

    # Confirmed selector first, then marker fallbacks.
    LIST_LINK_SELECTORS = [
        "#articleList > div.col-xs-12.col-sm-12 > div.articleList_listBox a",
        "#articleList > div.col-xs-12.col-sm-12 > div.articleList_listBox > div.article_List a",
        "#articleList a",
        "#navDownBox a",
    ]

    TITLE_SELECTORS = [
        "#article_header h3",
        "h1",
        "meta[name='ArticleTitle']",
        "title",
    ]

    TIME_SELECTORS = [
        "#article_header p.text-center span",
        "meta[name='PubDate']",
        "meta[name='lastmodifiedtime']",
    ]

    CONTENT_SELECTORS = [
        "#article_body",
        ".article_body",
        ".TRS_Editor",
        "article",
    ]

    SOURCE_SELECTORS = [
        "meta[name='ContentSource']",
    ]

    AUTHOR_SELECTORS = [
        "meta[name='Author']",
    ]

    ATTACHMENT_PATTERN = re.compile(r"\.(pdf|doc|docx|xls|xlsx|zip|rar|txt)$", re.I)
    ARTICLE_URL_PATTERN = re.compile(r"/\d{4}/\d{2}-\d{2}/\d+\.html(?:$|[?#])")
    DATE_PATTERN = re.compile(r"(20\d{2}[-/.年]\s*\d{1,2}[-/.月]\s*\d{1,2}(?:\s*\d{1,2}:\d{2}(?::\d{2})?)?)")
    REQUIRED_FIELDS = ["url", "title", "publish_time", "content_html", "content_text", "source"]

    @classmethod
    def _normalize_url(cls, href: str, base_url: str) -> str:
        abs_url = urljoin(base_url, href.strip())
        parsed = urlparse(abs_url)
        if not parsed.scheme or not parsed.netloc:
            return ""

        # Scrapling static fetch may reject some http redirect chains; prefer https on target host.
        if parsed.netloc.endswith("gd.henan.gov.cn") and parsed.scheme == "http":
            parsed = parsed._replace(scheme="https")
            return urlunparse(parsed)
        return abs_url

    @classmethod
    def _clean_text(cls, value: str) -> str:
        return re.sub(r"\s+", " ", value or "").strip()

    @classmethod
    def _fetch_html(cls, url: str, dynamic: bool = False) -> str:
        if dynamic:
            page = DynamicFetcher.fetch(url, headless=True, network_idle=True)
            engine = "DynamicFetcher"
        else:
            page = Fetcher.get(url, impersonate="chrome")
            engine = "Fetcher"

        html = getattr(page, "text", None) or getattr(page, "body", b"")
        if isinstance(html, bytes):
            html = html.decode("utf-8", errors="ignore")
        logger.info("Fetched URL via %s: %s", engine, url)
        return html

    @classmethod
    def _extract_page_count(cls, html: str) -> int:
        soup = BeautifulSoup(html, "lxml")
        node = soup.select_one("#pageDec[pagecount]")
        if not node:
            return 1
        raw = (node.get("pagecount") or "").strip()
        if raw.isdigit():
            return max(1, int(raw))
        return 1

    @classmethod
    def _build_page_url(cls, page_num: int) -> str:
        if page_num <= 1:
            return cls.LIST_URL
        return urljoin(cls.LIST_URL, f"index_{page_num}.html")

    @classmethod
    def _validate_required_fields(cls, item: dict[str, Any]) -> None:
        for field in cls.REQUIRED_FIELDS:
            value = item.get(field, "")
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"missing required field: {field}")

    @classmethod
    def _collect_full_list_links(cls, dynamic: bool = False) -> list[str]:
        first_html = cls._fetch_html(cls.LIST_URL, dynamic=dynamic)
        page_count = cls._extract_page_count(first_html)
        logger.info("Detected list page count: %d", page_count)

        seen: set[str] = set()
        links: list[str] = []
        first_page_links = cls.parse_list_html(first_html, base_url=cls.LIST_URL)
        for link in first_page_links:
            if link not in seen:
                seen.add(link)
                links.append(link)

        for page_num in range(2, page_count + 1):
            page_url = cls._build_page_url(page_num)
            try:
                html = cls._fetch_html(page_url, dynamic=dynamic)
            except Exception:
                # Fallback for sites that use `/N.html` naming on deep pages.
                fallback_url = urljoin(cls.LIST_URL, f"{page_num}.html")
                html = cls._fetch_html(fallback_url, dynamic=dynamic)
                page_url = fallback_url

            page_links = cls.parse_list_html(html, base_url=page_url)
            for link in page_links:
                if link not in seen:
                    seen.add(link)
                    links.append(link)

        logger.info("Collected total unique detail links: %d", len(links))
        return links

    @classmethod
    def parse_list_html(cls, html: str, base_url: str | None = None) -> list[str]:
        base = base_url or cls.LIST_URL
        soup = BeautifulSoup(html, "lxml")
        links: list[str] = []
        seen: set[str] = set()

        for selector in cls.LIST_LINK_SELECTORS:
            nodes = soup.select(selector)
            for node in nodes:
                if node.name == "a":
                    anchors = [node]
                else:
                    anchors = node.select("a[href]")

                for a in anchors:
                    href = a.get("href", "")
                    normalized = cls._normalize_url(href, base)
                    if not normalized:
                        continue
                    parsed = urlparse(normalized)
                    if not parsed.netloc.endswith("gd.henan.gov.cn"):
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
            logger.warning("No article links extracted from list page")
        return links

    @classmethod
    def parse_list_page(cls, url: str | None = None, dynamic: bool = False) -> list[str]:
        list_url = url or cls.LIST_URL
        html = cls._fetch_html(list_url, dynamic=dynamic)
        return cls.parse_list_html(html, base_url=list_url)

    @classmethod
    def _get_first_text(cls, soup: BeautifulSoup, selectors: list[str], from_meta: bool = False) -> str:
        for selector in selectors:
            node = soup.select_one(selector)
            if not node:
                continue
            if from_meta and node.name == "meta":
                value = cls._clean_text(node.get("content", ""))
            else:
                value = cls._clean_text(node.get_text(" ", strip=True))
            if value:
                return value
        return ""

    @classmethod
    def _extract_publish_time(cls, soup: BeautifulSoup) -> str:
        for selector in cls.TIME_SELECTORS:
            for node in soup.select(selector):
                raw = node.get("content", "") if node.name == "meta" else node.get_text(" ", strip=True)
                raw = cls._clean_text(raw)
                if not raw:
                    continue
                match = cls.DATE_PATTERN.search(raw)
                if match:
                    value = match.group(1)
                    value = value.replace("年", "-").replace("月", "-").replace("日", "")
                    value = re.sub(r"\s+", " ", value).strip()
                    return value
                if re.search(r"\d{4}-\d{2}-\d{2}", raw):
                    return raw
        return ""

    @classmethod
    def _extract_content(cls, soup: BeautifulSoup) -> tuple[str, str, list[str], list[str]]:
        for selector in cls.CONTENT_SELECTORS:
            node = soup.select_one(selector)
            if not node:
                continue

            content_html = str(node)
            content_text = cls._clean_text(node.get_text(" ", strip=True))

            images: list[str] = []
            for img in node.select("img[src]"):
                src = cls._normalize_url(img.get("src", ""), cls.LIST_URL)
                if src and src not in images:
                    images.append(src)

            attachments: list[str] = []
            for a in node.select("a[href]"):
                href = cls._normalize_url(a.get("href", ""), cls.LIST_URL)
                if href and cls.ATTACHMENT_PATTERN.search(href) and href not in attachments:
                    attachments.append(href)

            if not content_text and images:
                alts = [cls._clean_text((img.get("alt") or img.get("title") or "")) for img in node.select("img")]
                alts = [x for x in alts if x]
                content_text = " ".join(alts)

            return content_html, content_text, images, attachments

        return "", "", [], []

    @classmethod
    def parse_detail_html(cls, html: str, url: str) -> dict[str, Any]:
        soup = BeautifulSoup(html, "lxml")

        title = cls._get_first_text(soup, cls.TITLE_SELECTORS, from_meta=True)
        if title and title.endswith("_河南省广播电视局"):
            title = title.replace("_河南省广播电视局", "").strip()

        publish_time = cls._extract_publish_time(soup)
        content_html, content_text, images, attachments = cls._extract_content(soup)

        source = cls._get_first_text(soup, cls.SOURCE_SELECTORS, from_meta=True) or cls.SITE_NAME
        author = cls._get_first_text(soup, cls.AUTHOR_SELECTORS, from_meta=True)

        # Keep schema-required content_text non-empty for image-only notices.
        if not content_text:
            desc_meta = soup.select_one("meta[name='Description']")
            if desc_meta:
                content_text = cls._clean_text(desc_meta.get("content", ""))

        if not publish_time:
            pub_meta = soup.select_one("meta[name='PubDate']")
            if pub_meta:
                publish_time = cls._clean_text(pub_meta.get("content", ""))

        result = {
            "url": url,
            "title": title,
            "publish_time": publish_time,
            "content_html": content_html,
            "content_text": content_text,
            "source": source,
            "author": author,
            "images": images,
            "attachments": attachments,
        }
        logger.info("Parsed detail fields: title=%s, publish_time=%s", bool(title), bool(publish_time))
        return result

    @classmethod
    def parse_detail_page(cls, url: str, dynamic: bool = False) -> dict[str, Any]:
        html = cls._fetch_html(url, dynamic=dynamic)
        return cls.parse_detail_html(html, url=url)

    @classmethod
    def crawl_all(cls, dynamic: bool = False) -> dict[str, Any]:
        links = cls._collect_full_list_links(dynamic=dynamic)
        items: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []

        for index, url in enumerate(links, start=1):
            try:
                item = cls.parse_detail_page(url, dynamic=dynamic)
                cls._validate_required_fields(item)
                items.append(item)
                logger.info("Parsed detail %d/%d: %s", index, len(links), url)
            except Exception as exc:
                logger.exception("Failed parsing detail %s", url)
                errors.append({"url": url, "error": str(exc)})

        return {
            "site_slug": "henan-gov-cn",
            "list_url": cls.LIST_URL,
            "total_links": len(links),
            "success_count": len(items),
            "error_count": len(errors),
            "items": items,
            "errors": errors,
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = HenanGovCnSpider.crawl_all(dynamic=False)
    output_path = "out/henan-gov-cn/crawl_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"total_links={result['total_links']}")
    print(f"success_count={result['success_count']}")
    print(f"error_count={result['error_count']}")
    print(f"output_file={output_path}")
