# -*- coding:UTF-8  -*-
"""
喜马拉雅主播音频爬虫
https://www.ximalaya.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from common import *
from project.ximalaya import ximalaya


class XiMaLaYaAccount(ximalaya.XiMaLaYa):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SysConfigKey.NOT_CHECK_SAVE_DATA: False,
            crawler.SysConfigKey.APP_CONFIG_PATH: os.path.join(crawler.PROJECT_APP_PATH, "account.ini"),
        }
        ximalaya.XiMaLaYa.__init__(self, sys_config, **kwargs)

        # 解析存档文件
        # account_id  last_audio_id
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

        # 下载线程
        self.crawler_thread = CrawlerThread


class CrawlerThread(crawler.CrawlerThread):
    def __init__(self, main_thread, single_save_data):
        self.index_key = single_save_data[0]  # account id
        if len(single_save_data) >= 3 and single_save_data[2]:
            self.display_name = single_save_data[2]
        else:
            self.display_name = single_save_data[0]
        crawler.CrawlerThread.__init__(self, main_thread, single_save_data)

    # 获取所有可下载音频
    def get_crawl_list(self):
        page_count = 1
        unique_list = []
        audio_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的音频
        while not is_over:
            pagination_description = "第%s页音频" % page_count
            self.start_parse(pagination_description)
            try:
                audit_pagination_response = ximalaya.get_one_page_audio(self.index_key, page_count)
            except crawler.CrawlerException as e:
                self.error(e.http_error(pagination_description))
                raise
            self.parse_result(pagination_description, audit_pagination_response["audio_info_list"])

            # 寻找这一页符合条件的媒体
            for audio_info in audit_pagination_response["audio_info_list"]:
                # 检查是否达到存档记录
                if audio_info["audio_id"] > int(self.single_save_data[1]):
                    # 新增音频导致的重复判断
                    if audio_info["audio_id"] in unique_list:
                        continue
                    else:
                        audio_info_list.append(audio_info)
                        unique_list.append(audio_info["audio_id"])
                else:
                    is_over = True
                    break

            if not is_over:
                if audit_pagination_response["is_over"]:
                    is_over = True
                else:
                    page_count += 1

        return audio_info_list

    # 解析单首音频
    def crawl_audio(self, audio_info):
        audio_description = "音频%s《%s》" % (audio_info["audio_id"], audio_info["audio_title"])
        self.start_parse(audio_description)
        try:
            audio_play_response = ximalaya.get_audio_info_page(audio_info["audio_id"])
        except crawler.CrawlerException as e:
            self.error(e.http_error(audio_description))
            raise
        if audio_play_response["is_delete"]:
            self.error("%s 不存在" % audio_description)
            raise

        audio_url = audio_play_response["audio_url"]
        audio_name = "%09d - %s.%s" % (audio_info["audio_id"], path.filter_text(audio_info["audio_title"]), net.get_file_extension(audio_url))
        audio_path = os.path.join(self.main_thread.audio_download_path, self.display_name, audio_name)
        if self.download(audio_url, audio_path, audio_description):
            self.total_audio_count += 1  # 计数累加

        # 音频下载完毕
        self.single_save_data[1] = str(audio_info["audio_id"])  # 设置存档记录

    def _run(self):
        # 获取所有可下载音频
        audio_info_list = self.get_crawl_list()
        self.step("需要下载的全部音频解析完毕，共%s个" % len(audio_info_list))

        # 从最早的媒体开始下载
        while len(audio_info_list) > 0:
            self.crawl_audio(audio_info_list.pop())


if __name__ == "__main__":
    XiMaLaYaAccount().main()
