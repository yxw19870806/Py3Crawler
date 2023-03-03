# -*- coding:UTF-8  -*-
"""
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import hashlib
import json
import os
import platform
import random
import re
import string
import sys
import time
from typing import Optional, Union, List, NoReturn

# if sys.stdout.encoding != "UTF-8":
#     raise Exception("项目编码必须是UTF-8，请在IDE中修改相关设置")
if sys.version_info < (3,):
    raise Exception("仅支持python3.X，请访问官网 https://www.python.org/downloads/ 安装最新的python3")
if getattr(sys, "frozen", False):
    IS_EXECUTABLE = True
else:
    IS_EXECUTABLE = False

SUB_STRING_MODE_NONE = 0  # 不包含start_string和end_string
SUB_STRING_MODE_ONLY_START = 1  # 只包含start_string
SUB_STRING_MODE_ONLY_END = 2  # 只包含end_string
SUB_STRING_MODE_BOTH = 3  # 同时包含start_string和end_string

PROCESS_EXIT_CODE_NORMAL = 0
PROCESS_EXIT_CODE_ERROR = 1


def find_sub_string(haystack, start_string: Optional[str] = None, end_string: Optional[str] = None, include_string: int = SUB_STRING_MODE_NONE) -> str:
    """
    根据开始与结束的字符串，截取字符串

    :Args:
    - include_string - 是否包含查询条件的字符串
        0   都不包含
        1   只包含start_string
        2   只包含end_string
        3   包含start_string和end_string
    """
    # 参数验证
    haystack = str(haystack)
    if start_string is not None:
        start_string = str(start_string)
    if end_string is not None:
        end_string = str(end_string)
    include_string = int(include_string)
    if SUB_STRING_MODE_NONE < include_string > SUB_STRING_MODE_BOTH:
        include_string = SUB_STRING_MODE_BOTH

    if start_string is None:
        start_index = 0
    else:
        # 开始字符串第一次出现的位置
        start_index = haystack.find(start_string)
        if start_index == -1:
            return ""
        # 加上开始字符串的长度
        if start_string is not None:
            start_index += len(start_string)

    if end_string is None:
        stop_index = len(haystack)
    else:
        # 结束字符串第一次出现的位置
        stop_index = haystack.find(end_string, start_index)
        if stop_index == -1:
            return ""

    find_string = haystack[start_index:stop_index]
    # 是否需要追加开始或结束字符串
    if include_string & SUB_STRING_MODE_ONLY_START == SUB_STRING_MODE_ONLY_START and start_string is not None:
        find_string = start_string + find_string
    if include_string & SUB_STRING_MODE_ONLY_END == SUB_STRING_MODE_ONLY_END and end_string is not None:
        find_string += end_string
    return find_string


def is_integer(number) -> bool:
    """
    判断是不是整型，或者纯数字的字符串
    """
    if isinstance(number, int):
        return True
    elif isinstance(number, bool) or isinstance(number, list) or isinstance(number, dict) or number is None:
        return False
    else:
        return not re.compile("^[-+]?[0-9]+$").match(str(number)) is None


def json_decode(json_string: str, default_value=None) -> Union[list, dict, str]:
    """
    将json字符串解码为json对象
    """
    try:
        return json.loads(json_string)
    except ValueError:
        pass
    except TypeError:
        pass
    return default_value


def json_encode(json_obj: Union[list, dict], default_value=None) -> str:
    """
    将json对象编码为json字符串
    """
    try:
        return json.dumps(json_obj)
    except ValueError:
        pass
    except TypeError:
        pass
    return default_value


def list_to_string(source_lists: List[list], first_sign: str = "\n", second_sign: str = "\t") -> str:
    """
    按照指定连接符，合并二维列表生成字符串

    :Args:
    - source_lists - 需要合并的列表
    - first_sign - 第一维列表的连接字符
    - second_sign - 第二维列表的连接字符
    """
    temp_list = []
    for value in source_lists:
        temp_list.append(second_sign.join(map(str, value)))
    return first_sign.join(temp_list)


def string_to_list(source_string: str, first_split: str = "\n", second_split: str = "\t") -> List[list]:
    """
    按照指定分割符，分割字符串生成二维列表

    :Args:
    - source_string - 需要分割的字符串
    - first_split - 第一维列表的分割字符
    - second_split - 第二维列表的分割字符
    """
    result = source_string.split(first_split)
    temp_list = []
    for line in result:
        temp_list.append(line.split(second_split))
    return temp_list


def generate_random_string(string_length: int, char_lib_type: int = 7) -> str:
    """
    生成指定长度的随机字符串

    :Args:
    - string_length - 字符串长度
    - char_lib_type - 生成规则（与运算）
        1   大写字母
        2   小写字母
        4   数字
        7   默认，全部（数字+大小写字母）(1 & 2 & 4)
    """
    char_lib = {
        1: string.ascii_lowercase,  # 小写字母
        2: string.ascii_uppercase,  # 大写字母
        4: "0123456789",  # 数字
    }
    char_pool = []
    for i, random_string in char_lib.items():
        if char_lib_type & i == i:
            char_pool.append(random_string)
    char_pool = "".join(char_pool)
    if not char_pool:
        return ""
    result = []
    for random_count in range(string_length):
        result.append(random.choice(char_pool))
    return "".join(result)


def string_md5(source_string: str) -> str:
    """
    字符串md5
    """
    if not isinstance(source_string, str):
        return ""
    md5_class = hashlib.md5()
    md5_class.update(source_string.encode())
    return md5_class.hexdigest()


def process_exit(exit_code: int = PROCESS_EXIT_CODE_ERROR) -> NoReturn:
    """
    结束进程

    :Args:
    - exit_code - 状态码
        0   正常结束
        1   异常退出
    """
    sys.exit(exit_code)


def shutdown(delay_time: int = 30) -> None:
    """
    定时关机
    """
    if platform.system() == "Windows":
        os.system("shutdown -s -f -t " + str(delay_time))
    else:
        os.system("halt")


def get_time(string_format: str = "%m-%d %H:%M:%S", timestamp: Union[float, int] = time.time()) -> str:
    """
    获取当前时间
    """
    return time.strftime(string_format, time.localtime(timestamp))
