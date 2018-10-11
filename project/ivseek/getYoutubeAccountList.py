# -*- coding:UTF-8  -*-
"""
ivseek已解析文件中提取全部youtube频道账号
http://www.ivseek.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import *
from project.ivseek import ivseek
from project.youtube import youtube


def main():
    # 初始化类
    youtube_obj = youtube.Youtube()
    ivseek_obj = ivseek.IvSeek()

    save_data_list = ivseek.read_save_data(ivseek_obj.save_data_path)
    account_id_list = []
    for single_save_list in save_data_list:
        if single_save_list[2].find("//www.youtube.com") >= 0:
            # 已完成
            if single_save_list[4] == ivseek.DONE_SING:
                continue
            # 新的账号
            if single_save_list[3] not in account_id_list:
                account_id_list.append(single_save_list[3])
            # 增加已完成标记
            single_save_list[4] = ivseek.DONE_SING
    youtube_save_data_list = crawler.read_save_data(youtube_obj.save_data_path, 0, [])
    for account_id in account_id_list:
        if account_id not in youtube_save_data_list:
            youtube_save_data_list[account_id] = [account_id]
    file.write_file(tool.list_to_string(save_data_list), ivseek_obj.save_data_path, file.WRITE_FILE_TYPE_REPLACE)
    file.write_file(tool.list_to_string(youtube_save_data_list.values()), youtube_obj.save_data_path, file.WRITE_FILE_TYPE_REPLACE)


if __name__ == "__main__":
    main()
