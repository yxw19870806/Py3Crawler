# -*- coding:UTF-8  -*-
"""
グラドル自画撮り部 已下载文件中提取全部成员账号
http://jigadori.fkoji.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from common import *

# Twitter存档文件目录
SAVE_DATA_PATH = os.path.abspath(os.path.join(crawler.PROJECT_ROOT_PATH, "project/twitter/info/save.data"))
# 图片下载后的保存目录
FILE_STORAGE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "photo"))


# 从存档目录获取去重后的账号名字
def get_account_from_storage():
    account_list = {}
    for root_path, dir_name_list, file_name_list in os.walk(FILE_STORAGE_PATH):
        for file_name in file_name_list:
            count, account_name = str(file_name).split(".")[0].split("_", 1)
            account_list[account_name] = 1
    return account_list


def main():
    account_list_from_storage = get_account_from_storage()
    if len(account_list_from_storage) > 0:
        account_list_from_save_data = crawler.read_save_data(SAVE_DATA_PATH, 0, [])
        for account_id in account_list_from_storage:
            if account_id not in account_list_from_save_data:
                account_list_from_save_data[account_id] = [account_id, "", "", "", ""]
        temp_list = [account_list_from_save_data[key] for key in sorted(account_list_from_save_data.keys())]
        file.write_file(tool.list_to_string(temp_list), SAVE_DATA_PATH, file.WRITE_FILE_TYPE_REPLACE)


if __name__ == "__main__":
    main()
