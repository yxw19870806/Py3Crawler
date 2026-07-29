# -*- coding:UTF-8  -*-
# 获取指定存档文件中是否存在重复的主键
import os
import tkinter
from tkinter import filedialog

from common import *

# 存档中唯一标示（如，账号id）的字段下标
NAME_COLUMN = 0


# 检测存档文件中是否有相同的主键
def check_is_repeat(save_data_path):
    history = []
    for line in file.read_file(save_data_path, const.ReadFileMode.LINE):
        temp_list = line.strip("\n\r").split("\t")
        if temp_list[NAME_COLUMN] in history:
            log.warn(temp_list[NAME_COLUMN])
        else:
            history.append(temp_list[NAME_COLUMN])
    return history


def main():
    gui = tkinter.Tk()
    gui.withdraw()

    options = {
        "initialdir": os.path.dirname(__file__),
        "initialfile": "save.data",
        "filetypes": [("data file", "*.data"), ("all files", "*")],
        "parent": gui,
    }

    save_data_path = tkinter.filedialog.askopenfilename(**options)
    if not save_data_path:
        tool.process_exit()

    check_is_repeat(save_data_path)

    print("check done")


if __name__ == "__main__":
    main()
