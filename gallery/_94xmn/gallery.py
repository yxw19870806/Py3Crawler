# -*- coding:UTF-8  -*-
"""
http://www.94xmn.com/
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

SUB_PATH_LIST = {
    "xiaoqingxin": "1",
    "xingganmeinv": "2",
    "siwameitui": "3",
    "ribenmeinv": "4",
    "hanguomeinv": "5",
    "xioumeinv": "6",
    "jiepai": "8",
}


# 获取指定一页的图集
def get_album_page(sub_path, page_count):
    album_pagination_url = "http://www.94xmn.com/%s/list_%s_%s.html" % (sub_path, SUB_PATH_LIST[sub_path], page_count)
    album_pagination_response = net.http_request(album_pagination_url, method="GET", header_list={"Host": "www.94xmn.com"})
    result = {
        "album_info_list": {},  # 全部图集信息
        "is_over": False,  # 是不是最后一页图集
    }
    if album_pagination_response.status == 409:
        time.sleep(5)
        return get_album_page(sub_path, page_count)
    elif album_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_pagination_response.status))
    # 页面编码
    album_pagination_html = album_pagination_response.data.decode()
    # 获取图集信息，存在两种页面样式
    album_list_selector = pq(album_pagination_html).find(".wf-main .wf-cld a")
    if album_list_selector.length == 0:
        raise crawler.CrawlerException("页面截取图集列表失败\n%s" % album_pagination_html)
    for album_index in range(0, album_list_selector.length):
        result_album_info = {
            "album_id": None,  # 图集id
            "album_title": "",  # 图集id
            "album_url": None,  # 图集地址
        }
        album_selector = album_list_selector.eq(album_index)
        # 获取图集地址
        album_url = album_selector.attr("href")
        if not album_url:
            raise crawler.CrawlerException("图集列表截取图集地址失败\n%s" % album_selector.html())
        result_album_info["album_url"] = album_url
        # 获取图集id
        # http://www.94xmn.com/plus/view.php?aid=25
        if album_url.find("/view.php?") > 0:
            album_id = album_url.split("aid=")[-1]
        else:
            album_id = album_url.split("/")[-1].split(".")[0]
        if not crawler.is_integer(album_id):
            raise crawler.CrawlerException("图集地址截取图集id失败\n%s" % album_url)
        result_album_info["album_id"] = int(album_id)
        # 获取图集标题
        album_title = album_selector.attr("title")
        if not album_title:
            raise crawler.CrawlerException("图集列表截取图集标题失败\n%s" % album_url)
        result_album_info["album_title"] = album_title
        result["album_info_list"][result_album_info["album_id"]] = result_album_info
    # 判断是不是最后一页
    max_page_count = pq(album_pagination_html).find("div.page li:last span.pageinfo strong:first").html()
    if not crawler.is_integer(max_page_count):
        raise crawler.CrawlerException("页面截取总页数失败\n%s" % album_pagination_html)
    result["is_over"] = page_count >= int(max_page_count)
    return result


# 获取图集全部图片
def get_album_photo(album_url):
    page_count = max_page_count = 1
    result = {
        "image_url_list": [],  # 全部图片地址
    }
    while page_count <= max_page_count:
        if page_count == 1:
            photo_pagination_url = album_url
        else:
            photo_pagination_url = album_url.replace(".html", "_%s.html" % page_count)
        photo_pagination_response = net.http_request(photo_pagination_url, method="GET", header_list={"Host": "www.94xmn.com"})
        if photo_pagination_response.status == 409:
            time.sleep(5)
            continue
        elif photo_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
            raise crawler.CrawlerException("第%s页" % page_count + crawler.request_failre(photo_pagination_response.status))
        photo_pagination_content = photo_pagination_response.data.decode()
        # 获取图片地址
        image_list_selector = pq(photo_pagination_content).find("div.bbox a img")
        if image_list_selector.length == 0:
            raise crawler.CrawlerException("第%s页页面匹配图片地址失败\n%s" % (page_count, photo_pagination_content))
        for image_index in range(0, image_list_selector.length):
            result["image_url_list"].append("http://www.94xmn.com" + image_list_selector.eq(image_index).attr("src"))
        # 获取总页数
        if page_count == 1:
            max_page_html = pq(photo_pagination_content).find("#fenye li:first a").html()
            if not max_page_html:
                raise crawler.CrawlerException("页面匹配总页数信息失败\n%s" % photo_pagination_content)
            max_page_count_find = re.findall("共(\d*)页: ", max_page_html)
            if len(max_page_count_find) == 0:
                raise crawler.CrawlerException("总页数信息匹配总页数失败\n%s" % photo_pagination_content)
            max_page_count = int(max_page_count_find[0])
        page_count += 1
    return result


class Gallery(crawler.Crawler):
    def __init__(self):
        # 设置APP目录
        tool.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_IMAGE: True,
            crawler.SYS_NOT_CHECK_SAVE_DATA: True,
        }
        crawler.Crawler.__init__(self, sys_config)

        # 解析存档文件
        # sub_path  last_album_id
        self.account_list = crawler.read_save_data(self.save_data_path, 0, ["", "0"])
        for sub_path in SUB_PATH_LIST:
            if sub_path not in self.account_list:
                self.account_list[sub_path] = [sub_path, "0"]

    def main(self):
        # 循环下载每个id
        main_thread_count = threading.activeCount()
        for sub_path in sorted(self.account_list.keys()):
            # 检查正在运行的线程数
            while threading.activeCount() >= self.thread_count + main_thread_count:
                self.wait_sub_thread()

            # 提前结束
            if not self.is_running():
                break

            # 开始下载
            thread = Download(self.account_list[sub_path], self)
            thread.start()

            time.sleep(1)

        # 检查除主线程外的其他所有线程是不是全部结束了
        while threading.activeCount() > main_thread_count:
            self.wait_sub_thread()

        # 未完成的数据保存
        if len(self.account_list) > 0:
            tool.write_file(tool.list_to_string(list(self.account_list.values())), self.temp_save_data_path)

        # 重新排序保存存档文件
        crawler.rewrite_save_file(self.temp_save_data_path, self.save_data_path)

        log.step("全部下载完毕，耗时%s秒，共计图片%s张" % (self.get_run_time(), self.total_image_count))


class Download(crawler.DownloadThread):
    def __init__(self, account_info, main_thread):
        crawler.DownloadThread.__init__(self, account_info, main_thread)
        self.sub_path = self.account_info[0]
        log.step(self.sub_path + " 开始")

    # 获取所有可下载图集
    def get_crawl_list(self):
        page_count = 1
        album_info_list = []
        temp_album_info_list = {}
        is_over = False
        # 获取全部图集
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            log.step(self.sub_path + " 开始解析第%s页图集" % page_count)

            # 获取一页图集
            try:
                album_response = get_album_page(self.sub_path, page_count)
            except crawler.CrawlerException as e:
                log.error(self.sub_path + " 第%s页图集解析失败，原因：%s" % (page_count, e.message))
                raise

            log.trace(self.sub_path + " 第%s页解析的全部图集：%s" % (page_count, album_response["album_info_list"]))
            log.step(self.sub_path + " 第%s页解析获取%s个图集" % (page_count, len(album_response["album_info_list"])))

            temp_album_info_list.update(album_response["album_info_list"])

            if album_response["is_over"]:
                is_over = True
            else:
                page_count += 1

        # 获取全部还未下载过需要解析的图集
        for album_id in sorted(temp_album_info_list.keys(), reverse=True):
            # 检查是否达到存档记录
            if album_id > int(self.account_info[1]):
                album_info_list.append(temp_album_info_list[album_id])
            else:
                break

        return album_info_list

    # 解析单个图集
    def crawl_album(self, album_info):
        # 获取图集全部图片
        try:
            photo_pagination_response = get_album_photo(album_info["album_url"])
        except crawler.CrawlerException as e:
            log.error(self.sub_path + " 图集%s解析失败，原因：%s" % (album_info["album_id"], e.message))
            raise

        log.trace(self.sub_path + " 图集%s《%s》 %s 解析的全部图片：%s" % (album_info["album_id"], album_info["album_title"], album_info["album_url"], photo_pagination_response["image_url_list"]))
        log.step(self.sub_path + " 图集%s《%s》 %s 解析获取%s张图片" % (album_info["album_id"], album_info["album_title"], album_info["album_url"], len(photo_pagination_response["image_url_list"])))

        image_index = 1
        # 过滤标题中不支持的字符
        album_title = path.filter_text(album_info["album_title"])
        if album_title:
            album_path = os.path.join(self.main_thread.image_download_path, "%04d %s" % (int(album_info["album_id"]), album_title))
        else:
            album_path = os.path.join(self.main_thread.image_download_path, "%04d" % int(album_info["album_id"]))
        # 设置临时目录
        self.temp_path_list.append(album_path)
        for image_url in photo_pagination_response["image_url_list"]:
            self.main_thread_check()  # 检测主线程运行状态
            log.step(self.sub_path + " 图集%s《%s》开始下载第%s张图片 %s" % (album_info["album_id"], album_info["album_title"], image_index, image_url))

            file_type = image_url.split(".")[-1]
            file_path = os.path.join(album_path, "%03d.%s" % (image_index, file_type))
            save_file_return = net.save_net_file(image_url, file_path)
            if save_file_return["status"] == 1:
                log.step(self.sub_path + " 图集%s《%s》第%s张图片下载成功" % (album_info["album_id"], album_info["album_title"], image_index))
                image_index += 1
            else:
                log.error(self.sub_path + " 图集%s《%s》 %s 第%s张图片 %s 下载失败，原因：%s" % (album_info["album_id"], album_info["album_title"], album_info["album_url"], image_index, image_url, crawler.download_failre(save_file_return["code"])))

        # 图集内图片全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.total_image_count += image_index - 1  # 计数累加
        self.account_info[1] = str(album_info["album_id"])  # 设置存档记录

    def run(self):
        try:
            # 获取所有可下载图集
            album_info_list = self.get_crawl_list()
            log.step(self.sub_path + " 需要下载的全部图集解析完毕，共%s个" % len(album_info_list))

            # 从最早的图集开始下载
            while len(album_info_list) > 0:
                album_info = album_info_list.pop()
                log.step(self.sub_path + " 开始解析%s号图集 %s" % (album_info["album_id"], album_info["album_url"]))
                self.crawl_album(album_info)
                self.main_thread_check()  # 检测主线程运行状态
        except SystemExit as se:
            if se.code == 0:
                log.step(self.sub_path + " 提前退出")
            else:
                log.error(self.sub_path + " 异常退出")
            # 如果临时目录变量不为空，表示某个图集正在下载中，需要把下载了部分的内容给清理掉
            self.clean_temp_path()
        except Exception as e:
            log.error(self.sub_path + " 未知异常")
            log.error(str(e) + "\n" + traceback.format_exc())

        # 保存最后的信息
        with self.thread_lock:
            tool.write_file("\t".join(self.account_info), self.main_thread.temp_save_data_path)
            self.main_thread.total_image_count += self.total_image_count
            self.main_thread.account_list.pop(self.sub_path)
        log.step(self.sub_path + " 下载完毕，总共获得%s张图片" % self.total_image_count)
        self.notify_main_thread()


if __name__ == "__main__":
    Gallery().main()
