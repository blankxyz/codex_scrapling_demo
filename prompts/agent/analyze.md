# Stage: Analyze

你现在只做分析阶段，不做代码生成。

输入:
- site_slug: {{SITE_SLUG}}
- list_url: {{LIST_URL}}
- output_template_json: {{TEMPLATE_JSON}}
- pdr: docs/pdr.md

要求:
1. 访问真实网页，至少覆盖 1 个列表页 + 1 个详情页。
2. 优先动态渲染分析；识别可用 API（若有）。
3. 输出分析文档到: out/{{SITE_SLUG}}/analysis.md
4. 输出结构化分析到: out/{{SITE_SLUG}}/analysis.json

analysis.json 至少包含:
- site_slug
- list_url
- requires_dynamic
- api_candidates
- list_link_selectors
- title_selectors
- time_selectors
- content_selectors
- sample_detail_urls
