---
name: scrapling-spider-analysis
description: Analyze a list-to-detail site with browser/CDP evidence and emit Scrapling-ready artifacts to analysis_outputs/.
---

# Scrapling Spider Analysis

## When to use

- User provides a list-page URL and asks for crawler analysis, API discovery, selector extraction, first-page titles, or `analysis_outputs/` artifacts.

## When not to use

- Only a one-off HTTP fetch is needed (no spider required).
- User wants to modify or regenerate an existing spider (use the generator skill).
- Task requires search engine lookup of the target site.

## Language convention

- This file (SKILL.md) is English so the harness can match triggers reliably.
- `references/*.md` files are 中文, targeted at operators reading reference material directly.
- JSON artifact field names are English; human-readable strings (titles, column names) follow the source site encoding.

## Goal

Analyze a target list page so a later Scrapling spider can be generated with minimal follow-up. Produce concrete, crawler-ready findings in `analysis_outputs/`.

Use browser evidence. CDP is preferred when available because it exposes rendered DOM and network/XHR without relying on search engines or standalone HTTP probing. For CDP-backed analysis, prefer running without sandbox restrictions up front rather than probing from a restricted sandbox first. Treat "CDP unreachable from the current sandbox" as an environment/access problem first, not as target-site evidence.

## Interaction Policy

- Minimize user interruptions. Do not ask for confirmation for routine workspace reads/writes, selector probing, or repeated analysis steps.
- Batch browser/CDP probes and artifact writes so the user does not have to approve many small commands.
- Prefer non-sandbox execution for CDP/browser analysis when the environment allows it. If the current run is sandboxed and CDP is required, switch to a non-sandbox run instead of accumulating retries.
- Do not repeatedly stop for "press enter"/confirmation prompts. Make a reasonable assumption, continue, and report assumptions in the final analysis.
- Ask the user only for genuinely missing inputs that cannot be inferred safely, such as the target URL or an explicitly required output schema.

## Hard Rules

- Do not use search engines.
- Do not use `curl`, `wget`, `requests`, or any direct HTTP call to the target as analysis evidence.
- Use only `.venv/bin/python` for any Python helper; never `python` or `python3`.
- Use `tools/cdp_probe.py` for CDP analysis; it auto-detects the endpoint — do not hardcode addresses.
- If CDP is unavailable, use local browser/dynamic rendering tools, not search.
- Do not paginate unless the user explicitly asks; verify pagination existence only when needed.
- Write final artifacts to `analysis_outputs/`; output must support spider generation.

For command patterns, proxy-clearing prefix, and `--reuse-open-tab` usage, see [references/cdp_browser_analysis.md](references/cdp_browser_analysis.md).

## Workflow

1. Prepare output names:

   **Slug rule** (apply consistently to avoid downstream drift):
   1. Take `host` + `"/"` + `path` from the list URL.
   2. Replace `.` → `-` and `/` → `-`.
   3. Strip leading/trailing `-`.
   4. If the result ends with `-html` or `-shtml`, remove that suffix.
   5. Lowercase the whole string.

   Examples:
   - `www.hngrrb.cn/shizheng/` → `www-hngrrb-cn-shizheng`
   - `gdj.gansu.gov.cn/gdj/c109213/` → `gdj-gansu-gov-cn-gdj-c109213`
   - `www.zhengguannews.cn/list/17.html` → `www-zhengguannews-cn-list-17`

   Write into a **per-slug subfolder** `analysis_outputs/<slug>/`:
   - `analysis.md` — human-readable report
   - `analysis.json` — machine-readable artifact
   - `_probe.json` — intermediate CDP probe capture
   - `_detail_probe.json` — optional, when sampling a detail page

   Rationale: one site = one folder, so re-analysis is `rm -rf analysis_outputs/<slug>/` and `ls analysis_outputs/` shows a site list, not a flat file pile. Create the directory (`mkdir -p`) before writing probe/artifact outputs.

2. Connect to browser:
   - Use `tools/cdp_probe.py` with the `env -u` proxy-clearing prefix. See [references/cdp_browser_analysis.md](references/cdp_browser_analysis.md) for exact command patterns.
   - Prefer non-sandbox execution (`run_pipeline.sh` defaults Step 1 to `danger-full-access`).
   - If the challenge was cleared in a visible Chrome window, use `--reuse-open-tab --skip-networkidle`.
   - Do not retry CDP failures inside the sandbox; follow the **Failure & fallback decision tree** below instead.
   - Reuse `tools/cdp_probe.py` for all generic probes; write a one-off script only when it cannot cover a site-specific interaction.
   - Request one approval for the full browser-analysis command pattern, not per-page approvals.

## Failure & fallback decision tree

