# CDP Browser Analysis Notes

> 本文件为中文补充参考，供操作人员直接阅读。SKILL.md 为英文，用于模型触发；二者语义保持一致。

## CDP 连接失败 / 降级决策树

| 场景 | 判断 | 处理 |
|------|------|------|
| `No reachable CDP endpoint found` + 当前在 Codex 沙盒 | 沙盒看不到宿主机 loopback | 切到非沙盒重跑同一条命令，不重试 |
| `No reachable CDP endpoint found` + 非沙盒 | Chrome 未启动或端口未开 | 让用户运行 `./start_chrome_cdp.sh` 或手动启动 `--remote-debugging-port=9222` |
| CDP 可达但目标页显示挑战/验证页 | WAF / Cloudflare / 登录墙 | 让用户在可见 Chrome 里通过后，改用 `--reuse-open-tab --skip-networkidle` |
| 列表 XHR 抓不到但 DOM 已渲染 | 纯服务端渲染 | 设 `api.exists=false`，DOM 选择器记完整，session 改 `AsyncDynamicSession` |
| 列表 DOM 为空 | iframe 内嵌或滚动加载 | 记录 `wait_selector` 与滚动策略；仍无数据则停止并报告观察，不臆造选择器 |

## CDP Connection

`tools/cdp_probe.py` 自动探测可用的 CDP 地址，无需手动指定。探测优先级：
`--cdp-url` 参数值 → `$CHROME_CDP_URL` 环境变量 → `127.0.0.1:9222` → Docker bridge `172.17.0.1-20:9222`。

若要覆盖探测结果，设置环境变量 `CHROME_CDP_URL` 或传入 `--cdp-url` 参数。
连接成功后，浏览器观测应包含渲染 DOM 和网络响应。

CDP 分析优先使用非沙盒执行。只有在调用链明确要求沙盒时，才把它当成受限运行。

如果报错 `No reachable CDP endpoint found`，先把它当成“当前执行环境连不到本地 CDP”而不是“站点打不开”：

- Codex 沙盒里的命令可能看不到宿主机 loopback 上的 `127.0.0.1:9222`。
- 这时应优先改为非沙盒重跑同一条探测命令，而不是继续在沙盒里重复尝试。

### CDP 地址自动探测

`cdp_probe.py` 按以下优先级自动探测，无需手动干预：

1. `--cdp-url` 参数（或 `$CHROME_CDP_URL` 环境变量）
2. `http://127.0.0.1:9222`
3. Docker bridge 段 `172.17.0.1-20:9222`

> **注意**：容器内部 IP（如 `172.17.x.x`）可被自动发现，但若端口映射到 `127.0.0.1:9222`，该地址优先命中。

When Python is needed for browser probing in this repo, use only the local virtualenv interpreter:

```text
.venv/bin/python
```

Do not call `python` or `python3` for analysis helpers.

Prefer reusing the local generic probe before inventing a new site-specific script:

```bash
# CDP 地址自动探测，--cdp-url 可选（不传则自动发现）
env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
  .venv/bin/python tools/cdp_probe.py \
  --url "https://example.com/list.html" \
  --out analysis_outputs/_example_probe.json
```

如果这条命令在沙盒里失败且错误是“找不到可达 CDP 端点”，应直接把这条完整命令改为非沙盒执行后重跑。

如果用户已经在可见 Chrome 窗口里打开并通过了前置校验，优先复用那个已打开标签页：

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
  .venv/bin/python tools/cdp_probe.py \
  --reuse-open-tab \
  --skip-networkidle \
  --url "https://example.com/list.html" \
  --out analysis_outputs/_example_probe.json
```

要点：

- `--reuse-open-tab` 会附着到已打开的匹配标签页，而不是新开自动化页。
- `--skip-networkidle` 适合视频页、播放器页、统计脚本较多的页面。
- 如果同站点有多个相近标签页，可加 `--tab-url-prefix` 显式指定匹配前缀。

Write a one-off probe only when this generic tool cannot expose the interaction you need.

## Evidence Rules

- Browser-captured network requests are valid evidence.
- Browser-rendered DOM is valid evidence.
- A curl command copied by the user from DevTools is valid as a clue, but do not rely on replaying it as the primary analysis method.
- Search engine snippets are not evidence for this skill.
- Direct target HTTP requests outside the browser are not evidence for this skill.

## Things To Extract

List page:

- `document.title`
- visible column heading
- item/link selectors
- first-page title list（去噪/顺序/去重规则见 SKILL.md `### list.first_page_titles rules`）
- publish-time text
- list API/XHR request and response shape

Detail page:

- title selector
- metadata selector
- content selector
- publish time/source/view regexes
- duplicate content behavior

## 推荐 spider 运行时分层

分析阶段必须用浏览器采证据；分析结果按以下层级选最轻的 spider 运行时：

| Tier | runtime_tier | session | 判据 |
|------|--------------|---------|------|
| A | `api` | `AsyncFetcher` | 有可重放 JSON 列表 API，无浏览器动态 token |
| B | `fetcher-html` | `AsyncFetcher` | 列表在首屏 HTML 中（view-source 可见）且无挑战页 |
| C | `browser` | `AsyncStealthySession` / `AsyncDynamicSession` | 需要浏览器才能渲染 / 过检 / 取 token |

必须在 `spider_strategy.notes` 里加 `"decision: ..."` 说明为何选这一层；选 C 时还要加 `"risk: ..."` 解释 A/B 被排除的原因。

## Common Government Site Pattern

Some sites build list data with a browser-only token:

```text
/common/search/<channelId>?<dynamic_token>&_isAgg=true&_isJson=true&_pageSize=20&_template=index&page=1
```

For spider generation, prefer Scrapling browser `capture_xhr="/common/search/"` instead of reconstructing the token.

## Slug 生成规则

slug 不统一会导致下游 spider 文件名和 Prefect flow name 漂移，请严格按以下步骤生成：

1. 取列表页 URL 的 `host` + `"/"` + `path`。
2. 将 `.` 和 `/` 全部替换为 `-`。
3. 去掉首尾 `-`。
4. 如果结果以 `-html` 或 `-shtml` 结尾，去掉该后缀。
5. 全部小写。

示例：
- `www.hngrrb.cn/shizheng/` → `www-hngrrb-cn-shizheng`
- `gdj.gansu.gov.cn/gdj/c109213/` → `gdj-gansu-gov-cn-gdj-c109213`
- `www.zhengguannews.cn/list/17.html` → `www-zhengguannews-cn-list-17`

## Output Discipline

每个 slug 一个子目录 `analysis_outputs/<slug>/`，内部文件名固定：

- `analysis.md` — 人类可读报告
- `analysis.json` — 机读 artifact，顶层须含 `"schema_version": "1"`
- `_probe.json` — CDP 中间探针
- `_detail_probe.json` — 抽样详情页时可选产出

重新分析一站：`rm -rf analysis_outputs/<slug>/`。写文件前记得 `mkdir -p`。
