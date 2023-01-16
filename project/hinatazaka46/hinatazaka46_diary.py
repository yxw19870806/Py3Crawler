# -*- coding:UTF-8  -*-
"""
日向坂46公式Blog图片爬虫
https://www.hinatazaka46.com/s/official/diary/member/list
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from pyquery import PyQuery as pq
from common import *

EACH_PAGE_BLOG_COUNT = 20  # 每次请求获取的日志数量


# 获取指定页数的全部日志
def get_one_page_blog(account_id, page_count):
    # https://www.hinatazaka46.com/s/official/diary/member/list?ima=0000&ct=1
    blog_pagination_url = "https://www.hinatazaka46.com/s/official/diary/member/list"
    query_data = {
        "cd": "member",
        "ct": account_id,
        "page": str(page_count - 1),
    }
    blog_pagination_response = net.request(blog_pagination_url, method="GET", fields=query_data)
    result = {
        "blog_info_list": [],  # 全部日志信息
        "is_over": False,  # 是不是最后页日志
    }
    if blog_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(blog_pagination_response.status))
    blog_pagination_response_content = blog_pagination_response.data.decode(errors="ignore")
    account_info_html = pq(blog_pagination_response_content).find(".p-blog-member__head .c-blog-member__name").html()
    if not account_info_html or not account_info_html.strip():
        raise crawler.CrawlerException("账号不存在")
    # 日志正文部分
    blog_list_selector = pq(blog_pagination_response_content).find(".p-blog-group .p-blog-article")
    if blog_list_selector.length == 0:
        raise crawler.CrawlerException("页面截取日志列表失败\n" + blog_pagination_response_content)
    for blog_index in range(blog_list_selector.length):
        result_blog_info = {
            "blog_id": 0,  # 日志id
            "photo_url_list": [],  # 全部图片地址
        }
        blog_selector = blog_list_selector.eq(blog_index)
        # 获取日志id
        blog_url = blog_selector.find(".p-button__blog_detail a").attr("href")
        if not blog_url:
            raise crawler.CrawlerException("日志信息截取日志地址失败\n" + blog_selector.html())
        blog_id = blog_url.split("/")[-1].split("?")[0]
        if not tool.is_integer(blog_id):
            raise crawler.CrawlerException("日志地址 %s 截取日志id失败" % blog_url)
        result_blog_info["blog_id"] = int(blog_id)
        # 获取图片地址
        photo_list_selector = pq(blog_selector).find("img")
        for photo_index in range(photo_list_selector.length):
            photo_selector = photo_list_selector.eq(photo_index)
            # 跳过表情
            if photo_selector.has_class("emoji"):
                continue
            photo_url = photo_selector.attr("src")
            if not photo_url:
                continue
            result_blog_info["photo_url_list"].append(photo_url)
        result["blog_info_list"].append(result_blog_info)
    last_pagination_html = pq(blog_pagination_response_content).find(".p-pager--count .c-pager__item--next")
    if last_pagination_html.length != 1:
        if pq(blog_pagination_response_content).find(".p-pager--count").length != 1:
            raise crawler.CrawlerException("页面截取最后页按钮失败\n" + blog_pagination_response_content)
        result["is_over"] = True
    return result


class Hinatazaka46Diary(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 解析存档文件
        # account_id  last_blog_id
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

        # 下载线程
        self.download_thread = Download


class Download(crawler.CrawlerThread):
    def __init__(self, single_save_data, main_thread):
        self.index_key = single_save_data[0]  # account id
        if len(single_save_data) >= 3 and single_save_data[2]:
            self.display_name = single_save_data[2]
        else:
            self.display_name = single_save_data[0]
        crawler.CrawlerThread.__init__(self, single_save_data, main_thread)

    def _run(self):
        # 获取所有可下载日志
        blog_info_list = self.get_crawl_list()
        self.step("需要下载的全部日志解析完毕，共%s个" % len(blog_info_list))

        # 从最早的日志开始下载
        while len(blog_info_list) > 0:
            self.crawl_blog(blog_info_list.pop())
            self.main_thread_check()  # 检测主线程运行状态

    # 获取所有可下载日志
    def get_crawl_list(self):
        page_count = 1
        blog_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的日志
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态

            pagination_description = "第%s页日志" % page_count
            self.start_parse(pagination_description)

            # 获取一页博客信息
            try:
                blog_pagination_response = get_one_page_blog(self.index_key, page_count)
            except crawler.CrawlerException as e:
                self.error(e.http_error(pagination_description))
                raise

            self.parse_result(pagination_description, blog_pagination_response["blog_info_list"])

            # 寻找这一页符合条件的日志
            for blog_info in blog_pagination_response["blog_info_list"]:
                # 检查是否达到存档记录
                if blog_info["blog_id"] > int(self.single_save_data[1]):
                    blog_info_list.append(blog_info)
                else:
                    is_over = True
                    break

            if not is_over:
                if blog_pagination_response["is_over"]:
                    is_over = True
                else:
                    page_count += 1

        return blog_info_list

    # 解析单个日志
    def crawl_blog(self, blog_info):
        blog_description = "日志%s" % blog_info["blog_id"]
        self.start_parse(blog_description)

        self.parse_result(blog_description, blog_info["photo_url_list"])

        photo_index = 1
        for photo_url in blog_info["photo_url_list"]:
            self.main_thread_check()  # 检测主线程运行状态

            photo_name = "%05d_%02d.%s" % (blog_info["blog_id"], photo_index, net.get_file_extension(photo_url))
            photo_path = os.path.join(self.main_thread.photo_download_path, self.display_name, photo_name)
            self.temp_path_list.append(photo_path)  # 设置临时目录
            photo_description = "日志%s第%s张图片" % (blog_info["blog_id"], photo_index)
            if self.download(photo_url, photo_path, photo_description).is_success():
                self.total_photo_count += 1  # 计数累加
            photo_index += 1

        # 日志内图片全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.single_save_data[1] = str(blog_info["blog_id"])  # 设置存档记录


if __name__ == "__main__":
    Hinatazaka46Diary().main()
