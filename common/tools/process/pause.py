# -*- coding:UTF-8  -*-
"""
暂停所有正在运行的爬虫程序
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import portListenerEvent
from common.tools.process import processControl


if __name__ == "__main__":
    processControl.ProcessControl().send_code(portListenerEvent.PROCESS_STATUS_PAUSE)
