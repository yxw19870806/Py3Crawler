# -*- coding:UTF-8  -*-
"""
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import threading
import time

thread_lock = threading.Lock()


def print_msg(msg, is_time: bool = True):
    """
    console输出（线程安全）
    """
    msg = str(msg)
    if is_time:
        msg = _get_time() + " " + msg
    with thread_lock:
        print(msg)


def _get_time() -> str:
    """
    获取当前时间
    """
    return time.strftime("%m-%d %H:%M:%S", time.localtime(time.time()))
