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

YOUTUBE_SAVE_DATA_PATH = os.path.abspath(os.path.join(tool.PROJECT_APP_ROOT_PATH, "youtube/info/save.data"))


def main():
    save_data_list = crawler.read_save_data(crawler.quickly_get_save_data_path(), 0, [], False)
    account_id_list = []
    for page_id in save_data_list:
        if len(save_data_list[page_id]) < 4:
            continue
        if save_data_list[page_id][2].find("//www.youtube.com") >= 0:
            if save_data_list[page_id][3] not in account_id_list:
                account_id_list.append(save_data_list[page_id][3])
    youtube_save_data_list = crawler.read_save_data(YOUTUBE_SAVE_DATA_PATH, 0, [])
    for account_id in account_id_list:
        if account_id not in youtube_save_data_list:
            youtube_save_data_list[account_id] = [account_id]
    tool.write_file(tool.list_to_string(youtube_save_data_list.values()), YOUTUBE_SAVE_DATA_PATH, tool.WRITE_FILE_TYPE_REPLACE)


if __name__ == "__main__":
    main()
