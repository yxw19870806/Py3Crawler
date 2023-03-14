__all__ = [
    "crawler",
    "const",
    "console",
    "file",
    "log",
    "net",
    "path",
    "tool",
    "PROJECT_LIB_PATH",
    "PROJECT_ROOT_PATH",
    "PROJECT_CONFIG_PATH",
    "IS_EXECUTABLE",
]

import os
import sys

from common.logger import logger as log

# if sys.stdout.encoding != "UTF-8":
#     raise Exception("项目编码必须是UTF-8，请在IDE中修改相关设置")
if sys.version_info < (3,):
    raise Exception("仅支持python3.X，请访问官网 https://www.python.org/downloads/ 安装最新的python3")

if getattr(sys, "frozen", False):
    IS_EXECUTABLE = True
else:
    IS_EXECUTABLE = False

# lib库目录
PROJECT_LIB_PATH = os.path.abspath(os.path.dirname(__file__))
# 项目根目录
PROJECT_ROOT_PATH = os.path.abspath(os.path.join(PROJECT_LIB_PATH, ".."))
# 全局config.ini路径
PROJECT_CONFIG_PATH = os.path.abspath(os.path.join(PROJECT_LIB_PATH, "config.ini"))
