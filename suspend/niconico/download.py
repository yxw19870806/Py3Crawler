# -*- coding:UTF-8  -*-
"""
指定Nico Nico视频下载
http://www.nicovideo.jp/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import tkinter
from tkinter import filedialog
from common import *
from suspend.niconico import niconico


class NicoNicoDownload(niconico.NicoNico):
    def __init__(self, **kwargs):
        extra_sys_config = {
            crawler_enum.SysConfigKey.NOT_CHECK_SAVE_DATA: True
        }
        niconico.NicoNico.__init__(self, extra_sys_config=extra_sys_config, **kwargs)

        # GUI窗口
        self.gui = tkinter.Tk()
        self.gui.withdraw()

    @staticmethod
    def get_video_id_from_console():
        video_url = input(tool.get_time() + " 请输入Nico Nico视频地址：").lower()
        video_id = None
        # http://www.nicovideo.jp/watch/sm20429274?ref=search_key_video&ss_pos=3&ss_id=361e7a4b-278e-40c1-acbb-a0c55c84005d
        if video_url.find("//www.nicovideo.jp/watch/sm") > 0:
            video_id = video_url.split("/")[-1].split("?")[0].replace("sm", "")
        elif tool.is_integer(video_url):
            video_id = video_url
        elif video_url.startswith("sm") and tool.is_integer(video_url[len("sm"):]):
            video_id = video_url[len("sm"):]
        return video_id

    def main(self):
        try:
            while True:
                self._main()
        except KeyboardInterrupt:
            return

    def _main(self):
        # 输入需要解析的视频
        video_id = self.get_video_id_from_console()
        if not tool.is_integer(video_id):
            log.info("错误的视频地址，正确的地址格式如：http://www.nicovideo.jp/watch/sm20429274")
            return

        # 获取下载地址
        try:
            video_response = niconico.get_video_info(video_id)
        except crawler.CrawlerException as e:
            log.error(e.http_error("视频"))
            return
        if video_response["is_delete"]:
            log.info("视频不存在，跳过")
            return

        # 选择下载目录
        log.info("请选择下载目录")
        options = {
            "initialdir": self.video_download_path,
            "initialfile": "%08d - %s.mp4" % (int(video_id), path.filter_text(video_response["video_title"])),
            "filetypes": [("mp4", ".mp4")],
            "parent": self.gui,
        }
        file_path = tkinter.filedialog.asksaveasfilename(**options)
        if not file_path:
            return

        # 开始下载
        log.info("\n视频标题：%s\n视频地址：%s\n下载路径：%s" % (video_response["video_title"], video_response["video_url"], file_path))
        cookies_list = niconico.COOKIE_INFO
        if video_response["extra_cookie"]:
            cookies_list.update(video_response["extra_cookie"])
        download_return = net.Download(video_response["video_url"], file_path, auto_multipart_download=True, cookies_list=cookies_list)
        if download_return.status == net.Download.DOWNLOAD_SUCCEED:
            log.info("视频《%s》下载成功" % video_response["video_title"])
        else:
            log.error("视频《%s》下载失败，原因：%s" % (video_response["video_title"], crawler.download_failre(download_return.code)))


if __name__ == "__main__":
    NicoNicoDownload().main()
