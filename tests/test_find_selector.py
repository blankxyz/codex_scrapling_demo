from demo_marker_extractor import find_selector_by_text


def test_finds_element_by_exact_text():
    html = '<html><body><h1 class="title">习近平发表重要讲话</h1></body></html>'
    sel = find_selector_by_text(html, "习近平发表重要讲话")
    assert sel is not None
    assert "h1" in sel or "title" in sel


def test_returns_none_when_not_found():
    html = '<html><body><h1>其他标题</h1></body></html>'
    sel = find_selector_by_text(html, "找不到的文字")
    assert sel is None


def test_matches_partial_text():
    html = '<html><body><span class="pub-date">发布时间：2024-01-15 10:00</span></body></html>'
    sel = find_selector_by_text(html, "2024-01-15")
    assert sel is not None
