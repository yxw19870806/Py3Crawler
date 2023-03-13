# -*- coding:UTF-8  -*-
"""
暂停所有正在运行的爬虫程序
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import const
from common.tools.process import process_control

if __name__ == "__main__":
    process_control.ProcessControl().send_code(const.ProcessStatus.PAUSE)
