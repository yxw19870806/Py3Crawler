# -*- coding:UTF-8  -*-
# 获取指定存档文件中是否存在重复的主键
import os
from common import *

# 存档路径
SAVE_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "save.data"))
# 存档中唯一标示（如，账号id）的字段下标
NAME_COLUMN = 0


# 检测存档文件中是否有相同的主键
def check_is_repeat():
    history = []
    for line in file.read_file(SAVE_FILE_PATH, const.ReadFileMode.LINE):
        temp_list = line.strip("\n\r").split("\t")
        if temp_list[NAME_COLUMN] in history:
            console.log(temp_list[NAME_COLUMN])
        else:
            history.append(temp_list[NAME_COLUMN])
    return history


if __name__ == "__main__":
    check_is_repeat()
