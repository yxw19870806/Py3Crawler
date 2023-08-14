# -*- coding:UTF-8  -*-
"""
站酷图片爬虫
https://hodakwo.zcool.com.cn/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from pyquery import PyQuery as pq
from common import *


# 获取指定页数的全部作品
def get_one_page_album(account_name, page_count):
    # https://www.zcool.com.cn/u/17050872?myCate=0&sort=8&p=2
    if tool.is_integer(account_name):
        album_pagination_url = "https://www.zcool.com.cn/u/%s" % account_name
    else:
        album_pagination_url = "https://%s.zcool.com.cn/" % account_name
    query_data = {
        "myCate": "0",
        "sort": "8",  # 按时间倒叙
        "p": page_count,
    }
    album_pagination_response = net.Request(album_pagination_url, method="GET", fields=query_data)
    result = {
        "album_info_list": [],  # 全部作品信息
        "is_over": False,  # 是否最后页
    }
    if page_count == 1 and album_pagination_response.status == 404:
        raise CrawlerException("账号不存在")
    elif album_pagination_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(album_pagination_response.status))
    album_list_selector = pq(album_pagination_response.content).find(".work-list-box .card-box")
    for album_index in range(album_list_selector.length):
        result_album_info = {
            "album_id": "",  # 作品id
            "album_title": "",  # 作品标题
            "album_time": "",  # 作品创建时间
        }
        album_selector = album_list_selector.eq(album_index)
        # 获取作品id
        album_url = album_selector.find(".card-img>a").attr("href")
        if not album_url:
            raise CrawlerException("作品信息截取作品地址失败\n" + album_selector.html())
        # 文章
        if album_url.find("www.zcool.com.cn/article/") > 0:
            continue
        album_id = tool.find_sub_string(album_url, "/work/", ".html")
        if not album_id:
            raise CrawlerException("作品地址截取作品id失败\n" + album_selector.html())
        result_album_info["album_id"] = album_id
        # 获取作品标题
        album_title = album_selector.find(".card-img>a").attr("title")
        if not album_title:
            raise CrawlerException("作品信息截取作品标题失败\n" + album_selector.html())
        result_album_info["album_title"] = album_title
        # 获取作品创建日期
        album_time_text = album_selector.find(".card-item>span").attr("title")
        if not album_time_text:
            raise CrawlerException("作品信息截取作品日期信息失败\n" + album_selector.html())
        album_time_string = tool.find_sub_string(album_time_text, "创建时间：")
        if not album_time_string:
            raise CrawlerException("作品日期信息%s截取作品发布日期失败" % album_time_text)
        try:
            result_album_info["album_time"] = tool.convert_formatted_time_to_timestamp(album_time_string, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise CrawlerException("作品发布日期%s的格式不正确" % album_time_string)
        result["album_info_list"].append(result_album_info)
    result["is_over"] = album_list_selector.length == 0
    return result


# 获取作品
def get_album_page(album_id):
    album_url = "https://www.zcool.com.cn/work/%s.html" % album_id
    album_response = net.Request(album_url, method="GET")
    result = {
        "photo_url_list": [],  # 全部图片地址
    }
    if album_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(album_response.status))
    photo_list_selector = pq(album_response.content).find(".work-show-box .reveal-work-wrap img")
    if photo_list_selector.length == 0:
        raise CrawlerException("页面截取图片列表失败\n" + album_response.content)
    for photo_index in range(photo_list_selector.length):
        result["photo_url_list"].append(photo_list_selector.eq(photo_index).attr("src"))
    return result


# 去除指定分辨率
# https://img.zcool.cn/community/011d1d592bae06b5b3086ed41bf15f.jpg@1280w_1l_2o_100sh.jpg
# ->
# https://img.zcool.cn/community/011d1d592bae06b5b3086ed41bf15f.jpg
def get_photo_url(photo_url):
    return photo_url.split("@")[0]


class ZCool(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            const.SysConfigKey.DOWNLOAD_PHOTO: True,
            const.SysConfigKey.SAVE_DATA_FORMATE: (0, ["", "0"]),  # account_name  last_album_time
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 下载线程
        self.set_crawler_thread(CrawlerThread)


class CrawlerThread(crawler.CrawlerThread):
    def __init__(self, main_thread, single_save_data):
        self.index_key = single_save_data[0]  # account name
        if len(single_save_data) >= 3 and single_save_data[2]:
            self.display_name = single_save_data[2]
        else:
            self.display_name = single_save_data[0]
        crawler.CrawlerThread.__init__(self, main_thread, single_save_data)

    # 获取所有可下载作品
    def get_crawl_list(self):
        page_count = 1
        unique_list = []
        album_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的作品
        while not is_over:
            album_pagination_description = "第%s页作品" % page_count
            self.start_parse(album_pagination_description)
            try:
                album_pagination_response = get_one_page_album(self.index_key, page_count)
            except CrawlerException as e:
                self.error(e.http_error(album_pagination_description))
                raise
            self.parse_result(album_pagination_description, album_pagination_response["album_info_list"])

            # 寻找这一页符合条件的作品
            for album_info in album_pagination_response["album_info_list"]:
                # 检查是否达到存档记录
                if album_info["album_time"] > int(self.single_save_data[1]):
                    # 新增作品导致的重复判断
                    if album_info["album_id"] in unique_list:
                        continue
                    else:
                        album_info_list.append(album_info)
                        unique_list.append(album_info["album_id"])
                else:
                    is_over = True
                    break

            if not is_over:
                if album_pagination_response["is_over"]:
                    is_over = True
                else:
                    page_count += 1

        return album_info_list

    # 解析单个作品
    def crawl_album(self, album_info):
        album_description = "作品%s《%s》" % (album_info["album_id"], album_info["album_title"])
        self.start_parse(album_description)
        try:
            album_response = get_album_page(album_info["album_id"])
        except CrawlerException as e:
            self.error(e.http_error(album_description))
            raise
        self.parse_result(album_description, album_response["photo_url_list"])

        photo_index = 1
        album_name = "%s %s" % (album_info["album_id"], album_info["album_title"])
        album_path = os.path.join(self.main_thread.photo_download_path, self.index_key, album_name)
        self.temp_path_list.append(album_path)
        for photo_url in album_response["photo_url_list"]:
            photo_url = get_photo_url(photo_url)
            photo_path = os.path.join(album_path, "%02d.%s" % (photo_index, url.get_file_ext(photo_url)))
            photo_description = "作品%s《%s》第%s张图片" % (album_info["album_id"], album_info["album_title"], photo_index)
            if self.download(photo_url, photo_path, photo_description):
                self.total_photo_count += 1  # 计数累加
            photo_index += 1

        # 作品内图片全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.single_save_data[1] = str(album_info["album_time"])  # 设置存档记录

    def _run(self):
        # 获取所有可下载作品
        album_info_list = self.get_crawl_list()
        self.info("需要下载的全部作品解析完毕，共%s个" % len(album_info_list))

        # 从最早的作品开始下载
        while len(album_info_list) > 0:
            self.crawl_album(album_info_list.pop())


if __name__ == "__main__":
    ZCool().main()
