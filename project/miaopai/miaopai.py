# -*- coding:UTF-8  -*-
"""
秒拍视频爬虫
https://www.miaopai.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import re
import time
import traceback
from common import *


# 获取用户的suid，作为查找指定用户的视频页的凭证
# account_id -> mi9wmdhhof
def get_account_index_page(account_id):
    account_index_url = "https://www.miaopai.com/u/paike_%s/relation/follow.htm" % account_id
    account_index_response = net.http_request(account_index_url, method="GET")
    result = {
        "user_id": None,  # 账号user id
    }
    if account_index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(account_index_response.status))
    account_index_response_content = account_index_response.data.decode(errors="ignore")
    user_id = tool.find_sub_string(account_index_response_content, '<button class="guanzhu gz" suid="', '" heade="1" token="')
    if not user_id:
        raise crawler.CrawlerException("页面截取user id失败\n%s" % account_index_response_content)
    result["user_id"] = user_id
    return result


# 获取指定页数的全部视频
# suid -> 0r9ewgQ0v7UoDptu
def get_one_page_video(suid, page_count):
    # https://www.miaopai.com/gu/u?page=1&suid=0r9ewgQ0v7UoDptu&fen_type=channel
    video_pagination_url = "https://www.miaopai.com/gu/u"
    query_data = {
        "page": page_count,
        "suid": suid,
        "fen_type": "channel",
    }
    video_pagination_response = net.http_request(video_pagination_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "is_over": False,  # 是否最后一页视频
        "video_id_list": [],  # 全部视频id
    }
    if video_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_pagination_response.status))
    # 判断是不是最后一页
    result["is_over"] = crawler.get_json_value(video_pagination_response.json_data, "isall", type_check=bool)
    # 获取全部视频id
    result["video_id_list"] = re.findall('data-scid="([^"]*)"', crawler.get_json_value(video_pagination_response.json_data, "msg", type_check=str))
    if not result["is_over"] and len(result["video_id_list"]) == 0:
        raise crawler.CrawlerException("页面匹配视频id失败\n%s" % video_pagination_response.json_data)
    return result


# 获取指定id视频的详情页
def get_video_info_page(video_id):
    video_info_url = "https://gslb.miaopai.com/stream/%s.json" % video_id
    query_data = {"token": ""}
    video_info_response = net.http_request(video_info_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "video_url": None,  # 视频地址
    }
    if video_info_response.status == 403:
        return get_video_info_page_new(video_id)
    elif video_info_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_info_response.status))
    # 获取视频地址
    for video_info in crawler.get_json_value(video_info_response.json_data, "result", type_check=list):
        result["video_url"].append(crawler.get_json_value(video_info, "scheme", type_check=str) + crawler.get_json_value(video_info, "host", type_check=str) + crawler.get_json_value(video_info, "path", type_check=str))
        break
    else:
        raise crawler.get_json_value("返回信息截取视频地址失败\n%s" % video_info_response.json_data)
    return result


# 获取指定id视频的详情页（新版本API）
def get_video_info_page_new(video_id):
    # https://n.miaopai.com/api/aj_media/info.json?smid=k3l02GEPFQqCnn1bkT5S6jD0-~m8ekb6
    video_info_url = "https://n.miaopai.com/api/aj_media/info.json"
    query_data = {"smid": video_id}
    result = {
        "video_url": None,  # 视频地址
    }
    video_info_response = net.http_request(video_info_url, method="GET", fields=query_data, json_decode=True, is_gzip=False)
    if video_info_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_info_response.status))
    result["video_url"] = crawler.get_json_value(video_info_response.json_data, "data", "meta_data", 0, "play_urls", "n", type_check=str)
    return result


class MiaoPai(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_VIDEO: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 解析存档文件
        # account_id  video_count  last_video_url
        self.account_list = crawler.read_save_data(self.save_data_path, 0, ["", "0", "", ""])

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
        if len(self.account_info) >= 4 and self.account_info[3]:
            self.display_name = self.account_info[3]
        else:
            self.display_name = self.account_info[0]
        self.step("开始")

    # 获取所有可下载视频
    def get_crawl_list(self, user_id):
        page_count = 1
        video_id_list = []
        is_over = False
        # 获取全部还未下载过需要解析的视频
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析第%s页视频" % page_count)

            # 获取指定一页的视频信息
            try:
                video_pagination_response = get_one_page_video(user_id, page_count)
            except crawler.CrawlerException as e:
                self.error("第%s页视频解析失败，原因：%s" % (page_count, e.message))
                raise

            self.trace("第%s页解析的全部视频：%s" % (page_count, video_pagination_response["video_id_list"]))
            self.step("第%s页解析获取%s个视频" % (page_count, len(video_pagination_response["video_id_list"])))

            # 寻找这一页符合条件的视频
            for video_id in video_pagination_response["video_id_list"]:
                # 检查是否达到存档记录
                if video_id != self.account_info[2]:
                    # 新增视频导致的重复判断
                    if video_id in video_id_list:
                        continue
                    else:
                        video_id_list.append(video_id)
                else:
                    is_over = True
                    break

            # 没有视频了
            if video_pagination_response["is_over"]:
                if self.account_info[2] != "":
                    self.error("没有找到上次下载的最后一个视频地址")
                is_over = True
            else:
                page_count += 1
        return video_id_list

    # 解析单个视频
    def crawl_video(self, video_id):
        video_index = int(self.account_info[1]) + 1
        self.step("开始解析第%s个视频 %s" % (video_index, video_id))

        # 获取视频下载地址
        try:
            video_info_response = get_video_info_page(video_id)
        except crawler.CrawlerException as e:
            self.error("视频%s解析失败，原因：%s" % (video_id, e.message))
            raise

        file_path = os.path.join(self.main_thread.video_download_path, self.display_name, "%04d.mp4" % video_index)
        self.step("开始下载第%s个视频 %s" % (video_index, video_info_response["video_url"]))

        save_file_return = net.save_net_file(video_info_response["video_url"], file_path)
        if save_file_return["status"] == 1:
            self.step("第%s个视频下载成功" % video_index)
        else:
            self.error("第%s个视频 %s 下载失败，原因：%s" % (video_index, video_info_response["video_url"], crawler.download_failre(save_file_return["code"])))

        # 视频下载完毕
        self.account_info[1] = str(video_index)  # 设置存档记录
        self.account_info[2] = video_id  # 设置存档记录
        self.total_video_count += 1  # 计数累加

    def run(self):
        try:
            try:
                account_index_response = get_account_index_page(self.account_id)
            except crawler.CrawlerException as e:
                self.error("首页解析失败，原因：%s" % e.message)
                raise

            # 获取所有可下载视频
            video_id_list = self.get_crawl_list(account_index_response["user_id"])
            self.step("需要下载的全部视频解析完毕，共%s个" % len(video_id_list))

            # 从最早的视频开始下载
            while len(video_id_list) > 0:
                self.crawl_video(video_id_list.pop())
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
    MiaoPai().main()
