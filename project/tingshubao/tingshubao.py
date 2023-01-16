# -*- coding:UTF-8  -*-
"""
听书宝
http://m.tingshubao.com
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from pyquery import PyQuery as pq
from common import *

USER_AGENT = net._random_user_agent("chrome")


# 获取有声书首页
def get_album_index_page(album_id):
    album_index_url = "http://m.tingshubao.com/book/%s.html" % album_id
    header_list = {
        "User-Agent": USER_AGENT,
    }
    album_index_response = net.request(album_index_url, method="GET", header_list=header_list)
    result = {
        "audio_info_list": [],  # 全部音频信息
    }
    if album_index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_index_response.status))
    album_index_response_content = album_index_response.data.decode("GBK", errors="ignore")
    audio_list_selector = pq(album_index_response_content).find(".play-list li")
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
        if audio_play_url[0] == "/":
            audio_play_url = "http://m.tingshubao.com" + audio_play_url
        result_audio_info["audio_play_url"] = audio_play_url
        audio_id = audio_play_url.split("/")[-1].replace(".html", "").split("-")[-1]
        if not tool.is_integer(audio_id):
            raise crawler.CrawlerException("音频播放地址 %s 截取音频id失败" % audio_play_url)
        result_audio_info["audio_id"] = int(audio_id) + 1  # 页面是从0开始的
        result["audio_info_list"].append(result_audio_info)
    return result


# 获取指定id的音频播放页
# audio_url -> http://m.tingshubao.com/video/?3393-0-1170.html
def get_audio_info_page(audio_play_url):
    result = {
        "audio_url": "",  # 音频下载地址
    }
    header_list = {
        "User-Agent": USER_AGENT,
    }
    audio_play_response = net.request(audio_play_url, method="GET", header_list=header_list)
    if audio_play_response.status == net.HTTP_RETURN_CODE_TOO_MANY_REDIRECTS:
        return get_audio_info_page(audio_play_url)
    elif audio_play_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(audio_play_response.status))
    audio_play_response_content = audio_play_response.data.decode(errors="ignore")
    # 解析来自 http://m.tingshubao.com/player/main.js的FonHen_JieMa()方法
    encrypt_string = tool.find_sub_string(audio_play_response_content, "FonHen_JieMa('", "'")
    temp_list = []
    for temp in encrypt_string.split("*")[1:]:
        temp = chr(int(temp) & 0xffff)
        temp_list.append(temp)
    audio_url = "".join(temp_list).split("&")[0]
    if audio_url[:7] == "http://":
        result["audio_url"] = audio_url
    else:
        audio_detail_url = "http://43.129.176.64/player/key.php"
        query_data = {
            "url": "".join(temp_list).split("&")[0]
        }
        audio_detail_response = net.request(audio_detail_url, method="GET", fields=query_data, json_decode=True)
        if audio_detail_response.status != net.HTTP_RETURN_CODE_SUCCEED:
            raise crawler.CrawlerException(crawler.request_failre(audio_detail_response.status))
        result["audio_url"] = crawler.get_json_value(audio_detail_response.json_data, "url", type_check=str)
    return result


class TingShuBao(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_AUDIO: True,
            crawler.SYS_APP_CONFIG_PATH: os.path.join(crawler.PROJECT_APP_PATH, "app.ini"),
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 解析存档文件
        # album_id  last_audio_id
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

        # 下载线程
        self.download_thread = Download


class Download(crawler.CrawlerThread):
    def __init__(self, single_save_data, main_thread):
        self.index_key = single_save_data[0]  # album id
        if len(single_save_data) >= 3 and single_save_data[2]:
            self.display_name = single_save_data[2]
        else:
            self.display_name = single_save_data[0]
        crawler.CrawlerThread.__init__(self, single_save_data, main_thread)

    def _run(self):
        # 获取所有可下载音频
        audio_info_list = self.get_crawl_list()
        self.step("需要下载的全部音频解析完毕，共%s个" % len(audio_info_list))

        # 从最早的媒体开始下载
        while len(audio_info_list) > 0:
            self.crawl_audio(audio_info_list.pop())
            self.main_thread_check()  # 检测主线程运行状态

    # 获取所有可下载音频
    def get_crawl_list(self):
        audio_info_list = []

        index_description = "首页"
        self.start_parse(index_description)

        try:
            album_index_response = get_album_index_page(self.index_key)
        except crawler.CrawlerException as e:
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
        audio_description = "音频%s" % audio_info["audio_id"]
        self.start_parse(audio_description)

        # 获取音频播放页
        try:
            audio_play_response = get_audio_info_page(audio_info["audio_play_url"])
        except crawler.CrawlerException as e:
            self.error(e.http_error(audio_description))
            raise

        audio_url = audio_play_response["audio_url"]
        self.step("开始下载 %s %s" % (audio_description, audio_url))

        for retry_count in range(5):
            audio_name = "%04d %s.%s" % (audio_info["audio_id"], audio_info["audio_title"], net.get_file_extension(audio_url))
            audio_path = os.path.join(self.main_thread.audio_download_path, self.display_name, audio_name)
            download_return = net.Download(audio_url, audio_path)
            if download_return.status == net.Download.DOWNLOAD_SUCCEED:
                self.total_audio_count += 1  # 计数累加
                self.step("%s 下载成功" % audio_description)
                break
            else:
                if download_return.code != net.HTTP_RETURN_CODE_TOO_MANY_REDIRECTS or retry_count >= 4:
                    self.error("%s %s 下载失败，原因：%s" % (audio_description, audio_url, crawler.download_failre(download_return.code)))
                    self.check_download_failure_exit()
                else:
                    self.step("%s %s 下载失败，重试" % (audio_description, audio_url))

        # 音频下载完毕
        self.single_save_data[1] = str(audio_info["audio_id"])  # 设置存档记录


if __name__ == "__main__":
    TingShuBao().main()
