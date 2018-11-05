# -*- coding:UTF-8  -*-
"""
Vine视频爬虫
https://vine.co/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import time
import traceback
from common import *


# 获取用户首页
def get_account_index_page(account_id):
    if not crawler.is_integer(account_id):
        # 获取账号id
        account_vanity_url = "https://vine.co/api/users/profiles/vanity/%s" % account_id
        account_vanity_response = net.http_request(account_vanity_url, method="GET", json_decode=True)
        if account_vanity_response.status == 404:
            raise crawler.CrawlerException("账号不存在")
        elif account_vanity_response.status != net.HTTP_RETURN_CODE_SUCCEED:
            raise crawler.CrawlerException("账号ID页，%s" % crawler.request_failre(account_vanity_response.status))
        account_id = crawler.get_json_value(account_vanity_response.json_data, "data", "userIdStr", type_check=str)
    # 获取账号详情
    account_profile_url = "https://archive.vine.co/profiles/%s.json" % account_id
    result = {
        "video_id_list": [],  # 全部日志id
    }
    account_profile_response = net.http_request(account_profile_url, method="GET", json_decode=True)
    if account_profile_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException("账号详情页，%s" % crawler.request_failre(account_profile_response.status))
    if crawler.get_json_value(account_profile_response.json_data, "private", type_check=int) != 0:
        raise crawler.CrawlerException("账号详情页非公开\n%s" % account_profile_response.json_data)
    result["video_id_list"] = crawler.get_json_value(account_profile_response.json_data, "posts", type_check=list)
    return result


# 获取指定日志
def get_video_info_page(video_id):
    # https://archive.vine.co/posts/iUQV3w3mJMV.json
    video_info_url = "https://archive.vine.co/posts/%s.json" % video_id
    video_info_response = net.http_request(video_info_url, method="GET", json_decode=True)
    result = {
        "is_skip": False,  # 是否需要跳过
        "video_url": None,  # 视频地址
        "video_id": 0,  # 视频id（数字）
    }
    if video_info_response.status == 403:
        result["is_skip"] = True
    elif video_info_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_info_response.status))
    # 获取视频地址
    result["video_url"] = crawler.get_json_value(video_info_response.json_data, "videoUrl", type_check=str)
    # 获取视频id（数字）
    result["video_id"] = crawler.get_json_value(video_info_response.json_data, "postId", type_check=int)
    return result


class Vine(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_VIDEO: True,
            crawler.SYS_SET_PROXY: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 解析存档文件
        # account_id  video_count video_string_id  video_number_id
        self.account_list = crawler.read_save_data(self.save_data_path, 0, ["", "0", "", "0"])

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
    is_find = False  # 是不是有找到上次存档文件所指的视频id

    def __init__(self, account_info, main_thread):
        crawler.DownloadThread.__init__(self, account_info, main_thread)
        self.account_id = self.account_info[0]
        if len(self.account_info) >= 5 and self.account_info[4]:
            self.display_name = self.account_info[4]
        else:
            self.display_name = self.account_info[0]
        self.step("开始")

    # 获取所有可下载视频
    def get_crawl_list(self):
        # 获取账号信息，包含全部视频
        try:
            account_index_page_response = get_account_index_page(self.account_id)
        except crawler.CrawlerException as e:
            self.error("账号首页解析失败，原因：%s" % e.message)
            raise

        self.trace("解析的全部视频：%s" % account_index_page_response["video_id_list"])
        self.step("解析获取%s个视频" % len(account_index_page_response["video_id_list"]))

        video_id_list = []
        # 是否有根据视频id找到上一次的记录
        if self.account_info[2] == "":
            self.is_find = True
        # 寻找符合条件的视频
        for video_id in account_index_page_response["video_id_list"]:
            # 检查是否达到存档记录
            if video_id > self.account_info[2]:
                video_id_list.append(video_id)
            else:
                self.is_find = True
                break

        return video_id_list

    # 解析单个视频
    def crawl_video(self, video_id):
        self.step("开始解析视频%s" % video_id)

        # 获取指定视频信息
        try:
            video_response = get_video_info_page(video_id)
        except crawler.CrawlerException as e:
            self.error("视频%s解析失败，原因：%s" % (video_id, e.message))
            raise

        # 是否需要跳过，比如没有权限访问
        if video_response["is_skip"]:
            self.step("视频%s跳过" % video_id)
            return

        # 如果解析需要下载的视频时没有找到上次的记录，表示存档所在的视频已被删除，则判断数字id
        if not self.is_find:
            if video_response["video_id"] < int(self.account_info[3]):
                self.step("视频%s跳过" % video_id)
                return
            else:
                self.is_find = True

        video_index = int(self.account_info[1]) + 1
        self.step("开始下载第%s个视频 %s" % (video_index, video_response["video_url"]))

        video_file_path = os.path.join(self.main_thread.video_download_path, self.display_name, "%019d.%s" % (video_response["video_id"], net.get_file_type(video_response["video_url"])))
        save_file_return = net.save_net_file(video_response["video_url"], video_file_path)
        if save_file_return["status"] == 1:
            # 设置临时目录
            self.step("视频%s %s下载成功" % (video_id, video_response["video_id"]))
        else:
            self.error("视频%s %s %s 下载失败，原因：%s" % (video_id, video_response["video_id"], video_response["video_url"], crawler.download_failre(save_file_return["code"])))

        # 媒体内图片和视频全部下载完毕
        self.total_video_count += 1  # 计数累加
        self.account_info[1] = str(video_index)  # 设置存档记录
        self.account_info[2] = video_id  # 设置存档记录
        self.account_info[3] = str(video_response["video_id"])  # 设置存档记录

    def run(self):
        try:
            # 获取所有可下载视频
            video_id_list = self.get_crawl_list()
            self.step("需要下载的全部视频解析完毕，共%s个" % len(video_id_list))
            if not self.is_find:
                self.step("存档所在视频已删除，需要在下载时进行过滤")

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
    Vine().main()
