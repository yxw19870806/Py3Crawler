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
            const.SysConfigKey.NOT_CHECK_SAVE_DATA: True
        }
        ximalaya.XiMaLaYa.__init__(self, extra_sys_config=extra_sys_config, **kwargs)

        # GUI窗口
        self.gui = tkinter.Tk()
        self.gui.withdraw()

    @staticmethod
    def get_audio_id_from_console():
        audio_url = input(tool.convert_timestamp_to_formatted_time() + " 请输入喜马拉雅歌曲地址：").lower()
        audio_id = None
        if audio_url.find("//www.ximalaya.com/") > 0:
            temp_list = url.split_path(audio_url)
            if len(temp_list) >= 3 and tool.is_integer(temp_list[-1]) and tool.is_integer(temp_list[-2]):
                audio_id = temp_list[-1]
        return audio_id

    def main(self):
        try:
            while True:
                self.download_from_console()
        except KeyboardInterrupt:
            return

    def download_from_console(self):
        # 输入需要解析的音频
        audio_id = self.get_audio_id_from_console()
        if audio_id is None:
            log.info("错误的音频地址，正确的地址格式如：https://www.ximalaya.com/xiangsheng/9723091/46106824")
            return

        # 获取下载地址
        try:
            audio_response = ximalaya.get_audio_info_page(audio_id)
        except CrawlerException as e:
            log.error(e.http_error("歌曲"))
            return
        if audio_response["is_delete"]:
            log.info("歌曲不存在，跳过")
            return

        # 选择下载目录
        log.info("请选择下载目录")
        file_extension = url.get_file_ext(audio_response["audio_url"])
        options = {
            "initialdir": self.audio_download_path,
            "initialfile": f"{audio_id} - {audio_response['audio_title']}.{file_extension}",
            "filetypes": [(file_extension, "." + file_extension)],
            "parent": self.gui,
        }
        audio_path = tkinter.filedialog.asksaveasfilename(**options)
        if not audio_path:
            return

        # 开始下载
        log.info(f"\n歌曲标题：{audio_response['audio_title']}\n歌曲地址：{audio_response['audio_url']}\n下载路径：{audio_path}")
        audio_description = f"歌曲《{audio_response['audio_title']}》"
        self.download(audio_response["audio_url"], audio_path, audio_description)


if __name__ == "__main__":
    XiMaLaYaDownload().main()
