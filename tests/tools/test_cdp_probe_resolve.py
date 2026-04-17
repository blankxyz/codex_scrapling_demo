import os
import urllib.error
from unittest.mock import patch, MagicMock
import pytest


# 导入目标模块（此时 resolve_cdp_url 还不存在，测试会失败）
from tools.cdp_probe import resolve_cdp_url
