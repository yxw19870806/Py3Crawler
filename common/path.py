# -*- coding:UTF-8  -*-
"""
路径相关类
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import platform
import shutil
import time
from typing import List
from common import enum


def create_dir(dir_path: str, create_mode: enum.CreateDirMode = enum.CreateDirMode.IGNORE) -> bool:
    """
    创建文件夹

    :Args:
    - create_mode - 创建模式
        enum.CreateDirMode.IGNORE   当目录存在时忽略
        enum.CreateDirMode.DELETE   当目录存在时先删除再创建

    :Returns:
        True    创建成功
        False   创建失败
    """
    if not isinstance(create_mode, enum.CreateDirMode):
        raise ValueError("invalid create_mode")
    dir_path = os.path.abspath(dir_path)
    # 目录存在
    if os.path.exists(dir_path):
        if create_mode == enum.CreateDirMode.IGNORE:
            if os.path.isdir(dir_path):
                return True
            else:
                return False
        else:
            if os.path.isdir(dir_path):
                # empty dir
                if not os.listdir(dir_path):
                    return True
        delete_dir_or_file(dir_path)
    try:
        os.makedirs(dir_path)
    except FileExistsError:
        return True
    if os.path.exists(dir_path) and os.path.isdir(dir_path):
        return True
    return False


def delete_dir_or_file(dir_path: str) -> bool:
    """
    删除目录（包括所有子目录和文件）或者文件
    """
    dir_path = os.path.abspath(dir_path)
    if not os.path.exists(dir_path):
        return True
    if os.path.isdir(dir_path):
        # todo 异常捕获
        shutil.rmtree(dir_path, True)
        return True
    else:
        for retry_count in range(5):
            try:
                os.remove(dir_path)
            except PermissionError as e:
                # PermissionError: [WinError 32] 另一个程序正在使用此文件，进程无法访问。
                if str(e).find("[WinError 32]") >= 0:
                    time.sleep(5)
                    continue
                else:
                    raise
            else:
                return True
        else:
            return False


def delete_null_dir(dir_path: str) -> None:
    """
    删除所有空的子目录
    """
    dir_path = os.path.abspath(dir_path)
    if os.path.isdir(dir_path):
        for file_name in os.listdir(dir_path):
            sub_path = os.path.join(dir_path, file_name)
            if os.path.isdir(sub_path):
                delete_null_dir(sub_path)
        if len(os.listdir(dir_path)) == 0:
            os.rmdir(dir_path)


def get_dir_files_name(dir_path: str, order: enum.OrderType = enum.OrderType.DEFAULT, recursive: bool = False, full_path: bool = False) -> List[str]:
    """
    获取目录下的所有文件名

    :Args:
    - order - 排序模式
        enum.OrderType.ASC       根据文件名升序
        enum.OrderType.DESC      根据文件名降序
        enum.OrderType>DEFAULT   默认返回数据
    - recursive - 是否递归获取子目录
    - full_path - 返回的列表是否包含完整路径
    """
    if not isinstance(order, enum.OrderType):
        raise ValueError("invalid order")
    dir_path = os.path.abspath(dir_path)
    if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
        return []

    if recursive:
        files_list = []
        for root, dirs, files in os.walk(dir_path):
            if full_path:
                files_list += list(map(lambda file_name: os.path.join(root, file_name), files))
            else:
                files_list += files
    else:
        try:
            files_list = os.listdir(dir_path)
            if full_path:
                files_list = list(map(lambda file_name: os.path.join(dir_path, file_name), files_list))
        except PermissionError:
            return []
    # 升序
    if order == enum.OrderType.ASC:
        return sorted(files_list, reverse=False)
    # 降序
    elif order == enum.OrderType.DESC:
        return sorted(files_list, reverse=True)
    else:
        return files_list


def copy_file(source_file_path: str, destination_file_path: str) -> bool:
    """
    复制文件
    """
    source_file_path = os.path.abspath(source_file_path)
    destination_file_path = os.path.abspath(destination_file_path)
    # 源文件未存在 或者 目标文件已存在
    if not os.path.exists(source_file_path) or os.path.exists(destination_file_path):
        return False
    # 源文件是个目录
    if not os.path.isfile(source_file_path):
        return False
    if not create_dir(os.path.dirname(destination_file_path)):
        return False
    shutil.copyfile(source_file_path, destination_file_path)
    return os.path.exists(destination_file_path)


def copy_directory(source_dir_path: str, destination_dir_path: str) -> bool:
    """
    复制目录
    """
    # 源文件未存在 或者 目标文件已存在
    source_dir_path = os.path.abspath(source_dir_path)
    destination_dir_path = os.path.abspath(destination_dir_path)
    if not os.path.exists(source_dir_path) or os.path.exists(destination_dir_path):
        return False
    # 源文件不是个目录
    if not os.path.isdir(source_dir_path):
        return False
    if not create_dir(os.path.dirname(destination_dir_path)):
        return False
    shutil.copytree(source_dir_path, destination_dir_path)
    return os.path.isdir(destination_dir_path)


def move_file(source_path: str, destination_path: str) -> bool:
    """
    移动文件
    """
    source_path = os.path.abspath(source_path)
    destination_path = os.path.abspath(destination_path)
    if not os.path.exists(source_path) or os.path.exists(destination_path):
        return False
    if not create_dir(os.path.dirname(destination_path)):
        return False
    shutil.move(source_path, destination_path)
    return os.path.isdir(destination_path)


def filter_text(text: str) -> str:
    """
    过滤字符串中的无效字符（无效的操作系统文件名）
    """
    filter_character_list = ["\t", "\n", "\r", "\b"]
    if platform.system() == "Windows":
        filter_character_list += ["\\", "/", ":", "*", "?", '"', "<", ">", "|"]
    for filter_character in filter_character_list:
        text = text.replace(filter_character, " ")  # 过滤一些windows文件名屏蔽的字符
    # 去除前后空格以及点
    # 如果前后没有区别则直接返回
    while (new_text := text.strip().strip(".")) != text:
        text = new_text
    return text
