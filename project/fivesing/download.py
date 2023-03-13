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
            const.SysConfigKey.NOT_CHECK_SAVE_DATA: True
        }
        fivesing.FiveSing.__init__(self, extra_sys_config=extra_sys_config, **kwargs)

        # GUI窗口
        self.gui = tkinter.Tk()
        self.gui.withdraw()

    @staticmethod
    def get_audio_id_from_console():
        audio_url = input(tool.get_time() + " 请输入5sing歌曲地址：").lower()
        audio_type = None
        audio_id = None
        # http://5sing.kugou.com/fc/15887314.html
        if audio_url.find("//5sing.kugou.com/") > 0:
            temp_list = audio_url.split("/")
            audio_type = temp_list[-2]
            audio_id = temp_list[-1].split(".")[0]
        return [audio_type, audio_id]

    def main(self):
        try:
            while True:
                self.download_from_console()
        except KeyboardInterrupt:
            return

    def download_from_console(self):
        # 输入需要解析的歌曲
        audio_type, audio_id = self.get_audio_id_from_console()
        if not tool.is_integer(audio_id) or audio_type not in ["yc", "fc", "bz"]:
            log.info("错误的歌曲地址，正确的地址格式如：http://5sing.kugou.com/fc/15887314.html")
            return

        # 获取下载地址
        try:
            audio_response = fivesing.get_audio_play_page(audio_id, audio_type)
        except crawler.CrawlerException as e:
            log.error(e.http_error("歌曲"))
            return
        if audio_response["is_delete"]:
            log.info("歌曲不存在，跳过")
            return

        # 选择下载目录
        log.info("请选择下载目录")
        file_extension = net.get_file_extension(audio_response["audio_url"])
        options = {
            "initialdir": self.audio_download_path,
            "initialfile": "%08d - %s.%s" % (int(audio_id), path.filter_text(audio_response["audio_title"]), file_extension),
            "filetypes": [(file_extension, "." + file_extension)],
            "parent": self.gui,
        }
        audio_path = tkinter.filedialog.asksaveasfilename(**options)
        if not audio_path:
            return

        # 开始下载
        log.info("\n歌曲标题：%s\n歌曲地址：%s\n下载路径：%s" % (audio_response["audio_title"], audio_response["audio_url"], audio_path))

        audio_description = "歌曲《%s》" % audio_response["audio_title"]
        self.download(audio_response["audio_url"], audio_path, audio_description)


if __name__ == "__main__":
    FiveSingDownload().main()
