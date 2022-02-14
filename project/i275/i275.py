# -*- coding:UTF-8  -*-
"""
i275听书网音频爬虫
https://www.i275.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import time
from pyquery import PyQuery as pq
from common import *


# 获取指定页数的全部音频信息
def get_album_index_page(album_id):
    album_pagination_url = f"https://www.i275.com/book/{album_id}.html"
    album_pagination_response = net.request(album_pagination_url, method="GET")
    result = {
        "audio_info_list": [],  # 全部音频信息
    }
    if album_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_pagination_response.status))
    album_pagination_response_content = album_pagination_response.data.decode(errors="ignore")
    audio_info_selector_list = pq(album_pagination_response_content).find("ul.playul li")
    if audio_info_selector_list.length == 0:
        raise crawler.CrawlerException("页面截取音频列表失败\n" + album_pagination_response_content)
    # 获取音频信息
    for audio_info_index in range(0, audio_info_selector_list.length):
        result_audio_info = {
            "audio_id": None,  # 音频id
            "audio_title": "",  # 音频标题
        }
        audio_info_selector = audio_info_selector_list.eq(audio_info_index)
        # 获取音频id
        audio_id = tool.find_sub_string(audio_info_selector.find("a").attr("href"), f"/play/{album_id}/", ".html")
        if not tool.is_integer(audio_id):
            raise crawler.CrawlerException("音频信息截取音频id失败\n" + audio_info_selector.html())
        result_audio_info["audio_id"] = int(audio_id)
        # 获取音频标题
        result_audio_info["audio_title"] = audio_info_selector.find("a").text()

        result["audio_info_list"].append(result_audio_info)
    result["audio_info_list"].reverse()
    return result


# 获取指定id的音频播放页
# audio_id -> 16558983
def get_audio_info_page(album_id, audio_id):
    result = {
        "audio_url": "",  # 音频地址
    }
    audio_info_url = f"https://www.i275.com/pc/index/getchapterurl/bookId/{album_id}/chapterId/{audio_id}.html"
    audio_info_response = net.request(audio_info_url, method="GET", json_decode=True)
    if audio_info_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(audio_info_response.status))
    audio_src = crawler.get_json_value(audio_info_response.json_data, "src", type_check=str)
    # 解析来自 https://www.i275.com/static/haidao/script/common.js
    result["audio_url"] = "".join(map(chr, map(int, audio_src.split("*"))))
    return result


class I275(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_AUDIO: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 解析存档文件
        # album_id  last_audio_id
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

    def _main(self):
        # 循环下载每个id
        thread_list = []
        for album_id in sorted(self.save_data.keys()):
            # 提前结束
            if not self.is_running():
                break

            # 开始下载
            thread = Download(self.save_data[album_id], self)
            thread.start()
            thread_list.append(thread)

            time.sleep(1)

        # 等待子线程全部完成
        while len(thread_list) > 0:
            thread_list.pop().join()


class Download(crawler.DownloadThread):
    def __init__(self, single_save_data, main_thread):
        crawler.DownloadThread.__init__(self, single_save_data, main_thread)
        self.index_key = self.single_save_data[0]  # album id
        if len(self.single_save_data) >= 3 and self.single_save_data[2]:
            self.display_name = self.single_save_data[2]
        else:
            self.display_name = self.single_save_data[0]
        self.total_audio_count = 0
        self.step("开始")

    def _run(self):
        # 获取所有可下载音频
        audio_info_list = self.get_crawl_list()
        self.step(f"需要下载的全部音频解析完毕，共{len(audio_info_list)}个")

        # 从最早的媒体开始下载
        while len(audio_info_list) > 0:
            self.crawl_audio(audio_info_list.pop())
            self.main_thread_check()  # 检测主线程运行状态

    # 获取所有可下载音频
    def get_crawl_list(self):
        audio_info_list = []
        # 获取一页音频
        try:
            audit_pagination_response = get_album_index_page(self.index_key)
        except crawler.CrawlerException as e:
            self.error(e.http_error("首页"))
            raise

        self.trace(f"首页解析的全部音频：{audit_pagination_response['audio_info_list']}")
        self.step(f"首页解析获取{len(audit_pagination_response['audio_info_list'])}首音频")

        # 寻找这一页符合条件的媒体
        for audio_info in audit_pagination_response["audio_info_list"]:
            # 检查是否达到存档记录
            if audio_info["audio_id"] > int(self.single_save_data[1]):
                audio_info_list.append(audio_info)
            else:
                break

        return audio_info_list

    # 解析单首音频
    def crawl_audio(self, audio_info):
        self.step(f"开始解析音频{audio_info['audio_id']}")

        # 获取音频播放页
        try:
            audio_play_response = get_audio_info_page(self.index_key, audio_info["audio_id"])
        except crawler.CrawlerException as e:
            self.error(e.http_error(f"音频{audio_info['audio_id']}"))
            raise

        audio_url = audio_play_response["audio_url"]
        self.step(f"开始下载音频{audio_info['audio_id']}《{audio_info['audio_title']}》 {audio_url}")

        file_path = os.path.join(self.main_thread.audio_download_path, self.display_name, f"%07d - {path.filter_text(audio_info['audio_title'])}.{net.get_file_extension(audio_url)}" % (audio_info["audio_id"]))
        save_file_return = net.download(audio_url, file_path)
        if save_file_return["status"] == 1:
            self.total_audio_count += 1  # 计数累加
            self.step(f"音频{audio_info['audio_id']}《{audio_info['audio_title']}》下载成功")
        else:
            self.error(f"音频{audio_info['audio_id']}《{audio_info['audio_title']}》 {audio_url} 下载失败，原因：{crawler.download_failre(save_file_return['code'])}")
            self.check_download_failure_exit()

        # 音频下载完毕
        self.single_save_data[1] = str(audio_info["audio_id"])  # 设置存档记录


if __name__ == "__main__":
    I275().main()
