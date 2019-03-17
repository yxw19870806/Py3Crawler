# -*- coding:UTF-8  -*-
"""
获取一个目录下的所有文件的MD5值
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from common import *

FILE_ROOT_PATH = os.path.abspath("D:\\")
RECORD_FILE_PATH = os.path.join(os.path.dirname(__file__), "md5.txt")
DELETED_FILE_PATH = os.path.join(os.path.dirname(__file__), "delete.txt")


# 递归获取一个目录下的所有文件的md5值
def get_file_md5_from_dir(dir_path):
    record_string_list = file.read_file(RECORD_FILE_PATH, file.READ_FILE_TYPE_LINE)
    record_list = {}
    for record in record_string_list:
        temp = record.split("\t")
        record_list[os.path.basename(temp[0])] = temp[1]

    for file_name in path.get_dir_files_name(dir_path):
        file_path = os.path.join(dir_path, file_name)
        if os.path.isdir(file_path):
            get_file_md5_from_dir(file_path)
        else:
            if file_name in record_list:
                continue
            file_md5 = file.get_file_md5(file_path)
            output.print_msg("%s -> %s" % (file_path, file_md5))
            file.write_file("%s\t%s" % (file_path, file_md5), RECORD_FILE_PATH)


# 根据生产的md5文件查重并是删除
def check_record_data():
    record_list = file.read_file(RECORD_FILE_PATH, file.READ_FILE_TYPE_LINE)
    duplicate_list = {}
    check_list = {}
    for record in record_list:
        file_path, file_md5 = record.split("\t")
        if file_md5 not in check_list:
            check_list[file_md5] = file_path
        else:
            if file_md5 not in duplicate_list:
                duplicate_list[file_md5] = [check_list[file_md5]]
            duplicate_list[file_md5].append(file_path)
    for file_md5 in duplicate_list:
        deal_one_group(duplicate_list[file_md5])


# 对同一组别的文件进行处理
# 优先删除文件大小较小的
def deal_one_group(file_list):
    min_record_id = 0
    record_file_path = ""
    delete_list = []
    for file_path in file_list:
        file_name = os.path.basename(file_path)
        record_id = int(str(file_name.split(".")[0]).split("_")[0])
        # 进行比较
        if min_record_id == 0:  # 第一次，设置记录
            min_record_id = record_id
            record_file_path = file_path
        elif record_id > min_record_id:  # id比记录的文件大，删除当前的
            delete_list.append(file_path)
        else:  # 相同大小，id比记录的文件小，删除记录的
            delete_list.append(record_file_path)
            min_record_id = record_id
            record_file_path = file_path
    for file_path in delete_list:
        path.delete_dir_or_file(file_path)
        output.print_msg("delete " + file_path)
    file.write_file("\n".join(delete_list), DELETED_FILE_PATH, file.WRITE_FILE_TYPE_APPEND)
    output.print_msg("keep " + record_file_path)


# 重写记录文件
def rewrite_recode_file():
    record_list = file.read_file(RECORD_FILE_PATH, file.READ_FILE_TYPE_LINE)
    delete_list = file.read_file(DELETED_FILE_PATH, file.READ_FILE_TYPE_LINE)
    new_result = []
    for record in record_list:
        file_path, file_md5 = record.split("\t")
        if file_path not in delete_list:
            new_result.append(record)
    file.write_file("\n".join(new_result), RECORD_FILE_PATH, file.WRITE_FILE_TYPE_REPLACE)


def main():
    get_file_md5_from_dir(FILE_ROOT_PATH)
    check_record_data()
    rewrite_recode_file()


if __name__ == "__main__":
    main()
