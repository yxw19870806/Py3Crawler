# -*- coding:UTF-8  -*-
"""
指定xhamster视频下载
https://xhamster.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import tkinter
from tkinter import filedialog
from common import *
from project.xhamster import xhamster


def main():
    # 初始化
    xhamster_obj = xhamster.Xhamster(extra_sys_config={crawler.SYS_NOT_CHECK_SAVE_DATA: True})
    # GUI窗口
    gui = tkinter.Tk()
    gui.withdraw()

    while True:
        video_url = input("请输入xhamster视频地址：").lower()
        video_id = None
        if video_url.find("//xhamster.com/videos/") > 0:
            video_id = video_url.split("/")[-1].split("-")[-1]
        elif crawler.is_integer(video_url):
            video_id = video_url
        # 无效的视频地址
        if not crawler.is_integer(video_id):
            log.step("错误的视频地址，正确的地址格式如：https://xhamster.com/videos/xxx-xxx-xxx-123456")
            continue
        # 访问视频播放页
        try:
            video_response = xhamster.get_video_page(video_id)
        except crawler.CrawlerException as e:
            log.error("解析视频下载地址失败，原因：%s" % e.message)
            continue
        if video_response["is_delete"]:
            log.step("视频不存在，跳过")
            continue
        if video_response["is_password"]:
            log.step("视频已加密，跳过")
            continue
        # 选择下载目录
        options = {
            "initialdir": xhamster_obj.video_download_path,
            "initialfile": "%08d - %s.mp4" % (int(video_id), path.filter_text(video_response["video_title"])),
            "filetypes": [("mp4", ".mp4")],
            "parent": gui,
        }
        file_path = tkinter.filedialog.asksaveasfilename(**options)
        if not file_path:
            continue
        # 开始下载
        log.step("\n视频标题：%s\n视频地址：%s\n下载路径：%s" % (video_response["video_title"], video_response["video_url"], file_path))
        save_file_return = net.save_net_file(video_response["video_url"], file_path, head_check=True)
        if save_file_return["status"] == 1:
            # 设置临时目录
            log.step("视频《%s》下载成功" % video_response["video_title"])
        else:
            log.step("视频《%s》下载失败，原因：%s" % (video_response["video_title"], crawler.download_failre(save_file_return["code"])))


if __name__ == "__main__":
    main()
