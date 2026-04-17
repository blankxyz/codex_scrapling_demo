# CDP Probe 健壮性改造 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `tools/cdp_probe.py` 在代理环境 + 非标准 CDP 地址下自动探测并连接，消除 WebSocket 被代理拦截的问题。

**Architecture:** 在 `cdp_probe.py` 中新增同步函数 `resolve_cdp_url(hint)`，进入时清除代理环境变量，然后顺序探测候选地址列表（hint → $CHROME_CDP_URL → 127.0.0.1:9222 → Docker bridge 172.17.0.1-20），返回第一个 `/json/version` 可达的地址。同步更新 SKILL.md 和 references 文档，移除硬编码地址描述。

**Tech Stack:** Python 3.11, urllib.request (stdlib), pytest, unittest.mock

---

## 文件结构

| 动作 | 路径 | 职责 |
|------|------|------|
| 新建 | `tests/tools/test_cdp_probe_resolve.py` | `resolve_cdp_url` 的单元测试 |
| 修改 | `tools/cdp_probe.py` | 新增 `resolve_cdp_url` + 代理清除 |
| 修改 | `scrapling-spider-analysis/SKILL.md` | 移除硬编码 CDP 地址描述 |
| 修改 | `scrapling-spider-analysis/references/cdp_browser_analysis.md` | 更新 CDP 连接说明和示例 |

---

### Task 1: 建立测试文件骨架

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/tools/__init__.py`
- Create: `tests/tools/test_cdp_probe_resolve.py`

- [ ] **Step 1: 创建测试文件骨架**

```bash
mkdir -p tests/tools
touch tests/__init__.py tests/tools/__init__.py
```

创建 `tests/tools/test_cdp_probe_resolve.py`：

```python
import os
import urllib.error
from unittest.mock import patch, MagicMock
import pytest


# 导入目标模块（此时 resolve_cdp_url 还不存在，测试会失败）
from tools.cdp_probe import resolve_cdp_url
```

- [ ] **Step 2: 确认导入失败**

```bash
.venv/bin/python -m pytest tests/tools/test_cdp_probe_resolve.py -v 2>&1 | head -20
```

预期：`ImportError: cannot import name 'resolve_cdp_url' from 'tools.cdp_probe'`

---

### Task 2: 实现 `resolve_cdp_url` 并通过测试

**Files:**
- Modify: `tools/cdp_probe.py`（在现有 import 块后、`build_parser` 前插入新函数）
- Test: `tests/tools/test_cdp_probe_resolve.py`

- [ ] **Step 1: 写失败测试——代理环境变量被清除**

在 `tests/tools/test_cdp_probe_resolve.py` 中追加：

```python
def _mock_urlopen_success(url, timeout=None):
    """模拟 urlopen 成功返回。"""
    mock = MagicMock()
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


def test_clears_proxy_env_vars(monkeypatch):
    """resolve_cdp_url 调用后代理环境变量应被清除。"""
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:7897")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:7897")
    monkeypatch.setenv("http_proxy", "http://127.0.0.1:7897")
    monkeypatch.setenv("https_proxy", "http://127.0.0.1:7897")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:7897")
    monkeypatch.setenv("all_proxy", "http://127.0.0.1:7897")

    with patch("urllib.request.urlopen", side_effect=_mock_urlopen_success):
        resolve_cdp_url("http://127.0.0.1:9222")

    for key in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
        assert key not in os.environ, f"{key} should have been cleared"
```

- [ ] **Step 2: 运行，确认失败**

```bash
.venv/bin/python -m pytest tests/tools/test_cdp_probe_resolve.py::test_clears_proxy_env_vars -v
```

预期：`ImportError` 或 `AttributeError`（函数未实现）

- [ ] **Step 3: 实现 `resolve_cdp_url`**

在 `tools/cdp_probe.py` 的 `import` 块（`from playwright...` 行之前）新增：

```python
import os
import urllib.request
import urllib.error
```

（若已有 `import os`，跳过该行。）

在 `build_parser` 函数定义之前插入：

```python
_PROXY_KEYS = [
    "HTTP_PROXY", "HTTPS_PROXY", "http_proxy",
    "https_proxy", "ALL_PROXY", "all_proxy",
]


