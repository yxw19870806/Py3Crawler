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
        similarity = int(tool.remove_string_suffix(row[3].strip(), "%"))
        if similarity < MIN_SIMILARITY:
            continue
        # 文件大小
        file_size = row[5].strip()
        if file_size.endswith(" B"):
            file_size = float(tool.remove_string_suffix(file_size, " B"))
        elif file_size.endswith(" KB"):
            file_size = float(tool.remove_string_suffix(file_size, " KB")) * const.SIZE_KB
        elif file_size.endswith(" MB"):
            file_size = float(tool.remove_string_suffix(file_size, " MB")) * const.SIZE_MB
        elif file_size.endswith(" GB"):
            file_size = float(tool.remove_string_suffix(file_size, " GB")) * const.SIZE_GB
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
        log.info("delete " + file_path)
    if record_file_path:
        log.info("keep " + record_file_path)


if __name__ == "__main__":
    main(DUPLICATE_CSV_FILE_PATH)
