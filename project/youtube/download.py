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
            const.SysConfigKey.NOT_CHECK_SAVE_DATA: True
        }
        youtube.Youtube.__init__(self, extra_sys_config=extra_sys_config, **kwargs)

        # GUI窗口
        self.gui = tkinter.Tk()
        self.gui.withdraw()

    @staticmethod
    def get_video_id_from_console():
        video_url = input(tool.convert_timestamp_to_formatted_time() + " 请输入youtube视频地址：").lower()
        video_id = None
        # https://www.youtube.com/watch?v=lkHlnWFnA0c
        if video_url.find("//www.youtube.com/") > 0:
            video_id = url.parse_query(video_url).get("v", None)
        # https://youtu.be/lkHlnWFnA0c
        elif video_url.find("//youtu.be/") > 0:
            video_id = url.get_basename(video_url)
        elif re.match("[a-zA-Z0-9_]+$", video_url) is not None:
            video_id = video_url
        return video_id

    def main(self):
        try:
            while True:
                self.download_from_console()
        except KeyboardInterrupt:
            return

    def download_from_console(self):
        # 输入需要解析的视频
        video_id = self.get_video_id_from_console()
        if video_id is None:
            log.info("错误的视频地址，正确的地址格式如：https://www.youtube.com/watch?v=lkHlnWFnA0c 或 https://youtu.be/lkHlnWFnA0c")
            return

        # 获取下载地址
        try:
            video_response = youtube.get_video_page(video_id)
        except CrawlerException as e:
            log.error(e.http_error("视频"))
            return
        if video_response["skip_reason"]:
            log.error(f"视频{video_id} {video_response['skip_reason']}")
            return

        # 选择下载目录
        log.info("请选择下载目录")
        options = {
            "initialdir": self.video_download_path,
            "initialfile": f"{video_id} - {video_response['video_title']}.mp4",
            "filetypes": [("mp4", ".mp4")],
            "parent": self.gui,
        }
        video_path = tkinter.filedialog.asksaveasfilename(**options)
        if not video_path:
            return

        # 开始下载
        log.info(f"\n视频标题：{video_response['video_title']}\n视频地址：{video_response['video_url']}\n下载路径：{video_path}")
        video_description = f"视频《{video_response['video_title']}》"
        self.download(video_response["video_url"], video_path, video_description, auto_multipart_download=True)


if __name__ == "__main__":
    YoutubeDownload().main()
