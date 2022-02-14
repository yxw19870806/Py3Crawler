# -*- coding:UTF-8  -*-
"""
指定Youtube视频下载
https://www.youtube.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import re
import tkinter
from tkinter import filedialog
from common import *
from project.youtube import youtube


class YoutubeDownload(youtube.Youtube):
    def __init__(self, **kwargs):
        extra_sys_config = {
            crawler.SYS_NOT_CHECK_SAVE_DATA: True
        }
        youtube.Youtube.__init__(self, extra_sys_config=extra_sys_config, **kwargs)

        # GUI窗口
        self.gui = tkinter.Tk()
        self.gui.withdraw()

    @staticmethod
    def get_video_id_from_console():
        video_url = input("请输入youtube视频地址：")
        video_id = None
        # https://www.youtube.com/watch?v=lkHlnWFnA0c
        if video_url.lower().find("//www.youtube.com/") > 0:
            query_string_list = video_url.split("?")[-1].split("&")
            for query_string in query_string_list:
                if query_string.find("=") == -1:
                    continue
                key, value = query_string.split("=", 1)
                if key == "v":
                    video_id = value
                    break
        # https://youtu.be/lkHlnWFnA0c
        elif video_url.lower().find("//youtu.be/") > 0:
            video_id = video_url.split("/")[-1].split("&")[0]
        elif re.match("[a-zA-Z0-9_]+$", video_url) is not None:
            video_id = video_url
        return video_id

    def main(self):
        while True:
            self.download()

    def download(self):
        video_id = self.get_video_id_from_console()
        # 无效的视频地址
        # 无效的视频地址
        if video_id is None:
            log.step("错误的视频地址，正确的地址格式如：https://www.youtube.com/watch?v=lkHlnWFnA0c 或 https://youtu.be/lkHlnWFnA0c")
            return

        # 访问视频播放页
        try:
            video_response = youtube.get_video_page(video_id)
        except crawler.CrawlerException as e:
            log.error(e.http_error("视频"))
            return
        if video_response["skip_reason"]:
            log.error(f"视频{video_id} {video_response['skip_reason']}")
            return

        options = {
            "initialdir": self.video_download_path,
            "initialfile": f"{video_id} - {path.filter_text(video_response['video_title'])}.mp4",
            "filetypes": [("mp4", ".mp4")],
            "parent": self.gui,
        }
        file_path = tkinter.filedialog.asksaveasfilename(**options)
        if not file_path:
            return
        # 开始下载
        log.step(f"\n视频标题：{video_response['video_title']}\n视频地址：{video_response['video_url']}\n下载路径：{file_path}")
        save_file_return = net.download(video_response["video_url"], file_path, head_check=True)
        if save_file_return["status"] == 1:
            log.step(f"视频《{video_response['video_title']}》下载成功")
        else:
            log.error(f"视频《{video_response['video_title']}》下载失败，原因：{crawler.download_failre(save_file_return['code'])}")


if __name__ == "__main__":
    YoutubeDownload().main()
