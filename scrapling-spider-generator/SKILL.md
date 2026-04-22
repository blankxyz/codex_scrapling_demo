---
name: scrapling-spider-generator
description: Generate ready-to-run Scrapling spider code from prior browser/CDP analysis outputs, list-page API findings, DOM selectors, and required output schemas. Use when the user asks to create a Scrapling crawler/spider after analysis, wants one-shot crawler generation, or provides a list URL plus existing files in analysis_outputs.
---

# Scrapling Spider Generator

## Goal

Generate a focused, compact Scrapling spider from analysis artifacts and validate it enough that the user can run it directly.

This skill is for code generation, not site analysis. If analysis is missing or stale, ask for or run the separate analysis workflow first. CDP is an analysis tool only; generated spiders must run without depending on CDP unless the user explicitly requests a CDP-bound diagnostic script.

## Inputs

Use these sources in order:

1. Current user request, especially output schema, account codes, project names, pagination limits, and runtime constraints.
2. `analysis_outputs/*_analysis.json` and `analysis_outputs/*_analysis.md`.
3. Existing local spiders for style and helper conventions.
4. Local Scrapling package APIs, read from `.venv/lib/.../site-packages/scrapling` when unsure.

Do not use network search engines. Do not introduce non-browser HTTP clients for target pages when the analysis says the site requires browser execution.

If Python is needed during generation or validation, use only the current workspace virtualenv interpreter at `.venv/bin/python`. Do not use `python`, `python3`, or any system interpreter, even as a fallback.

## Workflow

1. Identify the list target and analysis file:
   - Prefer the newest relevant `analysis_outputs/*_analysis.json`.
   - Extract list URL, column name, channel/API endpoint, first-page size, detail URL field, title field, publish-time field, detail selectors, and pagination decision.
   - Detect whether the same site likely has multiple sibling sections/channels with the same DOM/API shape and only different section ids, classify codes, route params, or column names.
   - Unless the user explicitly asks for pagination, generate first-page only.
   - If the spider uses `SECTIONS`, this first-page-only rule applies to each section independently: by default, request only page 1 for every section.

2. Choose the Scrapling session:
   - If analysis found a list API with fixed parameters and `dynamic_token=false`, use Scrapling `FetcherSession` to request the list API directly.
   - Do not open a list page just to capture an already-known static API.
   - Use browser-rendered XHR capture only when the API needs JS-generated tokens, browser-only cookies, anti-bot state, or direct API validation fails.
   - If only detail pages require browser rendering, register the browser session with `lazy=True` so the crawl starts from the API request.
   - Default to `AsyncStealthySession` for protected government/news sites where normal dynamic rendering returns errors or needs browser fingerprints.
   - Use `AsyncDynamicSession` only when analysis or validation shows normal dynamic rendering works.
   - Never require `cdp_url` in production spiders. Runtime dynamic rendering should launch/drive Scrapling's browser itself.
   - Do not add `real_chrome` or `SCRAPLING_REAL_CHROME` to generated code.
   - Set `capture_xhr` only when using browser-rendered XHR capture rather than direct API requests.
   - Set `google_search=False`.

3. Generate a single spider file under `spiders/`:
   - Name from domain and column/path, e.g. `gdj_gansu_gov_cn_c109213.py`.
   - Use a stable `project_name` matching spider `name`.
   - Keep generated code as short as practical. Do not over-engineer helpers, abstractions, validators, or fallback paths.
   - Include only helpers that are used by this spider. Prefer simple inline logic over generic utility layers when it stays readable.
   - Keep helper functions local if there is no shared project helper module, but avoid broad reusable helper libraries in one-off spiders.
   - When the site has multiple same-structure sections, prefer one spider with a compact config list such as `SECTIONS = [{"column_name": "...", "classify_code": "..."}]` and loop over it.
   - Do not create parallel arrays like `COLUMNS = [...]` and `CLASSIFY_CODES = [...]`; use a list of objects/dicts so related values cannot drift out of sync.
   - Use this config-list pattern only when the fields and parsing logic are truly shared. If sections differ materially in schema or parsing, split them.
   - Use `response.meta` for data carried from list to detail. If the user provides examples using `response.save`, implement the equivalent with Scrapling `meta` unless the project has an established `save` pattern.
   - Preserve the user's required output schema exactly for field names, field order, constants, and value types.
   - Do not add, remove, rename, or reorder output fields from the user's schema.
   - Every generated spider must include both text-detail and video-detail handling paths unless the user explicitly forbids one of them.
   - Do not assume a section is text-only or video-only from first-page sampling, one list card layout, or one inspected detail page.
   - If the list/detail data contains multiple content types, generate type-specific item builders instead of forcing all details into one schema.
   - For news/text details, use the text-message schema. For video details, use the video-program schema when the user has provided it.

