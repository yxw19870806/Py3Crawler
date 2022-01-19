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
from project.nicoNico import niconico


def main():
    # 初始化
    nicoNico_class = niconico.NicoNico(extra_sys_config={crawler.SYS_NOT_CHECK_SAVE_DATA: True})
    if not niconico.check_login():
        log.error("没有检测到登录信息")
        niconico.COOKIE_INFO = {}
    # GUI窗口
    gui = tkinter.Tk()
    gui.withdraw()

    while True:
        video_url = input(crawler.get_time() + " 请输入Nico Nico视频地址：").lower()
        video_id = None
        # http://www.nicovideo.jp/watch/sm20429274?ref=search_key_video&ss_pos=3&ss_id=361e7a4b-278e-40c1-acbb-a0c55c84005d
        if video_url.find("//www.nicovideo.jp/watch/sm") > 0:
            video_id = video_url.split("/")[-1].split("?")[0].replace("sm", "")
        elif crawler.is_integer(video_url):
            video_id = video_url
        elif video_url[:2] == "sm" and crawler.is_integer(video_url[2:]):
            video_id = video_url[2:]
        if video_id is not None:
            log.step("错误的视频地址，正确的地址格式如：http://www.nicovideo.jp/watch/sm20429274")
            continue
        # 访问视频播放页
        try:
            video_response = niconico.get_video_info(video_id)
        except crawler.CrawlerException as e:
            log.error("解析视频下载地址失败，原因：%s" % e.message)
            tool.process_exit()
        if video_response["is_delete"]:
            log.step("视频不存在，跳过")
            continue
        # 选择下载目录
        options = {
            "initialdir": nicoNico_class.video_download_path,
            "initialfile": "%08d - %s.mp4" % (int(video_id), path.filter_text(video_response["video_title"])),
            "filetypes": [("mp4", ".mp4")],
            "parent": gui,
        }
        file_path = tkinter.filedialog.asksaveasfilename(**options)
        if not file_path:
            continue
        # 开始下载
        log.step("\n视频标题：%s\n视频地址：%s\n下载路径：%s" % (video_response["video_title"], video_response["video_url"], file_path))
        cookies_list = niconico.COOKIE_INFO
        if video_response["extra_cookie"]:
            cookies_list.update(video_response["extra_cookie"])
        save_file_return = net.download(video_response["video_url"], file_path, head_check=True, cookies_list=cookies_list)
        if save_file_return["status"] == 1:
            log.step("视频《%s》下载成功" % video_response["video_title"])
        else:
            log.error("视频《%s》下载失败，原因：%s" % (video_response["video_title"], crawler.download_failre(save_file_return["code"])))


if __name__ == "__main__":
    main()
