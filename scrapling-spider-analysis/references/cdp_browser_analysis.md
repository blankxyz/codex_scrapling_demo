# CDP Browser Analysis Notes

## CDP Connection

`tools/cdp_probe.py` 自动探测可用的 CDP 地址，无需手动指定。探测优先级：
`--cdp-url` 参数值 → `$CHROME_CDP_URL` 环境变量 → `127.0.0.1:9222` → Docker bridge `172.17.0.1-20:9222`。

若要覆盖探测结果，设置环境变量 `CHROME_CDP_URL` 或传入 `--cdp-url` 参数。
连接成功后，浏览器观测应包含渲染 DOM 和网络响应。

CDP 分析优先使用非沙盒执行。只有在调用链明确要求沙盒时，才把它当成受限运行。

如果报错 `No reachable CDP endpoint found`，先把它当成“当前执行环境连不到本地 CDP”而不是“站点打不开”：

- Codex 沙盒里的命令可能看不到宿主机 loopback 上的 `127.0.0.1:9222`。
- 这时应优先改为非沙盒重跑同一条探测命令，而不是继续在沙盒里重复尝试。
- 如果项目环境本来就提供 Docker Brave CDP，优先切到 `docker-brave` 后端，因为它更容易通过 Docker bridge 被探测到。

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
- first-page title list
- publish-time text
- list API/XHR request and response shape

Detail page:

- title selector
- metadata selector
- content selector
- publish time/source/view regexes
- duplicate content behavior

## Common Government Site Pattern

Some sites build list data with a browser-only token:

```text
/common/search/<channelId>?<dynamic_token>&_isAgg=true&_isJson=true&_pageSize=20&_template=index&page=1
```

For spider generation, prefer Scrapling browser `capture_xhr="/common/search/"` instead of reconstructing the token.

## Output Discipline

Always save both:

- `analysis_outputs/${SLUG}_analysis.md`
- `analysis_outputs/${SLUG}_analysis.json`

Keep JSON stable enough for the generator skill to read automatically.
