# -*- coding:UTF-8  -*-
"""
ivseek已解析文件中提取全部youtube频道账号
http://www.ivseek.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from common import *
from project.ivseek import ivseekCommon

YOUTUBE_SAVE_DATA_PATH = os.path.abspath(os.path.join(crawler.PROJECT_APP_ROOT_PATH, "youtube/info/save.data"))


def main():
    save_data_path = crawler.quickly_get_save_data_path()
    save_data_list = ivseekCommon.read_save_data(save_data_path)
    account_id_list = []
    for single_save_list in save_data_list:
        if single_save_list[2].find("//www.youtube.com") >= 0:
            # 已完成
            if single_save_list[4] == ivseekCommon.DONE_SING:
                continue
            # 新的账号
            if single_save_list[3] not in account_id_list:
                account_id_list.append(single_save_list[3])
            # 增加已完成标记
            single_save_list[4] = ivseekCommon.DONE_SING
    youtube_save_data_list = crawler.read_save_data(YOUTUBE_SAVE_DATA_PATH, 0, [])
    for account_id in account_id_list:
        if account_id not in youtube_save_data_list:
            youtube_save_data_list[account_id] = [account_id]
    file.write_file(tool.list_to_string(save_data_list), save_data_path, file.WRITE_FILE_TYPE_REPLACE)
    file.write_file(tool.list_to_string(youtube_save_data_list.values()), YOUTUBE_SAVE_DATA_PATH, file.WRITE_FILE_TYPE_REPLACE)


if __name__ == "__main__":
    main()
