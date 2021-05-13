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


def main():
    # 初始化
    bilibili_class = bilibili.BiliBili(extra_sys_config={crawler.SYS_NOT_CHECK_SAVE_DATA: True})
    # GUI窗口
    gui = tkinter.Tk()
    gui.withdraw()

    while True:
        video_url = input("请输入bilibili收藏夹播放地址：").lower()
        favorites_id = None
        if video_url.find("//www.bilibili.com/medialist/play/ml") > 0:
            favorites_id = tool.find_sub_string(video_url, "//www.bilibili.com/medialist/play/ml").split("?")[0].split("/")[0]
        elif crawler.is_integer(video_url):
            favorites_id = video_url
        elif video_url[:2] == "ml" and crawler.is_integer(video_url[2:]):
            favorites_id = video_url[2:]
        # 无效的视频地址
        if not crawler.is_integer(favorites_id):
            log.step("错误的收藏夹播放地址，正确的地址格式如：https://www.bilibili.com/medialist/play/ml1234567890")
            continue
        # 访问视频播放页
        try:
            favorites_response = bilibili.get_favorites_list(favorites_id)
        except crawler.CrawlerException as e:
            log.error("解析收藏列表失败，原因：%s" % e.message)
            continue

        # 选择下载目录
        options = {
            "initialdir": bilibili_class.video_download_path,
            "parent": gui,
        }
        root_dir = tkinter.filedialog.askdirectory(**options)
        if not root_dir:
            continue

        exist_list = []
        for file_path in path.get_dir_files_name(root_dir):
            if file_path.find(" ") > 0:
                video_id = file_path.split(" ")[0]
                if crawler.is_integer(video_id):
                    exist_list.append(int(video_id))

        while len(favorites_response["video_info_list"]) > 0:
            video_info = favorites_response["video_info_list"].pop()
            log.step("开始解析视频%s 《%s》，剩余%s个视频" % (video_info["video_id"], video_info["video_title"], len(favorites_response["video_info_list"])))

            if video_info["video_id"] in exist_list:
                continue

            try:
                video_play_response = bilibili.get_video_page(video_info["video_id"])
            except crawler.CrawlerException as e:
                log.error("解析视频%s《%s》下载地址失败，原因：%s" % (video_info["video_id"], video_info["video_title"], e.message))
                continue

            if video_play_response["is_private"]:
                log.step("视频%s《%s》需要登录才能访问，跳过" % (video_info["video_id"], video_info["video_title"]))
                continue

            if len(video_play_response["video_part_info_list"]) > 1:
                log.step("视频%s《%s》共获取%s个分段" % (video_info["video_id"], video_info["video_title"], len(video_play_response["video_part_info_list"])))

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
                    video_name = path.filter_text(video_name)
                    video_name = "%s.%s" % (video_name, net.get_file_type(video_part_url))
                    file_path = os.path.join(root_dir, video_name)

                    # 开始下载
                    log.step("\n视频标题：%s\n视频地址：%s\n下载路径：%s" % (video_play_response["video_title"], video_part_url, file_path))
                    save_file_return = net.save_net_file(video_part_url, file_path, header_list={"Referer": "https://www.bilibili.com/video/av%s" % video_info["video_id"]})
                    if save_file_return["status"] == 1:
                        log.step("视频%s《%s》第%s个视频下载成功" % (video_info["video_id"], video_info["video_title"], video_index))
                    else:
                        log.error("视频%s《%s》第%s个视频 %s，下载失败，原因：%s" % (video_info["video_id"], video_info["video_title"], video_index, video_part_url, crawler.download_failre(save_file_return["code"])))
                    video_split_index += 1
                    video_index += 1

                video_part_index += 1


if __name__ == "__main__":
    main()
