# -*- coding:UTF-8  -*-
"""
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os.path
import sqlite3

from common import *

DB_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "videos.db"))


def create_video_database():
    if os.path.exists(DB_FILE_PATH):
        return

    conn = None
    try:
        conn = sqlite3.connect(DB_FILE_PATH)
        cursor = conn.cursor()

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS videos (
            video_id TEXT,                 -- 视频ID，自增主键，唯一标识每条记录
            video_title TEXT NOT NULL,     -- 视频标题，非空
            video_single_actress TEXT,     -- 单个女演员信息，允许为空
            video_all_actress TEXT,        -- 所有女演员信息，允许为空
            PRIMARY KEY (video_id, video_title) 
        );
        """

        cursor.execute(create_table_sql)
        conn.commit()
    except sqlite3.Error as e:
        print(e)
    finally:
        # 3. 关闭数据库连接
        if conn:
            conn.close()


def batch_insert_videos(video_data_list=None):
    if os.path.exists(DB_FILE_PATH):
        raise Exception(f"DB {DB_FILE_PATH} not exist")

    conn = None
    try:
        conn = sqlite3.connect(DB_FILE_PATH)
        cursor = conn.cursor()

        batch_insert_sql = """
        INSERT INTO videos (video_id, video_title, video_single_actress, video_all_actress)
        VALUES (?, ?, ?, ?);
        """

        cursor.executemany(batch_insert_sql, video_data_list)
        conn.commit()
        print(f"insert {cursor.rowcount} records")
    except sqlite3.Error as e:
        print(f"execute sql failed：{e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def split_name(p):
    if not p.endswith(".mp4"):
        return None
    file_name = url.get_file_name(os.path.basename(p))
    video_number = file_name.split(" ")[0]
    try:
        video_title = file_name.split(" ", 1)[1]
    except:
        print(f"{file_name} invalid name format")
        return None

    if "A" <= video_number[-1] <= "Z" and video_number[-2] == "-":
        return None

    return [video_number, video_title]


def get_video_from_path(base_path):
    result_video_list = []
    for first_name in path.get_dir_files_name(base_path):
        first_path = os.path.join(base_path, first_name)
        for second_name in path.get_dir_files_name(first_path):
            second_path = os.path.join(first_path, second_name)
            # 单人，second_name = 名字
            if os.path.isdir(second_path):
                for third_name in path.get_dir_files_name(second_path):
                    third_path = os.path.join(second_path, third_name)
                    d = split_name(third_path)
                    if d is None:
                        continue
                    d.append(second_name)
                    d.append("")  # all actress
                    result_video_list.append(d)
            else:
                d = split_name(second_path)
                if d is None:
                    continue
                d.append("")  # single actress
                d.append("")  # all actress
                result_video_list.append(d)
    return result_video_list


if __name__ == "__main__":
    create_video_database()
    path_list = [r"Q:\视频", r"Y:\视频"]
    for single_path in path_list:
        video_list = get_video_from_path(single_path)
        batch_insert_videos(video_list)
