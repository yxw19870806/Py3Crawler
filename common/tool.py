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
from typing import Any, NoReturn, Optional, Union
from common import const


def find_sub_string(haystack: str, start_string: Optional[str] = None, end_string: Optional[str] = None, include_string: const.IncludeStringMode = const.IncludeStringMode.NONE) -> str:
    """
    根据开始与结束的字符串，截取字符串

    :Args:
    - include_string - 是否包含查询条件的字符串
        IncludeStringMode.NONE  都不包含
        IncludeStringMode.START 只包含start_string
        IncludeStringMode.END   只包含end_string
        IncludeStringMode.ALL   包含start_string和end_string
    """
    # 参数验证
    if not isinstance(include_string, const.IncludeStringMode):
        raise ValueError("invalid include_string")
    haystack = str(haystack)
    if start_string is not None:
        start_string = str(start_string)
    if end_string is not None:
        end_string = str(end_string)

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
    if start_string is not None and include_string in [const.IncludeStringMode.START, const.IncludeStringMode.ALL]:
        find_string = start_string + find_string
    if end_string is not None and include_string in [const.IncludeStringMode.END, const.IncludeStringMode.ALL]:
        find_string += end_string
    return find_string


def remove_string_prefix(haystack: str, start_string: str) -> str:
    """
    移除字符串的指定前缀
    """
    return haystack[len(start_string):] if haystack.startswith(start_string) else haystack


def remove_string_suffix(haystack: str, end_string: str) -> str:
    """
    移除字符串的指定后缀
    """
    return haystack[:-len(end_string)] if haystack.endswith(end_string) else haystack


def is_integer(number: Any) -> bool:
    """
    判断是不是整型，或者纯数字的字符串
    """
    if isinstance(number, bool) or isinstance(number, list) or isinstance(number, dict) or number is None:
        return False
    elif isinstance(number, int):
        return True
    else:
        return not re.compile("^[-+]?[0-9]+$").match(str(number)) is None


def is_date(date_string: str) -> bool:
    """
    判断字符串是否是有效的日期，格式：YYYY-mm-dd
    """
    return re.match(r"^\d{4}-\d{2}-\d{2}$", date_string) is not None


def json_decode(json_string: str, default_value=None) -> Any:
    """
    将json字符串解码为json对象
    """
    try:
        return json.loads(json_string)
    except json.decoder.JSONDecodeError:
        pass
    return default_value


def json_encode(json_obj: Union[list, dict], default_value=None) -> str:
    """
    将json对象编码为json字符串
    """
    try:
        return json.dumps(json_obj)
    except (TypeError, ValueError):
        pass
    return default_value


def dyadic_list_to_string(source_lists: list[list], first_sign: str = "\n", second_sign: str = "\t") -> str:
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


def string_to_dyadic_list(source_string: str, first_split: str = "\n", second_split: str = "\t") -> list[list[str]]:
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


def filter_emoji(text: str) -> str:
    """
    替换文本中的表情符号
    """
    try:
        emoji = re.compile("[\U00010000-\U0010ffff]")
    except re.error:
        emoji = re.compile("[\uD800-\uDBFF][\uDC00-\uDFFF]")
    return emoji.sub("", text)


def process_exit(exit_code: const.ExitCode = const.ExitCode.ERROR) -> NoReturn:
    """
    结束进程

    :Args:
    - exit_code - 状态码
        ExitCode.NORMAL     正常结束
        ExitCode.ERROR      异常退出
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


def convert_timestamp_to_formatted_time(time_format: str = "%m-%d %H:%M:%S", timestamp: Optional[Union[float, int]] = None) -> str:
    """
    时间戳 转换成 格式化时间
    """
    if timestamp is None:
        timestamp = time.time()
    return time.strftime(time_format, time.localtime(timestamp))


def convert_formatted_time_to_timestamp(time_string: str, time_format: str = "%Y-%m-%d %H:%M:%S") -> int:
    """
    格式化时间 转换成 时间戳
    """
    return int(time.mktime(time.strptime(time_string, time_format)))


def change_date_format(date_string: str, old_format: str, new_format: str = "%Y-%m-%d") -> str:
    return time.strftime(new_format, time.strptime(date_string, old_format))


def check_dict_sub_key(needles: Union[str, tuple], haystack: dict) -> bool:
    """
    判断类型是否为字典，并且检测是否存在指定的key
    """
    if not isinstance(needles, tuple):
        needles = tuple(needles)
    if isinstance(haystack, dict):
        for needle in needles:
            if needle not in haystack:
                return False
        return True
    return False
