# -*- coding:UTF-8  -*-
"""
端口监控类
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import threading
from multiprocessing.connection import Listener
from typing import Union, Optional, Final

SERVER_IP: Final[str] = "localhost"  # 监听服务器IP


class PortListenerEvent(threading.Thread):
    """
    程序运行状态控制
    """

    def __init__(self, port: Union[str, int], event_list: Optional[callable] = None) -> None:
        threading.Thread.__init__(self)
        self.ip = SERVER_IP
        self.port = int(port)
        self.event_list = event_list
        self.listener = None

    def __del__(self) -> None:
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
