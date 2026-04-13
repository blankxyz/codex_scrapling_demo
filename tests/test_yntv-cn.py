from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPIDER_PATH = ROOT / "spiders" / "yntv-cn.py"
LIST_FIXTURE = ROOT / "tests" / "fixtures" / "yntv-cn_list_sample.html"
DETAIL_FIXTURE = ROOT / "tests" / "fixtures" / "yntv-cn_detail_sample.html"


def _load_spider_class():
    spec = importlib.util.spec_from_file_location("yntv_cn_spider", SPIDER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module.YntvCnSpider


def test_parse_list_html_uses_marker_primary_selector() -> None:
    spider_cls = _load_spider_class()
    html = LIST_FIXTURE.read_text(encoding="utf-8")

    assert spider_cls.REQUIRES_DYNAMIC is True
    assert spider_cls.LIST_LINK_SELECTORS[0] == "#page_list_video > div.special_section2.row a"

    links = spider_cls.parse_list_html(html, base_url="https://mmr.yntv.cn/mmr/tplby.html?sectionid=89&page=1")

    assert len(links) == 2
    assert "https://www.yntv.cn/video/20250702/1751425471742822.html" in links
    assert "https://www.yntv.cn/video/20250702/1751425471742999.html" in links


def test_extract_list_page_urls_detects_pagination() -> None:
    spider_cls = _load_spider_class()
    html = LIST_FIXTURE.read_text(encoding="utf-8")

    pages = spider_cls._extract_list_page_urls(
        html,
        base_url="https://mmr.yntv.cn/mmr/tplby.html?sectionid=89&page=1",
    )

    assert "https://mmr.yntv.cn/mmr/tplby.html?sectionid=89&page=1" in pages
    assert "https://mmr.yntv.cn/mmr/tplby.html?sectionid=89&page=2" in pages


def test_parse_detail_html_outputs_schema_required_fields() -> None:
    spider_cls = _load_spider_class()
    html = DETAIL_FIXTURE.read_text(encoding="utf-8")
    url = "https://www.yntv.cn/video/20250702/1751425471742822.html"

    item = spider_cls.parse_detail_html(html, url=url)

    required_fields = ["url", "title", "publish_time", "content_html", "content_text", "source"]
    for field in required_fields:
        assert field in item
        assert isinstance(item[field], str)
        assert item[field].strip(), f"{field} should not be empty"

    assert item["title"] == "Summer has arrived, and Yunnan’s Eryuan wetlands welcome a parade of migratory birds"
    assert item["publish_time"] == "2025-07-02 10:34:31"
    assert item["source"] == "YNTV"
    assert len(item["images"]) == 1
    assert item["images"][0] == "https://www.yntv.cn/uploads/20250702/birds.jpg"


def test_validate_required_fields_raises_on_missing_value() -> None:
    spider_cls = _load_spider_class()
    bad_item = {
        "url": "https://www.yntv.cn/video/20250702/1751425471742822.html",
        "title": "Example",
        "publish_time": "",
        "content_html": "<div>ok</div>",
        "content_text": "ok",
        "source": "YNTV",
    }

    try:
        spider_cls._validate_required_fields(bad_item)
        raised = False
    except ValueError:
        raised = True

    assert raised, "validator should reject missing required fields"
