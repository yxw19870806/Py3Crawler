# -*- coding:UTF-8  -*-
"""
指定Dailymotion视频下载
https://www.dailymotion.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import re
import tkinter
from tkinter import filedialog
from common import *
from project.dailymotion import dailymotion


class DailyMotionDownload(dailymotion.DailyMotion):
    def __init__(self, **kwargs):
        extra_sys_config = {
            const.SysConfigKey.NOT_CHECK_SAVE_DATA: True
        }
        dailymotion.DailyMotion.__init__(self, extra_sys_config=extra_sys_config, **kwargs)

        # GUI窗口
        self.gui = tkinter.Tk()
        self.gui.withdraw()

    @staticmethod
    def get_video_id_from_console():
        video_url = input(tool.convert_timestamp_to_formatted_time() + " 请输入dailymotion视频地址：").lower()
        video_id = None
        # https://www.dailymotion.com/video/x6njw4l
        if video_url.find("//www.dailymotion.com/video/") > 0:
            video_id = url.get_basename(video_url)
        elif re.match("[a-zA-Z0-9]+$", video_url) is not None:
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
            log.info("错误的视频地址，正确的地址格式如：https://www.dailymotion.com/video/x6njw4l")
            return

        # 获取下载地址
        try:
            video_response = dailymotion.get_video_page(video_id)
        except CrawlerException as e:
            log.error(e.http_error("视频"))
            return
        if video_response["is_delete"]:
            log.info("视频不存在，跳过")
            return

        # 选择下载目录
        log.info("请选择下载目录")
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
        log.info("\n视频标题：%s\n视频地址：%s\n下载路径：%s" % (video_response["video_title"], video_response["video_url"], video_path))
        video_description = "视频《%s》" % video_response["video_title"]
        self.download(video_response["video_url"], video_path, video_description, auto_multipart_download=True)


if __name__ == "__main__":
    DailyMotionDownload().main()
