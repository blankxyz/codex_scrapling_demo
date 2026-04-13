from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPIDER_PATH = ROOT / "spiders" / "henan-gov-cn.py"
LIST_FIXTURE = ROOT / "tests" / "fixtures" / "henan-gov-cn_list_sample.html"
DETAIL_FIXTURE = ROOT / "tests" / "fixtures" / "henan-gov-cn_detail_sample.html"


def _load_spider_class():
    spec = importlib.util.spec_from_file_location("henan_gov_cn_spider", SPIDER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module.HenanGovCnSpider


def test_parse_list_html_extracts_article_links_from_confirmed_selector() -> None:
    spider_cls = _load_spider_class()
    html = LIST_FIXTURE.read_text(encoding="utf-8")

    links = spider_cls.parse_list_html(html, base_url="https://gd.henan.gov.cn/sy/tz/")

    assert links, "list parser should extract article links"
    assert all(link.startswith("https://gd.henan.gov.cn/") for link in links)
    assert any(link.endswith("/2025/12-02/3269560.html") for link in links)


def test_parse_detail_html_outputs_schema_required_fields() -> None:
    spider_cls = _load_spider_class()
    html = DETAIL_FIXTURE.read_text(encoding="utf-8")
    url = "https://gd.henan.gov.cn/2025/12-02/3269560.html"

    item = spider_cls.parse_detail_html(html, url=url)

    required_fields = ["url", "title", "publish_time", "content_html", "content_text", "source"]
    for field in required_fields:
        assert field in item
        assert isinstance(item[field], str)
        assert item[field].strip(), f"{field} should not be empty"

    assert item["title"] == "严正声明"
    assert "2025-12-02" in item["publish_time"]
    assert isinstance(item["images"], list)
    assert len(item["images"]) >= 1
    assert isinstance(item["attachments"], list)


def test_extract_page_count_from_list_fixture() -> None:
    spider_cls = _load_spider_class()
    html = LIST_FIXTURE.read_text(encoding="utf-8")

    page_count = spider_cls._extract_page_count(html)

    assert page_count == 39


def test_build_page_url_matches_expected_pattern() -> None:
    spider_cls = _load_spider_class()

    assert spider_cls._build_page_url(1) == "https://gd.henan.gov.cn/sy/tz/"
    assert spider_cls._build_page_url(2) == "https://gd.henan.gov.cn/sy/tz/index_2.html"


def test_validate_required_fields_raises_on_empty_value() -> None:
    spider_cls = _load_spider_class()
    bad_item = {
        "url": "https://gd.henan.gov.cn/2025/12-02/3269560.html",
        "title": "严正声明",
        "publish_time": "",
        "content_html": "<div>ok</div>",
        "content_text": "ok",
        "source": "省局",
    }

    try:
        spider_cls._validate_required_fields(bad_item)
        raised = False
    except ValueError:
        raised = True

    assert raised, "validator should reject empty required fields"
