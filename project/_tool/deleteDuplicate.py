# -*- coding:UTF-8  -*-
"""
相同文件删除（DuplicateCleaner）
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import csv
from common import *

DUPLICATE_CSV_FILE_PATH = os.path.abspath("duplicate.csv")


# 读取文件，同一组的文件进行处理
def main(file_path):
    group_id = 1
    group_list = []
    with open(file_path, encoding="UTF-8") as file_handle:
        for row in csv.DictReader(file_handle):
            # 处理一个组别的
            if group_id != int(row["组别"]):
                deal_one_group(group_list)
                group_id = int(row["组别"])
                group_list = []
            group_list.append(row)
        deal_one_group(group_list)


# 对同一组别的文件进行处理
# 优先删除文件大小较小的，文件大小相同时则优先删除记录id较小的
def deal_one_group(group_list):
    min_record_id = 0
    max_file_size = 0
    record_file_path = ""
    delete_list = []
    for row in group_list:
        record_id = int(row["文件名称"].split(".")[0].split("_")[0])
        file_path = os.path.join(row["路径"], row["文件名称"])
        file_size = int(row["大小"])
        # 进行比较
        if min_record_id == 0:  # 第一次，设置记录
            min_record_id = record_id
            max_file_size = file_size
            record_file_path = file_path
        elif file_size < max_file_size:  # 比记录的文件小，删除当前的
            delete_list.append(file_path)
        elif file_size > max_file_size:  # 比记录的文件大，删除记录的
            delete_list.append(record_file_path)
            min_record_id = record_id
            max_file_size = file_size
            record_file_path = file_path
        elif record_id > min_record_id:  # 相同大小，id比记录的文件大，删除当前的
            delete_list.append(file_path)
        else:  # 相同大小，id比记录的文件小，删除记录的
            delete_list.append(record_file_path)
            min_record_id = record_id
            record_file_path = file_path
    for file_path in delete_list:
        path.delete_dir_or_file(file_path)
        console.log("delete " + file_path)
    console.log("keep " + record_file_path)


if __name__ == "__main__":
    main(DUPLICATE_CSV_FILE_PATH)
