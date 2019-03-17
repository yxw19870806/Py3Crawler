# -*- coding:UTF-8  -*-
"""
获取一个目录下的所有文件的MD5值
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import traceback
from common import *


# 对同一组别的文件进行处理
# 优先删除文件大小较小的
def deal_one_group(file_list):
    min_record_id = 0
    record_file_path = ""
    delete_list = []
    for file_path in file_list:
        file_name = os.path.basename(file_path)
        record_id = int(str(file_name.split(".")[0]).split("_")[0])
        # 进行比较
        if min_record_id == 0:  # 第一次，设置记录
            min_record_id = record_id
            record_file_path = file_path
        elif record_id > min_record_id:  # id比记录的文件大，删除当前的
            delete_list.append(file_path)
        else:  # 相同大小，id比记录的文件小，删除记录的
            delete_list.append(record_file_path)
            min_record_id = record_id
            record_file_path = file_path
    for file_path in delete_list:
        path.delete_dir_or_file(file_path)
        output.print_msg("delete " + file_path)
    output.print_msg("keep " + record_file_path)
    return delete_list


class GetFileListMd5(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_NOT_CHECK_SAVE_DATA: True,
            crawler.SYS_NOT_DOWNLOAD: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        self.save_data_path = os.path.join(os.path.dirname(__file__), "md5.txt")
        self.deleted_file_path = os.path.join(os.path.dirname(__file__), "delete.txt")
        self.record_list = {}
        self.check_count = 0

    # 获取目录所有文件md5值
    def get_file_md5_from_dir(self, dir_path):
        log.step("开始检测目录：" + dir_path)
        for file_name in path.get_dir_files_name(dir_path):
            if not self.is_running():
                tool.process_exit(0)

            file_path = os.path.join(dir_path, file_name)

            if os.path.isdir(file_path):
                self.get_file_md5_from_dir(file_path)
            else:
                if file_name in self.record_list:
                    continue

                file_md5 = file.get_file_md5(file_path)
                self.check_count += 1
                log.step("%s -> %s" % (file_path, file_md5))
                file.write_file("%s\t%s" % (file_path, file_md5), self.save_data_path)
        log.step("已完成：" + dir_path)


    # 根据生产的md5文件查重并是删除
    def check_record_data(self):
        record_list = file.read_file(self.save_data_path, file.READ_FILE_TYPE_LINE)
        duplicate_list = {}
        check_list = {}
        for record in record_list:
            file_path, file_md5 = record.split("\t")
            if file_md5 not in check_list:
                check_list[file_md5] = file_path
            else:
                if file_md5 not in duplicate_list:
                    duplicate_list[file_md5] = [check_list[file_md5]]
                duplicate_list[file_md5].append(file_path)

        for file_md5 in duplicate_list:
            delete_list = deal_one_group(duplicate_list[file_md5])
            if len(delete_list) > 0:
                file.write_file("\n".join(delete_list), self.deleted_file_path, file.WRITE_FILE_TYPE_APPEND)

    # 重写记录文件
    def rewrite_recode_file(self):
        record_list = file.read_file(self.save_data_path, file.READ_FILE_TYPE_LINE)
        delete_list = file.read_file(self.deleted_file_path, file.READ_FILE_TYPE_LINE)
        new_result = []
        for record in record_list:
            file_path, file_md5 = record.split("\t")
            if file_path not in delete_list:
                new_result.append(record)
        file.write_file("\n".join(new_result), self.save_data_path, file.WRITE_FILE_TYPE_REPLACE)

    def main(self, file_path):
        try:
            # 读取记录
            record_string_list = file.read_file(self.save_data_path, file.READ_FILE_TYPE_LINE)
            for record in record_string_list:
                temp = record.split("\t")
                self.record_list[os.path.basename(temp[0])] = temp[1]
            log.step("历史检测记录加载完毕，共计文件%s个" % len(self.record_list))

            # 循环获取目录文件md5值
            self.get_file_md5_from_dir(file_path)
            # check_record_data()
            # rewrite_recode_file()
        except (SystemExit, KeyboardInterrupt) as e:
            if isinstance(e, SystemExit) and e.code == 1:
                log.error("异常退出")
            else:
                log.step("提前退出")
        except Exception as e:
            log.error("未知异常")
            log.error(str(e) + "\n" + traceback.format_exc())
        log.step("全部文件检测完毕，耗时%s秒，共计文件%s个" % (self.get_run_time(), self.check_count))


if __name__ == "__main__":
    file_root_path = os.path.abspath("D:\\")
    GetFileListMd5().main(file_root_path)
