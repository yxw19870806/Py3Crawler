# -*- coding:UTF-8  -*-
"""
指定喜马拉雅歌曲下载
https://www.ximalaya.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import tkinter
from tkinter import filedialog
from common import *
from project.ximalaya import ximalaya


class XiMaLaYaDownload(ximalaya.XiMaLaYa):
    def __init__(self, **kwargs):
        extra_sys_config = {
            crawler.SYS_NOT_CHECK_SAVE_DATA: True
        }
        ximalaya.XiMaLaYa.__init__(self, extra_sys_config=extra_sys_config, **kwargs)

        # GUI窗口
        self.gui = tkinter.Tk()
        self.gui.withdraw()

    @staticmethod
    def get_audio_id_from_console():
        audio_url = input("请输入喜马拉雅歌曲地址：").lower()
        audio_id = None
        if audio_url.find("//www.ximalaya.com/") > 0:
            temp_list = audio_url.split("/")
            if len(temp_list) >= 4 and tool.is_integer(temp_list[-1]) and tool.is_integer(temp_list[-2]):
                audio_id = temp_list[-1]
        return audio_id

    def main(self):
        try:
            while True:
                self.download()
        except KeyboardInterrupt:
            return

    def download(self):
        # 输入需要解析的音频
        audio_id = self.get_audio_id_from_console()
        if audio_id is None:
            log.step("错误的音频地址，正确的地址格式如：https://www.ximalaya.com/xiangsheng/9723091/46106824")
            return

        # 获取下载地址
        try:
            audio_response = ximalaya.get_audio_info_page(audio_id)
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
            "initialfile": "%s - %s.%s" % (audio_id, path.filter_text(audio_response["audio_title"]), file_extension),
            "filetypes": [(file_extension, "." + file_extension)],
            "parent": self.gui,
        }
        file_path = tkinter.filedialog.asksaveasfilename(**options)
        if not file_path:
            return

        # 开始下载
        log.step("\n歌曲标题：%s\n歌曲地址：%s\n下载路径：%s" % (audio_response["audio_title"], audio_response["audio_url"], file_path))
        download_return = net.Download(audio_response["audio_url"], file_path)
        if download_return.status == net.Download.DOWNLOAD_SUCCEED:
            log.step("歌曲《%s》下载成功" % audio_response["audio_title"])
        else:
            log.error("歌曲《%s》下载失败，原因：%s" % (audio_response["audio_title"], crawler.download_failre(download_return.code)))


if __name__ == "__main__":
    XiMaLaYaDownload().main()
