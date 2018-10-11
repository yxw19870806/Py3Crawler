# -*- coding:UTF-8  -*-
"""
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import *
from project.ivseek import ivseek, ivseekCommon


def main():
    # 初始化类
    ivseek_obj = ivseek.IvSeek()

    save_data = ivseekCommon.read_save_data(ivseek_obj.save_data_path)
    done_list = {}
    for single_save_list in save_data:
        if single_save_list[4] == ivseekCommon.DONE_SING:
            done_list[single_save_list[3]] = 1
    for single_save_list in save_data:
        if single_save_list[3] != "" and single_save_list[3] in done_list:
            if single_save_list[4] != ivseekCommon.DONE_SING:
                single_save_list[4] = ivseekCommon.DONE_SING
                output.print_msg("new done account " + str(single_save_list))
    file.write_file(tool.list_to_string(save_data), ivseek_obj.save_data_path, file.WRITE_FILE_TYPE_REPLACE)


if __name__ == "__main__":
    main()
