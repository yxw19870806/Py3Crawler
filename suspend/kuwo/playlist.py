# -*- coding:UTF-8  -*-
"""
酷我歌单音频爬虫
http://www.kuwo.cn/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import tkinter
from tkinter import filedialog
from common import *
from suspend.kuwo import kuwo


class KuWoPlaylist(kuwo.KuWo):
    def __init__(self, **kwargs):
        sys_config = {
            crawler_enum.SysConfigKey.NOT_CHECK_SAVE_DATA: True
        }
        kuwo.KuWo.__init__(self, extra_sys_config=sys_config, **kwargs)

        # GUI窗口
        self.gui = tkinter.Tk()
        self.gui.withdraw()

    @staticmethod
    def get_playlist_id_from_console():
        playlist_url = input(tool.get_time() + " 请输入歌单地址：").lower()
        playlist_id = None
        if playlist_url.find("//www.kuwo.cn/playlist_detail/") > 0:
            playlist_id = playlist_url.split(playlist_url)[-1]
        elif tool.is_integer(playlist_url):
            playlist_id = playlist_url
        return playlist_id

    def main(self):
        try:
            while True:
                self._main()
        except KeyboardInterrupt:
            return

    def _main(self):
        # 输入需要解析的视频
        playlist_id = self.get_playlist_id_from_console()
        # 无效的歌单地址
        if not tool.is_integer(playlist_id):
            log.step("错误的歌单地址，正确的地址格式如：https://www.kuwo.cn/playlist_detail/123456789")
            return

        # 选择下载目录
        log.step("请选择下载目录")
        options = {
            "initialdir": self.video_download_path,
            "parent": self.gui,
        }
        dir_path = tkinter.filedialog.askdirectory(**options)
        if not dir_path:
            return

        # 获取待解析列表
        is_over = False
        page_count = 1
        audio_info_list = []
        while not is_over:
            playlist_pagination_description = "第%s页歌曲" % page_count
            self.start_parse(playlist_pagination_description)
            try:
                playlist_pagination_response = kuwo.get_one_page_playlist(playlist_id, page_count)
            except crawler.CrawlerException as e:
                log.error(e.http_error(playlist_pagination_description))
                return
            self.parse_result(playlist_pagination_description, playlist_pagination_response["audio_info_list"])

            audio_info_list += playlist_pagination_response["audio_info_list"]
            
            if playlist_pagination_response["is_over"]:
                is_over = True
            else:
                page_count += 1
        log.step("用户总共解析获得%s首歌曲" % len(audio_info_list))

        # 循环待下载列表
        while len(audio_info_list) > 0:
            audio_info = audio_info_list.pop()
            log.step("开始解析歌曲%s《%s》，剩余%s首歌曲" % (audio_info["audio_id"], audio_info["audio_title"], len(audio_info_list)))

            # 获取下载地址
            try:
                audio_info_response = kuwo.get_audio_info_page(audio_info["audio_id"])
            except crawler.CrawlerException as e:
                log.error(e.http_error("歌曲%s《%s》" % (audio_info["audio_id"], audio_info["audio_title"])))
                continue

            file_path = os.path.join(dir_path, "%s - %s.%s" % (audio_info["audio_id"], path.filter_text(audio_info["audio_title"]), net.get_file_extension(audio_info_response["audio_url"])))
            if os.path.exists(file_path):
                continue

            # 开始下载
            log.step("\n歌曲名：%s\n歌曲地址：%s\n下载路径：%s" % (audio_info["audio_title"], audio_info_response["audio_url"], file_path))
            download_return = net.Download(audio_info_response["audio_url"], file_path, auto_multipart_download=True)
            if download_return.status == net.Download.DOWNLOAD_SUCCEED:
                # 设置临时目录
                log.step("歌曲《%s》下载成功" % audio_info["audio_title"])
            else:
                log.step("歌曲《%s》下载失败，原因：%s" % (audio_info["audio_title"], crawler.download_failre(download_return.code)))

        log.step("歌单歌曲全部下载完毕")


if __name__ == "__main__":
    KuWoPlaylist().main()
