# -*- coding:UTF-8  -*-
"""
ivseek已解析文件中提取全部账号
http://www.ivseek.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import *
from project.ivseek import ivseek
from project.youtube import youtube
from project.nicoNico import nicoNico


def main():
    # 初始化类
    youtube_obj = youtube.Youtube(extra_config={crawler.SYS_NOT_CHECK_SAVE_DATA: True})
    nicoNico_obj = nicoNico.NicoNico(extra_config={crawler.SYS_NOT_CHECK_SAVE_DATA: True})
    ivseek_obj = ivseek.IvSeek()

    save_data_list = ivseek.read_save_data(ivseek_obj.save_data_path)
    account_id_list = {
        "youtube": {},
        "niconico": {},
    }
    for single_save_list in save_data_list:
        # 已完成
        if single_save_list[4] == ivseek.DONE_SING:
            continue
        if single_save_list[2].find("//www.youtube.com") >= 0:
            account_id_list["youtube"][single_save_list[3]] = 1
        elif single_save_list[2].find("//www.nicovideo.jp") >= 0:
            account_id_list["niconico"][single_save_list[3]] = 1
        else:
            continue
        # single_save_list[4] = ivseek.DONE_SING
    for type in account_id_list:
        for account_id in account_id_list[type]:
            if type == "youtube":
                if account_id not in youtube_obj.account_list:
                    youtube_obj.account_list[account_id] = [account_id]
            elif type == "niconico":
                if not crawler.is_integer(account_id):
                    continue
                # if account_id not in nicoNico_obj.account_list:
                #     nicoNico_obj.account_list[account_id] = [account_id]
    file.write_file(tool.list_to_string(save_data_list), ivseek_obj.save_data_path, file.WRITE_FILE_TYPE_REPLACE)
    file.write_file(tool.list_to_string(youtube_obj.account_list.values()), youtube_obj.save_data_path, file.WRITE_FILE_TYPE_REPLACE)
    # file.write_file(tool.list_to_string(nicoNico_obj.account_list.values()), nicoNico_obj.save_data_path, file.WRITE_FILE_TYPE_REPLACE)


if __name__ == "__main__":
    main()
