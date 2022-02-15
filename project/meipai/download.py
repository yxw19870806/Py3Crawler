# -*- coding:UTF-8  -*-
"""
指定美拍视频下载
http://www.meipai.com/
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
            crawler.SYS_NOT_CHECK_SAVE_DATA: True
        }
        meipai.MeiPai.__init__(self, extra_sys_config=extra_sys_config, **kwargs)

        # GUI窗口
        self.gui = tkinter.Tk()
        self.gui.withdraw()

    @staticmethod
    def get_video_id_from_console():
        video_url = input("请输入美拍视频地址：").lower()
        video_id = None
        # http://www.meipai.com/media/209045867
        if video_url.find("//www.meipai.com/media/") > 0:
            video_id = video_url.split("/")[-1].split("?")[0]
        elif tool.is_integer(video_url):
            video_id = video_url
        return video_id

    def main(self):
        while True:
            self.download()

    def download(self):
        # 输入需要解析的视频
        video_id = self.get_video_id_from_console()
        if not tool.is_integer(video_id):
            log.step("错误的视频地址，正确的地址格式如：http://www.meipai.com/media/209045867")
            return

        # 获取下载地址
        try:
            video_response = meipai.get_video_play_page(video_id)
        except crawler.CrawlerException as e:
            log.error(e.http_error("视频"))
            return
        if video_response["is_delete"]:
            log.step("视频不存在，跳过")
            return

        # 选择下载目录
        options = {
            "initialdir": self.video_download_path,
            "initialfile": "%010d.mp4" % int(video_id),
            "filetypes": [("mp4", ".mp4")],
            "parent": self.gui,
        }
        file_path = tkinter.filedialog.asksaveasfilename(**options)
        if not file_path:
            return

        # 开始下载
        log.step(f"\n视频地址：{video_response['video_url']}\n下载路径：{file_path}")
        save_file_return = net.download(video_response["video_url"], file_path, head_check=True)
        if save_file_return["status"] == 1:
            log.step("视频下载成功")
        else:
            log.error(f"视频下载失败，原因：{crawler.download_failre(save_file_return['code'])}")


if __name__ == "__main__":
    MeiPaiDownload().main()
