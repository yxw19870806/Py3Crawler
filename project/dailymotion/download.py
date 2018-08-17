# -*- coding:UTF-8  -*-
"""
指定Dailymotion视频下载
https://www.youtube.com
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from common import *
from project.dailymotion import dailymotion

DOWNLOAD_FILE_PATH = os.path.join(os.path.dirname(__file__), "video")


def main():
    config = crawler._get_config()
    # 设置日志路径
    crawler.quicky_set_log_path(config)
    # 设置代理
    crawler.quickly_set_proxy(config)

    while True:
        video_url = input(crawler.get_time() + " 请输入dailymotion视频地址：").lower()
        # https://www.dailymotion.com/video/x6njw4l
        if video_url.find("//www.dailymotion.com/video/") == -1:
            log.step("错误的视频地址，正确的地址格式如：https://www.dailymotion.com/video/x6njw4l")
            continue
        video_id = video_url.split("/")[-1].split("?")[0]
        # 访问视频播放页
        try:
            video_response = dailymotion.get_video_page(video_id)
        except crawler.CrawlerException as e:
            log.error("解析视频下载地址失败，原因：%s" % e.message)
            tool.process_exit()
        # 开始下载
        video_file_path = os.path.abspath(os.path.join(DOWNLOAD_FILE_PATH, "%s - %s.mp4" % (video_id, path.filter_text(video_response["video_title"]))))
        log.step("\n视频标题：%s\n视频地址：%s\n下载路径：%s" % (video_response["video_title"], video_response["video_url"], video_file_path))
        save_file_return = net.save_net_file(video_response["video_url"], video_file_path, head_check=True)
        if save_file_return["status"] == 1:
            log.step("视频《%s》下载成功" % video_response["video_title"])
        else:
            log.error("视频《%s》下载失败，原因：%s" % (video_response["video_title"], crawler.download_failre(save_file_return["code"])))


if __name__ == "__main__":
    main()
