# -*- coding:UTF-8  -*-
"""
继续所有已经暂停的爬虫程序
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import crawler_enum
from common.tools.process import process_control

if __name__ == "__main__":
    process_control.ProcessControl().send_code(crawler_enum.ProcessStatus.RUN)
