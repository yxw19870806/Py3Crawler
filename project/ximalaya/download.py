# -*- coding:UTF-8  -*-
"""
指定喜马拉雅歌曲下载
https://www.ximalaya.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from common import *
from project.ximalaya import ximalaya

DOWNLOAD_FILE_PATH = os.path.join(os.path.dirname(__file__), "video")


def main():
    config = crawler._get_config()
    # 设置日志路径
    crawler.quicky_set_log_path(config)
    # 设置代理
    crawler.quickly_set_proxy(config)

    while True:
        audio_url = input(crawler.get_time() + " 请输入喜马拉雅歌曲地址：").lower()
        audio_id = None
        if audio_url.find("//www.ximalaya.com/") > 0:
            temp_list = audio_url.split("/")
            if len(temp_list) >= 4 and crawler.is_integer(temp_list[-1]) and crawler.is_integer(temp_list[-2]):
                audio_id = temp_list[-1]
        if audio_id is None:
            log.step("错误的歌曲地址，正确的地址格式如：https://www.ximalaya.com/xiangsheng/9723091/46106824")
            continue
        # 访问歌曲播放页
        try:
            audio_response = ximalaya.get_audio_info_page(audio_id)
        except crawler.CrawlerException as e:
            log.error("解析歌曲下载地址失败，原因：%s" % e.message)
            tool.process_exit()
        # 开始下载
        file_type = audio_response["audio_url"].split(".")[-1]
        file_path = os.path.abspath(os.path.join(DOWNLOAD_FILE_PATH, "%s - %s.%s" % (audio_id, path.filter_text(audio_response["audio_title"]), file_type)))
        log.step("\n歌曲标题：%s\n歌曲地址：%s\n下载路径：%s" % (audio_response["audio_title"], audio_response["audio_url"], file_path))
        save_file_return = net.save_net_file(audio_response["audio_url"], file_path, head_check=True)
        if save_file_return["status"] == 1:
            log.step("歌曲《%s》下载成功" % audio_response["audio_title"])
        else:
            log.error("歌曲《%s》下载失败，原因：%s" % (audio_response["audio_title"], crawler.download_failre(save_file_return["code"])))


if __name__ == "__main__":
    main()
