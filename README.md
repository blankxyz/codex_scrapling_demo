# Codex Spider Agent Workflow

你要的模式是 **Agent 工作流**：由 `codex exec` 分阶段推进并可自动修复迭代。

## Agent 流程
`Analyze -> Generate -> Validate -> Repair(loop) -> Validate`

- 每个阶段都由 Codex 执行
- 验证失败时自动进入 Repair，再次验证
- 日志保存到 `out/<site_slug>/agent_logs/`

## 推荐用法

```bash
./scripts/run_codex_spider_agent.sh <site_slug> <list_url> <template_json> [model] [max_repair_rounds]
```

示例：

```bash
./scripts/run_codex_spider_agent.sh \
  yntv-cn \
  "https://mmr.yntv.cn/mmr/tplby.html?sectionid=89&page=1" \
  /abs/path/to/template.json \
  gpt-5.4 \
  3
```

## 产物
- `spiders/<site_slug>.py`
- `out/<site_slug>/analysis.md`
- `out/<site_slug>/analysis.json`
- `out/<site_slug>/validation.json`
- `out/<site_slug>/agent_logs/*.txt`

## Prompt 模板
- `prompts/agent/analyze.md`
- `prompts/agent/generate.md`
- `prompts/agent/validate.md`
- `prompts/agent/repair.md`

这些模板可按你的业务继续收紧约束。
