from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, asdict
from typing import Any, Iterable, Optional
from urllib.parse import urlparse

import tldextract
from bs4 import BeautifulSoup, Tag

TITLE_PAT = re.compile(r"(title|headline|article-title|content_title|detail-title|news-title|tit)", re.I)
TIME_PAT = re.compile(r"(time|date|pub|publish|updated|update|posted|created)", re.I)
CONTENT_PAT = re.compile(r"(content|article|body|post|detail|editor|main|text|TRS_Editor)", re.I)
LIST_PAT = re.compile(r"(list|news|article|item|entry|card|link)", re.I)
AUTHOR_PAT = re.compile(r"(author|byline|writer|reporter|记者|作者|来源|source)", re.I)
NOISE_TAGS = {"script", "style", "noscript", "svg", "footer", "header", "nav", "aside", "form"}

try:
    from scrapling.fetchers import Fetcher, DynamicFetcher
except Exception:  # pragma: no cover
    Fetcher = None
    DynamicFetcher = None


@dataclass
class Candidate:
    selector: str
    score: int
    preview: str
    text_len: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _slugify_site(url: str) -> str:
    ext = tldextract.extract(url)
    core = "-".join([part for part in [ext.domain, ext.suffix.replace(".", "-")] if part])
    return re.sub(r"[^a-zA-Z0-9-]+", "-", core).strip("-").lower() or "site"


def fetch_html(url: str, render: str = "auto") -> tuple[str, list[Any], dict[str, Any]]:
    meta: dict[str, Any] = {"engine": None, "render_mode": render}
    if render in {"static", "auto"} and Fetcher is not None:
        try:
            page = Fetcher.get(url, impersonate="chrome")
            html = getattr(page, "text", None) or getattr(page, "body", b"")
            if isinstance(html, bytes):
                html = html.decode("utf-8", errors="ignore")
            meta["engine"] = "scrapling.Fetcher"
            meta["status"] = getattr(page, "status", None)
            return html, [], meta
        except Exception as e:
            meta["static_error"] = repr(e)

    if render in {"dynamic", "auto"} and DynamicFetcher is not None:
        try:
            page = DynamicFetcher.fetch(url, headless=True, network_idle=True, capture_xhr=r".*")
            html = getattr(page, "text", None) or getattr(page, "body", b"")
            if isinstance(html, bytes):
                html = html.decode("utf-8", errors="ignore")
            meta["engine"] = "scrapling.DynamicFetcher"
            meta["status"] = getattr(page, "status", None)
            xhr_responses = getattr(page, "captured_xhr", [])
            return html, xhr_responses, meta
        except Exception as e:
            meta["dynamic_error"] = repr(e)

    raise RuntimeError(
        "Failed to fetch page via Scrapling. Check whether Scrapling and browser dependencies are installed."
    )


def _clean_text(s: str) -> str:
    s = re.sub(r"\s+", " ", s or "").strip()
    return s


def _preview(tag: Tag, max_len: int = 80) -> str:
    text = _clean_text(tag.get_text(" ", strip=True))
    return text[:max_len]


def _text_len(tag: Tag) -> int:
    return len(_clean_text(tag.get_text(" ", strip=True)))


def _has_keyword(tag: Tag, pattern: re.Pattern[str]) -> bool:
    joined = " ".join(filter(None, [tag.get("id"), " ".join(tag.get("class", []))]))
    return bool(pattern.search(joined))


def _css_path(tag: Tag) -> str:
    if tag.get("id"):
        return f"#{tag.get('id')}"
    parts: list[str] = []
    current: Optional[Tag] = tag
    while current and current.name and current.name != "[document]":
        if current.get("id"):
            parts.append(f"#{current.get('id')}")
            break
        part = current.name
        classes = [c for c in current.get("class", []) if re.match(r"^[a-zA-Z0-9_-]{1,40}$", c)]
        if classes:
            part += "".join(f".{c}" for c in classes[:2])
        else:
            siblings = [sib for sib in current.parent.find_all(current.name, recursive=False)] if current.parent else []
            if len(siblings) > 1:
                idx = siblings.index(current) + 1
                part += f":nth-of-type({idx})"
        parts.append(part)
        current = current.parent if isinstance(current.parent, Tag) else None
    return " > ".join(reversed(parts[-5:]))


