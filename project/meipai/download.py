# -*- coding:UTF-8  -*-
"""
指定美拍视频下载
https://www.meipai.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import tkinter
from tkinter import filedialog
from common import *
from project.meipai import meipai


class MeiPaiDownload(meipai.MeiPai):
    def __init__(self, **kwargs):
        extra_sys_config = {
            const.SysConfigKey.NOT_CHECK_SAVE_DATA: True
        }
        meipai.MeiPai.__init__(self, extra_sys_config=extra_sys_config, **kwargs)

        # GUI窗口
        self.gui = tkinter.Tk()
        self.gui.withdraw()

    @staticmethod
    def get_video_id_from_console():
        video_url = input(tool.convert_timestamp_to_formatted_time() + " 请输入美拍视频地址：").lower()
        video_id = None
        # https://www.meipai.com/media/209045867
        if video_url.find("//www.meipai.com/media/") > 0:
            video_id = url.get_basename(video_url)
        elif tool.is_integer(video_url):
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
        if not tool.is_integer(video_id):
            log.info("错误的视频地址，正确的地址格式如：https://www.meipai.com/media/209045867")
            return

        video_description = f"视频{video_id}"
        # 获取下载地址
        try:
            video_response = meipai.get_video_play_page(video_id)
        except CrawlerException as e:
            log.error(e.http_error(video_description))
            return
        if video_response["is_delete"]:
            log.info(f"{video_description} 不存在，跳过")
            return

        # 选择下载目录
        options = {
            "initialdir": self.video_download_path,
            "initialfile": "%010d.mp4" % int(video_id),
            "filetypes": [("mp4", ".mp4")],
            "parent": self.gui,
        }
        video_path = tkinter.filedialog.asksaveasfilename(**options)
        if not video_path:
            return

        # 开始下载
        log.info(f"\n视频地址：{video_response['video_url']}\n下载路径：{video_path}")
        self.download(video_response["video_url"], video_path, video_description, auto_multipart_download=True)


if __name__ == "__main__":
    MeiPaiDownload().main()
