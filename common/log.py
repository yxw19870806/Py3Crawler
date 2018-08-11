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
from common import output, tool

IS_SHOW_ERROR = True
IS_SHOW_STEP = False
IS_SHOW_TRACE = False
IS_SHOW_NOTICE = False
ERROR_LOG_PATH = os.path.abspath(os.path.join(tool.PROJECT_ROOT_PATH, 'log\\errorLog.txt'))
STEP_LOG_PATH = os.path.abspath(os.path.join(tool.PROJECT_ROOT_PATH, 'log\\stepLog.txt'))
TRACE_LOG_PATH = os.path.abspath(os.path.join(tool.PROJECT_ROOT_PATH, 'log\\traceLog.txt'))
NOTICE_LOG_PATH = os.path.abspath(os.path.join(tool.PROJECT_ROOT_PATH, 'log\\debugLog.txt'))
thread_lock = threading.Lock()


def error(msg):
    """Error message logger"""
    msg = _get_time() + " [Error] " + str(msg)
    if IS_SHOW_ERROR:
        output.print_msg(msg, False)
    if ERROR_LOG_PATH != "":
        with thread_lock:
            tool.write_file(msg, ERROR_LOG_PATH)


def step(msg):
    """Step message logger"""
    msg = _get_time() + " " + str(msg)
    if IS_SHOW_STEP:
        output.print_msg(msg, False)
    if STEP_LOG_PATH != "":
        with thread_lock:
            tool.write_file(msg, STEP_LOG_PATH)


def trace(msg):
    """Trace message logger"""
    msg = _get_time() + " " + str(msg)
    if IS_SHOW_TRACE:
        output.print_msg(msg, False)
    if TRACE_LOG_PATH != "":
        with thread_lock:
            tool.write_file(msg, TRACE_LOG_PATH)


def notice(msg):
    """Debug message logger"""
    msg = _get_time() + " " + str(msg)
    if IS_SHOW_NOTICE:
        output.print_msg(msg, False)
    if NOTICE_LOG_PATH != "":
        with thread_lock:
            tool.write_file(msg, NOTICE_LOG_PATH)


def _get_time():
    """Get formatted time string(%m-%d %H:%M:%S)"""
    return time.strftime("%m-%d %H:%M:%S", time.localtime(time.time()))
