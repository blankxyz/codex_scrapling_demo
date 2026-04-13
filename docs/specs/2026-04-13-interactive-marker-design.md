# 设计文档：列表页→详情页 交互式标记工具

## Context

现有 `analyze_url.py` 只能分析单个 URL 并输出候选 CSS 选择器，没有交互界面，需要用户懂爬虫才能使用。目标是改造成一个完全引导式的 TUI 工具：用户只给一个列表页 URL，系统自动跟进详情页，逐字段让用户用方向键确认，最终输出可直接交给 Codex 生成 spider 的 `marker.json`。

---

## 新增依赖

在 `requirements.txt` 追加：
```
rich>=13.0
questionary>=2.0
```

---

## 文件改动

### 1. 修改 `demo_marker_extractor.py`

**改动 1：`_list_link_candidates` 的 preview 增加链接文本和 href**

当前 preview 只是 `"5 links"`，用户无法区分不同候选组。改为展示前 2-3 条链接的文本和 href：

```
[1] 关于印发xxx的通知 → /news/2026/04/123.html
[2] 市政府召开会议xxx → /news/2026/04/124.html
(共 12 条链接)
```

同时在候选 dict 中新增 `sample_links` 字段（前 3 条链接的 `{text, href}` 列表），供 `interactive_session.py` 提取 `detail_url` 时使用。

**改动 2：`_build_prompt` 适配 `confirmed` 块**

当 marker 中存在 `confirmed` 块时，prompt 应明确指示 Codex："优先使用 `confirmed` 中的选择器，候选列表仅作回退参考"。

### 2. 新建 `ui.py`

Rich 渲染组件，纯展示，无业务逻辑：

- `show_header()` — 启动时打印项目标题 banner
- `show_spinner(message)` — 返回 `rich.console.Console.status()` context manager，显示旋转动画（注意：`fetch_html` 是同步阻塞调用，无进度回调，不适合用进度条，只能用 spinner）
- `show_candidates_table(field_name, candidates)` — 用 rich Table 展示候选列表，列：序号、预览文本、评分
- `show_link_candidates_table(candidates)` — 专门展示链接候选组，显示每组的前 2-3 条链接文本和 href
- `show_confirmed_summary(confirmed: dict)` — 最终汇总面板，绿色显示所有已确认字段
- `show_next_steps(output_path)` — 完成后提示用户下一步（生成 spider）
- `show_error(message)` — 红色 Panel 展示错误信息

### 3. 新建 `interactive_session.py`

三阶段 TUI 流程，核心类 `InteractiveSession`：

```python
class InteractiveSession:
    def run(self, url: str, render: str = "auto", max_candidates: int = 4) -> dict
```

**阶段 1 — 列表页分析**
1. 用 `show_spinner` 包裹 `fetch_html(url)` 调用
2. 调用 `analyze_html()` (来自 `demo_marker_extractor`)
3. 若 `page_type != "list_or_index"`：用 questionary confirm 询问用户"看起来不像列表页，继续吗？"
4. 用 `show_link_candidates_table` 展示 `list_link_candidates`（最多 `max_candidates` 条），每个候选展示链接文本+href
5. questionary select 让用户选择正确的链接候选，或选"都不对，我来输入 CSS 选择器"
6. 记录 `confirmed["list_link_selector"]`
7. 从候选的 `sample_links` 中取第 1 条链接 href，用 `urllib.parse.urljoin(list_url, href)` 拼接成完整 URL → `detail_url`

**阶段 2 — 详情页分析**
1. 用 `show_spinner` 包裹 `fetch_html(detail_url)` 调用
2. 调用 `analyze_html()`
3. 依次处理三个字段：`title`、`time`、`content`
   - 对每个字段：
     - `show_candidates_table(field, candidates)`
     - questionary select：选候选 / "跳过此字段" / "手动输入选择器"
     - 若手动输入：questionary text，提示"请输入 CSS 选择器"
   - 记录到 `confirmed["title_selector"]` 等

**阶段 3 — 确认 & 保存**
1. **合并两次分析结果**：以详情页的 marker 为主体，覆盖以下字段：
   - `list_url` = 列表页 URL
   - `detail_sample_url` = detail_url
   - `list_link_candidates` = 列表页的候选（来自阶段 1）
   - `confirmed` = 用户确认的全部选择器
