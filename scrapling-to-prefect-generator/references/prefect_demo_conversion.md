# Prefect Project Conversion Notes

## Core Difference

The main difference between repo `spiders/*.py` and a target Prefect project's `spiders/*.py` is not extraction logic. It is orchestration and storage.

- Repo Scrapling spiders:
  - use `scrapling.spiders.Spider`
  - use `Request(...)`
  - yield items directly from callbacks
- target Prefect project spiders:
  - use `@task` and `@flow`
  - fetch list/detail pages in plain Python functions
  - collect `list[dict]` items, then write them through a sink

Keep extraction logic as similar as possible. Change the control plane, not the business logic.

## Preferred Output Shape

Typical converted spider layout:

```python
from prefect import flow, get_run_logger, task
from scrapling import Fetcher

@task
def fetch_list_entries() -> list[dict]:
    ...

@task
def fetch_details(entries: list[dict]) -> list[dict]:
    ...

@flow(name="...", log_prints=True)
def some_flow() -> list[dict]:
    entries = fetch_list_entries()
    items = fetch_details(entries)
    ...
    return items
```

For local/dev parity, reuse the nearby fallback pattern when present:

- `try: from prefect import ...`
- `except Exception: ... define pass-through decorators and logger`

Do not add this fallback if the surrounding target-project files for that sub-area do not use it.

## Sink Selection

### Default: `common.result_sink.save_items_to_sinks`

Use this when:

- the source Scrapling spider already produces final item dicts
- the user wants to preserve the original schema
- ClickHouse/Kafka style storage is acceptable

This is the usual choice for conversions from repo spiders that already emit ready-to-store records.

Typical pattern:

```python
saved = save_items_to_sinks(
    items,
    site_name=ACCOUNT_CODE,
    topic=KAFKA_TOPIC,
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
)
```

`save_items_to_sinks` stores the whole item dict as payload in ClickHouse and optionally publishes Kafka messages.

### Alternate: `common.spider_store.store_spider_results_sync`

Use this when:

- the user explicitly wants PostgreSQL-backed normalized storage
- the spider should store generic records instead of preserving the exact old item schema
- the target belongs to a workflow already built around `spider_results`

Typical pattern:

```python
count = store_spider_results_sync(
    records,
    spider_name="example-spider",
    default_source_name=ACCOUNT_CODE,
    default_item_type="item",
)
```

This path normalizes records into columns such as:

- `spider_name`
- `source_name`
- `item_type`
- `url`
- `published_at`
- `data`
- `raw_data`

Do not choose this path by accident. It changes persistence semantics.

## Accountcode Rule

If the user explicitly provides an `accountcode`, that value wins.

Priority order:

1. user-provided `accountcode`
2. source Scrapling spider constant
3. nearby target-project example constant only as a last resort

Do not silently keep the old constant when the user asked for a new one.
Do not invent a new `accountcode` if neither the user nor the source spider provides one.

## Dedupe

If nearby target-project spiders use URL-based filtering before detail fetch, preserve that behavior:

```python
new_entries = filter_new_items_by_url(entries, site_name=ACCOUNT_CODE)
```

This is usually the safest mapping from a first-page Scrapling spider into a Prefect spider.

## Mapping Rules

### Scrapling Spider class -> Prefect tasks/flow

- `start_requests()` -> `fetch_list_entries()`
- `parse()` -> list-page task logic
- `parse_detail()` -> detail task logic
- item builder helpers -> keep as plain helper functions
- `if __name__ == "__main__": spider.start()` -> `if __name__ == "__main__": flow_name()`

### Request metadata -> entry dict

If a Scrapling spider carries values through `response.meta`, convert that into per-entry dicts passed from list task to detail task:

```python
entries.append({
    "url": ...,
    "title": ...,
    "publish_time": ...,
    "column_name": ...,
})
```

Then in `fetch_details`, use those dict values the same way the old spider used `response.meta`.

### Session choice

In the target Prefect project, prefer:

- `Fetcher.get(...)` / `Fetcher.post(...)` for static HTTP flows
- browser tooling only when the source logic truly depends on rendering or browser-only XHR

Do not force Prefect spiders to use browser automation just because the original analysis used CDP.

## First-Page Rule

If the source Scrapling spider was first-page only, keep it first-page only.

If the source spider used `SECTIONS`, preserve section coverage but apply the same page scope per section:

- section list stays
- page scope stays page 1 unless the source already paginated

Do not expand “multiple sections” into “all pages of all sections.”

## Validation

Always run:

```bash
.venv/bin/python -m py_compile <target_repo>/spiders/<target>.py
```

When feasible, run a narrow sample path:

- one list fetch
- one detail fetch
- one sink invocation or dry run

Validation should confirm:

- item schema is preserved
- sink choice is intentional
- first-page behavior is preserved
- section coverage is preserved
