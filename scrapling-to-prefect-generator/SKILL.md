---
name: scrapling-to-prefect-generator
description: Convert an existing Scrapling spider in this repo into a Prefect-based spider for a separate target project, preserving list/detail extraction and output schema while adapting the entrypoint, task/flow structure, and storage layer to that project's conventions. Use when the user asks to port a generated Scrapling spider to a Prefect repo such as /home/blank/playground/prefect_demo, rewrite a spider into Prefect flow form, or align a scraper with a target Prefect project's common sinks and deployment style.
---

# Scrapling To Prefect Generator

## Goal

Convert a runnable Scrapling spider into a runnable Prefect spider in a separate target project with minimal behavior drift.

The conversion should preserve:

- source site coverage
- first-page or pagination scope
- list/detail extraction logic
- item schema and field names
- constants such as account codes, topics, and site names when provided

The conversion must adapt:

- `Spider` / `Request` orchestration into Prefect `@task` and `@flow`
- Scrapling spider class entrypoint into plain functions plus flow entrypoint
- storage and dedupe behavior to the target Prefect project's `common/*`

## Inputs

Use these sources in order:

1. Current user request, especially target spider, target Prefect project path, desired output path, explicit `accountcode`, and whether storage should go to ClickHouse/Kafka or PostgreSQL.
2. The source Scrapling spider the user wants converted.
3. Existing spiders in the target Prefect project with similar content type or site shape.
4. The target Prefect project's `common/*`, especially sink and helper modules.
5. `analysis_outputs/*` only when the source spider is missing context or selectors.

If Python is needed during conversion or validation, use only `.venv/bin/python`.

If a local Prefect Docker environment exists and the user asks for runnable verification, prefer validating inside that Docker environment in addition to local syntax checks.

## Workflow

1. Identify the source spider and target Prefect file:
   - Prefer converting from an existing `spiders/*.py` file, not from prose.
   - Write the converted spider under the user-specified target Prefect project, typically `<target_repo>/spiders/`.
   - Keep the filename aligned with the target Prefect project's naming conventions.

2. Read the source spider for stable behavior:
   - Extract list URLs, request method, pagination scope, selectors, helper functions, and item builders.
   - Preserve “first page only” behavior exactly. If the source spider uses `SECTIONS`, preserve section coverage but do not add pagination unless the source already had it or the user explicitly requests it.
   - Preserve schema key names and value types.
   - Treat an explicit user-provided `accountcode` as higher priority than the source spider's constant.

3. Choose the Prefect storage path:
   - Default to `common.result_sink.save_items_to_sinks` when the source spider already yields business-ready item dicts and the target should keep the same schema.
   - Use `common.spider_store.store_spider_results_sync` only when the user explicitly wants normalized PostgreSQL storage or when the target should store generic records instead of the original item schema.
   - Reuse `common.clickhouse_sink.filter_new_items_by_url` when the existing target-project spiders use URL-based dedupe before detail fetch.

4. Rewrite the spider structure:
   - Replace the Scrapling `Spider` class with small task functions such as `fetch_list_entries()` and `fetch_details(...)`.
   - Add one `@flow(..., log_prints=True)` function as the primary entrypoint.
   - Keep helper functions top-level and simple.
   - Prefer `scrapling.Fetcher` in the target Prefect project unless the existing local Prefect patterns for that site require browser automation.
   - Add Prefect fallback shims only if existing nearby spiders use them and the environment may run without Prefect installed.

5. Preserve item schema:
   - Do not rename or reorder item keys unless the user explicitly asks for Prefect-specific normalization.
   - If the source spider yields text items and video items, keep separate builders in the converted file.
   - Keep account code, source name, topic, and table constants explicit near the top of the file.
   - If the user provides `accountcode`, write that exact value into the converted spider and do not silently inherit a different value from the source spider or nearby Prefect examples.

6. Save and validate:
   - Run `.venv/bin/python -m py_compile <target_file>`.
   - If feasible, run the flow locally once or run the key task functions against a small sample.
   - If a local Prefect Docker environment is available, verify the converted spider in the running worker/container used by that environment.
   - For Docker verification, first confirm which container actually runs spider code, then copy the converted file into the container's active spider path and execute the flow there.
   - Prefer validating with Kafka disabled unless the user explicitly wants end-to-end Kafka verification.
   - Report whether the converted spider preserved first-page behavior, section behavior, and sink choice.
   - Report whether Docker validation was performed, which container/path was used, and whether data was actually written or filtered by dedupe.

## Hard Rules

- Do not introduce pagination that the source spider did not already have.
- Do not silently change storage semantics. State and implement either `result_sink` or `spider_store`.
- Do not replace the source item schema with a new schema just because a Prefect target project exists.
- Do not drop or overwrite an explicit user-provided `accountcode`.
- Do not add deployment scripts unless the user asks for them.
- Do not use system `python` or `python3`; use `.venv/bin/python` only.
- Do not assume the running Docker worker mounts the current repo. Verify the active container code path before testing.
- Do not claim the spider is runnable in Prefect until at least `py_compile` passes; if Docker verification was requested and available, run it there before claiming success.

## Reference

For conversion rules and sink selection, read [references/prefect_demo_conversion.md](references/prefect_demo_conversion.md).
