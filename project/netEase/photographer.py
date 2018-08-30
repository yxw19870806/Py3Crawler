# -*- coding:UTF-8  -*-
"""
网易摄影图片爬虫
http://pp.163.com/square/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import re
import threading
import time
import traceback
from pyquery import PyQuery as pq
from common import *


# 获取账号主页
def get_account_index_page(account_name):
    account_index_url = "http://%s.pp.163.com/" % account_name
    account_index_response = net.http_request(account_index_url, method="GET")
    result = {
        "album_url_list": [],  # 全部相册地址
    }
    if account_index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(account_index_response.status))
    # 页面编码
    account_index_response_content = account_index_response.data.decode("GBK", errors="ignore")
    if account_index_response_content.find("<title>该页面不存在</title>") >= 0:
        raise crawler.CrawlerException("账号不存在")
    # 获取全部相册地址
    album_result_selector = pq(account_index_response_content).find("#p_contents li")
    if album_result_selector.length == 0:
        raise crawler.CrawlerException("页面匹配相册列表失败\n%s" % account_index_response_content)
    for album_index in range(0, album_result_selector.length):
        result["album_url_list"].append(album_result_selector.eq(album_index).find("a.detail").attr("href"))
    return result


# 解析相册id
def get_album_id(album_url):
    album_id = tool.find_sub_string(album_url, "pp/", ".html")
    if crawler.is_integer(album_id):
        return album_id
    return None


# 获取相册页
def get_album_page(album_url):
    album_response = net.http_request(album_url, method="GET")
    result = {
        "album_title": "",  # 相册标题
        "photo_url_list": [],  # 全部图片地址
    }
    if album_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_response.status))
    album_response_content = album_response.data.decode("GBK", errors="ignore")
    # 获取相册标题
    album_title = tool.find_sub_string(album_response_content, '<h2 class="picset-title" id="p_username_copy">', "</h2>").strip()
    if album_title:
        result["album_title"] = album_title
    # 获取图片地址
    result["photo_url_list"] = re.findall('data-lazyload-src="([^"]*)"', album_response_content)
    if len(result["photo_url_list"]) == 0:
        raise crawler.CrawlerException("页面匹配图片地址失败\n%s" % album_response_content)
    return result


class Photographer(crawler.Crawler):
    def __init__(self):
        # 设置APP目录
        tool.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
        }
        crawler.Crawler.__init__(self, sys_config)

        # 解析存档文件
        # account_id last_album_id
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
            tool.write_file(tool.list_to_string(list(self.account_list.values())), self.temp_save_data_path)

        # 重新排序保存存档文件
        crawler.rewrite_save_file(self.temp_save_data_path, self.save_data_path)

        log.step("全部下载完毕，耗时%s秒，共计图片%s张" % (self.get_run_time(), self.total_photo_count))


class Download(crawler.DownloadThread):
    def __init__(self, account_info, main_thread):
        crawler.DownloadThread.__init__(self, account_info, main_thread)
        self.account_name = self.account_info[0]
        self.display_name = self.account_name
        self.step("开始")

    # 获取所有可下载相册
    def get_crawl_list(self):
        # 获取主页
        try:
            account_index_response = get_account_index_page(self.account_name)
        except crawler.CrawlerException as e:
            self.error("主页解析失败，原因：%s" % e.message)
            raise

        self.trace("解析的全部相册：%s" % account_index_response["album_url_list"])
        self.step("解析获取%s个相册" % len(account_index_response["album_url_list"]))

        album_url_list = []
        # 获取全部还未下载过需要解析的相册
        for album_url in account_index_response["album_url_list"]:
            # 获取相册id
            album_id = get_album_id(album_url)
            if album_id is None:
                self.error("相册地址%s解析相册id失败" % album_url)
                tool.process_exit()

            # 检查是否达到存档记录
            if int(album_id) > int(self.account_info[1]):
                album_url_list.append(album_url)
            else:
                break

        return album_url_list

    # 解析单个相册
    def crawl_album(self, album_url):
        try:
            album_response = get_album_page(album_url)
        except crawler.CrawlerException as e:
            self.error("相册%s解析失败，原因：%s" % (album_url, e.message))
            raise

        self.trace("相册%s解析的全部图片：%s" % (album_url, album_response["photo_url_list"]))
        self.step("相册%s解析获取%s张图片" % (album_url, len(album_response["photo_url_list"])))

        photo_index = 1
        album_id = get_album_id(album_url)
        # 过滤标题中不支持的字符
        album_title = path.filter_text(album_response["album_title"])
        if album_title:
            album_path = os.path.join(self.main_thread.photo_download_path, self.account_name, "%s %s" % (album_id, album_title))
        else:
            album_path = os.path.join(self.main_thread.photo_download_path, self.account_name, str(album_id))
        self.temp_path_list.append(album_path)
        for photo_url in album_response["photo_url_list"]:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("相册%s《%s》开始下载第%s张图片 %s" % (album_id, album_response["album_title"], photo_index, photo_url))

            file_path = os.path.join(album_path, "%03d.%s" % (photo_index, net.get_file_type(photo_url)))
            save_file_return = net.save_net_file(photo_url, file_path)
            if save_file_return["status"] == 1:
                self.step("相册%s《%s》第%s张图片下载成功" % (album_id, album_response["album_title"], photo_index))
                photo_index += 1
            else:
                self.error("相册%s《%s》第%s张图片 %s 下载失败，原因：%s" % (album_id, album_response["album_title"], photo_index, photo_url, crawler.download_failre(save_file_return["code"])))

        # 相册内图片全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.total_photo_count += photo_index - 1  # 计数累加
        self.account_info[1] = album_id  # 设置存档记录

    def run(self):
        try:
            # 获取所有可下载相册
            album_url_list = self.get_crawl_list()
            self.step("需要下载的全部相册解析完毕，共%s个" % len(album_url_list))

            # 从最早的相册开始下载
            while len(album_url_list) > 0:
                album_url = album_url_list.pop()
                self.step("开始解析第相册%s" % get_album_id(album_url))
                self.crawl_album(album_url)
                self.main_thread_check()  # 检测主线程运行状态
        except SystemExit as se:
            if se.code == 0:
                self.step("提前退出")
            else:
                self.error("异常退出")
            # 如果临时目录变量不为空，表示某个相册正在下载中，需要把下载了部分的内容给清理掉
            self.clean_temp_path()
        except Exception as e:
            self.error("未知异常")
            self.error(str(e) + "\n" + traceback.format_exc(), False)

        # 保存最后的信息
        with self.thread_lock:
            tool.write_file("\t".join(self.account_info), self.main_thread.temp_save_data_path)
            self.main_thread.total_photo_count += self.total_photo_count
            self.main_thread.account_list.pop(self.account_name)
        self.step("下载完毕，总共获得%s张图片" % self.total_photo_count)
        self.notify_main_thread()


if __name__ == "__main__":
    Photographer().main()
