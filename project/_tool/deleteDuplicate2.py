# -*- coding:UTF-8  -*-
"""
相同文件删除（Video Comparer）
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from common import *

MIN_SIMILARITY = 45  # 多少相似度以上的比较结果进行处理
DUPLICATE_CSV_FILE_PATH = os.path.abspath("duplicate.csv")


# 读取文件，同一组的文件进行处理
def main(file_path):
    group_id = 1
    group_list = []
    for line in file.read_file(file_path, const.ReadFileMode.LINE):
        row = line.split("\t")
        # 处理一个组别的
        if group_id != int(row[4]):
            deal_one_group(group_list)
            group_id = int(row[4])
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
    unique_list = {}
    for row in group_list:
        file_path = os.path.join(row[2], row[1])
        if file_path in unique_list:
            continue
        unique_list[file_path] = 1
        record_id = int(row[1].split(".")[0])
        # 相似度
        similarity = int(row[3].replace("%", ""))
        if similarity < MIN_SIMILARITY:
            continue
        # 文件大小
        file_size = row[5]
        if file_size.find(" B") > 0:
            file_size = float(file_size.replace(" B", "").strip())
        elif file_size.find(" KB") > 0:
            file_size = float(file_size.replace(" KB", "").strip()) * 1024
        elif file_size.find(" MB") > 0:
            file_size = float(file_size.replace(" MB", "").strip()) * 1024 * 1024
        elif file_size.find(" GB") > 0:
            file_size = float(file_size.replace(" GB", "").strip()) * 1024 * 1024 * 1024
        else:
            print("unknown file_size " + file_size)
            return
        file_size = int(file_size)
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
    if record_file_path:
        console.log("keep " + record_file_path)


if __name__ == "__main__":
    main(DUPLICATE_CSV_FILE_PATH)
