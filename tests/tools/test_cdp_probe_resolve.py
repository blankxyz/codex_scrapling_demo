import os
import urllib.error
from unittest.mock import patch, MagicMock
import pytest


# 导入目标模块（此时 resolve_cdp_url 还不存在，测试会失败）
from tools.cdp_probe import resolve_cdp_url


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
