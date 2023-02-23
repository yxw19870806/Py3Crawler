# -*- coding:UTF-8  -*-
"""
文件操作类
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import hashlib
import os
from typing import Union, Optional

try:
    from . import path
except ImportError:
    from common import path

READ_FILE_TYPE_FULL = 1  # 读取整个文件 ，返回字符串
READ_FILE_TYPE_LINE = 2  # 按行读取，返回list

WRITE_FILE_TYPE_APPEND = 1  # 追加写入文件
WRITE_FILE_TYPE_REPLACE = 2  # 覆盖写入文件

BOM_SIGN = b"\xef\xbb\xbf".decode()


def read_file(file_path: str, read_type: int = READ_FILE_TYPE_FULL) -> Union[str, list]:
    """
    读取文件

    :Args:
    - file_path - 需要读取文件的路径
    - read_type - 读取类型
        READ_FILE_TYPE_FULL     read full file
        READ_FILE_TYPE_LINE     read each line of file

    :Returns:
        READ_FILE_TYPE_FULL     type of string
        READ_FILE_TYPE_LINE     type of list
    """
    if read_type not in [READ_FILE_TYPE_FULL, READ_FILE_TYPE_LINE]:
        read_type = READ_FILE_TYPE_FULL
    if read_type == READ_FILE_TYPE_FULL:
        default_value = ""
    else:
        default_value = []
    if not file_path:
        return default_value
    file_path = os.path.abspath(file_path)
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return default_value
    with open(file_path, "r", encoding="UTF-8") as file_handle:
        if read_type == READ_FILE_TYPE_FULL:
            result = file_handle.read()
            if len(result) > 0:
                if result.startswith(BOM_SIGN):
                    result = result[len(BOM_SIGN):]
                if result.endswith("\n"):
                    result = result[:-len("\n")]
        else:
            result = []
            for line in file_handle.readlines():
                if len(line) > 0:
                    if line.startswith(BOM_SIGN):
                        line = line[len(BOM_SIGN):]
                    if line.endswith("\n"):
                        line = line[:-len("\n")]
                if len(line) == 0:
                    continue
                result.append(line)
    return result


def write_file(msg: str, file_path: str, append_type: int = WRITE_FILE_TYPE_APPEND, encoding: str = "UTF-8") -> bool:
    """
    写入文件

    :Args:
    - file_path: - 需要写入文件的路径
    - append_type - 写入模式
        WRITE_FILE_TYPE_APPEND      "a" mode to write file
        WRITE_FILE_TYPE_REPLACE     "w" mode to write file

    :Returns:
        READ_FILE_TYPE_FULL     type of string
        READ_FILE_TYPE_LINE     type of list
    """
    if append_type not in [WRITE_FILE_TYPE_APPEND, WRITE_FILE_TYPE_REPLACE]:
        append_type = WRITE_FILE_TYPE_APPEND
    if not file_path:
        return False
    file_path = os.path.abspath(file_path)
    if not path.create_dir(os.path.dirname(file_path)):
        return False
    if append_type == WRITE_FILE_TYPE_APPEND:
        open_type = "a"
    elif append_type == WRITE_FILE_TYPE_REPLACE:
        open_type = "w"
    else:
        return False
    with open(file_path, open_type, encoding=encoding) as file_handle:
        file_handle.write(msg + "\n")
    return True


def get_file_md5(file_path: str) -> Optional[str]:
    """
    获取指定文件的MD5值
    """
    if not file_path:
        return None
    file_path = os.path.abspath(file_path)
    if not os.path.exists(file_path):
        return None
    md5_class = hashlib.md5()
    with open(file_path, "rb") as file_handle:
        buffer_size = 2 ** 20  # 1M
        while file_buffer := file_handle.read(buffer_size):
            md5_class.update(file_buffer)
    return md5_class.hexdigest()
