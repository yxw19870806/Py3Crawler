# -*- coding:UTF-8  -*-
"""
指定bilibili收藏夹视频下载
https://www.bilibili.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import tkinter
from tkinter import filedialog
from common import *
from project.bilibili import bilibili


class BiliBiliFavorites(bilibili.BiliBili):
    def __init__(self, **kwargs):
        extra_sys_config = {
            const.SysConfigKey.NOT_CHECK_SAVE_DATA: True
        }
        bilibili.BiliBili.__init__(self, extra_sys_config=extra_sys_config, **kwargs)

        # GUI窗口
        self.gui = tkinter.Tk()
        self.gui.withdraw()

    @staticmethod
    def get_favorites_id_from_console():
        video_url = input(tool.convert_timestamp_to_formatted_time() + " 请输入bilibili收藏夹播放地址：").lower()
        favorites_id = None
        if video_url.find("//www.bilibili.com/medialist/play/ml") > 0:
            favorites_id = tool.find_sub_string(video_url, "//www.bilibili.com/medialist/play/ml").split("?")[0].split("/")[0]
        elif tool.is_integer(video_url):
            favorites_id = video_url
        elif video_url.startswith("ml") and tool.is_integer(video_url[len("ml"):]):
            favorites_id = video_url[len("ml"):]
        return favorites_id

    def main(self):
        try:
            while True:
                self.download_from_console()
        except KeyboardInterrupt:
            return

    def download_from_console(self):
        # 输入需要解析的视频
        favorites_id = self.get_favorites_id_from_console()
        if not tool.is_integer(favorites_id):
            log.info("错误的收藏夹播放地址，正确的地址格式如：https://www.bilibili.com/medialist/play/ml1234567890")
            return

        # 访问视频播放页
        try:
            favorites_response = bilibili.get_favorites_list(favorites_id)
        except crawler.CrawlerException as e:
            log.error(e.http_error("收藏列表"))
            return

        # 选择下载目录
        log.info("请选择下载目录")
        options = {
            "initialdir": self.video_download_path,
            "parent": self.gui,
        }
        root_dir = tkinter.filedialog.askdirectory(**options)
        if not root_dir:
            return

        # 已下载列表
        exist_list = []
        for video_path in path.get_dir_files_name(root_dir):
            if video_path.find(" ") > 0:
                video_id = video_path.split(" ")[0]
                if tool.is_integer(video_id):
                    exist_list.append(int(video_id))

        while len(favorites_response["video_info_list"]) > 0:
            video_info = favorites_response["video_info_list"].pop()

            video_description = "视频%s 《%s》" % (video_info["video_id"], video_info["video_title"])
            self.start_parse(video_description + ", 剩余%s个视频" % len(favorites_response["video_info_list"]))
            if video_info["video_id"] in exist_list:
                continue
            try:
                video_play_response = bilibili.get_video_page(video_info["video_id"])
            except crawler.CrawlerException as e:
                log.error(e.http_error(video_description))
                continue
            if video_play_response["is_private"]:
                log.info("%s 需要登录才能访问，跳过" % video_description)
                continue
            self.parse_result(video_description, video_play_response["video_part_info_list"])

            video_index = 1
            video_part_index = 1
            for video_part_info in video_play_response["video_part_info_list"]:
                video_split_index = 1
                for video_part_url in video_part_info["video_url_list"]:
                    video_name = "%010d %s" % (video_info["video_id"], video_info["video_title"])
                    if len(video_play_response["video_part_info_list"]) > 1:
                        if video_part_info["video_part_title"]:
                            video_name += "_" + video_part_info["video_part_title"]
                        else:
                            video_name += "_" + str(video_part_index)
                    if len(video_part_info["video_url_list"]) > 1:
                        video_name += " (%s)" % video_split_index
                    video_name = "%s.%s" % (path.filter_text(video_name), net.get_file_extension(video_part_url))
                    video_path = os.path.join(root_dir, video_name)

                    # 开始下载
                    log.info("\n视频标题：%s\n视频地址：%s\n下载路径：%s" % (video_play_response["video_title"], video_part_url, video_path))
                    headers = {"Referer": "https://www.bilibili.com/video/av%s" % video_info["video_id"]}
                    self.download(video_part_url, video_path, video_description, auto_multipart_download=True, headers=headers)
                    video_split_index += 1
                    video_index += 1

                video_part_index += 1


if __name__ == "__main__":
    BiliBiliFavorites().main()
