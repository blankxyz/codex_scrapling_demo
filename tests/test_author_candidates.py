from demo_marker_extractor import _author_candidates
from bs4 import BeautifulSoup

def test_finds_author_by_class():
    html = '<html><body><span class="author">张三</span></body></html>'
    soup = BeautifulSoup(html, "lxml")
    results = _author_candidates(soup, max_candidates=3)
    assert len(results) >= 1
    assert results[0]["preview"] == "张三"

def test_skips_long_text():
    long = "这是一段超过三十个字符的文本内容，不应该被识别为作者字段，因为太长了"
    html = f'<html><body><span class="author">{long}</span></body></html>'
    soup = BeautifulSoup(html, "lxml")
    results = _author_candidates(soup, max_candidates=3)
    assert len(results) == 0

def test_empty_when_no_author():
    html = '<html><body><p>正文内容</p></body></html>'
    soup = BeautifulSoup(html, "lxml")
    results = _author_candidates(soup, max_candidates=3)
    assert results == []
