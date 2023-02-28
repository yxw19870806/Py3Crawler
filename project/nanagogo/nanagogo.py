# -*- coding:UTF-8  -*-
"""
7gogo图片&视频爬虫
https://7gogo.jp/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from common import *

INIT_TARGET_ID = "99999"
EACH_PAGE_BLOG_COUNT = 30  # 每次请求获取的日志数量
COOKIE_INFO = {}


# 获取talk首页
def get_index_page(account_name):
    index_url = "https://7gogo.jp/%s" % account_name
    index_response = net.request(index_url, method="GET")
    if index_response.status == 404:
        raise crawler.CrawlerException("talk已被删除")
    return index_response


# 获取指定页数的全部日志信息
def get_one_page_blog(account_name, target_id):
    blog_pagination_url = "https://api.7gogo.jp/web/v2/talks/%s/images" % account_name
    query_data = {
        "targetId": target_id,
        "limit": EACH_PAGE_BLOG_COUNT,
        "direction": "PREV",
    }
    blog_pagination_response = net.request(blog_pagination_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "blog_info_list": [],  # 全部日志信息
    }
    if target_id == INIT_TARGET_ID and blog_pagination_response.status == 400:
        raise crawler.CrawlerException("talk不存在")
    elif blog_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(blog_pagination_response.status))
    for blog_info in crawler.get_json_value(blog_pagination_response.json_data, "data", type_check=list):
        result_blog_info = {
            "blog_id": 0,  # 日志id
            "photo_url_list": [],  # 全部图片地址
            "video_url_list": [],  # 全部视频地址
        }
        # 获取日志id
        result_blog_info["blog_id"] = crawler.get_json_value(blog_info, "post", "postId", type_check=int)
        # 获取日志内容
        for blog_body_info in crawler.get_json_value(blog_info, "post", "body", type_check=list):
            # bodyType = 1: text, bodyType = 3: photo, bodyType = 8: video
            body_type = crawler.get_json_value(blog_body_info, "bodyType", type_check=int)
            if body_type == 1:  # 文本
                continue
            elif body_type == 2:  # 表情
                continue
            elif body_type == 3:  # 图片
                result_blog_info["photo_url_list"].append(crawler.get_json_value(blog_body_info, "image", type_check=str))
            elif body_type == 7:  # 转发
                continue
            elif body_type == 8:  # video
                result_blog_info["video_url_list"].append(crawler.get_json_value(blog_body_info, "movieUrlHq", type_check=str))
            else:
                raise crawler.CrawlerException("日志信息%s中'bodyType'字段取值不正确" % blog_body_info)
        result["blog_info_list"].append(result_blog_info)
    return result


class NanaGoGo(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SysConfigKey.DOWNLOAD_PHOTO: True,
            crawler.SysConfigKey.DOWNLOAD_VIDEO: True,
            crawler.SysConfigKey.SET_PROXY: True,
            crawler.SysConfigKey.GET_COOKIE: ("7gogo.jp", "api.7gogo.jp"),
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 设置全局变量，供子线程调用
        COOKIE_INFO.update(self.cookie_value)

        # 解析存档文件
        # account_name  last_post_id
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

        # 下载线程
        self.crawler_thread = CrawlerThread


class CrawlerThread(crawler.CrawlerThread):
    def __init__(self, main_thread, single_save_data):
        self.index_key = self.display_name = single_save_data[0]  # account name
        crawler.CrawlerThread.__init__(self, main_thread, single_save_data)

    # 获取所有可下载日志
    def get_crawl_list(self):
        target_id = INIT_TARGET_ID
        blog_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的日志
        while not is_over:
            blog_pagination_description = "target：%s后一页日志" % target_id
            self.start_parse(blog_pagination_description)
            try:
                blog_pagination_response = get_one_page_blog(self.index_key, target_id)
            except crawler.CrawlerException as e:
                self.error(e.http_error(blog_pagination_description))
                raise
            self.parse_result(blog_pagination_description, blog_pagination_response["blog_info_list"])

            # 已经没有日志了
            if len(blog_pagination_response["blog_info_list"]) == 0:
                break

            # 寻找这一页符合条件的日志
            for blog_info in blog_pagination_response["blog_info_list"]:
                # 检查是否达到存档记录
                if blog_info["blog_id"] > int(self.single_save_data[1]):
                    blog_info_list.append(blog_info)
                    # 设置下一页指针
                    target_id = blog_info["blog_id"]
                else:
                    is_over = True
                    break

        return blog_info_list

    # 解析单个日志
    def crawl_blog(self, blog_info):
        blog_description = "日志%s" % blog_info["blog_id"]
        self.start_parse(blog_description)

        # 图片下载
        if self.main_thread.is_download_photo:
            self.crawl_photo(blog_info)

        # 视频下载
        if self.main_thread.is_download_video:
            self.crawl_video(blog_info)

        # 日志内图片和视频全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.single_save_data[1] = str(blog_info["blog_id"])

    def crawl_photo(self, blog_info):
        self.parse_result("日志%s图片" % blog_info["blog_id"], blog_info["photo_url_list"])

        photo_index = 1
        for photo_url in blog_info["photo_url_list"]:
            photo_name = "%05d_%02d.%s" % (blog_info["blog_id"], photo_index, net.get_file_extension(photo_url))
            photo_path = os.path.join(self.main_thread.photo_download_path, self.index_key, photo_name)
            photo_description = "日志%s第%s张图片" % (blog_info["blog_id"], photo_index)
            if self.download(photo_url, photo_path, photo_description):
                self.temp_path_list.append(photo_path)  # 设置临时目录
                self.total_photo_count += 1  # 计数累加
            photo_index += 1

    def crawl_video(self, blog_info):
        self.parse_result("日志%s视频" % blog_info["blog_id"], blog_info["video_url_list"])

        video_index = 1
        for video_url in blog_info["video_url_list"]:
            video_name = "%05d_%02d.%s" % (blog_info["blog_id"], video_index, net.get_file_extension(video_url))
            video_path = os.path.join(self.main_thread.video_download_path, self.index_key, video_name)
            video_description = "日志%s第%s个视频" % (blog_info["blog_id"], video_index)
            if self.download(video_url, video_path, video_description):
                self.temp_path_list.append(video_path)  # 设置临时目录
                self.total_video_count += 1  # 计数累加
            video_index += 1

    def _run(self):
        # 获取首页
        try:
            get_index_page(self.index_key)
        except crawler.CrawlerException as e:
            self.error(e.http_error("首页"))
            raise

        # 获取所有可下载日志
        blog_info_list = self.get_crawl_list()
        self.step("需要下载的全部日志解析完毕，共%s个" % len(blog_info_list))

        # 从最早的日志开始下载
        while len(blog_info_list) > 0:
            self.crawl_blog(blog_info_list.pop())


if __name__ == "__main__":
    NanaGoGo().main()
