# -*- coding:UTF-8  -*-
"""
文件操作类
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import hashlib
import os
from typing import Union, Optional, Final
from common import const, path

BOM_SIGN: Final[str] = b"\xef\xbb\xbf".decode()


def read_file(file_path: str, read_type: const.ReadFileMode = const.ReadFileMode.FULL) -> Union[str, list]:
    """
    读取文件

    :Args:
    - file_path - 需要读取文件的路径
    - read_type - 读取类型
        const.ReadFileMode.FULL   read full file
        const.ReadFileMode.LINE   read each line of file

    :Returns:
        const.ReadFileMode.FULL   type of string
        const.ReadFileMode.LINE   type of list
    """
    if not isinstance(read_type, const.ReadFileMode):
        raise ValueError("invalid read_type")
    if read_type == const.ReadFileMode.FULL:
        default_value = ""
    else:
        default_value = []
    if not file_path:
        return default_value
    file_path = os.path.abspath(file_path)
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return default_value
    with open(file_path, "r", encoding="UTF-8") as file_handle:
        if read_type == const.ReadFileMode.FULL:
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


def write_file(msg: str, file_path: str, write_type: const.WriteFileMode = const.WriteFileMode.APPEND, encoding: str = "UTF-8") -> bool:
    """
    写入文件

    :Args:
    - file_path: - 需要写入文件的路径
    - append_type - 写入模式
        const.WriteFileMode.APPEND    "a" mode to write file
        const.WriteFileMode.REPLACE   "w" mode to write file
    """
    if not isinstance(write_type, const.WriteFileMode):
        raise ValueError("invalid write_type")
    if not file_path:
        return False
    file_path = os.path.abspath(file_path)
    if not path.create_dir(os.path.dirname(file_path)):
        return False
    if write_type == const.WriteFileMode.APPEND:
        open_type = "a"
    else:
        open_type = "w"
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
