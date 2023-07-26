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
from typing import Any, Final
from common import color_format, file

DEFAULT_LOG_CONFIG: Final[dict[str, Any]] = {
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
LOG_CONFIG: Final[dict[str, Any]] = file.read_json_file(os.path.join(os.path.dirname(__file__), "log_config.json"), DEFAULT_LOG_CONFIG)
for key in DEFAULT_LOG_CONFIG:
    if key not in LOG_CONFIG:
        LOG_CONFIG[key] = DEFAULT_LOG_CONFIG
LOG_DEBUG_PATH: str = os.path.abspath(os.path.join(os.path.dirname(__file__), LOG_CONFIG["LOG_DEBUG_PATH"]))
LOG_INFO_PATH: str = os.path.abspath(os.path.join(os.path.dirname(__file__), LOG_CONFIG["LOG_INFO_PATH"]))
LOG_WARNING_PATH: str = os.path.abspath(os.path.join(os.path.dirname(__file__), LOG_CONFIG["LOG_WARNING_PATH"]))
LOG_ERROR_PATH: str = os.path.abspath(os.path.join(os.path.dirname(__file__), LOG_CONFIG["LOG_ERROR_PATH"]))


class ColorFormatter(logging.Formatter):
    log_colors: dict[int, color_format.ColorFormat] = {
        logging.CRITICAL: color_format.ColorFormat(foreground_color=color_format.ForegroundColor.LIGHT_MAGENTA),
        logging.ERROR: color_format.ColorFormat(foreground_color=color_format.ForegroundColor.RED),
        logging.WARNING: color_format.ColorFormat(foreground_color=color_format.ForegroundColor.CYAN),
        logging.INFO: color_format.ColorFormat(foreground_color=color_format.ForegroundColor.GREEN),
        logging.DEBUG: color_format.ColorFormat(foreground_color=color_format.ForegroundColor.BLUE),
    }

    def __init__(self) -> None:
        logging.Formatter.__init__(self, fmt="[%(asctime)s]: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    def format(self, record: LogRecord) -> str:
        s = super().format(record)
        level_no = record.levelno
        if level_no in self.log_colors:
            return self.log_colors[level_no].fomat(s)
        return s


class FilterConsole(logging.Filter):
    def filter(self, record: LogRecord) -> bool:
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


class FilterFunc(logging.Filter):
    def __init__(self, log_level: int) -> None:
        self.log_level = log_level
        super().__init__()

    def filter(self, record: LogRecord) -> bool:
        return record.levelno == self.log_level


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
    debug_file_handle.addFilter(FilterFunc(logging.DEBUG))
    logger.addHandler(debug_file_handle)

if DEFAULT_LOG_CONFIG["IS_WRITE_INFO"]:
    info_file_handle = logging.FileHandler(LOG_INFO_PATH, encoding="UTF-8")
    info_file_handle.setLevel(logging.INFO)
    info_file_handle.setFormatter(file_formatter)
    info_file_handle.addFilter(FilterFunc(logging.INFO))
    logger.addHandler(info_file_handle)

if DEFAULT_LOG_CONFIG["IS_WRITE_WARNING"]:
    warning_file_handle = logging.FileHandler(LOG_WARNING_PATH, encoding="UTF-8")
    warning_file_handle.setLevel(logging.WARNING)
    warning_file_handle.setFormatter(file_formatter)
    warning_file_handle.addFilter(FilterFunc(logging.WARNING))
    logger.addHandler(warning_file_handle)

if DEFAULT_LOG_CONFIG["IS_WRITE_ERROR"]:
    error_file_handle = logging.FileHandler(LOG_ERROR_PATH, encoding="UTF-8")
    error_file_handle.setLevel(logging.ERROR)
    error_file_handle.setFormatter(file_formatter)
    error_file_handle.addFilter(FilterFunc(logging.ERROR))
    logger.addHandler(error_file_handle)
