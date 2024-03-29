# -*- coding:UTF-8  -*-
# 判断存档文件中的数量和保存目录中的数量是否一致
import os
from common import *

# 文件保存目录
FILE_STORAGE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "photo"))
# 存档文件所在路径
SAVE_DATA_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "save.data"))
# 存档中作为保存文件夹名字所在字段所在数组下标，从0开始
PRIME_KEY_INDEX = 0
# 存档中记录已下载文件数的字段所在数组下标，从0开始
COUNT_INDEX = 1
# 下载的文件是不是自增整数
IS_INTEGER = True


# 获取指定目录下全部子目录内的文件数量
# is_integer    文件名是不是整数，如果为True，另外判断最大的那个序号是否和总文件数一致
def get_storage_file_count():
    if not os.path.exists(FILE_STORAGE_PATH):
        console.log(f"file root path {FILE_STORAGE_PATH} not exist")
        return {}
    account_list = {}
    # 根目录下的全部子目录
    for dir_name in os.listdir(FILE_STORAGE_PATH):
        sub_path = os.path.join(FILE_STORAGE_PATH, dir_name)
        file_list = os.listdir(sub_path)
        total_file_count = len(file_list)
        # 如果文件名全部是整数，那么判断最大的序号是否和总数一致
        if IS_INTEGER:
            file_max_index = 0
            for file_name in file_list:
                file_max_index = max(int(file_name.split(".")[0]), file_max_index)
            if file_max_index != total_file_count:
                console.log(f"{dir_name} total count {total_file_count} not equal to max count {file_max_index}")
        account_list[dir_name] = total_file_count
    return account_list


# 获取存档文件内的全部存档的下载数量
def get_save_data_file_count():
    if not os.path.exists(SAVE_DATA_FILE_PATH):
        console.log(f"save data {SAVE_DATA_FILE_PATH} not exist")
        return {}
    account_list = {}
    for line in file.read_file(SAVE_DATA_FILE_PATH, const.ReadFileMode.LINE):
        temp_list = line.strip("\n\r").split("\t")
        account_list[temp_list[PRIME_KEY_INDEX]] = int(temp_list[COUNT_INDEX])
    return account_list


def check_count():
    account_list_from_storage = get_storage_file_count()
    account_list_from_save_data = get_save_data_file_count()
    if not account_list_from_storage or not account_list_from_save_data:
        return
    for account_id in dict(account_list_from_storage):
        if account_id not in account_list_from_save_data:
            account_list_from_save_data[account_id] = 0
        if account_list_from_save_data[account_id] != account_list_from_storage[account_id]:
            console.log(f"{account_id} count in save data: {account_list_from_save_data[account_id]}, in root path: {account_list_from_storage[account_id]}")
    for account_id in dict(account_list_from_storage):
        if account_id not in account_list_from_save_data:
            console.log(f"{account_id} not found in save data")


if __name__ == "__main__":
    check_count()
