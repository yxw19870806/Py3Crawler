# -*- coding:UTF-8  -*-
"""
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from common import *

DUPLICATE_CSV_FILE_PATH = os.path.abspath("D:\\duplicate.csv")


def main(file_path):
    index = 1
    check_list = []
    for line in file.read_file(DUPLICATE_CSV_FILE_PATH, file.READ_FILE_TYPE_LINE):
        row = line.split("\t")
        # 处理一个组别的
        if index != int(row[4]):
            deal_one_group(check_list)
            index = int(row[4])
            check_list = []
        check_list.append(row)
    deal_one_group(check_list)


def deal_one_group(check_list):
    min_post_id = 0
    max_file_size = 0
    cache_file_path = ""
    delete_list = []
    unique_list = {}
    for row in check_list:
        post_id = int(row[1].split(".")[0])
        file_path = os.path.join(row[2], row[1])
        if file_path in unique_list:
            continue
        # 相似度
        if int(row[3].replace("%", "")) < 45:
            continue
        unique_list[file_path] = 1
        if row[5].find(" B") > 0:
            file_size = float(row[5].replace(" B", "").strip())
        elif row[5].find(" KB") > 0:
            file_size = float(row[5].replace(" KB", "").strip()) * 1024
        elif row[5].find(" MB") > 0:
            file_size = float(row[5].replace(" MB", "").strip()) * 1024 * 1024
        elif row[5].find(" GB") > 0:
            file_size = float(row[5].replace(" GB", "").strip()) * 1024 * 1024 * 1024
        else:
            print("unknown file_size " + row[5])
            return
        file_size = int(file_size)
        if min_post_id == 0:  # 第一次，设置记录
            min_post_id = post_id
            max_file_size = file_size
            cache_file_path = file_path
        elif file_size < max_file_size:  # 比记录的文件小，删除当前的
            delete_list.append(file_path)
        elif file_size > max_file_size:  # 比记录的文件大，删除记录的
            delete_list.append(cache_file_path)
            min_post_id = post_id
            max_file_size = file_size
            cache_file_path = file_path
        elif post_id > min_post_id:  # 相同大小，id比记录的文件大，删除当前的
            delete_list.append(file_path)
        else:  # 相同大小，id比记录的文件小，删除记录的
            delete_list.append(cache_file_path)
            min_post_id = post_id
            cache_file_path = file_path
    for file_path in delete_list:
        path.delete_dir_or_file(file_path)
        output.print_msg("delete " + file_path)
    output.print_msg("keep " + cache_file_path)


if __name__ == "__main__":
    main(DUPLICATE_CSV_FILE_PATH)
