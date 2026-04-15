# Stage: Generate

你现在只做生成阶段。

输入:
- site_slug: {{SITE_SLUG}}
- list_url: {{LIST_URL}}
- output_template_json: {{TEMPLATE_JSON}}
- analysis_file: out/{{SITE_SLUG}}/analysis.json
- pdr: docs/pdr.md

要求:
1. 生成 spiders/{{SITE_SLUG}}.py
2. 必须使用 Scrapling（Fetcher/DynamicFetcher + page.css），禁止 bs4/lxml。
3. 输出字段严格对齐模板 JSON。
4. 结构尽量简洁，包含 parse_list / parse_detail。
