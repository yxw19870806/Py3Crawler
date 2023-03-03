# -*- coding:UTF-8  -*-
"""
结束所有爬虫程序
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import port_listener_event
from common.tools.process import process_control

if __name__ == "__main__":
    process_control.ProcessControl().send_code(port_listener_event.ProcessStatus.STOP)
