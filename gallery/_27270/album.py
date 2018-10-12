# -*- coding:UTF-8  -*-
"""
http://www.27270.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import json
import os
import time
import traceback
from pyquery import PyQuery as pq
from common import *

SUB_PATH_LIST = {
    "ent/lianglimeimo": "12",
    "ent/meinvtupian": "11",
    "ent/rentiyishu": "32",
    "game/cosplaymeitu": "20",
}
CACHE_FILE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "cache"))


# 获取图集首页
def get_one_page_album(sub_path, page_count):
    album_pagination_url = "http://www.27270.com/%s/list_%s_%s.html" % (sub_path, SUB_PATH_LIST[sub_path], page_count)
    album_pagination_response = net.http_request(album_pagination_url, method="GET", is_auto_redirect=False)
    result = {
        "album_info_list": {},  # 全部图集信息
        "is_over": False,  # 是否最后一页图集
    }
    if album_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_pagination_response.status))
    album_pagination_response_content = album_pagination_response.data.decode("GBK", errors="ignore")
    album_list_selector = pq(album_pagination_response_content).find(".MeinvTuPianBox ul li")
    # 另一种样式
    if album_list_selector.length == 0:
        album_list_selector = pq(album_pagination_response_content).find("ul.pic_list li")
    if album_list_selector.length == 0:
        raise crawler.CrawlerException("页面截取图集列表失败\n%s" % album_pagination_response_content)
    for album_index in range(0, album_list_selector.length):
        result_album_info = {
            "album_id": None,  # 图集id
            "album_title": "",  # 图集id
            "album_url": None,  # 图集地址
        }
        album_selector = album_list_selector.eq(album_index)
        # 获取图集地址
        album_url = album_selector.children("a").attr("href")
        if not album_url:
            raise crawler.CrawlerException("图集列表截取图集地址失败\n%s" % album_selector.html())
        result_album_info["album_url"] = album_url
        # 获取图集id
        # http://www.27270.com/game/cosplaymeitu/2017/172714.html
        album_id = album_url.split("/")[-1].split(".")[0]
        if not crawler.is_integer(album_id):
            raise crawler.CrawlerException("图集地址截取图集id失败\n%s" % album_url)
        result_album_info["album_id"] = int(album_id)
        # 获取图集标题
        album_title = album_selector.children("a").attr("title")
        if not album_title:
            raise crawler.CrawlerException("图集列表截取图集标题失败\n%s" % album_url)
        result_album_info["album_title"] = album_title
        result["album_info_list"][result_album_info["album_id"]] = result_album_info
    # 判断是不是最后一页
    result["is_over"] = pq(album_pagination_response_content).find("div.NewPages li:last a").attr("href") is None
    return result


# 获取指定图集
def get_album_page(album_url, album_id):
    page_count = 1
    result = {
        "photo_url_list": [],  # 全部图片地址
    }
    while True:
        if page_count == 1:
            pagination_album_url = album_url
        else:
            pagination_album_url = album_url.replace(".html", "_%s.html" % page_count)
        album_response = net.http_request(pagination_album_url, method="GET")
        if album_response.status != net.HTTP_RETURN_CODE_SUCCEED:
            raise crawler.CrawlerException("第%s页" % page_count + crawler.request_failre(album_response.status))
        album_response_content = album_response.data.decode("GBK", errors="ignore")
        # 获取图片地址
        photo_list_selector = pq(album_response_content).find("#picBody a img")
        if photo_list_selector.length == 0:
            raise crawler.CrawlerException("第%s页页面匹配图片地址失败\n%s" % (page_count, album_response_content))
        for photo_index in range(0, photo_list_selector.length):
            result["photo_url_list"].append(photo_list_selector.eq(photo_index).attr("src"))
        next_page_url_path = pq(album_response_content).find(".page-tag #nl a").attr("href")
        # 判断是不是最后一页
        if next_page_url_path == "%s_%s.html" % (album_id, page_count + 1):
            page_count += 1
        elif next_page_url_path == "##":
            break
        else:
            raise crawler.CrawlerException("第%s页页面截取下一页地址失败\n%s" % (page_count, album_response_content))
    return result


class Album(crawler.Crawler):
    def __init__(self):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
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
        thread_list = []
        for sub_path in sorted(self.account_list.keys()):
            # 提前结束
            if not self.is_running():
                break

            # 开始下载
            thread = Download(self.account_list[sub_path], self)
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

        log.step("全部下载完毕，耗时%s秒，共计图片%s张" % (self.get_run_time(), self.total_photo_count))


class Download(crawler.DownloadThread):
    def __init__(self, account_info, main_thread):
        crawler.DownloadThread.__init__(self, account_info, main_thread)
        self.sub_path = self.account_info[0]
        self.display_name = self.sub_path
        self.step("开始")

    # 获取所有可下载图集
    def get_crawl_list(self):
        album_info_list = []
        album_id_to_url_list = {}
        # 从缓存文件中读取
        cache_file_path = os.path.join(CACHE_FILE_DIR, "%s.json" % SUB_PATH_LIST[self.sub_path])
        cache_album_id_to_url_list = tool.json_decode(file.read_file(cache_file_path))
        if cache_album_id_to_url_list is None:
            page_count = 1
            is_over = False
            # 获取全部图集
            while not is_over:
                self.main_thread_check()  # 检测主线程运行状态
                self.step("开始解析第%s页图集" % page_count)

                # 获取一页图集
                try:
                    album_response = get_one_page_album(self.sub_path, page_count)
                except crawler.CrawlerException as e:
                    self.error("第%s页图集解析失败，原因：%s" % (page_count, e.message))
                    raise

                self.trace("第%s页解析的全部图集：%s" % (page_count, album_response["album_info_list"]))
                self.step("第%s页解析获取%s个图集" % (page_count, len(album_response["album_info_list"])))

                album_id_to_url_list.update(album_response["album_info_list"])

                if album_response["is_over"]:
                    is_over = True
                else:
                    page_count += 1

            # 保存到缓存文件中
            file.write_file(json.dumps(album_id_to_url_list), cache_file_path, file.WRITE_FILE_TYPE_REPLACE)
        else:
            # 写入文件后key变成string类型了
            for temp in cache_album_id_to_url_list:
                album_id_to_url_list[int(temp)] = cache_album_id_to_url_list[temp]

        # 获取全部还未下载过需要解析的图集
        for album_id in sorted(album_id_to_url_list.keys(), reverse=True):
            # 检查是否达到存档记录
            if album_id > int(self.account_info[1]):
                album_info_list.append(album_id_to_url_list[album_id])
            else:
                break

        return album_info_list

    # 解析单个图集
    def crawl_album(self, album_info):
        # 获取图集全部图片
        try:
            album_response = get_album_page(album_info["album_url"], album_info["album_id"])
        except crawler.CrawlerException as e:
            self.error("图集%s解析失败，原因：%s" % (album_info["album_url"], e.message))
            raise

        self.trace("图集%s《%s》 %s 解析的全部图片：%s" % (album_info["album_id"], album_info["album_title"], album_info["album_url"], album_response["photo_url_list"]))
        self.step("图集%s《%s》 %s 解析获取%s张图片" % (album_info["album_id"], album_info["album_title"], album_info["album_url"], len(album_response["photo_url_list"])))

        photo_index = 1
        # 过滤标题中不支持的字符
        album_path = os.path.join(self.main_thread.photo_download_path, "%06d %s" % (album_info["album_id"], path.filter_text(album_info["album_title"])))
        # 设置临时目录
        self.temp_path_list.append(album_path)
        for photo_url in album_response["photo_url_list"]:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("图集%s《%s》开始下载第%s张图片 %s" % (album_info["album_id"], album_info["album_title"], photo_index, photo_url))

            file_path = os.path.join(album_path, "%03d.%s" % (photo_index, net.get_file_type(photo_url)))
            save_file_return = net.save_net_file(photo_url, file_path)
            if save_file_return["status"] == 1:
                self.step("图集%s《%s》第%s张图片下载成功" % (album_info["album_id"], album_info["album_title"], photo_index))
            else:
                self.error("图集%s《%s》 %s 第%s张图片 %s 下载失败，原因：%s" % (album_info["album_id"], album_info["album_title"], album_info["album_url"], photo_index, photo_url, crawler.download_failre(save_file_return["code"])))
            photo_index += 1

        # 图集内图片全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.total_photo_count += photo_index - 1  # 计数累加
        self.account_info[1] = str(album_info["album_id"])  # 设置存档记录

    def run(self):
        try:
            # 获取所有可下载图集
            album_info_list = self.get_crawl_list()
            self.step("需要下载的全部图集解析完毕，共%s个" % len(album_info_list))

            # 从最早的图集开始下载
            while len(album_info_list) > 0:
                album_info = album_info_list.pop()
                self.step("开始解析图集%s %s" % (album_info["album_id"], album_info["album_url"]))
                self.crawl_album(album_info)
                self.main_thread_check()  # 检测主线程运行状态
        except SystemExit as se:
            if se.code == 0:
                self.step("提前退出")
            else:
                self.error("异常退出")
            # 如果临时目录变量不为空，表示某个图集正在下载中，需要把下载了部分的内容给清理掉
            self.clean_temp_path()
        except Exception as e:
            self.error("未知异常")
            self.error(str(e) + "\n" + traceback.format_exc(), False)

        # 保存最后的信息
        with self.thread_lock:
            # file.write_file("\t".join(self.account_info), self.main_thread.temp_save_data_path)
            self.main_thread.total_photo_count += self.total_photo_count
            self.main_thread.account_list.pop(self.sub_path)
        self.step("下载完毕，总共获得%s张图片" % self.total_photo_count)
        self.notify_main_thread()


if __name__ == "__main__":
    Album().main()
