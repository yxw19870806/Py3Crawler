__all__ = [
    "crawler",
    "const",
    "console",
    "file",
    "log",
    "net",
    "path",
    "tool",
    "url",
    "PROJECT_LIB_PATH",
    "PROJECT_ROOT_PATH",
    "PROJECT_CONFIG_PATH",
    "IS_EXECUTABLE",
    "CrawlerException",
]

import os
import sys
from common.logger import logger as log
from common import console

# if sys.stdout.encoding != "UTF-8":
#     raise Exception("项目编码必须是UTF-8，请在IDE中修改相关设置")
if sys.version_info < (3,):
    raise Exception("仅支持python3.X，请访问官网 https://www.python.org/downloads/ 安装最新的python3")

# 是否是exe程序
IS_EXECUTABLE = getattr(sys, "frozen", False)

# lib库目录
PROJECT_LIB_PATH = os.path.abspath(os.path.dirname(__file__))
# 项目根目录
PROJECT_ROOT_PATH = os.path.abspath(os.path.join(PROJECT_LIB_PATH, ".."))
# 全局config.ini路径
PROJECT_CONFIG_PATH = os.path.abspath(os.path.join(PROJECT_LIB_PATH, "config.ini"))


class CrawlerException(SystemExit):
    def __init__(self, msg: str = "", is_print: bool = True) -> None:
        SystemExit.__init__(self, 1)
        if is_print:
            console.log(msg)
        self.exception_message = msg

    @property
    def message(self) -> str:
        return self.exception_message

    def http_error(self, target: str) -> str:
        return "%s解析失败，原因：%s" % (target, self.message)