def _dedupe(cands: Iterable[Candidate], max_candidates: int) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for cand in sorted(cands, key=lambda x: (-x.score, -x.text_len, len(x.selector))):
        if cand.selector in seen:
            continue
        seen.add(cand.selector)
        out.append(cand.to_dict())
        if len(out) >= max_candidates:
            break
    return out


def _title_candidates(soup: BeautifulSoup, max_candidates: int) -> list[dict[str, Any]]:
    cands: list[Candidate] = []
    for tag in soup.find_all(["h1", "h2", "div", "header", "section"]):
        if tag.name in NOISE_TAGS:
            continue
        text = _clean_text(tag.get_text(" ", strip=True))
        if not text or len(text) < 8 or len(text) > 160:
            continue
        score = 0
        if tag.name == "h1":
            score += 80
        if _has_keyword(tag, TITLE_PAT):
            score += 60
        if len(text) <= 60:
            score += 20
        cands.append(Candidate(selector=_css_path(tag), score=score, preview=text, text_len=len(text)))
    return _dedupe(cands, max_candidates)


def _time_candidates(soup: BeautifulSoup, max_candidates: int) -> list[dict[str, Any]]:
    cands: list[Candidate] = []
    time_regex = re.compile(r"(20\d{2}[-/.年]\s*\d{1,2}[-/.月]\s*\d{1,2}|\d{4}-\d{2}-\d{2}|\d{2}:\d{2})")
    for tag in soup.find_all(["time", "span", "div", "p"]):
        if tag.name in NOISE_TAGS:
            continue
        text = _clean_text(tag.get_text(" ", strip=True))
        if not text:
            continue
        score = 0
        if tag.name == "time":
            score += 90
        if _has_keyword(tag, TIME_PAT):
            score += 50
        if time_regex.search(text):
            score += 50
        if score == 0:
            continue
        cands.append(Candidate(selector=_css_path(tag), score=score, preview=text, text_len=len(text)))
    return _dedupe(cands, max_candidates)


