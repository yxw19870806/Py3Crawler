# -*- coding:UTF-8  -*-
"""
美拍视频爬虫
http://www.meipai.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import base64
import os
import threading
import time
import traceback
from functools import reduce
from pyquery import PyQuery as pq
from common import *

VIDEO_COUNT_PER_PAGE = 20  # 每次请求获取的视频数量


# 获取指定页数的全部视频
def get_one_page_video(account_id, page_count):
    # http://www.meipai.com/users/user_timeline?uid=22744352&page=1&count=20&single_column=1
    video_pagination_url = "http://www.meipai.com/users/user_timeline"
    query_data = {
        "uid": account_id,
        "page": page_count,
        "count": VIDEO_COUNT_PER_PAGE,
        "single_column": 1,
    }
    video_pagination_response = net.http_request(video_pagination_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "video_info_list": [],  # 全部视频信息
    }
    if video_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_pagination_response.status))
    if not crawler.check_sub_key(("medias",), video_pagination_response.json_data):
        raise crawler.CrawlerException("返回数据'medias'字段不存在\n%s" % video_pagination_response.json_data)
    for media_data in video_pagination_response.json_data["medias"]:
        # 历史直播，跳过
        if crawler.check_sub_key(("lives",), media_data):
            continue
        result_video_info = {
            "video_id": None,  # 视频id
            "video_url": None,  # 视频地址
        }
        # 获取视频id
        if not crawler.check_sub_key(("id",), media_data):
            raise crawler.CrawlerException("视频信息'id'字段不存在\n%s" % media_data)
        if not crawler.is_integer(media_data["id"]):
            raise crawler.CrawlerException("视频信息'id'字段类型不正确\n%s" % media_data)
        result_video_info["video_id"] = int(media_data["id"])
        # 获取视频下载地址
        if not crawler.check_sub_key(("video",), media_data):
            raise crawler.CrawlerException("视频信息'video'字段不存在\n%s" % media_data)
        video_url = decrypt_video_url(media_data["video"])
        if video_url is None:
            raise crawler.CrawlerException("加密视频地址解密失败\n%s" % media_data["video"])
        result_video_info["video_url"] = video_url
        result["video_info_list"].append(result_video_info)
    return result


# 获取指定视频播放页
def get_video_play_page(video_id):
    video_play_url = "http://www.meipai.com/media/%s" % video_id
    video_play_response = net.http_request(video_play_url, method="GET")
    result = {
        "is_delete": False,  # 是否已删除
        "video_url": None,  # 视频地址
    }
    if video_play_response.status == 404:
        result["is_delete"] = True
        return result
    elif video_play_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_play_response.status))
    video_play_response_content = video_play_response.data.decode(errors="ignore")
    video_url_crypt_string = pq(video_play_response_content).find("meta[property='og:video:url']").attr("content")
    if not video_url_crypt_string:
        raise crawler.CrawlerException("页面截取加密视频地址失败\n%s" % video_play_response_content)
    video_url = decrypt_video_url(video_url_crypt_string)
    if not video_url:
        raise crawler.CrawlerException("加密视频地址解密失败\n%s" % video_url_crypt_string)
    result["video_url"] = video_url
    return result


# 视频地址解谜
# 破解于播放器swf文件中com.meitu.cryptography.meipai.Default.decode
def decrypt_video_url(encrypted_string):
    loc1 = _get_hex(encrypted_string)
    loc2 = _get_dec(loc1["hex"])
    loc3 = _sub_str(loc1["str"], loc2["pre"])
    video_url_string = _sub_str(loc3, _get_pos(loc3, loc2["tail"]))
    try:
        video_url = base64.b64decode(video_url_string)
    except TypeError:
        return None
    video_url = video_url.decode(errors="ignore")
    if video_url.find("http") != 0:
        return None
    return video_url


def _get_hex(arg1):
    return {"str": arg1[4:], "hex": reduce(lambda x, y: y + x, arg1[0:4])}


def _get_dec(arg1):
    loc1 = str(int(arg1, 16))
    return {"pre": [int(loc1[0]), int(loc1[1])], "tail": [int(loc1[2]), int(loc1[3])]}


def _sub_str(arg1, arg2):
    loc1 = arg1[:arg2[0]]
    loc2 = arg1[arg2[0]: arg2[0] + arg2[1]]
    return loc1 + arg1[arg2[0]:].replace(loc2, "", 1)


def _get_pos(arg1, arg2):
    arg2[0] = len(arg1) - arg2[0] - arg2[1]
    return arg2


class MeiPai(crawler.Crawler):
    def __init__(self):
        # 设置APP目录
        tool.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_VIDEO: True,
        }
        crawler.Crawler.__init__(self, sys_config)

        # 解析存档文件
        # account_id  last_video_id
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

        log.step("全部下载完毕，耗时%s秒，共计视频%s个" % (self.get_run_time(), self.total_video_count))


class Download(crawler.DownloadThread):
    def __init__(self, account_info, main_thread):
        crawler.DownloadThread.__init__(self, account_info, main_thread)
        self.account_id = self.account_info[0]
        if len(self.account_info) >= 3 and self.account_info[2]:
            self.display_name = self.account_info[2]
        else:
            self.display_name = self.account_info[0]
        self.step("开始")

    # 获取所有可下载视频
    def get_crawl_list(self):
        page_count = 1
        unique_list = []
        video_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的视频
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析第%s页视频" % page_count)

            # 获取一页视频
            try:
                video_pagination_response = get_one_page_video(self.account_id, page_count)
            except crawler.CrawlerException as e:
                self.error("第%s页视频解析失败，原因：%s" % (page_count, e.message))
                raise

            # 已经没有视频了
            if len(video_pagination_response["video_info_list"]) == 0:
                break

            self.trace("第%s页解析的全部视频：%s" % (page_count, video_pagination_response["video_info_list"]))
            self.step("第%s页解析获取%s个视频" % (page_count, len(video_pagination_response["video_info_list"])))

            # 寻找这一页符合条件的视频
            for video_info in video_pagination_response["video_info_list"]:
                # 检查是否达到存档记录
                if video_info["video_id"] > int(self.account_info[1]):
                    # 新增视频导致的重复判断
                    if video_info["video_id"] in unique_list:
                        continue
                    else:
                        video_info_list.append(video_info)
                        unique_list.append(video_info["video_id"])
                else:
                    is_over = True
                    break

            if not is_over:
                if len(video_pagination_response["video_info_list"]) >= VIDEO_COUNT_PER_PAGE:
                    page_count += 1
                else:
                    # 获取的数量小于请求的数量，已经没有剩余视频了
                    is_over = True

        return video_info_list

    # 下载单个视频
    def crawl_video(self, video_info):
        file_path = os.path.join(self.main_thread.video_download_path, self.display_name, "%010d.mp4" % video_info["video_id"])
        save_file_return = net.save_net_file(video_info["video_url"], file_path)
        if save_file_return["status"] == 1:
            self.step("视频%s下载成功" % video_info["video_id"])
        else:
            self.error("视频%s %s 下载失败，原因：%s" % (video_info["video_id"], video_info["video_url"], crawler.download_failre(save_file_return["code"])))

        # 视频下载完毕
        self.account_info[1] = str(video_info["video_id"])  # 设置存档记录
        self.total_video_count += 1  # 计数累加

    def run(self):
        try:
            # 获取所有可下载视频
            video_info_list = self.get_crawl_list()
            self.step("需要下载的全部视频解析完毕，共%s个" % len(video_info_list))

            # 从最早的视频开始下载
            while len(video_info_list) > 0:
                video_info = video_info_list.pop()
                self.step("开始下载视频%s %s" % (video_info["video_id"], video_info["video_url"]))
                self.crawl_video(video_info)
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
        self.step("下载完毕，总共获得%s个视频" % self.total_video_count)
        self.notify_main_thread()


if __name__ == "__main__":
    MeiPai().main()
