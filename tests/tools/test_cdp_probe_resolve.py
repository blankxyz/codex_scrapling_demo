import os
import urllib.error
from unittest.mock import patch, MagicMock
import pytest


# 导入目标模块（此时 resolve_cdp_url 还不存在，测试会失败）
from tools.cdp_probe import resolve_cdp_url


def _mock_urlopen_success(url, timeout=None):
    """模拟 urlopen 成功返回。"""
    return MagicMock()


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


def test_returns_hint_when_it_responds(monkeypatch):
    """hint 地址能通时直接返回它，不尝试其他候选。"""
    monkeypatch.delenv("CHROME_CDP_URL", raising=False)
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


def test_raises_when_all_fail(monkeypatch):
    """所有候选地址不通时抛出 RuntimeError，错误信息包含沙盒排障提示。"""
    monkeypatch.delenv("CHROME_CDP_URL", raising=False)
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
        with pytest.raises(RuntimeError) as excinfo:
            resolve_cdp_url("http://127.0.0.1:9222")

    message = str(excinfo.value)
    assert "No reachable CDP endpoint found" in message
    assert "Codex sandbox" in message
    assert "docker-brave CDP backend" in message


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
