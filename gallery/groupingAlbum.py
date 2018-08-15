# -*- coding:UTF-8  -*-
"""
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from common import *

ALBUM_ROOT_PATH = "D:\\album"
RESULT_FILE_PATH = "D:\\result"
ALBUM_CATEGORY_LIST = []


def main():
    for website_name in path.get_dir_files_name(ALBUM_ROOT_PATH):
        website_path = os.path.join(ALBUM_ROOT_PATH, website_name)
        website_result_file_path = os.path.join(RESULT_FILE_PATH, "%s.txt" % website_name)
        for album_dir in path.get_dir_files_name(website_path, path.RETURN_FILE_LIST_ASC):
            # 图集id  图集名字
            album_id, album_name = album_dir.split(" ", 1)
            album_path = os.path.join(website_path, album_dir)
            # 图片数量
            file_count = 0
            # 图片总大小
            file_size = 0
            for file_name in path.get_dir_files_name(album_path):
                file_size += os.path.getsize(os.path.join(album_path, file_name))
                file_count += 1
            # 图集分类
            album_category = ""
            for temp_album_category in ALBUM_CATEGORY_LIST:
                if album_name.find(temp_album_category) >= 0:
                    album_category = album_category
                    break
            # 图集id  图集名字  图集分类  图片数量  图片总大小
            tool.write_file("%s\t%s\t%s\t%s\t%s" % (str(int(album_id)), album_name, album_category, file_count, file_size), website_result_file_path)


if __name__ == "__main__":
    main()
