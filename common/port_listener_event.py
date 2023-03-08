# -*- coding:UTF-8  -*-
"""
端口监控类
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import threading
from enum import unique, Enum
from multiprocessing.connection import Listener

SERVER_IP = "localhost"  # 监听服务器IP


@unique
class ProcessStatus(Enum):
    RUN: int = 0  # 进程运行中
    PAUSE: int = 1  # 进程暂停，知道状态变为0时才继续下载
    STOP: int = 2  # 进程立刻停止，删除还未完成的数据


class PortListenerEvent(threading.Thread):
    """
    程序运行状态控制
    """

    def __init__(self, port, event_list=None):
        threading.Thread.__init__(self)
        self.ip = SERVER_IP
        self.port = int(port)
        self.event_list = event_list
        self.listener = None

    def __del__(self):
        if isinstance(self.listener, Listener):
            self.listener.close()

    def run(self) -> None:
        self.listener = Listener((self.ip, self.port))
        while True:
            conn = self.listener.accept()
            try:
                command = str(conn.recv())
                if self.event_list and command in self.event_list:
                    self.event_list[command]()
            except IOError:
                pass
            finally:
                conn.close()
