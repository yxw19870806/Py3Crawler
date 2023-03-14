# -*- coding:UTF-8  -*-
"""
一些暂时用不到的方法
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import zipfile
from common import const, path


def zip_dir(source_dir: str, zip_file_path: str, need_source_dir=True) -> bool:
    """
    压缩文件夹

    :Args:
    - need_source_dir - 是否需要把文件夹名作为根目录
    """
    if not os.path.exists(source_dir) or os.path.exists(zip_file_path):
        return False

    file_list = []
    path_prefix_len = len(source_dir)  # 文件列表路径前缀的长度
    # 是文件，直接添加
    if os.path.isfile(source_dir):
        file_list.append(source_dir)
    else:
        # 如果需要包含目录
        if need_source_dir:
            path_prefix_len -= len(os.path.basename(source_dir)) + 1
        for root, dirs, files in os.walk(source_dir):
            for name in files:
                file_list.append(os.path.join(root, name))

    with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in file_list:
            in_zip_file_path = file_path[path_prefix_len:]
            zip_file.write(file_path, in_zip_file_path)

    return zipfile.is_zipfile(zip_file_path)


def unzip_file(zip_file_path: str, destination_path: str) -> bool:
    """
    解压缩文件
    """
    if not os.path.exists(zip_file_path) or os.path.exists(destination_path):
        return False

    os.makedirs(destination_path)

    zip_file = zipfile.ZipFile(zip_file_path)
    for zip_file_path in zip_file.namelist():
        zip_file_path = zip_file_path.replace("\\", "/")
        if zip_file_path.endswith("/"):  # 解压目录
            os.makedirs(os.path.join(destination_path, zip_file_path))
        else:  # 解压文件
            file_path = os.path.join(destination_path, zip_file_path)  # 文件的完整路径
            file_dir = os.path.dirname(file_path)
            if not os.path.exists(file_dir):
                os.makedirs(file_dir)
            outfile = open(file_path, "wb")
            outfile.write(zip_file.read(zip_file_path))
            outfile.close()

    return os.path.exists(destination_path)


def sort_file(source_path: str, destination_path: str, start_count: int, file_name_length: int) -> bool:
    """
    将指定文件夹内的所有文件排序重命名并复制到其他文件夹中

    :Args:
    - source_path - 待排序文件所在目录
    - destination_path - 排序后所复制的目录
    - start_count - 重命名开始的序号
    - file_name_length - 复制后的文件名长度
    """
    file_list = path.get_dir_files_name(source_path, const.OrderType.DESC)
    # 判断排序目标文件夹是否存在
    if len(file_list) >= 1:
        if not path.create_dir(destination_path):
            return False
        # 倒叙排列
        for file_name in file_list:
            start_count += 1
            file_extension = os.path.splitext(file_name)[1]  # 包括 .扩展名
            new_file_name = str(("%0" + str(file_name_length) + "d") % start_count) + file_extension
            path.copy_file(os.path.join(source_path, file_name), os.path.join(destination_path, new_file_name))
        # 删除临时文件夹
        path.delete_dir_or_file(source_path)
    return True