def resolve_cdp_url(hint: str) -> str:
    """Clear proxy env vars and probe candidates to find the first live CDP endpoint."""
    for key in _PROXY_KEYS:
        os.environ.pop(key, None)

    seen: set[str] = set()
    candidates: list[str] = []

    def _add(addr: str) -> None:
        normalized = addr.rstrip("/")
        if normalized not in seen:
            seen.add(normalized)
            candidates.append(normalized)

    _add(hint)
    env_url = os.environ.get("CHROME_CDP_URL", "")
    if env_url:
        _add(env_url)
    _add("http://127.0.0.1:9222")
    for i in range(1, 21):
        _add(f"http://172.17.0.{i}:9222")

    errors: list[str] = []
    for addr in candidates:
        try:
            urllib.request.urlopen(f"{addr}/json/version", timeout=1.5)
            return addr
        except Exception as exc:
            errors.append(f"{addr}: {exc}")

    raise RuntimeError(
        "No reachable CDP endpoint found. Tried:\n"
        + "\n".join(f"  {e}" for e in errors)
    )
```

- [ ] **Step 4: 运行，确认代理测试通过**

```bash
.venv/bin/python -m pytest tests/tools/test_cdp_probe_resolve.py::test_clears_proxy_env_vars -v
```

预期：`PASSED`

---

### Task 3: 补全 `resolve_cdp_url` 的核心行为测试

**Files:**
- Modify: `tests/tools/test_cdp_probe_resolve.py`

- [ ] **Step 1: 追加测试——hint 优先**

```python
def test_returns_hint_when_it_responds():
    """hint 地址能通时直接返回它，不尝试其他候选。"""
    call_log: list[str] = []

    def mock_urlopen(url, timeout=None):
        call_log.append(url)
        if "127.0.0.1:9222" in url:
            return _mock_urlopen_success(url)
        raise urllib.error.URLError("unreachable")

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        result = resolve_cdp_url("http://127.0.0.1:9222")

    assert result == "http://127.0.0.1:9222"
    assert call_log == ["http://127.0.0.1:9222/json/version"]
```

- [ ] **Step 2: 追加测试——hint 不通时回落到 CHROME_CDP_URL**

```python
def test_falls_back_to_env_var(monkeypatch):
    """hint 不通时使用 $CHROME_CDP_URL 指定的地址。"""
    monkeypatch.setenv("CHROME_CDP_URL", "http://172.17.0.5:9222")

    def mock_urlopen(url, timeout=None):
        if "172.17.0.5:9222" in url:
            return _mock_urlopen_success(url)
        raise urllib.error.URLError("unreachable")

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        result = resolve_cdp_url("http://127.0.0.1:9222")

    assert result == "http://172.17.0.5:9222"
```

- [ ] **Step 3: 追加测试——全部失败时抛出 RuntimeError**

```python
def test_raises_when_all_fail():
    """所有候选地址不通时抛出 RuntimeError，错误信息包含候选列表。"""
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
        with pytest.raises(RuntimeError, match="No reachable CDP endpoint found"):
            resolve_cdp_url("http://127.0.0.1:9222")
```

- [ ] **Step 4: 追加测试——去重，同一地址不重复探测**

```python
def test_deduplicates_candidates(monkeypatch):
    """hint 与 127.0.0.1:9222 相同时，该地址只探测一次。"""
    monkeypatch.delenv("CHROME_CDP_URL", raising=False)
    call_log: list[str] = []

    def mock_urlopen(url, timeout=None):
        call_log.append(url)
        if "127.0.0.1:9222" in url:
            return _mock_urlopen_success(url)
        raise urllib.error.URLError("unreachable")

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        resolve_cdp_url("http://127.0.0.1:9222")

    assert call_log.count("http://127.0.0.1:9222/json/version") == 1
