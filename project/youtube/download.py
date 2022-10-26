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
        video_url = input(tool.get_time() + " 请输入youtube视频地址：")
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
        try:
            while True:
                self.download()
        except KeyboardInterrupt:
            return

    def download(self):
        # 输入需要解析的视频
        video_id = self.get_video_id_from_console()
        if video_id is None:
            log.step("错误的视频地址，正确的地址格式如：https://www.youtube.com/watch?v=lkHlnWFnA0c 或 https://youtu.be/lkHlnWFnA0c")
            return

        # 获取下载地址
        try:
            video_response = youtube.get_video_page(video_id)
        except crawler.CrawlerException as e:
            log.error(e.http_error("视频"))
            return
        if video_response["skip_reason"]:
            log.error("视频%s %s" % (video_id, video_response["skip_reason"]))
            return

        # 选择下载目录
        log.step("请选择下载目录")
        options = {
            "initialdir": self.video_download_path,
            "initialfile": "%s - %s.mp4" % (video_id, path.filter_text(video_response["video_title"])),
            "filetypes": [("mp4", ".mp4")],
            "parent": self.gui,
        }
        video_path = tkinter.filedialog.asksaveasfilename(**options)
        if not video_path:
            return

        # 开始下载
        log.step("\n视频标题：%s\n视频地址：%s\n下载路径：%s" % (video_response["video_title"], video_response["video_url"], video_path))
        download_return = net.Download(video_response["video_url"], video_path, auto_multipart_download=True)
        if download_return.status == net.Download.DOWNLOAD_SUCCEED:
            log.step("视频《%s》下载成功" % video_response["video_title"])
        else:
            log.error("视频《%s》下载失败，原因：%s" % (video_response["video_title"], crawler.download_failre(download_return.code)))


if __name__ == "__main__":
    YoutubeDownload().main()
