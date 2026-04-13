# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **web marker extraction demo** that:
1. Fetches a webpage and extracts multiple CSS selector candidates for key fields (title, time, content, list links)
2. Outputs a `marker.json` + `codex_prompt.txt` to guide Codex in generating a production-grade spider
3. The `spider-authoring` skill in `.agents/skills/spider-authoring/SKILL.md` defines how Codex should read a marker and produce `spiders/<site>.py` + `tests/test_<site>.py`

## Running the Tool

```bash
# Install dependencies (Python 3.11 recommended)
uv pip install -r requirements.txt

# Analyze a URL (auto-detects render mode)
python analyze_url.py "https://example.com/article/123"

# Force dynamic rendering (Playwright)
python analyze_url.py "https://example.com/article/123" --render dynamic

# Limit candidates
python analyze_url.py "https://example.com/article/123" --max-candidates 3
```

Outputs are written to `out/<site_slug>/marker.json` and `out/<site_slug>/codex_prompt.txt`.

## Architecture

```
analyze_url.py          CLI entry point — parses args, calls analyze_url(), writes outputs
demo_marker_extractor.py  Core library — fetches HTML and runs heuristic extraction
schemas/news_article.schema.json  Canonical output schema for all generated spiders
.agents/skills/spider-authoring/SKILL.md  Skill definition used by Codex to generate spiders
examples/generated_spider_example.py  Reference implementation showing spider patterns
```

### Key Data Flow

1. `analyze_url()` → `fetch_html()` (Scrapling Fetcher or DynamicFetcher) → `analyze_html()`
2. `analyze_html()` returns a **marker dict** with:
   - `page_type`: `detail` | `list_or_index` | `unknown`
   - `signals`: structural page features (has_article_tag, has_time_tag, etc.)
   - `title_candidates`, `time_candidates`, `content_candidates`, `list_link_candidates`: scored lists of `{selector, score, preview, text_len}`
3. Codex uses the marker to generate spiders that use **multi-fallback selector lists** — never a single brittle selector

### Scoring Heuristics (in `demo_marker_extractor.py`)

| Field | Top signals |
|-------|------------|
| title | `h1` (+80), keyword attrs (+60), 8–160 char range |
| time | `<time>` tag (+90), keyword attrs (+50), date regex (+50) |
| content | `<article>` (+100), `<main>` (+70), keyword attrs (+60), length bonus |
| list links | ≥4 links required, internal link preference (+20) |

### CSS Path Generation

`_css_path()` walks up to 5 ancestor levels, preferring `#id` → `.class + tag` → `:nth-of-type(n)`.

## Unified Schema

All generated spiders must output fields matching `schemas/news_article.schema.json`:

- **Required**: `url`, `title`, `publish_time`, `content_html`, `content_text`, `source`
- **Optional**: `author`, `images[]`, `attachments[]`

## Spider Authoring Skill

When generating or fixing a spider, use the `spider-authoring` skill (`.agents/skills/spider-authoring/SKILL.md`). The skill instructs Codex to:

1. Read `out/<site_slug>/marker.json` and `schemas/news_article.schema.json`
2. Prefer `Fetcher` (static); fall back to `DynamicFetcher` only for JS-heavy pages
3. Output `spiders/<site>.py` with multi-fallback selectors and `tests/test_<site>.py`
4. Save an HTML fixture for regression testing
5. Tests must verify at least `title`, `publish_time`, and `content_text`

See `examples/generated_spider_example.py` for the expected spider class structure (`TITLE_SELECTORS`, `TIME_SELECTORS`, `CONTENT_SELECTORS` class-level lists + `_first_text()` / `_first_html()` helpers + `parse_detail()` method).
