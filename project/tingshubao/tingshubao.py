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
import traceback
from pyquery import PyQuery as pq
from common import *


# 获取有声书首页
def get_album_index_page(album_id):
    album_index_url = "http://m.tingshubao.com/book/%s.html" % album_id
    album_index_response = net.http_request(album_index_url, method="GET")
    result = {
        "audio_info_list": [],  # 全部音频信息
    }
    if album_index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_index_response.status))
    album_index_response_content = album_index_response.data.decode(errors="ignore")
    audio_list_selector = pq(album_index_response_content).find(".play-list ul li")
    for audio_index in range(audio_list_selector.length, 0, -1):
        result_audio_info = {
            "audio_id": None,  # 音频id
            "audio_play_url": "",  # 音频播放地址
        }
        audio_info_selector = audio_list_selector.eq(audio_index - 1)
        audio_id = audio_info_selector.find("a").attr("title")
        if crawler.is_integer(audio_id):
            result_audio_info["audio_id"] = int(audio_id)
        audio_play_url = audio_info_selector.find("a").attr("href")
        if audio_play_url[0] == "/":
            audio_play_url = "http://m.tingshubao.com" + audio_play_url
        result_audio_info["audio_play_url"] = audio_play_url
        result["audio_info_list"].append(result_audio_info)
    return result


# 获取指定id的音频播放页
# audio_url -> http://m.tingshubao.com/video/?3393-0-1170.html
def get_audio_info_page(audio_play_url):
    result = {
        "audio_url": "",  # 音频下载地址
    }
    audio_play_response = net.http_request(audio_play_url, method="GET")
    if audio_play_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(audio_play_response.status))
    audio_play_response_content = audio_play_response.data.decode(errors="ignore")
    # 解析来自 http://m.tingshubao.com/player/main.js的FonHen_JieMa()方法
    encrypt_string = tool.find_sub_string(audio_play_response_content, "FonHen_JieMa('", "'")
    temp_list = []
    for temp in encrypt_string.split("*")[1:]:
        temp = chr(int(temp) & 0xffff)
        temp_list.append(temp)
    audio_detail_url = "https://www.gushiciju.com/player/key.php?url="
    query_data = {
        "url": "".join(temp_list).split("&")[0]
    }
    audio_detail_response = net.http_request(audio_detail_url, method="GET", fields=query_data, json_decode=True)
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
        self.account_list = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

    def main(self):
        try:
            # 循环下载每个id
            thread_list = []
            for album_id in sorted(self.account_list.keys()):
                # 提前结束
                if not self.is_running():
                    break

                # 开始下载
                thread = Download(self.account_list[album_id], self)
                thread.start()
                thread_list.append(thread)

                time.sleep(1)

            # 等待子线程全部完成
            while len(thread_list) > 0:
                thread_list.pop().join()
        except KeyboardInterrupt:
            self.stop_process()

        # 未完成的数据保存
        if len(self.account_list) > 0:
            file.write_file(tool.list_to_string(list(self.account_list.values())), self.temp_save_data_path)

        # 重新排序保存存档文件
        crawler.rewrite_save_file(self.temp_save_data_path, self.save_data_path)

        log.step("全部下载完毕，耗时%s秒，共计音频%s首" % (self.get_run_time(), self.total_audio_count))


class Download(crawler.DownloadThread):
    def __init__(self, account_info, main_thread):
        crawler.DownloadThread.__init__(self, account_info, main_thread)
        self.album_id = self.account_info[0]
        if len(self.account_info) >= 3 and self.account_info[2]:
            self.display_name = self.account_info[2]
        else:
            self.display_name = self.account_info[0]
        self.total_audio_count = 0
        self.step("开始")

    # 获取所有可下载音频
    def get_crawl_list(self):
        audio_info_list = []

        self.step("开始解析首页")
        album_index_response = get_album_index_page(self.album_id)
        self.trace("首页解析的全部音频：%s" % (album_index_response["audio_info_list"]))
        self.step("首页解析获取%s首音频" % (len(album_index_response["audio_info_list"])))

        for audio_info in album_index_response["audio_info_list"]:
            # 检查是否达到存档记录
            if audio_info["audio_id"] > int(self.account_info[1]):
                audio_info_list.append(audio_info)
            else:
                break

        return audio_info_list

    # 解析单首音频
    def crawl_audio(self, audio_info):
        self.step("开始解析音频%s" % audio_info["audio_id"])

        # 获取音频播放页
        try:
            audio_play_response = get_audio_info_page(audio_info["audio_play_url"])
        except crawler.CrawlerException as e:
            self.error("音频%s解析失败，原因：%s" % (audio_info["audio_id"], e.message))
            raise

        audio_url = audio_play_response["audio_url"]
        self.step("开始下载音频%s %s" % (audio_info["audio_id"], audio_url))

        file_path = os.path.join(self.main_thread.audio_download_path, self.display_name, "%04d.%s" % (audio_info["audio_id"], net.get_file_type(audio_url)))
        save_file_return = net.save_net_file(audio_url, file_path)
        if save_file_return["status"] == 1:
            self.step("音频%s下载成功" % audio_info["audio_id"])
        else:
            self.error("音频%s %s 下载失败，原因：%s" % (audio_info["audio_id"], audio_url, crawler.download_failre(save_file_return["code"])))
            raise crawler.CrawlerException()

        # 音频下载完毕
        self.total_audio_count += 1  # 计数累加
        self.account_info[1] = str(audio_info["audio_id"])  # 设置存档记录

    def run(self):
        try:
            # 获取所有可下载音频
            audio_info_list = self.get_crawl_list()
            self.step("需要下载的全部音频解析完毕，共%s个" % len(audio_info_list))

            # 从最早的媒体开始下载
            while len(audio_info_list) > 0:
                self.crawl_audio(audio_info_list.pop())
                self.main_thread_check()  # 检测主线程运行状态
        except (SystemExit, KeyboardInterrupt) as e:
            if isinstance(e, SystemExit) and e.code == 1:
                self.error("异常退出")
            else:
                self.step("提前退出")
        except Exception as e:
            self.error("未知异常")
            self.error(str(e) + "\n" + traceback.format_exc(), False)

        # 保存最后的信息
        with self.thread_lock:
            file.write_file("\t".join(self.account_info), self.main_thread.temp_save_data_path)
            self.main_thread.total_audio_count += self.total_audio_count
            self.main_thread.account_list.pop(self.album_id)
        self.step("下载完毕，总共获得%s首音频" % self.total_audio_count)
        self.notify_main_thread()


if __name__ == "__main__":
    TingShuBao().main()