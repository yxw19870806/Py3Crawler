# -*- coding:UTF-8  -*-
"""
指定Nico Nico视频下载
http://www.nicovideo.jp/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import tkinter
from tkinter import filedialog
from common import *
from project.nicoNico import nicoNico


def main():
    config = crawler._get_config()
    # 设置日志路径
    crawler.quicky_set_log_path(config)
    # 设置代理
    crawler.quickly_set_proxy(config)
    # GUI窗口
    gui = tkinter.Tk()
    gui.withdraw()

    while True:
        video_url = input(crawler.get_time() + " 请输入Nico Nico视频地址：").lower()
        # http://www.nicovideo.jp/watch/sm20429274?ref=search_key_video&ss_pos=3&ss_id=361e7a4b-278e-40c1-acbb-a0c55c84005d
        if video_url.find("//www.nicovideo.jp/watch/sm") == -1:
            log.step("错误的视频地址，正确的地址格式如：http://www.nicovideo.jp/watch/sm20429274")
            continue
        video_id = video_url.split("/")[-1].split("?")[0].replace("sm", "")
        # 访问视频播放页
        try:
            video_response = nicoNico.get_video_info(video_id)
        except crawler.CrawlerException as e:
            log.error("解析视频下载地址失败，原因：%s" % e.message)
            tool.process_exit()
        if video_response["is_delete"]:
            log.step("视频不存在，跳过")
            continue
        # 选择下载目录
        options = {
            "initialdir": os.path.join(os.path.dirname(__file__), "video"),
            "initialfile": "%08d - %s.mp4" % (int(video_id), path.filter_text(video_response["video_title"])),
            "filetypes": [("mp4", ".mp4")],
            "parent": gui,
        }
        file_path = tkinter.filedialog.asksaveasfilename(**options)
        if not file_path:
            continue
        # 开始下载
        log.step("\n视频标题：%s\n视频地址：%s\n下载路径：%s" % (video_response["video_title"], video_response["video_url"], file_path))
        save_file_return = net.save_net_file(video_response["video_url"], file_path, head_check=True)
        if save_file_return["status"] == 1:
            log.step("视频《%s》下载成功" % video_response["video_title"])
        else:
            log.error("视频《%s》下载失败，原因：%s" % (video_response["video_title"], crawler.download_failre(save_file_return["code"])))


if __name__ == "__main__":
    main()
