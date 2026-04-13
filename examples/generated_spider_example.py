from __future__ import annotations

from scrapling.fetchers import Fetcher, DynamicFetcher


class ExampleNewsSpider:
    TITLE_SELECTORS = [
        "h1::text",
        ".article-title::text",
        ".content_title::text",
    ]
    TIME_SELECTORS = [
        "time::text",
        ".pubtime::text",
        ".date::text",
    ]
    CONTENT_SELECTORS = [
        "article",
        ".article-content",
        ".TRS_Editor",
    ]

    @staticmethod
    def _first_text(page, selectors: list[str]) -> str:
        for selector in selectors:
            value = page.css(selector).get()
            if value:
                return str(value).strip()
        return ""

    @staticmethod
    def _first_html(page, selectors: list[str]) -> str:
        for selector in selectors:
            nodes = page.css(selector)
            if nodes:
                return nodes[0].get()
        return ""

    @classmethod
    def parse_detail(cls, url: str, dynamic: bool = False) -> dict:
        if dynamic:
            page = DynamicFetcher.fetch(url, headless=True, network_idle=True)
        else:
            page = Fetcher.get(url, impersonate="chrome")

        title = cls._first_text(page, cls.TITLE_SELECTORS)
        publish_time = cls._first_text(page, cls.TIME_SELECTORS)
        content_html = cls._first_html(page, cls.CONTENT_SELECTORS)
        content_text = " ".join(page.css(f"{cls.CONTENT_SELECTORS[0]} ::text").getall()).strip()

        return {
            "url": url,
            "title": title,
            "publish_time": publish_time,
            "content_html": content_html,
            "content_text": content_text,
            "source": url,
            "author": "",
            "images": [],
            "attachments": [],
        }
