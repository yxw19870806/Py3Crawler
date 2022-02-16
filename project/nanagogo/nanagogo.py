# -*- coding:UTF-8  -*-
"""
7gogo图片&视频爬虫
https://7gogo.jp/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import time
from common import *

INIT_TARGET_ID = "99999"
EACH_PAGE_BLOG_COUNT = 30  # 每次请求获取的日志数量


# 获取talk首页
def get_index_page(account_name):
    index_url = f"https://7gogo.jp/{account_name}"
    index_response = net.request(index_url, method="GET")
    if index_response.status == 404:
        raise crawler.CrawlerException("talk已被删除")
    return index_response


# 获取指定页数的全部日志信息
def get_one_page_blog(account_name, target_id):
    blog_pagination_url = f"https://api.7gogo.jp/web/v2/talks/{account_name}/images"
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
            "blog_id": None,  # 日志id
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
                raise crawler.CrawlerException(f"日志信息{blog_body_info}中'bodyType'字段取值不正确")
        result["blog_info_list"].append(result_blog_info)
    return result


class NanaGoGo(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_DOWNLOAD_VIDEO: True,
            crawler.SYS_SET_PROXY: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 解析存档文件
        # account_name  last_post_id
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

        # 下载线程
        self.download_thread = Download


class Download(crawler.DownloadThread):
    def __init__(self, single_save_data, main_thread):
        crawler.DownloadThread.__init__(self, single_save_data, main_thread)
        self.index_key = self.display_name = self.single_save_data[0]  # account name
        self.step("开始")

    def _run(self):
        # 获取首页
        try:
            get_index_page(self.index_key)
        except crawler.CrawlerException as e:
            self.error(e.http_error("首页"))
            raise

        # 获取所有可下载日志
        blog_info_list = self.get_crawl_list()
        self.step(f"需要下载的全部日志解析完毕，共{len(blog_info_list)}个")

        # 从最早的日志开始下载
        while len(blog_info_list) > 0:
            self.crawl_blog(blog_info_list.pop())
            self.main_thread_check()  # 检测主线程运行状态

    # 获取所有可下载日志
    def get_crawl_list(self):
        target_id = INIT_TARGET_ID
        blog_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的日志
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step(f"开始解析target：{target_id}页")

            # 获取一页日志信息
            try:
                blog_pagination_response = get_one_page_blog(self.index_key, target_id)
            except crawler.CrawlerException as e:
                self.error(e.http_error(f"target：{target_id}后一页日志"))
                raise

            self.trace(f"target：{target_id}页解析的全部日志：{blog_pagination_response['blog_info_list']}")
            self.step(f"target：{target_id}页解析获取{len(blog_pagination_response['blog_info_list'])}个日志")

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
        self.step(f"开始解析日志{blog_info['blog_id']}")

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
        self.trace(f"日志{blog_info['blog_id']}解析的全部图片：{blog_info['photo_url_list']}")
        self.step(f"日志{blog_info['blog_id']}解析获取{len(blog_info['photo_url_list'])}张图片")

        photo_index = 1
        for photo_url in blog_info["photo_url_list"]:
            self.main_thread_check()  # 检测主线程运行状态
            self.step(f"开始下载日志{blog_info['blog_id']}的第{photo_index}张图片 {photo_url}")

            photo_file_path = os.path.join(self.main_thread.photo_download_path, self.index_key, f"%05d_%02d.{net.get_file_extension(photo_url)}" % (blog_info["blog_id"], photo_index))
            download_return = net.Download(photo_url, photo_file_path)
            if download_return.status == net.Download.DOWNLOAD_SUCCEED:
                self.temp_path_list.append(photo_file_path)  # 设置临时目录
                self.total_photo_count += 1  # 计数累加
                self.step(f"日志{blog_info['blog_id']}的第{photo_index}张图片下载成功")
            else:
                self.error(f"日志{blog_info['blog_id']}第{photo_index}张图片 {photo_url} 下载失败，原因：{crawler.download_failre(download_return.code)}")
                self.check_download_failure_exit()
            photo_index += 1

    def crawl_video(self, blog_info):
        self.trace(f"日志{blog_info['blog_id']}解析的全部视频：{blog_info['video_url_list']}")
        self.step(f"日志{blog_info['blog_id']}解析获取{len(blog_info['video_url_list'])}个视频")

        video_index = 1
        for video_url in blog_info["video_url_list"]:
            self.main_thread_check()  # 检测主线程运行状态
            self.step(f"开始下载日志{blog_info['blog_id']}的第{video_index}个视频 {video_url}")

            video_file_path = os.path.join(self.main_thread.video_download_path, self.index_key, f"%05d_%02d.{net.get_file_extension(video_url)}" % (blog_info["blog_id"], video_index))
            download_return = net.Download(video_url, video_file_path)
            if download_return.status == net.Download.DOWNLOAD_SUCCEED:
                self.temp_path_list.append(video_file_path)  # 设置临时目录
                self.total_video_count += 1  # 计数累加
                self.step(f"日志{blog_info['blog_id']}的第{video_index}个视频下载成功")
            else:
                self.error(f"日志{blog_info['blog_id']}的第{video_index}个视频 {video_url} 下载失败，原因：{crawler.download_failre(download_return.code)}")
                self.check_download_failure_exit()
            video_index += 1


if __name__ == "__main__":
    NanaGoGo().main()
