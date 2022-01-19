# -*- coding:UTF-8  -*-
"""
酷我歌单音频爬虫
http://www.kuwo.cn/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import tkinter
from tkinter import filedialog
from common import *
from project.kuwo import kuwo


def main():
    # 初始化
    kuwo_class = kuwo.KuWo()
    # GUI窗口
    gui = tkinter.Tk()
    gui.withdraw()

    while True:
        playlist_url = input("请输入歌单地址：").lower()
        playlist_id = None
        if playlist_url.find("//www.kuwo.cn/playlist_detail/") > 0:
            playlist_id = playlist_url.split(playlist_url)[-1]
        elif crawler.is_integer(playlist_url):
            playlist_id = playlist_url
        # 无效的歌单地址
        if not crawler.is_integer(playlist_id):
            log.step("错误的歌单地址，正确的地址格式如：https://www.kuwo.cn/playlist_detail/123456789")
            continue

        is_over = False
        page_count = 1
        audio_info_list = []
        while not is_over:
            try:
                playlist_pagination_response = kuwo.get_one_page_playlist(playlist_id, page_count)
            except crawler.CrawlerException as e:
                log.error("解析视频下载地址失败，原因：%s" % e.message)
                return

            audio_info_list += playlist_pagination_response["audio_info_list"]
            is_over = playlist_pagination_response["is_over"]
            page_count += 1

        # 选择下载目录
        options = {
            "initialdir": kuwo_class.audio_download_path,
            "initialfile": "%s - %s.mp4" % (video_id, path.filter_text(video_response["video_title"])),
            "filetypes": [("mp4", ".mp4")],
            "parent": gui,
        }
        file_path = tkinter.filedialog.asksaveasfilename(**options)


if __name__ == "__main__":
    main()
