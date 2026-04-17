# CDP Probe 健壮性改造设计

**日期**：2026-04-17  
**状态**：已批准，待实施

---

## 背景与问题

`scrapling-spider-analysis` 技能在以下环境组合下不稳定：

1. **CDP 地址不匹配**：技能硬编码 `127.0.0.1:9222`，但实际 Docker 容器可能暴露在 `172.17.x.x:9222`。
2. **代理拦截 WebSocket**：终端设置了 `HTTP_PROXY=http://127.0.0.1:7897`（Clash/v2ray 等本地代理）。Python 的 HTTP 客户端对非 `NO_PROXY` 白名单的地址（包括 `172.17.x.x`）会走代理，导致 Playwright 的 WebSocket 握手被拦截失败。

根因：`curl /json/version` 能通是因为 curl 对局域网地址默认绕过代理，而 Python 不做此判断。

---

## 目标

- `cdp_probe.py` 在任意环境下自动找到可用的 CDP 地址，无需用户手动指定。
- 消除代理对 CDP WebSocket 连接的干扰。
- 保持现有 list+detail 整体成功/失败语义不变。

---

## 非目标

- 不改动 `run_pipeline.sh`。
- 不增加 list/detail 分离落盘逻辑。
- 不引入并行探测（候选地址数量有限，顺序探测已足够）。

---

## 改造方案：Probe-in-Tool

### 1. `tools/cdp_probe.py`

新增 `resolve_cdp_url(hint: str) -> str` 函数，在 `main()` 里替换原来的直接使用 `args.cdp_url`。

**执行流程：**

```
1. 清除代理环境变量（进程级，影响后续 Playwright 连接）
   os.environ.pop 以下 key（存在则删，不存在忽略）：
   HTTP_PROXY, HTTPS_PROXY, http_proxy, https_proxy, ALL_PROXY, all_proxy

2. 构建候选地址列表（去重、保序）：
   a. hint（即 --cdp-url 参数值，默认 http://127.0.0.1:9222）
   b. 环境变量 $CHROME_CDP_URL（若存在且不同于 hint）
   c. http://127.0.0.1:9222（若前两项都不是它）
   d. Docker bridge：http://172.17.0.{1..20}:9222

3. 顺序探测：
   for addr in candidates:
       urllib.request.urlopen(addr + "/json/version", timeout=1.5)
       成功 → 返回 addr，停止
       失败 → 继续

4. 全部失败 → raise RuntimeError，错误信息包含已尝试的地址列表
```

**函数签名：**

```python
def resolve_cdp_url(hint: str) -> str:
    """清除代理并探测第一个可用 CDP 地址，失败时抛出 RuntimeError。"""
```

**调用位置**：`main()` 开头，`args = build_parser().parse_args()` 之后：

```python
cdp_url = resolve_cdp_url(args.cdp_url)
browser = await p.chromium.connect_over_cdp(cdp_url)
```

### 2. `scrapling-spider-analysis/SKILL.md`

两处改动（文字替换，不改结构）：

**Hard Rules 第 5 条**，从：
```
Default to Chrome CDP at `http://127.0.0.1:9222` without a separate health check.
```
改为：
```
Default to Chrome CDP. `tools/cdp_probe.py` auto-detects the available CDP endpoint
(tries $CHROME_CDP_URL, 127.0.0.1:9222, then Docker bridge range).
Do not hardcode the CDP address in prompts or commands.
```

**Workflow Step 2 的调用示例**，确保包含 `env -u` 前缀：
```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy \
  .venv/bin/python tools/cdp_probe.py \
  --url "..." \
  --out analysis_outputs/...
```

### 3. `scrapling-spider-analysis/references/cdp_browser_analysis.md`

两处改动：

- **CDP Connection 小节**：移除"使用 `http://127.0.0.1:9222`"的硬编码地址表述，改为说明工具自动探测，覆盖方式为 `$CHROME_CDP_URL` 或 `--cdp-url`。
- **示例命令**：保留现有 `env -u` 前缀格式，移除注释中"默认 `127.0.0.1:9222`"字样，改为"自动探测"。

---

## 改动范围汇总

| 文件 | 改动量 | 类型 |
|------|--------|------|
| `tools/cdp_probe.py` | +~40 行 | 新增函数 + 代理清除 |
| `scrapling-spider-analysis/SKILL.md` | ~5 行替换 | 文字更新 |
| `scrapling-spider-analysis/references/cdp_browser_analysis.md` | ~8 行替换 | 文字更新 |

---

## 测试验证

实施后，在有代理的环境（`HTTP_PROXY` 已设置）且 CDP 在非标准地址时，执行：

```bash
env -u HTTP_PROXY -u HTTPS_PROXY \
  .venv/bin/python tools/cdp_probe.py \
  --url "http://目标站点/列表页" \
  --out analysis_outputs/_test_probe.json
```

预期：工具自动找到可用 CDP 地址并成功输出 JSON，不报 WebSocket 连接错误。
