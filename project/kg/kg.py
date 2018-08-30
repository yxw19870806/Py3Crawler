# -*- coding:UTF-8  -*-
"""
全民k歌歌曲爬虫
https://kg.qq.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import threading
import time
import traceback
from common import *

AUDIO_COUNT_PER_PAGE = 8


# 获取指定页数的一页歌曲信息
def get_one_page_audio(account_id, page_count):
    audio_pagination_url = "https://kg.qq.com/cgi/kg_ugc_get_homepage"
    query_data = {
        "type": "get_ugc",
        "format": "json",
        "share_uid": account_id,
        "start": page_count,
        "num": AUDIO_COUNT_PER_PAGE,
    }
    audio_pagination_response = net.http_request(audio_pagination_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "audio_info_list": [],  # 全部歌曲信息
        "is_over": False,  # 是否最后一页歌曲
    }
    if audio_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(audio_pagination_response.status))
    if crawler.check_sub_key(("code",), audio_pagination_response.json_data) and crawler.is_integer(audio_pagination_response.json_data["code"]):
        if int(audio_pagination_response.json_data["code"]) == 1101:
            raise crawler.CrawlerException("账号不存在")
    if not crawler.check_sub_key(("data",), audio_pagination_response.json_data):
        raise crawler.CrawlerException("返回数据'data'字段不存在\n%s" % audio_pagination_response.json_data)
    if not crawler.check_sub_key(("has_more", "ugclist"), audio_pagination_response.json_data["data"]):
        raise crawler.CrawlerException("返回数据'has_more'或者'ugclist'字段不存在\n%s" % audio_pagination_response.json_data)
    for audio_info in audio_pagination_response.json_data["data"]["ugclist"]:
        result_audio_info = {
            "audio_id": None,  # 歌曲id
            "audio_key": None,  # 歌曲访问token
            "audio_time": None,  # 歌曲上传时间
            "audio_title": "",  # 歌曲标题
        }
        # 获取歌曲id
        if not crawler.check_sub_key(("ksong_mid",), audio_info):
            raise crawler.CrawlerException("返回数据'ksong_mid'字段不存在\n%s" % audio_info)
        result_audio_info["audio_id"] = audio_info["ksong_mid"]
        # 获取歌曲访问token
        if not crawler.check_sub_key(("shareid",), audio_info):
            raise crawler.CrawlerException("返回数据'shareid'字段不存在\n%s" % audio_info)
        result_audio_info["audio_key"] = audio_info["shareid"]
        # 获取歌曲标题
        if not crawler.check_sub_key(("title",), audio_info):
            raise crawler.CrawlerException("返回数据'title'字段不存在\n%s" % audio_info)
        result_audio_info["audio_title"] = audio_info["title"]
        # 获取歌曲上传时间
        if not crawler.check_sub_key(("time",), audio_info):
            raise crawler.CrawlerException("返回数据'time'字段不存在\n%s" % audio_info)
        if not crawler.is_integer(audio_info["time"]):
            raise crawler.CrawlerException("返回数据'time'字段类型不正确\n%s" % audio_info)
        result_audio_info["audio_time"] = int(audio_info["time"])
        result["audio_info_list"].append(result_audio_info)
    # 判断是不是最后一页
    result["is_over"] = not bool(int(audio_pagination_response.json_data["data"]["has_more"]))
    return result


# 获取歌曲播放地址
def get_audio_play_page(audio_key):
    audio_play_url = "https://kg.qq.com/node/play"
    query_data = {"s": audio_key}
    audio_play_response = net.http_request(audio_play_url, method="GET", fields=query_data)
    result = {
        "audio_title": "",  # 歌曲标题
        "audio_url": None,  # 歌曲地址
    }
    if audio_play_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(audio_play_response.status))
    audio_play_response_content = audio_play_response.data.decode(errors="ignore")
    # 获取歌曲标题
    audio_title = tool.find_sub_string(audio_play_response_content, '<h2 class="play_name">', "</h2>")
    if not audio_title:
        raise crawler.CrawlerException("页面截取歌曲标题失败\n%s" % audio_play_response_content)
    result["audio_title"] = audio_title.strip()
    # 获取歌曲地址
    audio_url = tool.find_sub_string(audio_play_response_content, '"playurl":"', '"')
    if not audio_url:
        audio_url = tool.find_sub_string(audio_play_response_content, '"playurl_video":"', '"')
    if not audio_url:
        raise crawler.CrawlerException("页面截取歌曲地址失败\n%s" % audio_play_response_content)
    result["audio_url"] = audio_url
    return result


# 获取文件后缀
def get_file_type(file_url):
    file_name_and_param = file_url.split("/")[-1]
    file_name_and_type = file_name_and_param.split("?")[0].split(".")[-1]
    if len(file_name_and_type) == 2:
        return file_name_and_type[1]
    query_string_list = file_name_and_param.split("?")[-1].split("&")
    for query_string in query_string_list:
        if query_string.find("=") == -1:
            continue
        key, value = query_string.split("=", 1)
        if key == "fname":
            return value.split(".")[-1]
    return "m4a"


class KG(crawler.Crawler):
    def __init__(self):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_VIDEO: True,
        }
        crawler.Crawler.__init__(self, sys_config)

        # 解析存档文件
        # account_id
        self.account_list = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

    def main(self):
        # 循环下载每个id
        thread_list = []
        for account_id in sorted(self.account_list.keys()):
            # 提前结束
            if not self.is_running():
                break

            # 开始下载
            thread = Download(self.account_list[account_id], self)
            thread.start()
            thread_list.append(thread)

            time.sleep(1)

        # 等待子线程全部完成
        while len(thread_list) > 0:
            thread_list.pop().join()

        # 未完成的数据保存
        if len(self.account_list) > 0:
            file.write_file(tool.list_to_string(list(self.account_list.values())), self.temp_save_data_path)

        # 重新排序保存存档文件
        crawler.rewrite_save_file(self.temp_save_data_path, self.save_data_path)

        log.step("全部下载完毕，耗时%s秒，共计歌曲%s首" % (self.get_run_time(), self.total_video_count))


class Download(crawler.DownloadThread):
    def __init__(self, account_info, main_thread):
        crawler.DownloadThread.__init__(self, account_info, main_thread)
        self.account_id = self.account_info[0]
        if len(self.account_info) >= 3 and self.account_info[2]:
            self.display_name = self.account_info[2]
        else:
            self.display_name = self.account_info[0]
        self.step("开始")

    # 获取所有可下载歌曲
    def get_crawl_list(self):
        page_count = 1
        unique_list = []
        audio_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的歌曲
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析第%s页歌曲" % page_count)

            # 获取一页歌曲
            try:
                audio_pagination_response = get_one_page_audio(self.account_id, page_count)
            except crawler.CrawlerException as e:
                self.error("第%s页歌曲解析失败，原因：%s" % (page_count, e.message))
                raise

            self.trace("第%s页解析的全部歌曲：%s" % (page_count, audio_pagination_response["audio_info_list"]))
            self.step("第%s页解析获取%s首歌曲" % (page_count, len(audio_pagination_response["audio_info_list"])))

            # 寻找这一页符合条件的歌曲
            for audio_info in audio_pagination_response["audio_info_list"]:
                # 检查是否达到存档记录
                if audio_info["audio_time"] > int(self.account_info[1]):
                    # 新增歌曲导致的重复判断
                    if audio_info["audio_id"] in unique_list:
                        continue
                    else:
                        audio_info_list.append(audio_info)
                        unique_list.append(audio_info["audio_id"])
                else:
                    is_over = True
                    break

            if audio_pagination_response["is_over"]:
                is_over = True
            else:
                page_count += 1

        return audio_info_list

    # 解析单首歌曲
    def crawl_audio(self, audio_info):
        # 获取歌曲播放页
        try:
            audio_play_response = get_audio_play_page(audio_info["audio_key"])
        except crawler.CrawlerException as e:
            self.error("歌曲%s《%s》解析失败，原因：%s" % (audio_info["audio_key"], audio_info["audio_title"], e.message))
            raise

        self.main_thread_check()  # 检测主线程运行状态
        self.step("开始下载歌曲%s《%s》 %s" % (audio_info["audio_key"], audio_info["audio_title"], audio_play_response["audio_url"]))

        file_type = get_file_type(audio_play_response["audio_url"])
        file_path = os.path.join(self.main_thread.video_download_path, self.display_name, "%s - %s.%s" % (audio_info["audio_id"], path.filter_text(audio_info["audio_title"]), file_type))
        save_file_return = net.save_net_file(audio_play_response["audio_url"], file_path)
        if save_file_return["status"] == 1:
            self.step("歌曲%s《%s》下载成功" % (audio_info["audio_key"], audio_info["audio_title"]))
        else:
            self.error("歌曲%s《%s》 %s 下载失败，原因：%s" % (audio_info["audio_key"], audio_info["audio_title"], audio_play_response["audio_url"], crawler.download_failre(save_file_return["code"])))

        # 歌曲下载完毕
        self.total_video_count += 1  # 计数累加
        self.account_info[1] = str(audio_info["audio_time"])  # 设置存档记录

    def run(self):
        try:
            # 获取所有可下载歌曲
            audio_info_list = self.get_crawl_list()
            self.step("需要下载的全部歌曲解析完毕，共%s首" % len(audio_info_list))

            while len(audio_info_list) > 0:
                audio_info = audio_info_list.pop()
                self.step("开始解析歌曲%s《%s》" % (audio_info["audio_key"], audio_info["audio_title"]))
                self.crawl_audio(audio_info)
                self.main_thread_check()  # 检测主线程运行状态
        except SystemExit as se:
            if se.code == 0:
                self.step("提前退出")
            else:
                self.error("异常退出")
        except Exception as e:
            self.error("未知异常")
            self.error(str(e) + "\n" + traceback.format_exc(), False)

        # 保存最后的信息
        with self.thread_lock:
            file.write_file("\t".join(self.account_info), self.main_thread.temp_save_data_path)
            self.main_thread.total_video_count += self.total_video_count
            self.main_thread.account_list.pop(self.account_id)
        self.step("下载完毕，总共获得%s首歌曲" % self.total_video_count)
        self.notify_main_thread()


if __name__ == "__main__":
    KG().main()