4. Implement list parsing:
   - Prefer direct API requests when analysis found a stable API endpoint with fixed query parameters.
   - For direct API lists, start from the API URL with `page=1`, observed `size`, section/channel parameters, and the cache-buster parameter only if the API expects it.
   - For multi-section spiders, iterate the section config list from `start_requests()` or chain section requests explicitly so each section is requested in a controlled way.
   - When pagination was not explicitly requested, do not continue past page 1 for any section in a `SECTIONS` spider.
   - When one shared HTTP session gives unstable results across simultaneous section requests, prefer serial section scheduling over concurrent list requests.
   - Decode the API JSON response and filter to page 1 when first-page only.
   - Use captured XHR JSON only when direct API is not safe or not working.
   - Yield detail `Request`s with `sid` pointing to the browser session and metadata for title, publish time, column name, image/poster, content type, source, or other required fields.
   - Add a rendered DOM fallback for first page links using selectors from analysis.

5. Implement detail parsing:
   - Use detail selectors from analysis.
   - Prefer list metadata for title and publish time; use detail-page selectors/regex as fallback.
   - Extract content from the narrowest article container. If the page duplicates content in multiple matching containers, use the first article container.
   - Never classify a detail page from a partial content sample alone. At runtime, inspect the full detail response for both article text signals and video signals.
   - Every spider must implement runtime type detection for each detail page, combining:
     - carried list metadata such as `content_type`, channel flags, or API fields,
     - stable URL/path hints such as `/video/`,
     - full-page media signals such as `<video>`, `<source>`, player config JSON, inline script `source`/`mp4` fields, or embedded player iframes.
   - Branch by resolved detail type instead of a single sampled heuristic:
     - `news`/text pages must emit the text schema.
     - `video` pages must extract `video_url` from the player/source script or media element and emit the video schema.
   - If both text and video signals exist, prefer the video schema unless the user explicitly requires dual emission.
   - Normalize whitespace.

6. Save and validate:
   - Write the generated spider directly to the exact output path requested by the user.
   - Returning code in chat without creating the file is a failure.
   - Run `.venv/bin/python -m py_compile <spider>`.
   - Prefer running schema checks in a temporary snippet or external test command. Do not embed schema validator functions in the production spider unless the user explicitly asks.
   - Run an output schema check for at least one text item and one video item when both types exist or may plausibly coexist under the same section:
     - `list(item.keys())` must equal the exact expected key list for that item type.
     - Required constants must match exactly, including `accountcode`, text `type`, text `tags`, video `source`, video `episode`, and numeric counters.
     - Text `spidertime` and `createtime` must be formatted strings using `%Y-%m-%d %H:%M:%S`.
     - Video `spider_time` and `create_time` must be integer Unix timestamps from `int(time.time())`.
   - Validation must not rely on one sampled detail page to conclude the whole section is text-only or video-only.
   - If runtime access is available, run the spider once with `.venv/bin/python`.
   - If a normal dynamic session fails with target-side 400/403/timeouts, switch to `AsyncStealthySession` and validate again.
   - Report whether validation fetched list, API, and detail pages, and whether output item count matches first-page size.

## Production Constraints

- CDP may be used to analyze a site, but generated production spiders must not require a running local Chrome CDP endpoint.
- Prefer direct stable APIs over browser-rendered XHR capture. Prefer browser-rendered XHR capture over reconstructing anti-bot token URLs manually.
- Do not emit `real_chrome`-style toggles or environment variables in generated code.
- Do not add pagination unless the user asks for it.
- Do not stop after printing code; the requested spider file must actually be created on disk.
- For `SECTIONS` spiders, do not interpret multiple sections as permission to paginate. Default to page 1 for each section.
- Do not write unrelated framework scaffolding.
- Do not let generated spiders grow unnecessarily large. Avoid copied boilerplate, unused helpers, duplicate normalizers, embedded test code, and diagnostic-only code.
- Do not revert unrelated repository changes.
- Avoid external dependencies beyond the current project environment.

## Reference

For compact code patterns and known Scrapling response/session details, read [references/scrapling_spider_patterns.md](references/scrapling_spider_patterns.md).
