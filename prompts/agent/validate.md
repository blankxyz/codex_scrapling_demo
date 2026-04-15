# Stage: Validate

你现在只做验证阶段。

输入:
- site_slug: {{SITE_SLUG}}
- list_url: {{LIST_URL}}
- output_template_json: {{TEMPLATE_JSON}}
- spider_file: spiders/{{SITE_SLUG}}.py

要求:
1. 运行 python -m py_compile spiders/{{SITE_SLUG}}.py
2. 抽样执行 parse_list + parse_detail（至少 1 条）
3. 校验模板要求字段
4. 写入 out/{{SITE_SLUG}}/validation.json，格式:
{
  "ok": true/false,
  "site_slug": "...",
  "required_fields": [...],
  "missing_fields": [...],
  "sample_url": "...",
  "notes": "..."
}
