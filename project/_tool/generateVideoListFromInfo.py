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
    if not os.path.exists(DB_FILE_PATH):
        return

    conn = None
    try:
        conn = sqlite3.connect(DB_FILE_PATH)
        cursor = conn.cursor()

        create_actress_map_table_sql = """
        CREATE TABLE IF NOT EXISTS actress (
            actress_name TEXT,
            actress_old_name TEXT NOT NULL,
            PRIMARY KEY (actress_name, actress_old_name) 
        );
        """

        cursor.execute(create_actress_map_table_sql)
        conn.commit()
    except sqlite3.Error as e:
        print(e)
    finally:
        # 3. 关闭数据库连接
        if conn:
            conn.close()


def batch_insert_videos(video_data_list=None):
    if not os.path.exists(DB_FILE_PATH):
        raise Exception(f"DB {DB_FILE_PATH} not exist")

    conn = None
    try:
        conn = sqlite3.connect(DB_FILE_PATH)
        cursor = conn.cursor()

        batch_insert_sql = """
        INSERT INTO videos (video_id, video_title, video_single_actress, video_all_actress)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(video_id, video_title) DO UPDATE SET 
        `video_single_actress` = excluded.`video_single_actress`,
        `video_all_actress` = excluded.`video_all_actress`;
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


def batch_insert_actress(actress_dict=None):
    if not os.path.exists(DB_FILE_PATH):
        raise Exception(f"DB {DB_FILE_PATH} not exist")

    conn = None
    try:
        conn = sqlite3.connect(DB_FILE_PATH)
        cursor = conn.cursor()

        batch_insert_sql = """
        INSERT INTO actress (actress_name, actress_old_name)
        VALUES (?, ?);
        """

        actress_list = []
        for actress_name in actress_dict:
            for actress_old_name in actress_dict[actress_name]:
                print(actress_name, actress_old_name)
                actress_list.append([actress_name, actress_old_name])

        cursor.executemany(batch_insert_sql, actress_list)
        conn.commit()
        print(f"insert {cursor.rowcount} records")
    except sqlite3.Error as e:
        print(f"execute sql failed：{e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def main(file_path):
    actress_dict = {}
    result_video_list = []
    for line in file.read_file(file_path, const.ReadFileMode.LINE):
        video_info = line.split("\t")
        video_id: str = video_info[0]
        video_title: str = video_info[1]
        video_actress_old: list = video_info[4].split(", ") if video_info[4] else []
        video_actress = []
        if len(video_actress_old) > 0:
            for actress_name in video_actress_old:
                if actress_name.find("/") > 0:
                    actress_name_list = actress_name.split("/")
                    video_actress.append(actress_name_list[0])

                    if actress_name_list[0] not in actress_dict:
                        actress_dict[actress_name_list[0]] = actress_name_list[1:]
                else:
                    video_actress.append(actress_name)
        is_vr: bool = video_title.startswith("【VR】")
        vr_state = "1" if is_vr else "0"
        # video_id, video_title, video_single_actress, video_all_actress, is_vr
        result_video_list.append([video_id, video_title, video_actress[0] if len(video_actress) == 1 else '', tool.json_encode(video_actress), vr_state])

        if len(result_video_list) > 5000:
            batch_insert_videos(result_video_list)
            result_video_list = []

    if result_video_list:
        batch_insert_videos(result_video_list)
    batch_insert_actress(actress_dict)


if __name__ == "__main__":
    create_video_database()

    result_file_path = r"D:\PyCrawler\gallery\javbus\content\video.txt"
    main(result_file_path)
