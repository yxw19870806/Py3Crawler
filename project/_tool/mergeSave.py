# -*- coding:UTF-8  -*-
# 合并两个存档文件，相同的id后者覆盖前者
import os
import tkinter
from tkinter import filedialog
from common import *

# 存档中作为保存文件夹名字所在字段所在数组下标，从0开始
PRIME_KEY_INDEX = 0


def main():
    # GUI窗口
    gui = tkinter.Tk()
    gui.withdraw()
    # 原始存档文件所在路径
    options = {
        "initialdir": os.path.join(os.path.dirname(__file__), "video"),
        "initialfile": "save.data",
        "filetypes": [("data", ".data"), ("all file", "*")],
        "title": "原始存档文件",
    }
    save_data_file_path = tkinter.filedialog.askopenfilename(**options)
    if not save_data_file_path:
        return
    options["title"] = "临时存档文件"
    temp_save_data_file_path = tkinter.filedialog.askopenfilename(**options)
    if not save_data_file_path:
        return
    if save_data_file_path == temp_save_data_file_path:
        output.print_msg("存档文件相同，无需合并")
        return
    # 临时存档文件所在路径
    save_data = crawler.read_save_data(save_data_file_path, PRIME_KEY_INDEX)
    temp_save_data = crawler.read_save_data(temp_save_data_file_path, PRIME_KEY_INDEX)
    save_data.update(temp_save_data)
    temp_list = [save_data[key] for key in sorted(save_data.keys())]
    file.write_file(tool.list_to_string(temp_list), save_data_file_path, crawler_enum.WriteFileMode.REPLACE)


if __name__ == "__main__":
    main()
