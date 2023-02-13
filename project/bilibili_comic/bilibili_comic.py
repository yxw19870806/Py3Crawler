# -*- coding:UTF-8  -*-
"""
bilibili漫画爬虫
https://manga.bilibili.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from common import *

COOKIE_INFO = {}


# 检测是否已登录
def check_login():
    api_url = "https://api.bilibili.com/x/web-interface/nav"
    api_response = net.request(api_url, method="GET", cookies_list=COOKIE_INFO, json_decode=True)
    if api_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        return crawler.get_json_value(api_response.json_data, "data", "isLogin", type_check=bool)
    return False


def get_comic_index_page(comic_id):
    # https://manga.bilibili.com/detail/mc24742
    api_url = "https://manga.bilibili.com/twirp/comic.v1.Comic/ComicDetail?device=pc&platform=web"
    post_data = {
        "comic_id": comic_id
    }
    api_response = net.request(api_url, method="POST", fields=post_data, cookies_list=COOKIE_INFO, json_decode=True)
    result = {
        "comic_info_list": {},  # 漫画列表信息
    }
    if api_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(api_response.status))
    for ep_info in crawler.get_json_value(api_response.json_data, "data", "ep_list", type_check=list):
        result_comic_info = {
            "ep_id": 0,  # 章节id
            "ep_name": "",  # 章节名字
        }
        # 获取页面id
        result_comic_info["ep_id"] = crawler.get_json_value(ep_info, "id", type_check=int)
        # 获取章节名字
        short_title = crawler.get_json_value(ep_info, "short_title", type_check=str).strip()
        title = crawler.get_json_value(ep_info, "title", type_check=str).strip()
        result_comic_info["ep_name"] = (short_title + " " + title) if title else short_title
        result["comic_info_list"][result_comic_info["ep_id"]] = result_comic_info
    return result


# 获取漫画指定章节
def get_chapter_page(ep_id):
    # https://m.dmzj.com/view/9949/19842.html
    api_url = "https://manga.bilibili.com/twirp/comic.v1.Comic/GetImageIndex?device=pc&platform=web"
    post_data = {
        "ep_id": ep_id
    }
    api_response = net.request(api_url, method="POST", fields=post_data, cookies_list=COOKIE_INFO, json_decode=True)
    result = {
        "need_buy": False,  # 是否需要购买
        "photo_url_list": [],  # 全部漫画图片地址
    }
    if api_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(api_response.status))
    if crawler.get_json_value(api_response.json_data, "code", type_check=int) == 1:
        raise crawler.CrawlerException("需要购买")
    image_path_list = []
    for image_info in crawler.get_json_value(api_response.json_data, "data", "images", type_check=list):
        image_path_list.append(crawler.get_json_value(image_info, "path", type_check=str))
    token_api_url = "https://manga.bilibili.com/twirp/comic.v1.Comic/ImageToken?device=pc&platform=web"
    post_data = {
        "urls": tool.json_encode(image_path_list)
    }
    token_api_response = net.request(token_api_url, method="POST", fields=post_data, json_decode=True)
    if api_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException("图片token获取，" + crawler.request_failre(api_response.status))
    for token_info in crawler.get_json_value(token_api_response.json_data, "data", type_check=list):
        url = crawler.get_json_value(token_info, "url", type_check=str)
        token = crawler.get_json_value(token_info, "token", type_check=str)
        result["photo_url_list"].append("%s?token=%s" % (url, token))
    return result


class BiliBiliComic(crawler.Crawler):
    def __init__(self, **kwargs):
        global COOKIE_INFO

        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_GET_COOKIE: ("bilibili.com",),
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 设置全局变量，供子线程调用
        COOKIE_INFO = self.cookie_value

        # 解析存档文件
        # comic_id  last_comic_id (comic_name)
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

        # 下载线程
        self.crawler_thread = CrawlerThread

    def init(self):
        # 检测登录状态
        if check_login():
            return

        while True:
            input_str = input(tool.get_time() + " 没有检测到账号登录状态，可能无法解析需要登录才能查看的漫画，继续程序(C)ontinue？或者退出程序(E)xit？:")
            input_str = input_str.lower()
            if input_str in ["e", "exit"]:
                tool.process_exit()
            elif input_str in ["c", "continue"]:
                break


class CrawlerThread(crawler.CrawlerThread):
    def __init__(self, main_thread, single_save_data):
        self.index_key = single_save_data[0]  # comic id
        if len(single_save_data) >= 3 and single_save_data[2]:
            self.display_name = single_save_data[2]
        else:
            self.display_name = single_save_data[0]
        crawler.CrawlerThread.__init__(self, main_thread, single_save_data)

    # 获取所有可下载漫画
    def get_crawl_list(self):
        comic_info_list = []

        index_description = "漫画首页"
        self.start_parse(index_description)
        try:
            blog_pagination_response = get_comic_index_page(self.index_key)
        except crawler.CrawlerException as e:
            self.error(e.http_error(index_description))
            raise
        self.parse_result(index_description, blog_pagination_response["comic_info_list"])

        # 寻找符合条件的章节
        for ep_id in sorted(list(blog_pagination_response["comic_info_list"].keys()), reverse=True):
            comic_info = blog_pagination_response["comic_info_list"][ep_id]
            # 检查是否达到存档记录
            if ep_id > int(self.single_save_data[1]):
                comic_info_list.append(comic_info)
            else:
                break

        return comic_info_list

    def crawl_comic(self, comic_info):
        comic_description = "漫画%s 《%s》" % (comic_info["ep_id"], comic_info["ep_name"])
        self.start_parse(comic_description)
        try:
            chapter_response = get_chapter_page(comic_info["ep_id"])
        except crawler.CrawlerException as e:
            self.error(e.http_error(comic_description))
            raise
        self.parse_result(comic_description, chapter_response["photo_url_list"])

        # 图片下载
        photo_index = 1
        chapter_name = "%06d %s" % (comic_info["ep_id"], path.filter_text(comic_info["ep_name"]))
        chapter_path = os.path.join(self.main_thread.photo_download_path, self.display_name, chapter_name)
        # 设置临时目录
        self.temp_path_list.append(chapter_path)
        for photo_url in chapter_response["photo_url_list"]:
            photo_path = os.path.join(chapter_path, "%03d.%s" % (photo_index, net.get_file_extension(photo_url)))
            photo_description = "漫画%s 《%s》第%s张图片" % (comic_info["ep_id"], comic_info["ep_name"], photo_index)
            if self.download(photo_url, photo_path, photo_description, header_list={"Referer": "https://m.dmzj.com/"}):
                self.total_photo_count += 1  # 计数累加
            photo_index += 1

        # 章节内图片全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.single_save_data[1] = str(comic_info["ep_id"])  # 设置存档记录

    def _run(self):
        # 获取所有可下载章节
        comic_info_list = self.get_crawl_list()
        self.step("需要下载的全部漫画解析完毕，共%s个" % len(comic_info_list))

        # 从最早的章节开始下载
        while len(comic_info_list) > 0:
            self.crawl_comic(comic_info_list.pop())
            self.main_thread_check()  # 检测主线程运行状态


if __name__ == "__main__":
    BiliBiliComic().main()
