---
name: scrapling-analysis-to-prefect-generator
description: Generate a Prefect-based spider directly from Scrapling analysis outputs while keeping Scrapling as the crawler foundation. Use when the user wants to go from `analysis_outputs/*` straight to a target Prefect project without first materializing an intermediate local Scrapling spider file.
---

# Scrapling Analysis To Prefect Generator

## Goal

Generate a runnable Prefect spider directly from `analysis_outputs/*` with minimal behavior drift from the analyzed site.

This merged path still uses Scrapling as the crawler base library:

- Prefect replaces orchestration only.
- Fetching, rendering, selector parsing, and list/detail traversal must still use Scrapling.
- Do not generate a Prefect spider backed by `requests`, `httpx`, `aiohttp`, `urllib`, raw Playwright, or Selenium unless the user explicitly asks for a non-Scrapling rewrite.
- Do not add `real_chrome` or `SCRAPLING_REAL_CHROME` to generated code.

## Inputs

Use these sources in order:

1. Current user request, especially target Prefect project path, desired output path, sink/storage choice, explicit `accountcode`, and whether the spider should remain first-page only.
2. `analysis_outputs/*_analysis.json` for API findings, selectors, page shape, and strategy notes.
3. `analysis_outputs/*_analysis.md` when the JSON omits useful caveats or extraction details.
4. Existing spiders in the target Prefect project with similar site shape or sink usage.
5. Local Scrapling spider patterns in this repo when choosing the correct session/fetch style.

If Python is needed during generation or validation, use only `.venv/bin/python`.

## Workflow

1. Identify the analysis artifact and target file:
   - Prefer an explicit `analysis_outputs/..._analysis.json` from the user or pipeline.
   - Write the Prefect spider to the user-specified target project, typically `<target_repo>/spiders/<slug>_spider.py`.

2. Derive the crawler strategy from analysis:
   - Preserve first-page scope unless the user explicitly requests pagination.
   - If analysis found a stable list API, implement it with Scrapling HTTP/session calls.
   - If analysis requires rendering, XHR capture strategy, or anti-bot handling, implement it with Scrapling browser-backed sessions.
   - Preserve section coverage, detail selectors, and item schema from analysis.

3. Build a Prefect structure on top of Scrapling:
   - Use `@task` and `@flow` for orchestration.
   - Keep list fetch, detail fetch, and item-build helpers as small top-level functions.
   - Use Scrapling sessions/selectors inside those functions.
   - Carry list metadata into detail processing with plain dicts, mirroring what a Scrapling spider would otherwise place in `response.meta`.

4. Choose the Scrapling fetch layer intentionally:
   - For static/API flows, prefer `FetcherSession` or the target project's equivalent Scrapling wrapper.
   - For rendered pages, prefer `AsyncDynamicSession`.
   - For protected pages that need stealth, prefer `AsyncStealthySession`.
   - Reuse `Selector` when nearby project code parses raw HTML outside the `Spider` callback model.

5. Choose storage intentionally:
   - Default to `common.result_sink.save_items_to_sinks` when the generated items already match the desired business schema.
   - Use `common.spider_store.store_spider_results_sync` only when the user explicitly wants normalized storage or the target project clearly requires it.
   - Reuse target-project dedupe helpers when nearby spiders already filter by URL before detail fetch.

6. Save and validate:
   - Write the generated Prefect spider directly to the exact target file requested by the user.
   - Returning code in chat without creating the file is a failure.
   - Run `.venv/bin/python -m py_compile <target_file>`.
   - If feasible, run a narrow local validation of one list fetch and one detail fetch.
   - Report the chosen Scrapling session type, sink choice, and whether the output stayed first-page only.

## Hard Rules

- Do not generate an intermediate non-Scrapling crawler and then port that into Prefect.
- Do not replace Scrapling with generic HTTP or browser libraries unless the user explicitly requests that.
- Do not introduce pagination that the analysis or user request did not require.
- Do not silently change storage semantics.
- Do not drop or overwrite an explicit user-provided `accountcode`.
- Do not claim success until at least `py_compile` passes.
- Do not stop after printing code; the requested Prefect spider file must actually be created on disk.

## References

- For Scrapling crawler/session patterns, read [../scrapling-spider-generator/references/scrapling_spider_patterns.md](../scrapling-spider-generator/references/scrapling_spider_patterns.md).
- For Prefect sink selection and structure, read [../scrapling-to-prefect-generator/references/prefect_demo_conversion.md](../scrapling-to-prefect-generator/references/prefect_demo_conversion.md).
