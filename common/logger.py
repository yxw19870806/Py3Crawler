# -*- coding:UTF-8  -*-
"""
封装后的日志类
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import logging
from logging import LogRecord
from typing import Final
from common import file, tool

DEFAULT_LOG_CONFIG = {
    "IS_CONSOLE_DEBUG": False,
    "IS_CONSOLE_INFO": True,
    "IS_CONSOLE_WARNING": True,
    "IS_CONSOLE_ERROR": True,
    "IS_WRITE_DEBUG": False,
    "IS_WRITE_INFO": False,
    "IS_WRITE_WARNING": True,
    "IS_WRITE_ERROR": True,
    "LOG_DEBUG_PATH": "../log/debugLog.txt",
    "LOG_INFO_PATH": "../log/infoLog.txt",
    "LOG_WARNING_PATH": "../log/warningLog.txt",
    "LOG_ERROR_PATH": "../log/errorLog.txt",
}
LOG_CONFIG: Final = tool.json_decode(file.read_file(os.path.join(os.path.dirname(__file__), "log_config.json")), DEFAULT_LOG_CONFIG)
LOG_DEBUG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), LOG_CONFIG["LOG_DEBUG_PATH"]))
LOG_INFO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), LOG_CONFIG["LOG_INFO_PATH"]))
LOG_WARNING_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), LOG_CONFIG["LOG_WARNING_PATH"]))
LOG_ERROR_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), LOG_CONFIG["LOG_ERROR_PATH"]))


class ColorFormatter(logging.Formatter):
    log_colors = {
        logging.CRITICAL: "\033[0;33m",
        logging.ERROR: "\033[0;31m",
        logging.WARNING: "\033[0;35m",
        logging.INFO: "\033[0;32m",
        logging.DEBUG: "\033[0;00m",
    }

    def __init__(self):
        logging.Formatter.__init__(self, fmt="[%(asctime)s]: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    def format(self, record: LogRecord) -> str:
        s = super().format(record)
        level_no = record.levelno
        if level_no in self.log_colors:
            return self.log_colors[level_no] + s + "\033[0m"
        return s


class FilterConsole(logging.Filter):
    def filter(self, record: LogRecord):
        if record.levelno == logging.DEBUG:
            return DEFAULT_LOG_CONFIG["IS_CONSOLE_DEBUG"]
        elif record.levelno == logging.INFO:
            return DEFAULT_LOG_CONFIG["IS_CONSOLE_INFO"]
        elif record.levelno == logging.WARNING:
            return DEFAULT_LOG_CONFIG["IS_CONSOLE_WARNING"]
        elif record.levelno == logging.ERROR:
            return DEFAULT_LOG_CONFIG["IS_CONSOLE_ERROR"]
        else:
            return False


class FilterDebug(logging.Filter):
    def filter(self, record: LogRecord):
        return record.levelno == logging.DEBUG


class FilterInfo(logging.Filter):
    def filter(self, record: LogRecord):
        return record.levelno == logging.INFO


class FilterWarning(logging.Filter):
    def filter(self, record: LogRecord):
        return record.levelno == logging.WARNING


class FilterError(logging.Filter):
    def filter(self, record: LogRecord):
        return record.levelno == logging.ERROR


logger = logging.getLogger("PyCrawler")
logger.setLevel(logging.DEBUG)

# 控制台
stream_handle = logging.StreamHandler()
stream_handle.setLevel(logging.DEBUG)
stream_handle.setFormatter(ColorFormatter())
stream_handle.addFilter(FilterConsole())
logger.addHandler(stream_handle)

# 文件日志
file_formatter = logging.Formatter(fmt="[%(asctime)s][%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

if DEFAULT_LOG_CONFIG["IS_WRITE_DEBUG"]:
    debug_file_handle = logging.FileHandler(LOG_DEBUG_PATH, encoding="UTF-8")
    debug_file_handle.setLevel(logging.DEBUG)
    debug_file_handle.setFormatter(file_formatter)
    debug_file_handle.addFilter(FilterDebug())
    logger.addHandler(debug_file_handle)

if DEFAULT_LOG_CONFIG["IS_WRITE_INFO"]:
    info_file_handle = logging.FileHandler(LOG_INFO_PATH, encoding="UTF-8")
    info_file_handle.setLevel(logging.INFO)
    info_file_handle.setFormatter(file_formatter)
    info_file_handle.addFilter(FilterInfo())
    logger.addHandler(info_file_handle)

if DEFAULT_LOG_CONFIG["IS_WRITE_WARNING"]:
    warning_file_handle = logging.FileHandler(LOG_WARNING_PATH, encoding="UTF-8")
    warning_file_handle.setLevel(logging.WARNING)
    warning_file_handle.setFormatter(file_formatter)
    warning_file_handle.addFilter(FilterWarning())
    logger.addHandler(warning_file_handle)

if DEFAULT_LOG_CONFIG["IS_WRITE_ERROR"]:
    error_file_handle = logging.FileHandler(LOG_ERROR_PATH, encoding="UTF-8")
    error_file_handle.setLevel(logging.ERROR)
    error_file_handle.setFormatter(file_formatter)
    error_file_handle.addFilter(FilterError())
    logger.addHandler(error_file_handle)
