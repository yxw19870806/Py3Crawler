# -*- coding:UTF-8  -*-
"""
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import *
from project.ivseek import ivseekCommon


def main():
    save_data_path = crawler.quickly_get_save_data_path()
    save_data = ivseekCommon.read_save_data(save_data_path)
    done_list = {}
    for single_save_list in save_data:
        if single_save_list[4] == ivseekCommon.DONE_SING:
            done_list[single_save_list[3]] = 1
    for single_save_list in save_data:
        if single_save_list[3] != "" and single_save_list[3] in done_list:
            if single_save_list[4] != ivseekCommon.DONE_SING:
                single_save_list[4] = ivseekCommon.DONE_SING
                output.print_msg("new done account " + str(single_save_list))
    tool.write_file(tool.list_to_string(save_data), save_data_path, tool.WRITE_FILE_TYPE_REPLACE)

if __name__ == "__main__":
    main()