1. **CDP connection fails** (`No reachable CDP endpoint found`)
   - Is the current command running inside a Codex sandbox?
     - **Yes** → switch to a non-sandbox run of the same `tools/cdp_probe.py` command. Do not retry inside the sandbox.
     - **No** → check whether `chrome --remote-debugging-port=9222` is running. If not, prompt the user to start Chrome or run `./start_chrome_cdp.sh`.

2. **CDP reachable but target shows a challenge / verification page** (WAF, Cloudflare, login wall)
   - Preferred: have the user open and clear the challenge in the visible Chrome window, then switch to `--reuse-open-tab --skip-networkidle`.
   - Fallback: use `AsyncStealthySession` and add a `risk: challenge-page` note to `spider_strategy.notes`.

3. **DOM rendered but no list API/XHR found**
   - Do not fabricate an API. Set `api.exists=false`, record full DOM selectors in `list.*`, set `spider_strategy.session="AsyncDynamicSession"`, and add a `"DOM-only"` note.

4. **List DOM empty or structurally abnormal**
   - Check for iframe embedding or scroll-triggered loading; document `wait_selector` and scroll strategy in `notes`.
   - If still no data, stop and report the concrete observation (page text excerpt, last XHR seen). Do not invent selectors.

## Strategy Selection Policy

Analysis always uses browser/CDP for evidence (see Hard Rules). The output must recommend the cheapest viable runtime for the spider, in this priority:

1. **Tier A — API + AsyncFetcher** (preferred)
   - A stable, replayable list API exists.
   - No dynamic anti-bot token required by the browser (or the token is in a static cookie / fixed header that AsyncFetcher can reproduce).
   - Response is JSON with clear `rows / title / detail_url / publish_time`.
   - Set `spider_strategy.runtime_tier = "api"`, `spider_strategy.session = "AsyncFetcher"`, `api.exists = true`, and fill `api.*` completely.

2. **Tier B — HTML + AsyncFetcher** (fallback when no API)
   - List data is present in the initial server-rendered HTML (visible in view-source, not injected by JS after load).
   - No challenge page, no required cookies beyond vanilla UA.
   - Set `spider_strategy.runtime_tier = "fetcher-html"`, `spider_strategy.session = "AsyncFetcher"`, `api.exists = false`, and fill `list.*` DOM selectors.

3. **Tier C — Browser session** (last resort)
   - Required when ANY of: dynamic anti-bot token, JS-rendered list, login wall, Cloudflare/WAF challenge, scroll-triggered loading.
   - Set `spider_strategy.runtime_tier = "browser"`, and pick `AsyncStealthySession` (challenge/fingerprinting) or `AsyncDynamicSession` (plain JS rendering).
   - If `capture_xhr` is needed for a browser-only token, record the pattern.

The analysis MUST justify the chosen tier by adding a string to `spider_strategy.notes` starting with `"decision: "`, e.g. `"decision: Tier A — /common/search API returns JSON with stable query params; no browser token observed."`. When Tier C is chosen, also add a `"risk: ..."` note explaining why A and B were ruled out, based on browser evidence.

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

6. Decide crawler strategy (apply **Strategy Selection Policy** above):
   - Start from Tier A. Did CDP capture a list API/XHR that AsyncFetcher can replay (no browser-only token)?
   - If not, try Tier B. Is the list visible in the initial server-rendered HTML?
   - If still no, fall to Tier C and choose between `AsyncStealthySession` and `AsyncDynamicSession`.
   - Record the chosen `runtime_tier`, `session` class, `capture_xhr` pattern (Tier C with token), pagination plan, DOM fallback selectors, and required wait selectors.

7. Save artifacts:
   - Markdown: human-readable explanation, first-page titles, selectors, API details, strategy.
   - JSON: machine-readable fields for spider generation.

## JSON Shape

Use this shape when possible:

```json
{
  "schema_version": "1",
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
    "runtime_tier": "api",
    "session": "AsyncFetcher",
    "google_search": false,
    "network_idle": false,
    "pagination": "none",
    "notes": []
  }
}
```

### list.first_page_titles rules

- Include only titles produced by `list.item_selector` + `list.title_selector`; exclude nav/header/footer/breadcrumb anchors.
- Preserve DOM order (top-to-bottom as rendered on the page).
- Trim leading/trailing whitespace; collapse internal whitespace to single spaces.
- De-duplicate only adjacent identical entries; non-adjacent duplicates may be legitimate and must be preserved.
- Exclude entries where title text is empty after trim, or where `href` is missing, `#`, or starts with `javascript:`.
- Length must equal `list.item_count`. If any entry was excluded by the rules above, add an `assumption` note to `spider_strategy.notes` explaining the skip.

## Reporting

In the final response, include:

- Artifact paths.
- Whether analysis used CDP or another browser-rendered method.
- API/XHR availability.
- First-page item count and titles when requested.
- Detail selectors.
- Spider-generation notes and risks.

For CDP/browser command patterns and compact extraction snippets, read [references/cdp_browser_analysis.md](references/cdp_browser_analysis.md).
