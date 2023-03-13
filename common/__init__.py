__all__ = [
    "crawler",
    "const",
    "file",
    "log",
    "net",
    "output",
    "path",
    "tool",
    "PROJECT_ROOT_PATH",
    "PROJECT_CONFIG_PATH",
]

import os

from common.logger import logger as log

# 项目根目录
PROJECT_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# 全局config.ini路径
PROJECT_CONFIG_PATH = os.path.abspath(os.path.join(PROJECT_ROOT_PATH, "common", "config.ini"))
