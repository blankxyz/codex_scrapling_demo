# Stage: Repair

你现在只做修复阶段。

输入:
- site_slug: {{SITE_SLUG}}
- list_url: {{LIST_URL}}
- output_template_json: {{TEMPLATE_JSON}}
- spider_file: spiders/{{SITE_SLUG}}.py
- analysis_file: out/{{SITE_SLUG}}/analysis.json
- validation_file: out/{{SITE_SLUG}}/validation.json

当前验证失败信息:
{{VALIDATION_SUMMARY}}

要求:
1. 仅修改必要代码来修复失败项。
2. 优先修复字段缺失、错误 selector、动态/静态抓取策略。
3. 修复后不做最终总结，由外部流程再次调用 validate 阶段。