```

- [ ] **Step 5: 运行所有新测试，确认通过**

```bash
.venv/bin/python -m pytest tests/tools/test_cdp_probe_resolve.py -v
```

预期：4 个测试全部 `PASSED`

- [ ] **Step 6: commit**

```bash
git add tools/cdp_probe.py tests/
git commit -m "feat: add resolve_cdp_url with proxy clearing and auto-detection"
```

---

### Task 4: 接入 `main()` 并更新测试中的 import

**Files:**
- Modify: `tools/cdp_probe.py`（`main()` 函数内）

- [ ] **Step 1: 在 `main()` 里替换 CDP URL 来源**

找到 `main()` 内的以下代码（约第 154-155 行）：

```python
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(args.cdp_url)
```

替换为：

```python
    cdp_url = resolve_cdp_url(args.cdp_url)
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(cdp_url)
```

- [ ] **Step 2: 运行全部测试，确认无回归**

```bash
.venv/bin/python -m pytest tests/ -v
```

预期：全部 `PASSED`

- [ ] **Step 3: commit**

```bash
git add tools/cdp_probe.py
git commit -m "feat: wire resolve_cdp_url into cdp_probe main()"
```

---

### Task 5: 更新 SKILL.md

**Files:**
- Modify: `scrapling-spider-analysis/SKILL.md`

- [ ] **Step 1: 替换 Hard Rules 第 5 条**

找到：

```
- Default to Chrome CDP at `http://127.0.0.1:9222` without a separate health check.
```

替换为：

```
- Default to Chrome CDP. `tools/cdp_probe.py` auto-detects the available CDP endpoint (tries `$CHROME_CDP_URL`, `127.0.0.1:9222`, then Docker bridge range `172.17.0.1-20`). Do not hardcode the CDP address in prompts or commands.
```

- [ ] **Step 2: 替换 Workflow Step 2 调用示例**

找到 Step 2 内 `tools/cdp_probe.py` 的调用示例（形如 `.venv/bin/python tools/cdp_probe.py ...`），确保其以 `env -u` 前缀开头。若原文已有 `env -u` 前缀，检查是否包含全部 6 个 key；若没有则改为：

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
  .venv/bin/python tools/cdp_probe.py \
  --url "https://example.com/list.html" \
  --out analysis_outputs/_example_probe.json
```

- [ ] **Step 3: commit**

```bash
git add scrapling-spider-analysis/SKILL.md
git commit -m "docs: update SKILL.md to remove hardcoded CDP address"
```

---

### Task 6: 更新 `references/cdp_browser_analysis.md`

**Files:**
- Modify: `scrapling-spider-analysis/references/cdp_browser_analysis.md`

- [ ] **Step 1: 替换 CDP Connection 小节**

找到：

```
Use local Chrome CDP when the user has started it. Default to performing the real CDP action directly instead of probing health endpoints first:

```text
http://127.0.0.1:9222
```
```

替换为：

```
`tools/cdp_probe.py` 自动探测可用的 CDP 地址，无需手动指定。探测顺序：
`$CHROME_CDP_URL` → `127.0.0.1:9222` → Docker bridge `172.17.0.1-20:9222`。

若要覆盖探测结果，设置环境变量 `CHROME_CDP_URL` 或传入 `--cdp-url` 参数。
```

- [ ] **Step 2: 更新示例命令注释**

找到：

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy \
.venv/bin/python tools/cdp_probe.py \
  --url "https://example.com/list.html" \
  --out analysis_outputs/_example_probe.json
```

替换为（补全 6 个 key，并加说明注释）：

```bash
# CDP 地址自动探测，--cdp-url 可选（不传则自动发现）
env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
  .venv/bin/python tools/cdp_probe.py \
  --url "https://example.com/list.html" \
  --out analysis_outputs/_example_probe.json
```

- [ ] **Step 3: 删除或修正"始终使用 127.0.0.1:9222，不要使用容器 IP"小节**

该小节已不准确（工具现在自动探测）。将标题和描述改为：

```markdown
### CDP 地址自动探测

`cdp_probe.py` 按以下优先级自动探测，无需手动干预：

1. `--cdp-url` 参数（或 `$CHROME_CDP_URL` 环境变量）
2. `http://127.0.0.1:9222`
3. Docker bridge 段 `172.17.0.1-20:9222`

> **注意**：容器内部 IP（如 `172.17.x.x`）可被自动发现，但若端口映射到 `127.0.0.1:9222`，该地址优先命中。
```

- [ ] **Step 4: commit**

```bash
git add scrapling-spider-analysis/references/cdp_browser_analysis.md
git commit -m "docs: update cdp_browser_analysis.md to reflect auto-detection"
```

---

## 完成验证

在有代理环境（`HTTP_PROXY` 已设置）下运行：

```bash
# 全部单元测试
.venv/bin/python -m pytest tests/ -v

# 手动集成验证（CDP 需已启动）
env HTTP_PROXY=http://127.0.0.1:7897 HTTPS_PROXY=http://127.0.0.1:7897 \
  .venv/bin/python tools/cdp_probe.py \
  --url "https://example.com" \
  --out /tmp/cdp_test.json
cat /tmp/cdp_test.json | python -c "import sys,json; d=json.load(sys.stdin); print('OK:', d['cdp_url'])"
```

预期输出：`OK: http://<自动探测到的地址>:9222`
