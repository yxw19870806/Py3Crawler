# -*- coding:UTF-8  -*-
"""
日志写入类
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import threading
import time

try:
    from . import file, output, tool
except ImportError:
    from common import file, output, tool

# 读取日志相关配置
DEFAULT_LOG_CONFIG = {
    "IS_SHOW_ERROR": True,  # 是否在控制台显示错误信息（异常报错内容）
    "IS_SHOW_STEP": True,  # 是否在控制台显示步骤信息（正常运行输出）
    "IS_SHOW_TRACE": False,  # 是否在控制台显示追踪信息（一些正常的调试信息）
    "IS_SHOW_NOTICE": True,  # 是否在控制台显示提示信息（一些需要额外处理的调试信息）
    "IS_LOG_ERROR": True,  # 是否在文件中保存错误信息
    "IS_LOG_STEP": False,  # 是否在文件中保存步骤信息
    "IS_LOG_TRACE": False,  # 是否在文件中保存追踪信息
    "IS_LOG_NOTICE": True,  # 是否在文件中保存提示信息
    "ERROR_LOG_PATH": "../log/errorLog.txt",  # 错误日志保存路径，支持相对路径和绝对路径
    "STEP_LOG_PATH": "../log/stepLog_{date}.txt",  # 步骤日志保存路径，支持相对路径和绝对路径
    "TRACE_LOG_PATH": "../log/traceLog_{date}.txt",  # 追踪日志保存路径，支持相对路径和绝对路径
    "NOTICE_LOG_PATH": "../log/noticeLog.txt",  # 提示日志保存路径，支持相对路径和绝对路径
}
LOG_CONFIG = tool.json_decode(file.read_file(os.path.join(os.path.dirname(__file__), "log_config.json")), DEFAULT_LOG_CONFIG)
# 日志路径
ERROR_LOG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), LOG_CONFIG["ERROR_LOG_PATH"]))
STEP_LOG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), LOG_CONFIG["STEP_LOG_PATH"]))
TRACE_LOG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), LOG_CONFIG["TRACE_LOG_PATH"]))
NOTICE_LOG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), LOG_CONFIG["NOTICE_LOG_PATH"]))
# 文件写入锁
thread_lock = threading.Lock()


def error(msg):
    """Error message logger"""
    msg = _get_time() + " [Error] " + str(msg)
    if LOG_CONFIG["IS_SHOW_ERROR"]:
        output.print_msg(msg, False)
    if LOG_CONFIG["IS_LOG_ERROR"]:
        with thread_lock:
            file.write_file(msg, _replace_path_macro(ERROR_LOG_PATH))


def step(msg):
    """Step message logger"""
    msg = _get_time() + " " + str(msg)
    if LOG_CONFIG["IS_SHOW_STEP"]:
        output.print_msg(msg, False)
    if LOG_CONFIG["IS_LOG_STEP"]:
        with thread_lock:
            file.write_file(msg, _replace_path_macro(STEP_LOG_PATH))


def trace(msg):
    """Trace message logger"""
    msg = _get_time() + " " + str(msg)
    if LOG_CONFIG["IS_SHOW_TRACE"]:
        output.print_msg(msg, False)
    if LOG_CONFIG["IS_LOG_TRACE"]:
        with thread_lock:
            file.write_file(msg, _replace_path_macro(TRACE_LOG_PATH))


def notice(msg):
    """Debug message logger"""
    msg = _get_time() + " " + str(msg)
    if LOG_CONFIG["IS_SHOW_NOTICE"]:
        output.print_msg(msg, False)
    if LOG_CONFIG["IS_LOG_NOTICE"]:
        with thread_lock:
            file.write_file(msg, _replace_path_macro(NOTICE_LOG_PATH))


def _get_time():
    """Get formatted time string(%m-%d %H:%M:%S)"""
    return time.strftime("%m-%d %H:%M:%S", time.localtime(time.time()))


def _replace_path_macro(file_path):
    """Replace Macro in log file path {date} -> YYYYMMDD"""
    return file_path.replace("{date}", time.strftime("%Y%m%d", time.localtime(time.time())))
