# -*- coding:UTF-8  -*-
import os
import tkinter
from tkinter import filedialog

from common import *


class DownloadHls:
    def __init__(self):
        # GUI窗口
        self.gui = tkinter.Tk()
        self.gui.withdraw()

    def main(self):
        video_url = self.get_video_url_from_console()
        video_path = self.get_video_title_from_console(video_url)
        if not video_path:
            return
        download_return = net.DownloadHls(video_url, video_path)
        log.info(f"\n视频地址：{video_url}\n下载路径：{video_path}")
        if download_return.status == const.DownloadStatus.SUCCEED:
            log.info("下载成功")
        else:
            log.error(f"下载失败，{crawler.download_failre(download_return.code)}")

    @staticmethod
    def get_video_url_from_console() -> str:
        while True:
            video_url = input(tool.convert_timestamp_to_formatted_time() + " 请输入视频m3u8地址：")
            if video_url.endswith(".m3u8") and (video_url.startswith("http") or video_url.startswith("https")):
                return video_url

    def get_video_title_from_console(self, video_url) -> str:
        log.info("请选择下载目录")
        default_name = url.get_file_name(video_url)
        options = {
            "initialdir": os.path.dirname(__file__),
            "initialfile": f"{default_name}.ts",
            "filetypes": [("ts", ".ts")],
            "parent": self.gui,
        }
        return tkinter.filedialog.asksaveasfilename(**options)


if __name__ == "__main__":
    DownloadHls().main()
