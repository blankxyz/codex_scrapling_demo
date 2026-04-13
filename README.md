# Codex + Scrapling 无标注提标记 Demo

这个 demo 的目标不是“直接让模型在线提取网页数据”，而是先自动从网页里提取一份 `marker.json`：
- 页面类型推断
- 标题/时间/正文/列表链接 的候选 CSS 选择器
- 结构信号（有无 `<article>` / `<time>` 等）
- 可直接喂给 Codex 的 prompt

然后再由 Codex 依据 `marker.json` + 统一 schema 生成稳定的 Scrapling spider、测试和 fixtures。

## 设计思路

- **Scrapling 负责抓页面**  
  静态页优先 `Fetcher`，需要渲染时再切 `DynamicFetcher`。Scrapling 官方文档说明，从 v0.3 开始 fetcher 会保持 session，不必每次都重开浏览器。  
- **本 demo 负责自动提候选“标记”**  
  不是只找一个 selector，而是提取多组候选选择器，便于后续由 Codex 做“定稿”。
- **Codex 负责产出工程化代码**  
  本仓库自带 `.agents/skills/spider-authoring/SKILL.md`，Codex 在当前目录启动时就能扫描到这个技能目录。

## 目录

- `analyze_url.py`：输入 URL，输出 `marker.json` 和 `codex_prompt.txt`
- `demo_marker_extractor.py`：标记提取逻辑
- `schemas/news_article.schema.json`：统一输出 schema
- `.agents/skills/spider-authoring/SKILL.md`：给 Codex 的技能
- `out/`：分析结果输出目录

## 安装

推荐 Python 3.11：

```bash
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
```

## 使用

### 1) 先跑自动提标记

```bash
python analyze_url.py "https://example.com/article/123"
```

如果你怀疑是 JS 页面：

```bash
python analyze_url.py "https://example.com/article/123" --render dynamic
```

程序会输出：
- `out/<slug>/marker.json`
- `out/<slug>/codex_prompt.txt`

### 2) 再让 Codex 基于 marker 生成 spider

先安装 Codex CLI（官方文档示例）：

```bash
npm i -g @openai/codex
```

在本项目根目录运行：

```bash
codex
```

然后把 `out/<slug>/codex_prompt.txt` 的内容贴给 Codex，或者直接把核心要求粘进去，让它：
- 读取 `marker.json`
- 读取 `schemas/news_article.schema.json`
- 使用 `spider-authoring` skill
- 生成 `spiders/<site>.py`
- 生成 `tests/test_<site>.py`
- 保存 fixture

## 期望效果

你不再需要“每个站点每个字段都手动点一遍”，而是：
1. 输入几个样本 URL
2. 自动提候选标记
3. 用 Codex 生成首版 extractor
4. 通过测试和样本回归来确认

## 注意

- 这是最小 demo，不是完整产品。
- 对复杂站点，候选 selector 不一定一次命中；本 demo 的价值在于把“人工逐字段标注”降到“审核候选 + 回归测试”。
- 若目标页面需要登录、验证码或复杂交互，请优先在独立 fetch 步骤中解决，再进入提标记流程。
