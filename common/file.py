# -*- coding:UTF-8  -*-
"""
文件操作类
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import hashlib
import os

try:
    from . import path
except ImportError:
    from common import path

READ_FILE_TYPE_FULL = 1  # 读取整个文件 ，返回字符串
READ_FILE_TYPE_LINE = 2  # 按行读取，返回list

WRITE_FILE_TYPE_APPEND = 1  # 追加写入文件
WRITE_FILE_TYPE_REPLACE = 2  # 覆盖写入文件

BOM_SIGN = b'\xef\xbb\xbf'.decode()


def read_file(file_path, read_type=READ_FILE_TYPE_FULL):
    """Read local file

    :param file_path:
        the path of file

    :param read_type:
        READ_FILE_TYPE_FULL     read full file
        READ_FILE_TYPE_LINE     read each line of file

    :return:
        READ_FILE_TYPE_FULL     type of string
        READ_FILE_TYPE_LINE     type of list
    """
    file_path = os.path.abspath(file_path)
    if not os.path.exists(file_path):
        if read_type == 1:
            return ""
        else:
            return []
    with open(file_path, "r", encoding="UTF-8") as file_handle:
        if read_type == 1:
            result = file_handle.read()
            if len(result) > 0:
                if result[0] == BOM_SIGN:
                    result = result[1:]
                if result[-1] == "\n":
                    result = result[:-1]
        else:
            result = []
            for line in file_handle.readlines():
                if len(line) > 0:
                    if line[0] == BOM_SIGN:
                        line = line[1:]
                    if line[-1] == "\n":
                        line = line[:-1]
                if len(line) == 0:
                    continue
                result.append(line)
    return result


def write_file(msg, file_path, append_type=WRITE_FILE_TYPE_APPEND):
    """Write local file

    :param file_path:
        the path of file

    :param append_type:
        WRITE_FILE_TYPE_APPEND      "a" mode to write file
        WRITE_FILE_TYPE_REPLACE     "w" mode to write file

    :return:
        READ_FILE_TYPE_FULL     type of string
        READ_FILE_TYPE_LINE     type of list
    """
    file_path = os.path.abspath(file_path)
    if not path.create_dir(os.path.dirname(file_path)):
        return False
    if append_type == WRITE_FILE_TYPE_APPEND:
        open_type = "a"
    elif append_type == WRITE_FILE_TYPE_REPLACE:
        open_type = "w"
    else:
        return False
    with open(file_path, open_type, encoding="UTF-8") as file_handle:
        file_handle.write(msg + "\n")


# 获取指定文件的MD5值
def get_file_md5(file_path):
    file_path = os.path.abspath(file_path)
    if not os.path.exists(file_path):
        return None
    md5_class = hashlib.md5()
    with open(file_path, "rb") as file_handle:
        buffer_size = 2 ** 20  # 1M
        while True:
            file_buffer = file_handle.read(buffer_size)
            if not file_buffer:
                break
            md5_class.update(file_buffer)
    return md5_class.hexdigest()
