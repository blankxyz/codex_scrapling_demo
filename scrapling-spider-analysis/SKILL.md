---
name: scrapling-spider-analysis
description: Analyze dynamic list-to-detail websites for Scrapling spider generation using browser/CDP evidence only. Use when the user provides a list-page URL and asks for crawler analysis, API discovery, selector extraction, first-page titles, or analysis outputs under analysis_outputs. Do not use search engines or non-browser target fetching.
---

# Scrapling Spider Analysis

## Goal

Analyze a target list page so a later Scrapling spider can be generated with minimal follow-up. Produce concrete, crawler-ready findings in `analysis_outputs/`.

Use browser evidence. CDP is preferred when available because it exposes rendered DOM and network/XHR without relying on search engines or standalone HTTP probing. By default, connect to CDP directly instead of probing or pre-validating the endpoint first; if it cannot be used, fail at the actual connection step and report the error or fall back only when the workflow explicitly allows it.

## Interaction Policy

- Minimize user interruptions. Do not ask for confirmation for routine workspace reads/writes, selector probing, or repeated analysis steps.
- Batch browser/CDP probes and artifact writes so the user does not have to approve many small commands.
- If a command needs sandbox escalation, request it once with a reasonably scoped `prefix_rule` that covers the repeated browser/CDP probing needed for this analysis.
- Do not repeatedly stop for "press enter"/confirmation prompts. Make a reasonable assumption, continue, and report assumptions in the final analysis.
- Ask the user only for genuinely missing inputs that cannot be inferred safely, such as the target URL or an explicitly required output schema.

## Hard Rules

- Do not use search engines.
- Do not use non-browser target fetching for site analysis. Avoid `curl`, `wget`, `requests`, or direct API calls to the target as evidence unless the user explicitly asks for a browser-observed request to be replayed for debugging.
- If Python is needed during analysis, use only the current workspace virtualenv interpreter at `.venv/bin/python`.
- Do not use `python`, `python3`, or any system interpreter for analysis commands, even as a fallback.
- Default to Chrome CDP. `tools/cdp_probe.py` auto-detects the available CDP endpoint (tries `$CHROME_CDP_URL`, `127.0.0.1:9222`, then Docker bridge range `172.17.0.1-20`). Do not hardcode the CDP address in prompts or commands.
- If CDP is unavailable, use local browser/dynamic rendering tools, not search.
- If the user asks for first page only, do not click or request pagination except to verify whether pagination exists when explicitly needed.
- Write analysis artifacts to `analysis_outputs/`.
- The output must support the next step: generating a Scrapling list-to-detail spider.

## Workflow

1. Prepare output names:
   - Convert the list URL host/path into a slug like `gdj-gansu-gov-cn-c109213`.
   - Write `analysis_outputs/<slug>_analysis.md`.
   - Write `analysis_outputs/<slug>_analysis.json`.

2. Connect to browser:
   - Prefer Chrome CDP: use `tools/cdp_probe.py` which auto-detects the endpoint. Do not hardcode `127.0.0.1:9222` in commands.
   - If the direct CDP action fails, report the concrete error and either stop or switch to another local browser-rendered method when the workflow permits.
   - Before writing a new probe script, look for an existing reusable local probe tool and use it first. In this repo, prefer `tools/cdp_probe.py` for generic CDP DOM/network/detail capture.
   - When invoking that tool or any other Python helper, call it with `.venv/bin/python` explicitly.
   - Always invoke `tools/cdp_probe.py` with the `env -u` proxy-clearing prefix:

     ```bash
     env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
       .venv/bin/python tools/cdp_probe.py \
       --url "https://example.com/list.html" \
       --out analysis_outputs/_example_probe.json
     ```

   - Only write a one-off probe when the reusable script cannot capture a site-specific behavior that is required for analysis, and explain that gap briefly.
   - Open or reuse a tab for the list URL.
   - Enable DOM/runtime/network observation through CDP or browser automation.
   - If starting or controlling Chrome requires approval, request one approval for the full browser-analysis command pattern rather than separate approvals for each page probe.

3. Observe rendered list page:
   - Page title and visible column name.
   - List item selector.
   - Detail URL selector and URL normalization base.
   - Title selector/field.
   - Publish time selector/field.
   - First-page item count and first-page titles.

4. Observe network/XHR:
   - Identify list API/XHR endpoint if present.
   - Record method, URL path, query parameters, page parameter, page size, channel/section ID, and whether a dynamic anti-bot token is added by browser JavaScript.
   - Prefer browser-captured XHR response shape over manual API reconstruction.
   - Record JSON paths for rows, detail URL, title, publish time, column name, source, total, page, and page size.

5. Observe one detail page:
   - Detail title selector.
   - Publish time/source/views selectors or regexes.
   - Main content container selector.
   - Whether article content is duplicated in multiple containers.
   - Any media/download/file selectors if relevant.

6. Decide crawler strategy:
   - `session`: `AsyncStealthySession` or `AsyncDynamicSession`.
   - `capture_xhr` pattern if API exists.
   - First-page only or pagination plan.
   - DOM fallback selectors.
   - Required wait selectors for list and detail pages.

7. Save artifacts:
   - Markdown: human-readable explanation, first-page titles, selectors, API details, strategy.
   - JSON: machine-readable fields for spider generation.

## JSON Shape

Use this shape when possible:

```json
{
  "source_url": "",
  "slug": "",
  "site": {
    "domain": "",
    "base_url": "",
    "page_title": "",
    "column_name": ""
  },
  "list": {
    "first_page_only": true,
    "item_count": 0,
    "item_selector": "",
    "link_selector": "",
    "title_selector": "",
    "publish_time_selector": "",
    "wait_selector": "",
    "first_page_titles": []
  },
  "api": {
    "exists": false,
    "capture_xhr": "",
    "method": "GET",
    "path": "",
    "channel_id": "",
    "page_param": "",
    "page_size_param": "",
    "dynamic_token": false,
    "response_paths": {
      "rows": "",
      "page": "",
      "total": "",
      "detail_url": "",
      "title": "",
      "publish_time": "",
      "column_name": "",
      "source": ""
    }
  },
  "detail": {
    "sample_url": "",
    "title_selector": "",
    "meta_selector": "",
    "content_selector": "",
    "publish_time_regex": "",
    "source_regex": "",
    "views_regex": "",
    "wait_selector": "",
    "content_duplicated": false
  },
  "spider_strategy": {
    "session": "AsyncStealthySession",
    "google_search": false,
    "network_idle": false,
    "pagination": "none",
    "notes": []
  }
}
```

## Reporting

In the final response, include:

- Artifact paths.
- Whether analysis used CDP or another browser-rendered method.
- API/XHR availability.
- First-page item count and titles when requested.
- Detail selectors.
- Spider-generation notes and risks.

For CDP/browser command patterns and compact extraction snippets, read [references/cdp_browser_analysis.md](references/cdp_browser_analysis.md).
