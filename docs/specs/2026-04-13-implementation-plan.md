# 实施计划：列表页→详情页 交互式标记工具

设计文档：`docs/specs/2026-04-13-interactive-marker-design.md`

## 步骤

### 1. 安装依赖
在 `requirements.txt` 末尾追加：
```
rich>=13.0
questionary>=2.0
```

### 2. 修改 `demo_marker_extractor.py`

**2a. 改造 `_list_link_candidates`**
- preview 改为展示前 2-3 条链接的文本和 href（当前只是 "N links"）
- 候选 dict 新增 `sample_links` 字段：前 3 条链接的 `[{text, href}, ...]`
- 供 `interactive_session.py` 提取 `detail_url` 和展示用

**2b. 改造 `_build_prompt`**
- 当 marker 中存在 `confirmed` 块时，prompt 增加指示："优先使用 confirmed 中的选择器，候选列表仅作回退参考"

### 3. 新建 `ui.py`
纯展示层，使用 rich，无业务逻辑：
- `show_header()` — banner
- `show_spinner(message)` — `Console.status()` 旋转动画（不是进度条，因为 fetch 是同步阻塞无回调）
- `show_candidates_table(field_name, candidates)` — rich Table，列：序号、预览文本、评分
- `show_link_candidates_table(candidates)` — 链接候选专用表格，展示每组前 2-3 条链接文本+href
- `show_confirmed_summary(confirmed: dict)` — 绿色汇总面板
- `show_next_steps(output_path)` — 完成后提示
- `show_error(message)` — 红色 Panel 错误信息

### 4. 新建 `interactive_session.py`
核心类 `InteractiveSession.run(url, render, max_candidates)`，三阶段：

**阶段 1 — 列表页**
- `show_spinner` 包裹 `fetch_html` + `analyze_html`（复用 `demo_marker_extractor`）
- 若非列表页：questionary confirm 提示
- `show_link_candidates_table` 展示 `list_link_candidates`（含链接文本+href）
- questionary select 选择或手动输入选择器
- 用 `urllib.parse.urljoin(list_url, href)` 拼接第 1 条链接为完整 `detail_url`

**阶段 2 — 详情页**
- `show_spinner` 包裹 `fetch_html(detail_url)` + `analyze_html`
- 依次处理 title / time / content：展示候选 → questionary select（选候选 / 跳过 / 手动输入）

**阶段 3 — 合并 & 保存**
- 合并两次分析结果：以详情页 marker 为主体，叠加 `list_url`、`detail_sample_url`、列表页的 `list_link_candidates`、`confirmed` 块
- `show_confirmed_summary`
- questionary confirm 保存
- 写入 `out/<site_slug>/marker.json` + `codex_prompt.txt`
- `show_next_steps`

错误处理：
- 抓取失败 → `show_error` 红色面板 + 建议 `--render dynamic`
- 候选为空 → 提示手动输入
- Ctrl+C → 捕获 KeyboardInterrupt，打印"已取消"，不残留空文件

### 5. 修改 `analyze_url.py`
- 改为 `InteractiveSession().run(url, render, max_candidates)`
- 保留 `--render`、`--max-candidates` 参数
- 顶层 `try/except KeyboardInterrupt` 捕获中断
- ~30 行

### 6. 修改 `.agents/skills/spider-authoring/SKILL.md`
在"你的任务"部分新增：
- 若 marker 含 `confirmed` 块，**优先使用 `confirmed` 中的选择器**
- `confirmed.list_link_selector` 用于列表页链接提取
- `confirmed.title_selector` / `time_selector` / `content_selector` 用于详情页

## 关键文件
- `demo_marker_extractor.py` — 改造 `_list_link_candidates` preview + `_build_prompt` 适配 confirmed
- `analyze_url.py` — 入口，精简，调用 InteractiveSession
- `ui.py` — 新建，展示层
- `interactive_session.py` — 新建，流程层
- `.agents/skills/spider-authoring/SKILL.md` — 更新 confirmed 指示

## 验证
```bash
uv pip install rich questionary
python analyze_url.py "https://某新闻列表页/"
```
- 链接候选展示链接文本+href（不是只显示数量）
- 选择后 detail_url 是完整 URL（相对路径已拼接）
- marker.json 的 confirmed 块有 4 个字段
- codex_prompt.txt 提到优先使用 confirmed
- Ctrl+C 干净退出，不残留空文件
- SKILL.md 包含 confirmed 相关指示
