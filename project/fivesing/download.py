# -*- coding:UTF-8  -*-
"""
指定5sing歌曲下载
http://5sing.kugou.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import tkinter
from tkinter import filedialog
from common import *
from project.fivesing import fivesing


class FiveSingDownload(fivesing.FiveSing):
    def __init__(self, **kwargs):
        extra_sys_config = {
            crawler.SYS_NOT_CHECK_SAVE_DATA: True
        }
        fivesing.FiveSing.__init__(self, extra_sys_config=extra_sys_config, **kwargs)

        # GUI窗口
        self.gui = tkinter.Tk()
        self.gui.withdraw()

    @staticmethod
    def get_audio_id_from_console():
        audio_url = input("请输入5sing歌曲地址：").lower()
        audio_type = None
        audio_id = None
        # http://5sing.kugou.com/fc/15887314.html
        if audio_url.find("//5sing.kugou.com/") > 0:
            temp_list = audio_url.split("/")
            audio_type = temp_list[-2]
            audio_id = temp_list[-1].split(".")[0]
        return [audio_type, audio_id]

    def main(self):
        while True:
            self.download()

    def download(self):
        # 输入需要解析的歌曲
        audio_type, audio_id = self.get_audio_id_from_console()
        if not tool.is_integer(audio_id) or audio_type not in ["yc", "fc", "bz"]:
            log.step("错误的歌曲地址，正确的地址格式如：http://5sing.kugou.com/fc/15887314.html")
            return

        # 获取下载地址
        try:
            audio_response = fivesing.get_audio_play_page(audio_id, audio_type)
        except crawler.CrawlerException as e:
            log.error(e.http_error("歌曲"))
            return
        if audio_response["is_delete"]:
            log.step("歌曲不存在，跳过")
            return

        # 选择下载目录
        log.step("请选择下载目录")
        file_extension = net.get_file_extension(audio_response["audio_url"])
        options = {
            "initialdir": self.audio_download_path,
            "initialfile": f"%08d - {path.filter_text(audio_response['audio_title'])}.{file_extension}" % int(audio_id),
            "filetypes": [(file_extension, "." + file_extension)],
            "parent": self.gui,
        }
        file_path = tkinter.filedialog.asksaveasfilename(**options)
        if not file_path:
            return

        # 开始下载
        log.step(f"\n歌曲标题：{audio_response['audio_title']}\n歌曲地址：{audio_response['audio_url']}\n下载路径：{file_path}")
        download_return = net.Download(audio_response["audio_url"], file_path)
        if download_return.status == net.Download.DOWNLOAD_SUCCEED:
            log.step(f"歌曲《{audio_response['audio_title']}》下载成功")
        else:
            log.error(f"歌曲《{audio_response['audio_title']}》下载失败，原因：{crawler.download_failre(download_return.code)}")


if __name__ == "__main__":
    FiveSingDownload().main()
