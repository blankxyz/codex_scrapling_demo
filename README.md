# Codex Scrapling Demo

This directory contains three local Codex skills for a browser-first Scrapling crawler workflow.

## Skills

### `scrapling-spider-analysis`

Use this skill to analyze a list page before writing a crawler.

Rules captured in the skill:

- Use browser/CDP evidence for analysis.
- Do not use search engines.
- Do not use non-browser target fetching as analysis evidence.
- Use only `.venv/bin/python` for analysis-time Python commands; do not fall back to system `python` or `python3`.
- Default to Chrome CDP at `http://127.0.0.1:9222` for analysis, without a separate preflight validation step.
- Prefer reusing the generic local probe script at `tools/cdp_probe.py` before writing a one-off probe.
- Save analysis results to `analysis_outputs/`.
- Produce crawler-ready selectors, XHR/API findings, first-page titles, detail selectors, and strategy notes.

Example prompt:

```text
使用当前目录的 $scrapling-spider-analysis 分析这个列表页，并把结果输出到 analysis_outputs：https://example.com/list.html
```

### `scrapling-spider-generator`

Use this skill to generate a runnable Scrapling spider from prior analysis outputs.

Rules captured in the skill:

- Read `analysis_outputs/*_analysis.json` and `analysis_outputs/*_analysis.md`.
- Prefer browser-captured XHR/API findings from analysis.
- Generate production spiders that do not depend on CDP.
- Use only `.venv/bin/python` for generator-time Python commands and validation; do not fall back to system `python` or `python3`.
- Use Scrapling dynamic rendering; prefer `AsyncStealthySession` for protected sites.
- Do not add pagination unless explicitly requested.
- If the generated spider uses `SECTIONS`, only the first page of each section should be fetched by default.
- Preserve the user-provided output schema.
- Every generated spider should include both text and video detail handling by default, and resolve the final type per detail page at runtime.
- Do not rely on one sampled detail page or local content fragment to conclude an entire section is text-only or video-only.
- Validate generated spider code with `py_compile`, and run it when feasible.

Example prompt:

```text
使用当前目录的 $scrapling-spider-generator，根据 analysis_outputs 里的分析结果生成 Scrapling 爬虫。
```

### `scrapling-to-prefect-generator`

Use this skill to convert an existing Scrapling spider in this repo into a Prefect spider for a separate target project such as `/home/blank/playground/prefect_demo/`.

Rules captured in the skill:

- Read the source spider first and preserve its extraction logic and item schema.
- Rewrite the entrypoint into Prefect `@task` / `@flow` structure at the user-specified target path.
- Adapt storage to the target Prefect project's `common/*`, choosing between `result_sink` and `spider_store` intentionally.
- Allow the user to explicitly specify `accountcode`, and preserve that exact value in the converted spider.
- Use only `.venv/bin/python` for conversion-time Python commands and validation.
- Do not add pagination unless the source spider already had it or the user explicitly asks for it.

## Recommended Workflow

1. Start Chrome CDP for analysis when needed:

```bash
./start_chrome_cdp.sh
```

2. Analyze a list page:

```text
使用当前目录的 $scrapling-spider-analysis 分析这个列表页，并把结果输出到 analysis_outputs：<list-url>
```

3. Generate the spider:

```text
使用当前目录的 $scrapling-spider-generator，根据 analysis_outputs/hinews-cn-module-b0ba0a6167674227932bbeca1cc20e77_analysis 里的分析结果生成 Scrapling 爬虫。只抓第一页。
```

4. Run the generated spider:

```bash
.venv/bin/python spiders/<generated_spider>.py
```

## Current Outputs

- Analysis files go in `analysis_outputs/`.
- Spider files go in `spiders/`.
- Converted Prefect spiders should go to the separate target project, not this repo.
- Local skills are stored in:
  - `scrapling-spider-analysis/`
  - `scrapling-spider-generator/`
  - `scrapling-to-prefect-generator/`

## Notes

- CDP is only for analysis unless explicitly requested otherwise.
- Runtime crawler environments may not have CDP. Generated spiders should rely on Scrapling's browser rendering, not a local debug endpoint.
- If normal dynamic rendering returns target-side `400` or similar anti-bot errors, use Scrapling stealth rendering in the generated spider.
- For similar detail pages at scale, avoid partial-sample assumptions: generated spiders should inspect each detail page for both article-text and video-player signals.
