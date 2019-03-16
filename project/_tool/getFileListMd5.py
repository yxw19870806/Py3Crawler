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
RECORD_LIST = {}


# 获取之前的记录
def get_record_data():
    global RECORD_LIST
    record_list = file.read_file(RECORD_FILE_PATH, file.READ_FILE_TYPE_LINE)
    for record in record_list:
        temp = record.split("\t")
        RECORD_LIST[os.path.basename(temp[0])] = temp[1]


# 递归获取一个目录下的所有文件的md5值
def get_file_md5_from_dir(dir_path):
    for file_name in path.get_dir_files_name(dir_path):
        file_path = os.path.join(dir_path, file_name)
        if os.path.isdir(file_path):
            get_file_md5_from_dir(file_path)
        else:
            if file_name in RECORD_LIST:
                continue
            file_md5 = file.get_file_md5(file_path)
            print("%s -> %s" % (file_path, file_md5))
            file.write_file("%s\t%s" % (file_path, file_md5), RECORD_FILE_PATH)


def main():
    get_record_data()
    get_file_md5_from_dir(FILE_ROOT_PATH)


if __name__ == "__main__":
    main()