2. `show_confirmed_summary(confirmed)` 展示汇总
3. questionary confirm "保存 marker.json？"
4. 保存到 `out/<site_slug>/marker.json`
5. 同时更新 `codex_prompt.txt`（使用改造后的 `_build_prompt`）
6. `show_next_steps(output_path)`

**错误处理**：
- 抓取失败：`show_error()` 红色面板 + 建议使用 `--render dynamic`，退出
- 候选为空：提示"未找到候选，请手动输入选择器"
- Ctrl+C / KeyboardInterrupt：捕获后打印"已取消"并干净退出，不残留空文件

### 4. 修改 `analyze_url.py`

- 改为调用 `InteractiveSession().run(url, render, max_candidates)`
- 保留 `--render` 和 `--max-candidates` 参数
- 顶层 `try/except KeyboardInterrupt` 捕获中断
- 整个文件压缩到 ~30 行

### 5. 修改 `.agents/skills/spider-authoring/SKILL.md`

在"你的任务"部分新增指示：
- 若 marker 中包含 `confirmed` 块，**优先使用 `confirmed` 中的选择器**，候选列表仅作回退参考
- `confirmed.list_link_selector` 用于列表页翻页/链接提取
- `confirmed.title_selector` / `time_selector` / `content_selector` 用于详情页字段提取

---

## marker.json 结构扩展

在现有字段基础上，顶层新增 `confirmed` 块和列表页信息：

```json
{
  "site_slug": "example-com",
  "list_url": "https://example.com/news/",
  "detail_sample_url": "https://example.com/news/article-1",
  "page_type": "detail",
  "confirmed": {
    "list_link_selector": "ul.news-list a",
    "title_selector": "h1.article-title",
    "time_selector": "time[datetime]",
    "content_selector": "div.article-body"
  },
  "fetch_meta": {},
  "signals": {},
  "title_candidates": [],
  "time_candidates": [],
  "content_candidates": [],
  "list_link_candidates": [],
  "notes": []
}
```

- `confirmed` 是 Codex spider-authoring skill 的权威输入
- `list_url` + `detail_sample_url` 记录分析来源
- 其余候选列表保留作备用参考

---

## Codex CLI 一键模板

为支持“不同站点/不同目录结构”的复用执行，根目录新增参数化模板脚本：

- [codex_spider_run_template.sh](/home/blank/bohui_lab/codex_scrapling_demo/codex_spider_run_template.sh)

脚本用途：
- 调用 `codex exec` 非交互执行
- 动态读取 `marker` / `schema` 路径
- 自动完成 spider 生成、测试生成、全量抓取、JSON 输出

示例（可直接复制）：

```bash
./codex_spider_run_template.sh \
  --site-slug henan-gov-cn \
  --list-url https://gd.henan.gov.cn/sy/tz/ \
  --marker out/henan-gov-cn/marker.json \
  --schema schemas/news_article.schema.json \
  --spider spiders/henan-gov-cn.py \
  --test tests/test_henan-gov-cn.py \
  --output out/henan-gov-cn/crawl_results.json
```

参数说明：
- `--site-slug`：站点标识（用于上下文提示）
- `--list-url`：列表页入口 URL
- `--marker`：本次交互生成的 marker 文件路径
- `--schema`：统一文章 schema 路径
- `--spider`：输出 spider 文件路径
- `--test`：输出测试文件路径
- `--output`：爬取结果 JSON 路径

如果仅想复跑现有 spider 导出 JSON，可直接运行一次性命令：

```bash
cat <<'PROMPT' | codex exec --cd /home/blank/bohui_lab/codex_scrapling_demo --skip-git-repo-check -
Run the existing spider in spiders/henan-gov-cn.py to crawl all article links from its list page,
save results to out/henan-gov-cn/crawl_results.json, and print total/success/error counts.
PROMPT
```

---

## 验证方式

```bash
uv pip install rich questionary
python analyze_url.py "https://www.example-news.com/news/"
```

- 阶段 1：链接候选展示**链接文本+href**（不是只显示数量），用户能区分
- 阶段 1：选择后 `detail_url` 是完整 URL（相对路径已正确拼接）
- 阶段 2：每个字段候选非空，预览文本可读
- 阶段 3：`marker.json` 写入成功，`confirmed` 块完整
- 验证 `codex_prompt.txt` 中提到优先使用 `confirmed` 选择器
- 验证 Ctrl+C 能干净退出，不残留空文件
- 验证 SKILL.md 已包含 `confirmed` 相关指示
