# -*- coding:UTF-8  -*-
"""
喜马拉雅音频爬虫
https://www.ximalaya.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import math
import os
import random
import time
import traceback
from common import *


# 获取指定页数的全部音频信息
def get_one_page_album(album_id, page_count):
    album_pagination_url = "https://www.ximalaya.com/revision/album/v1/getTracksList"
    query_data = {
        "albumId": album_id,
        "pageNum": page_count,
    }
    album_pagination_response = net.http_request(album_pagination_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "audio_info_list": [],  # 全部音频信息
        "is_over": False,  # 是否最后一页音频
    }
    if album_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_pagination_response.status))
    # 获取音频信息
    for audio_info in crawler.get_json_value(album_pagination_response.json_data, "data", "tracks", type_check=list):
        result_audio_info = {
            "audio_id": None,  # 音频id
            "audio_title": "",  # 音频标题
        }
        # 获取音频id
        result_audio_info["audio_id"] = crawler.get_json_value(audio_info, "trackId", type_check=int)
        # 获取音频标题
        result_audio_info["audio_title"] = crawler.get_json_value(audio_info, "title", type_check=str).strip()
        result["audio_info_list"].append(result_audio_info)
    # 判断是不是最后一页
    total_audio_count = crawler.get_json_value(album_pagination_response.json_data, "data", "trackTotalCount", type_check=int)
    real_page_size = crawler.get_json_value(album_pagination_response.json_data, "data", "pageSize", type_check=int)
    result["is_over"] = page_count >= math.ceil(total_audio_count / real_page_size)
    return result


# 获取指定页数的全部音频信息
def get_one_page_audio(account_id, page_count):
    # https://www.ximalaya.com/zhubo/1014267/sound/
    audio_pagination_url = "https://www.ximalaya.com/revision/user/track"
    query_data = {
        "page": page_count,
        "pageSize": "10",
        "keyWord": "",
        "uid": account_id,
        "orderType": "2",  # 降序
    }
    now = int(time.time() * 1000)
    # 加密方法解析来自 https://s1.xmcdn.com/yx/ximalaya-web-static/last/dist/scripts/b20b549ee.js
    header_list = {
        "xm-sign": "%s(%s)%s(%s)%s" % (tool.string_md5("himalaya-" + str(now)), random.randint(1, 100), now, random.randint(1, 100), now + random.randint(1, 100 * 60))
    }
    audit_pagination_response = net.http_request(audio_pagination_url, method="GET", fields=query_data, header_list=header_list, json_decode=True)
    result = {
        "audio_info_list": [],  # 全部音频信息
        "is_over": False,  # 是否最后一页音频
    }
    if audit_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(audit_pagination_response.status))
    # 获取音频信息
    for audio_info in crawler.get_json_value(audit_pagination_response.json_data, "data", "trackList", type_check=list):
        result_audio_info = {
            "audio_id": None,  # 音频id
            "audio_title": "",  # 音频标题
        }
        # 获取音频id
        result_audio_info["audio_id"] = crawler.get_json_value(audio_info, "trackId", type_check=int)
        # 获取音频标题
        result_audio_info["audio_title"] = crawler.get_json_value(audio_info, "title", type_check=str).strip()
        result["audio_info_list"].append(result_audio_info)
    # 判断是不是最后一页
    total_audio_count = crawler.get_json_value(audit_pagination_response.json_data, "data", "maxCount", type_check=int)
    real_page_size = crawler.get_json_value(audit_pagination_response.json_data, "data", "pageSize", type_check=int)
    result["is_over"] = page_count >= math.ceil(total_audio_count / real_page_size)
    return result


# 获取指定id的音频播放页
# audio_id -> 16558983
def get_audio_info_page(audio_id):
    audio_info_url = "https://www.ximalaya.com/tracks/%s.json" % audio_id
    result = {
        "audio_title": "",  # 音频标题
        "audio_url": None,  # 音频地址
        "is_delete": False,  # 是否已删除
    }
    audio_play_response = net.http_request(audio_info_url, method="GET", json_decode=True)
    if audio_play_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(audio_play_response.status))
    if crawler.get_json_value(audio_play_response.json_data, "id", type_check=int) == 0:
        result["is_delete"] = True
        return result
    # 获取音频标题
    result["audio_title"] = crawler.get_json_value(audio_play_response.json_data, "title", type_check=str)
    # 获取音频地址
    for key_name in ["play_path_64", "play_path_32", "play_path"]:
        audio_url = crawler.get_json_value(audio_play_response.json_data, key_name, default_value="", type_check=str)
        if audio_url:
            result["audio_url"] = audio_url
            break
    else:
        raise crawler.CrawlerException("返回信息匹配音频地址失败\n%s" % audio_play_response.json_data)
    return result


class XiMaLaYa(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_AUDIO: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 解析存档文件
        # account_id  last_audio_id
        self.account_list = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

    def main(self):
        try:
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
        self.account_id = self.account_info[0]
        if len(self.account_info) >= 3 and self.account_info[2]:
            self.display_name = self.account_info[2]
        else:
            self.display_name = self.account_info[0]
        self.total_audio_count = 0
        self.step("开始")

    # 获取所有可下载音频
    def get_crawl_list(self):
        page_count = 1
        unique_list = []
        audio_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的音频
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析第%s页音频" % page_count)

            # 获取一页音频
            try:
                audit_pagination_response = get_one_page_audio(self.account_id, page_count)
            except crawler.CrawlerException as e:
                self.error("第%s页音频解析失败，原因：%s" % (page_count, e.message))
                break

            self.trace("第%s页解析的全部音频：%s" % (page_count, audit_pagination_response["audio_info_list"]))
            self.step("第%s页解析获取%s首音频" % (page_count, len(audit_pagination_response["audio_info_list"])))

            # 寻找这一页符合条件的媒体
            for audio_info in audit_pagination_response["audio_info_list"]:
                # 检查是否达到存档记录
                if audio_info["audio_id"] > int(self.account_info[1]):
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
        self.step("开始解析音频%s" % audio_info["audio_id"])

        # 获取音频播放页
        try:
            audio_play_response = get_audio_info_page(audio_info["audio_id"])
        except crawler.CrawlerException as e:
            self.error("音频%s解析失败，原因：%s" % (audio_info["audio_id"], e.message))
            return

        if audio_play_response["is_delete"]:
            self.error("音频%s不存在" % audio_info["audio_id"])
            return

        audio_url = audio_play_response["audio_url"]
        self.step("开始下载音频%s《%s》 %s" % (audio_info["audio_id"], audio_info["audio_title"], audio_url))

        file_path = os.path.join(self.main_thread.audio_download_path, self.display_name, "%09d - %s.%s" % (audio_info["audio_id"], path.filter_text(audio_info["audio_title"]), net.get_file_type(audio_url)))
        save_file_return = net.save_net_file(audio_url, file_path)
        if save_file_return["status"] == 1:
            self.step("音频%s《%s》下载成功" % (audio_info["audio_id"], audio_info["audio_title"]))
        else:
            self.error("音频%s《%s》 %s 下载失败，原因：%s" % (audio_info["audio_id"], audio_info["audio_title"], audio_url, crawler.download_failre(save_file_return["code"])))
            return

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
            self.main_thread.account_list.pop(self.account_id)
        self.step("下载完毕，总共获得%s首音频" % self.total_audio_count)
        self.notify_main_thread()


if __name__ == "__main__":
    XiMaLaYa().main()
