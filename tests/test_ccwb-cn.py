from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPIDER_PATH = ROOT / "spiders" / "ccwb-cn.py"
LIST_FIXTURE = ROOT / "tests" / "fixtures" / "ccwb-cn_list_sample.html"
DETAIL_FIXTURE = ROOT / "tests" / "fixtures" / "ccwb-cn_detail_sample.html"


def _load_spider_class():
    spec = importlib.util.spec_from_file_location("ccwb_cn_spider", SPIDER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module.CcwbCnSpider


def test_parse_list_html_uses_marker_primary_selector() -> None:
    spider_cls = _load_spider_class()
    html = LIST_FIXTURE.read_text(encoding="utf-8")

    links = spider_cls.parse_list_html(html, base_url="https://www.ccwb.cn/col459.html")

    assert len(links) == 3
    assert all(link.startswith("https://www.ccwb.cn/content/") for link in links)
    assert "https://www.ccwb.cn/content/202604/13/c868395.html" in links


def test_extract_list_page_urls_detects_pagination() -> None:
    spider_cls = _load_spider_class()
    html = LIST_FIXTURE.read_text(encoding="utf-8")

    pages = spider_cls._extract_list_page_urls(html, base_url="https://www.ccwb.cn/col459.html")

    assert "https://www.ccwb.cn/col459.html" in pages
    assert "https://www.ccwb.cn/col459_2.html" in pages


def test_parse_detail_html_outputs_schema_required_fields() -> None:
    spider_cls = _load_spider_class()
    html = DETAIL_FIXTURE.read_text(encoding="utf-8")
    url = "https://www.ccwb.cn/content/202604/13/c868387.html"

    item = spider_cls.parse_detail_html(html, url=url)

    required_fields = ["url", "title", "publish_time", "content_html", "content_text", "source"]
    for field in required_fields:
        assert field in item
        assert isinstance(item[field], str)
        assert item[field].strip(), f"{field} should not be empty"

    assert item["title"].startswith("“走出一条中国特色城市现代化新路子”")
    assert item["publish_time"] == "2026-04-13 15:22:28"
    assert item["source"] == "人民日报"
    assert len(item["images"]) == 1
    assert item["images"][0].startswith("https://www.ccwb.cn/images/")
    assert len(item["attachments"]) == 1
    assert item["attachments"][0].endswith("/files/notice.pdf")


def test_validate_required_fields_raises_on_missing_value() -> None:
    spider_cls = _load_spider_class()
    bad_item = {
        "url": "https://www.ccwb.cn/content/202604/13/c868387.html",
        "title": "测试标题",
        "publish_time": "",
        "content_html": "<div>ok</div>",
        "content_text": "ok",
        "source": "测试来源",
    }

    try:
        spider_cls._validate_required_fields(bad_item)
        raised = False
    except ValueError:
        raised = True

    assert raised, "validator should reject missing required fields"
