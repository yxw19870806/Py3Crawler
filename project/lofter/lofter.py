# -*- coding:UTF-8  -*-
"""
lofter图片爬虫
https://www.lofter.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import re
from common import *

COOKIES = {}


def init_session():
    index_url = "https://www.lofter.com"
    index_response = net.Request(index_url, method="GET").disable_redirect()
    if index_response.status in [const.ResponseCode.SUCCEED, 302]:
        COOKIES.update(net.get_cookies_from_response_header(index_response.headers))


# 获取指定页数的全部日志
def get_one_page_blog(account_name, page_count):
    # https://moexia.lofter.com/?page=1
    blog_pagination_url = "https://%s.lofter.com/" % account_name
    query_data = {"page": page_count}
    blog_pagination_response = net.Request(blog_pagination_url, method="GET", fields=query_data, cookies=COOKIES).disable_redirect()
    result = {
        "blog_url_list": [],  # 全部日志地址
    }
    if blog_pagination_response.status == 302:
        COOKIES.update(net.get_cookies_from_response_header(blog_pagination_response.headers))
        return get_one_page_blog(account_name, page_count)
    if page_count == 1 and blog_pagination_response.status == 404:
        raise crawler.CrawlerException("账号不存在")
    elif blog_pagination_response.status != const.ResponseCode.SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(blog_pagination_response.status))
    # 获取全部日志地址
    blog_url_list = re.findall(r'"(https?://%s.lofter.com/post/[^"]*)"' % account_name, blog_pagination_response.content)
    # 去重排序
    result["blog_url_list"] = sorted(list(set(blog_url_list)), reverse=True)
    return result


# 获取日志
def get_blog_page(blog_url):
    blog_response = net.Request(blog_url, method="GET", cookies=COOKIES)
    result = {
        "photo_url_list": [],  # 全部图片地址
    }
    if blog_response.status != const.ResponseCode.SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(blog_response.status))
    # 获取全部图片地址
    result["photo_url_list"] = re.findall(r'bigimgsrc="([^"]*)"', blog_response.content)
    return result


# 从日志地址中解析出日志id
def get_blog_id(blog_url):
    return int(blog_url.split("/")[-1].split("_")[-1], 16)


# 去除图片的参数
def get_photo_url(photo_url):
    if photo_url.rfind("?") > photo_url.rfind("."):
        return photo_url.split("?")[0]
    return photo_url


# 检测图片是不是已被屏蔽
def check_photo_invalid(photo_path):
    # https://imglf.nosdn.127.net/img/WWpvYmlBb3BlNCt0clU3WUNVb2U5UmhjMW56ZEh1TVFuc1BMVTI4aUR4OG0rNUdIK2xTbzNRPT0.jpg
    if os.path.getsize(photo_path) == 31841 and file.get_file_md5(photo_path) == "e4e09c4989d0f4db68610195b97688bf":
        return True
    return False


class Lofter(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            const.SysConfigKey.DOWNLOAD_PHOTO: True,
            const.SysConfigKey.SAVE_DATA_FORMATE: (0, ["", "0"]),  # account_name  last_blog_id
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 下载线程
        self.crawler_thread = CrawlerThread

    def init(self):
        net.set_default_user_agent()
        net.disable_fake_proxy_ip()
        init_session()


class CrawlerThread(crawler.CrawlerThread):
    def __init__(self, main_thread, single_save_data):
        self.index_key = self.display_name = single_save_data[0]  # account name
        crawler.CrawlerThread.__init__(self, main_thread, single_save_data)

    # 获取所有可下载日志
    def get_crawl_list(self):
        page_count = 1
        unique_list = []
        blog_url_list = []
        is_over = False
        # 获取全部还未下载过需要解析的日志
        while not is_over:
            blog_pagination_description = "第%s页日志" % page_count
            self.start_parse(blog_pagination_description)
            try:
                blog_pagination_response = get_one_page_blog(self.index_key, page_count)
            except crawler.CrawlerException as e:
                self.error(e.http_error(blog_pagination_description))
                raise
            self.parse_result(blog_pagination_description, blog_pagination_response["blog_url_list"])

            # 已经没有日志了
            if len(blog_pagination_response["blog_url_list"]) == 0:
                break

            # 寻找这一页符合条件的日志
            for blog_url in blog_pagination_response["blog_url_list"]:
                blog_id = get_blog_id(blog_url)

                # 检查是否达到存档记录
                if blog_id > int(self.single_save_data[1]):
                    # 新增日志导致的重复判断
                    if blog_id in unique_list:
                        continue
                    else:
                        blog_url_list.append(blog_url)
                        unique_list.append(blog_id)
                else:
                    is_over = True
                    break

            if not is_over:
                page_count += 1

        return blog_url_list

    # 解析单个日志
    def crawl_blog(self, blog_url):
        blog_description = "日志%s" % blog_url
        self.start_parse(blog_description)
        try:
            blog_response = get_blog_page(blog_url)
        except crawler.CrawlerException as e:
            self.error(e.http_error(blog_description))
            raise
        self.parse_result(blog_description, blog_response["photo_url_list"])

        blog_id = get_blog_id(blog_url)
        photo_index = 1
        for photo_url in blog_response["photo_url_list"]:
            # 去除图片地址的参数
            photo_url = get_photo_url(photo_url)

            file_name = "%09d_%02d.%s" % (blog_id, photo_index, net.get_file_extension(photo_url))
            photo_path = os.path.join(self.main_thread.photo_download_path, self.index_key, file_name)
            photo_description = "日志%s(%s)第%s张图片" % (blog_id, blog_url, photo_index)
            if self.download(photo_url, photo_path, photo_description, success_callback=self.download_success_callback):
                self.temp_path_list.append(photo_path)  # 设置临时目录
                self.total_photo_count += 1  # 计数累加
            photo_index += 1

        # 日志内图片全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.single_save_data[1] = str(blog_id)  # 设置存档记录

    def download_success_callback(self, photo_url, photo_path, photo_description, download_return):
        if check_photo_invalid(photo_path):
            path.delete_dir_or_file(photo_path)
            self.error("%s %s 已被屏蔽，删除" % (photo_description, photo_url))
            return False
        return True

    def _run(self):
        # 获取所有可下载日志
        blog_url_list = self.get_crawl_list()
        self.info("需要下载的全部日志解析完毕，共%s个" % len(blog_url_list))

        # 从最早的日志开始下载
        while len(blog_url_list) > 0:
            self.crawl_blog(blog_url_list.pop())


if __name__ == "__main__":
    Lofter().main()
