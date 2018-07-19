# -*- coding:UTF-8  -*-
"""
ivseek 存档文件公共类
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from common import *

DONE_SING = "~"


def read_save_data(save_data_path):
    result_list = []
    if not os.path.exists(save_data_path):
        return result_list
    for single_save_data in tool.read_file(save_data_path, tool.READ_FILE_TYPE_LINE):
        single_save_data = single_save_data.replace("\xef\xbb\xbf", "").replace("\n", "").replace("\r", "")
        if len(single_save_data) == 0:
            continue
        single_save_list = single_save_data.split("\t")
        while len(single_save_list) < 5:
            single_save_list.append("")
        result_list.append(single_save_list)
    return result_list
