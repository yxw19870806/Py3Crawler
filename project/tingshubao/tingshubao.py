# -*- coding:UTF-8  -*-
"""
听书宝
http://m.tingshubao.com
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import time

from pyquery import PyQuery as pq
from common import *


# 获取有声书首页
def get_album_index_page(album_id):
    album_index_url = f"http://m.tingshubao.com/book/{album_id}.html"
    album_index_response = net.Request(album_index_url, method="GET")
    result = {
        "audio_info_list": [],  # 全部音频信息
    }
    if album_index_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(album_index_response.status))
    audio_list_selector = pq(album_index_response.content).find(".play-list li")
    for audio_index in range(audio_list_selector.length, 0, -1):
        result_audio_info = {
            "audio_id": 0,  # 音频id
            "audio_title": "",  # 音频id
            "audio_play_url": "",  # 音频播放地址
        }
        audio_info_selector = audio_list_selector.eq(audio_index - 1)
        # 获取音频标题
        result_audio_info["audio_title"] = audio_info_selector.find("a").attr("title")
        # 获取音频播放地址
        audio_play_url = audio_info_selector.find("a").attr("href")
        if audio_play_url.startswith("/"):
            audio_play_url = "http://m.tingshubao.com" + audio_play_url
        result_audio_info["audio_play_url"] = audio_play_url
        audio_id = url.get_file_name(audio_play_url).split("-")[-1]
        if not tool.is_integer(audio_id):
            raise CrawlerException(f"音频播放地址 {audio_play_url} 截取音频id失败")
        result_audio_info["audio_id"] = int(audio_id) + 1  # 页面是从0开始的
        result["audio_info_list"].append(result_audio_info)
    return result


# 获取指定id的音频播放页
# audio_url -> http://m.tingshubao.com/video/?3393-0-1170.html
def get_audio_info_page(audio_play_url):
    result = {
        "audio_url": "",  # 音频下载地址
    }
    audio_play_response = net.Request(audio_play_url, method="GET")
    if audio_play_response.status == const.ResponseCode.TOO_MANY_REDIRECTS:
        return get_audio_info_page(audio_play_url)
    elif audio_play_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(audio_play_response.status))
    # 解析来自 http://m.tingshubao.com/player/main.js的FonHen_JieMa()方法
    encrypt_string = tool.find_sub_string(audio_play_response.content, "FonHen_JieMa('", "'")
    temp_list = []
    for temp in encrypt_string.split("*")[1:]:
        temp = chr(int(temp) & 0xffff)
        temp_list.append(temp)
    audio_url = "".join(temp_list).split("&")[0]
    if audio_url.startswith("http://"):
        result["audio_url"] = audio_url
    else:
        audio_detail_url = "http://43.129.176.64/player/key.php"
        query_data = {
            "url": audio_url
        }
        audio_detail_response = net.Request(audio_detail_url, method="GET", fields=query_data).enable_json_decode()
        if audio_detail_response.status != const.ResponseCode.SUCCEED:
            raise CrawlerException(crawler.request_failre(audio_detail_response.status))
        result["audio_url"] = crawler.get_json_value(audio_detail_response.json_data, "url", type_check=str)
    return result


class TingShuBao(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            const.SysConfigKey.DOWNLOAD_AUDIO: True,
            const.SysConfigKey.APP_CONFIG_PATH: os.path.join(crawler.PROJECT_APP_PATH, "app.ini"),
            const.SysConfigKey.SAVE_DATA_FORMATE: (0, ["", "0"]),  # album_id  last_audio_id
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 下载线程
        self.set_crawler_thread(CrawlerThread)

    def init(self):
        net.set_default_charset("GBK")
        net.set_default_user_agent(const.BrowserType.CHROME)


class CrawlerThread(crawler.CrawlerThread):
    def __init__(self, main_thread, single_save_data):
        self.index_key = single_save_data[0]  # album id
        if len(single_save_data) >= 3 and single_save_data[2]:
            self.display_name = single_save_data[2]
        else:
            self.display_name = single_save_data[0]
        crawler.CrawlerThread.__init__(self, main_thread, single_save_data)

    # 获取所有可下载音频
    def get_crawl_list(self):
        audio_info_list = []

        index_description = "首页"
        self.start_parse(index_description)
        try:
            album_index_response = get_album_index_page(self.index_key)
        except CrawlerException as e:
            self.error(e.http_error(index_description))
            raise
        self.parse_result(index_description, album_index_response["audio_info_list"])

        for audio_info in album_index_response["audio_info_list"]:
            # 检查是否达到存档记录
            if audio_info["audio_id"] > int(self.single_save_data[1]):
                audio_info_list.append(audio_info)
            else:
                break

        return audio_info_list

    # 解析单首音频
    def crawl_audio(self, audio_info):
        audio_description = f"音频{audio_info['audio_id']}"
        self.start_parse(audio_description)
        try:
            audio_play_response = get_audio_info_page(audio_info["audio_play_url"])
        except CrawlerException as e:
            self.error(e.http_error(audio_description))
            raise

        audio_name = "%04d %s.%s" % (audio_info["audio_id"], audio_info["audio_title"], url.get_file_ext(audio_play_response["audio_url"]))
        audio_path = os.path.join(self.main_thread.audio_download_path, self.display_name, audio_name)
        if self.download(audio_play_response["audio_url"], audio_path, audio_description, failure_callback=self.download_failure_callback):
            self.total_audio_count += 1  # 计数累加

        # 音频下载完毕
        self.single_save_data[1] = str(audio_info["audio_id"])  # 设置存档记录

    def download_failure_callback(self, audio_url, audio_path, audio_description, download_return: net.Download):
        while download_return.code == const.ResponseCode.TOO_MANY_REDIRECTS and (retry_count := 1) <= 4:
            time.sleep(3)
            self.main_thread_check()
            download_return.update(net.Download(audio_url, audio_path))
            if download_return:
                self.info(f"{audio_description}s 下载成功")
                return False
            else:
                self.info(f"{audio_description} 访问异常，重试")
            retry_count += 1
        return True

    def _run(self):
        # 获取所有可下载音频
        audio_info_list = self.get_crawl_list()
        self.info(f"需要下载的全部音频解析完毕，共{len(audio_info_list)}个")

        # 从最早的媒体开始下载
        while len(audio_info_list) > 0:
            self.crawl_audio(audio_info_list.pop())


if __name__ == "__main__":
    TingShuBao().main()