def _content_candidates(soup: BeautifulSoup, max_candidates: int) -> list[dict[str, Any]]:
    cands: list[Candidate] = []
    for tag in soup.find_all(["article", "main", "section", "div"]):
        if tag.name in NOISE_TAGS:
            continue
        text_len = _text_len(tag)
        if text_len < 300:
            continue
        score = 0
        if tag.name == "article":
            score += 100
        if tag.name == "main":
            score += 70
        if _has_keyword(tag, CONTENT_PAT):
            score += 60
        score += min(text_len // 50, 80)
        cands.append(Candidate(selector=_css_path(tag), score=score, preview=_preview(tag), text_len=text_len))
    return _dedupe(cands, max_candidates)


def _author_candidates(soup: BeautifulSoup, max_candidates: int) -> list[dict[str, Any]]:
    cands: list[Candidate] = []
    for tag in soup.find_all(["span", "p", "em", "a", "div"]):
        if tag.name in NOISE_TAGS:
            continue
        text = _clean_text(tag.get_text(" ", strip=True))
        if not text or len(text) < 2 or len(text) > 30:
            continue
        score = 0
        if _has_keyword(tag, AUTHOR_PAT):
            score += 60
        if tag.name in {"span", "em"}:
            score += 10
        if score == 0:
            continue
        cands.append(Candidate(selector=_css_path(tag), score=score, preview=text, text_len=len(text)))
    return _dedupe(cands, max_candidates)


def _title_matches_any_link(links: list[Tag], title_hint: str) -> bool:
    """检查是否有任意链接文本包含 title_hint（或反向包含）。"""
    hint = title_hint.strip()
    for a in links:
        text = _clean_text(a.get_text(" ", strip=True))
        if not text:
            continue
        if hint in text or text in hint:
            return True
    return False


def _list_link_candidates(
    soup: BeautifulSoup, max_candidates: int, title_hint: str = ""
) -> list[dict[str, Any]]:
    cands: list[Candidate] = []
    tag_links_map: dict[str, tuple[Tag, list[Tag]]] = {}

    for tag in soup.find_all(["ul", "ol", "div", "section"]):
        if tag.name in NOISE_TAGS:
            continue
        links = tag.find_all("a", href=True)
        if len(links) < 4:
            continue
        sel = _css_path(tag) + " a"

        href_hosts = Counter(urlparse(a.get("href", "")).netloc for a in links if a.get("href"))
        internal_bias = 20 if "" in href_hosts or len(href_hosts) <= 2 else 0
        score = min(len(links) * 5, 60) + internal_bias
        if _has_keyword(tag, LIST_PAT):
            score += 20
        if title_hint and _title_matches_any_link(links, title_hint):
            score += 50

        sample_links = [
            {"text": _clean_text(a.get_text(" ", strip=True))[:60], "href": a.get("href", "")}
            for a in links[:3]
        ]
        preview_parts = [f"[{i+1}] {s['text']} → {s['href']}" for i, s in enumerate(sample_links)]
        preview = "\n".join(preview_parts) + f"\n(共 {len(links)} 条链接)"
        cand = Candidate(selector=sel, score=score, preview=preview, text_len=len(links))
        cands.append(cand)
        tag_links_map[sel] = (tag, links)

    deduped = _dedupe(cands, max_candidates)
    for item in deduped:
        sel = item["selector"]
        if sel in tag_links_map:
            _, links = tag_links_map[sel]
            item["sample_links"] = [
                {"text": _clean_text(a.get_text(" ", strip=True))[:60], "href": a.get("href", "")}
                for a in links[:3]
            ]
            item["title_matched"] = bool(title_hint and _title_matches_any_link(links, title_hint))
        else:
            item["sample_links"] = []
            item["title_matched"] = False
    return deduped


_API_URL_PAT = re.compile(r"(/api/|/json|/data/|/v\d+/)", re.I)
_ARTICLE_KEYS = {"title", "content", "publish_time", "data", "list", "items", "article", "news", "body", "text"}


def _api_candidates(xhr_responses: list[Any], max_candidates: int = 6) -> list[dict[str, Any]]:
    cands: list[dict[str, Any]] = []
    for resp in xhr_responses:
        try:
            ct = ""
            headers = getattr(resp, "headers", {}) or {}
            if isinstance(headers, dict):
                ct = headers.get("content-type", "") or headers.get("Content-Type", "")
            if "application/json" not in ct:
                continue
            body = getattr(resp, "body", None) or getattr(resp, "text", None) or b""
            if isinstance(body, str):
                raw = body
            else:
                raw = body.decode("utf-8", errors="ignore")
            data = json.loads(raw)
        except Exception:
            continue

        if not isinstance(data, (dict, list)):
            continue

        size = len(raw.encode("utf-8"))
        url = getattr(resp, "url", "") or ""
        status = getattr(resp, "status", 0) or 0

        score = 0
        if _API_URL_PAT.search(url):
            score += 40
        top_keys = set(data.keys()) if isinstance(data, dict) else set()
        if top_keys & _ARTICLE_KEYS:
            score += 50
        if 1024 <= size <= 200 * 1024:
            score += 20
        if status == 200:
            score += 10

        if score == 0:
            continue

        # Build a compact preview: truncate lists to 1 item, cap total length at 300 chars
        if isinstance(data, list):
            preview: Any = data[:1]
        else:
            preview = {}
            for k, v in data.items():
                preview[k] = v[:1] if isinstance(v, list) else v
        cands.append({
            "url": url,
            "status": status,
            "score": score,
            "size_bytes": size,
            "preview": json.dumps(preview, ensure_ascii=False)[:300],
        })

    cands.sort(key=lambda x: -x["score"])
    return cands[:max_candidates]


def _signals(soup: BeautifulSoup) -> dict[str, Any]:
    return {
        "has_article_tag": soup.find("article") is not None,
        "has_time_tag": soup.find("time") is not None,
        "has_breadcrumb": bool(soup.select('[class*="breadcrumb"], [id*="breadcrumb"], nav[aria-label*="breadcrumb" i]')),
        "h1_count": len(soup.find_all("h1")),
        "article_count": len(soup.find_all("article")),
    }


def _page_type(title_candidates: list[dict[str, Any]], content_candidates: list[dict[str, Any]]) -> str:
    if title_candidates and content_candidates:
        return "detail"
    if not content_candidates:
        return "list_or_index"
    return "unknown"


def _build_prompt(url: str, site_slug: str, marker: dict[str, Any]) -> str:
    confirmed = marker.get("confirmed")
    confirmed_section = ""
    if confirmed:
        confirmed_section = f"""
Confirmed selectors (use these first — user-validated):
{json.dumps(confirmed, ensure_ascii=False, indent=2)}

Note: The `confirmed` block above contains user-validated selectors.
Prioritize these over the candidate lists below. Use candidate lists only as fallback alternatives.
"""
    return f"""Use the spider-authoring skill.

Task:
Generate a Scrapling spider for the site '{site_slug}' using the marker file below and the unified schema at schemas/news_article.schema.json.
{confirmed_section}
Requirements:
1. Check marker's "requires_dynamic" field: if true, use DynamicFetcher; otherwise use Fetcher.
2. Use fallback selector chains from marker candidates, not a single fragile selector.
3. Output: spiders/{site_slug}.py
4. Keep field names aligned with schemas/news_article.schema.json.
5. Do not use bs4.
6. Do not generate test files. Run `python -m py_compile spiders/{site_slug}.py` to verify syntax only.

Target URL:
{url}

Marker JSON:
{json.dumps(marker, ensure_ascii=False, indent=2)}
"""


def analyze_html(
    html: str, url: str, fetch_meta: dict[str, Any],
    xhr_responses: list[Any] | None = None,
    max_candidates: int = 6, title_hint: str = "",
) -> dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    site_slug = _slugify_site(url)

    title_candidates = _title_candidates(soup, max_candidates=max_candidates)
    time_candidates = _time_candidates(soup, max_candidates=max_candidates)
    content_candidates = _content_candidates(soup, max_candidates=max_candidates)
    list_link_candidates = _list_link_candidates(soup, max_candidates=max_candidates, title_hint=title_hint)

    marker = {
        "site_slug": site_slug,
        "url": url,
        "page_type": _page_type(title_candidates, content_candidates),
        "fetch_meta": fetch_meta,
        "signals": _signals(soup),
        "title_candidates": title_candidates,
        "time_candidates": time_candidates,
        "content_candidates": content_candidates,
        "list_link_candidates": list_link_candidates,
        "api_candidates": _api_candidates(xhr_responses or [], max_candidates=max_candidates),
        "notes": [
            "Prefer title/time/content top-ranked selectors first.",
            "If selector drift occurs, keep multiple fallback selectors in the spider.",
            "This marker file is a heuristic bootstrap, not a final guarantee."
        ],
    }

    return {
        "site_slug": site_slug,
        "marker": marker,
        "codex_prompt": _build_prompt(url, site_slug, marker),
    }


def analyze_url(url: str, render: str = "auto", max_candidates: int = 6) -> dict[str, Any]:
    html, xhr_responses, fetch_meta = fetch_html(url=url, render=render)
    return analyze_html(html=html, url=url, fetch_meta=fetch_meta,
                        xhr_responses=xhr_responses, max_candidates=max_candidates)
