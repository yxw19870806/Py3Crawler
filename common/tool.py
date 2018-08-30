# -*- coding:UTF-8  -*-
"""
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import json
import os
import platform
import random
import string
import sys

# if sys.stdout.encoding != "UTF-8":
#     raise Exception("项目编码必须是UTF-8，请在IDE中修改相关设置")
if sys.version_info < (3,):
    raise Exception("仅支持python3.X，请访问官网 https://www.python.org/downloads/ 安装最新的python3")
if getattr(sys, "frozen", False):
    IS_EXECUTABLE = True
else:
    IS_EXECUTABLE = False


# 根据开始与结束的字符串，截取字符串
# include_string是否包含查询条件的字符串
#   0 都不包含
#   1 只包含start_string
#   2 只包含end_string
#   3 包含start_string和end_string
def find_sub_string(haystack, start_string=None, end_string=None, include_string=0):
    # 参数验证
    haystack = str(haystack)
    if start_string is not None:
        start_string = str(start_string)
    if end_string is not None:
        end_string = str(end_string)
    include_string = int(include_string)
    if 0 < include_string > 3:
        include_string = 3

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
    if include_string & 1 == 1 and start_string is not None:
        find_string = start_string + find_string
    if include_string & 2 == 2 and end_string is not None:
        find_string += end_string
    return find_string


# decode a json string
def json_decode(json_string, default_value=None):
    try:
        return json.loads(json_string)
    except ValueError:
        pass
    except TypeError:
        pass
    return default_value


# 按照指定连接符合并二维数组生成字符串
def list_to_string(source_lists, first_sign="\n", second_sign="\t"):
    temp_list = []
    for value in source_lists:
        if second_sign != "":
            temp_list.append(second_sign.join(map(str, value)))
        else:
            temp_list.append(str(value))
    return first_sign.join(temp_list)


# 按照指定分割符，分割字符串生成二维数组
def string_to_list(source_string, first_split="\n", second_split="\t"):
    result = source_string.split(first_split)
    if second_split is None:
        return result
    temp_list = []
    for line in result:
        temp_list.append(line.split(second_split))
    return temp_list


# 生成指定长度的随机字符串
# char_lib_type 需要的字库取和， 1 - 大写字母；2 - 小写字母; 4 - 数字，默认7(1+2+4)包括全部
def generate_random_string(string_length, char_lib_type=7):
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
    for random_count in range(0, string_length):
        result.append(random.choice(char_pool))
    return "".join(result)


# 结束进程
# exit_code 0: 正常结束, 1: 异常退出
def process_exit(exit_code=1):
    sys.exit(exit_code)


# 定时关机
def shutdown(delay_time=30):
    if platform.system() == "Windows":
        os.system("shutdown -s -f -t " + str(delay_time))
    else:
        os.system("halt")
