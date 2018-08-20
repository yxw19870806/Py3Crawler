# -*- coding:UTF-8  -*-
"""
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import threading
import time

thread_lock = threading.Lock()


def print_msg(msg, is_time=True):
    """Console print message, thread safe"""
    msg = str(msg)
    if is_time:
        msg = _get_time() + " " + msg
    with thread_lock:
        print(msg)


def _get_time():
    """Get formatted time string(%m-%d %H:%M:%S)"""
    return time.strftime("%m-%d %H:%M:%S", time.localtime(time.time()))
