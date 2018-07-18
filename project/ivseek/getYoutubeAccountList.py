# -*- coding:UTF-8  -*-
"""
ivseek 所有视频所在YouTube账号获取
http://jigadori.fkoji.com/users
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from common import *

DONE_SING = "~"
YOUTUBE_SAVE_DATA_PATH = os.path.abspath(os.path.join(tool.PROJECT_APP_ROOT_PATH, "../data/youtube/save.data"))


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


def main():
    save_data_path = crawler.quickly_get_save_data_path()
    save_data_list = read_save_data(save_data_path)
    account_id_list = []
    for single_save_list in save_data_list:
        if single_save_list[2].find("//www.youtube.com") >= 0:
            # 已完成
            if len(single_save_list) >= 5 and single_save_list[4] == DONE_SING:
                continue
            # 新的账号
            if single_save_list[3] not in account_id_list:
                account_id_list.append(single_save_list[3])
            # 增加已完成标记
            single_save_list[4] = DONE_SING
    youtube_save_data_list = crawler.read_save_data(YOUTUBE_SAVE_DATA_PATH, 0, [])
    for account_id in account_id_list:
        if account_id not in youtube_save_data_list:
            youtube_save_data_list[account_id] = [account_id]
    tool.write_file(tool.list_to_string(save_data_list), save_data_path, tool.WRITE_FILE_TYPE_REPLACE)
    tool.write_file(tool.list_to_string(youtube_save_data_list.values()), YOUTUBE_SAVE_DATA_PATH, tool.WRITE_FILE_TYPE_REPLACE)


if __name__ == "__main__":
    main()
