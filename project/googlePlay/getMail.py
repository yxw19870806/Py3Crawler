# -*- coding:UTF-8  -*-
"""
生成去重开发者邮箱列表
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import csv
from project.googlePlay import appInfo


def main():
    # 之前的记录
    mail_list = {}
    if os.path.exists(appInfo.DEVELOPER_MAIL_FILE_PATH):
        with open(appInfo.DEVELOPER_MAIL_FILE_PATH, "r", encoding="UTF-8") as file_handle:
            for temp_list in csv.reader(file_handle):
                if len(temp_list) == 0:
                    continue
                mail_list[temp_list[0]] = 1

    with open(appInfo.RESULT_FILE_PATH, "r", encoding="UTF-8") as source_file_handle, \
            open(appInfo.DEVELOPER_MAIL_FILE_PATH, "a", newline="", encoding="UTF-8") as destination_file_handle:
        csv_writer = csv.writer(destination_file_handle)
        for app_info in csv.reader(source_file_handle):
            if len(app_info) == 0:
                continue
            # 已经查过了，跳过
            developer_mail = app_info[6]
            if developer_mail in mail_list:
                continue
            mail_list[developer_mail] = 1
            csv_writer.writerow([developer_mail])


if __name__ == "__main__":
    main()
