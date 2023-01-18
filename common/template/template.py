# -*- coding:UTF-8  -*-
"""
模板
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import re
import time
from pyquery import PyQuery as pq
from common import *


# 检测登录状态
def check_login():
    return False


# 获取一页日志
def get_one_page_blog(account_id, page_count):
    result = {
        "blog_id_list": [],  # 日志id
    }
    return result


# 获取指定日志
def get_blog_page(account_id, blog_id):
    result = {
        "photo_url_list": [],  # 全部图片地址
        "video_url_list": [],  # 全部视频地址
        "audio_url_list": [],  # 全部音频地址
    }
    return result


class Template(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        # todo 配置
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_DOWNLOAD_VIDEO: True,
            crawler.SYS_DOWNLOAD_AUDIO: True,
            crawler.SYS_SET_PROXY: True,
            crawler.SYS_NOT_CHECK_SAVE_DATA: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # todo 存档文件格式
        # 解析存档文件
        # account_id
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", ])

        # 检测登录状态
        if not check_login():
            while True:
                input_str = input(tool.get_time() + " 没有检测到账号登录状态，可能无法解析只对会员开放的日志，继续程序(C)ontinue？或者退出程序(E)xit？:")
                input_str = input_str.lower()
                if input_str in ["e", "exit"]:
                    tool.process_exit()
                elif input_str in ["c", "continue"]:
                    break

        # 下载线程
        self.crawler_thread = CrawlerThread
        

class CrawlerThread(crawler.CrawlerThread):
    def __init__(self, main_thread, single_save_data)::
        crawler.CrawlerThread.__init__(self, main_thread, single_save_data)
        self.index_key = self.single_save_data[0]
        # 日志前缀
        self.display_name = self.single_save_data[0]
        self.step("开始")

    def _run(self):
        # 获取所有可下载日志
        blog_id_list = self.get_crawl_list()
        self.step("需要下载的全部日志解析完毕，共%s个" % len(blog_id_list))

        # 从最早的日志开始下载
        while len(blog_id_list) > 0:
            blog_id = blog_id_list.pop()
            self.crawl_blog(blog_id)
            self.main_thread_check()  # 检测主线程运行状态

    # 获取所有可下载日志
    def get_crawl_list(self):
        page_count = 1
        blog_id_list = []
        is_over = False
        # 获取全部还未下载过需要解析的日志
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析第%s页日志" % page_count)

            # todo 一页日志解析规则
            # 获取指定时间后的一页日志
            try:
                blog_pagination_response = get_one_page_blog(self.index_key, page_count)
            except crawler.CrawlerException as e:
                self.error(e.http_error("第%s页日志" % page_count))
                raise

            self.trace("第%s页解析的全部日志：%s" % (page_count, blog_pagination_response["blog_id_list"]))

            # 寻找这一页符合条件的媒体
            for blog_id in blog_pagination_response["blog_id_list"]:
                # 检查是否达到存档记录
                if int(blog_id) > int(self.single_save_data[3]):
                    blog_id_list.append(blog_id)
                else:
                    is_over = True
                    break

        return blog_id_list

    # 解析单个日志
    def crawl_blog(self, blog_id):
        self.step("开始解析日志%s" % blog_id)

        # todo 日志解析规则
        # 获取指定日志
        try:
            blog_response = get_blog_page(self.index_key, blog_id)
        except crawler.CrawlerException as e:
            self.error(e.http_error("日志%s" % blog_id))
            raise

        # todo 图片下载逻辑
        # 图片下载
        photo_index = self.single_save_data[1] + 1
        if self.main_thread.is_download_photo:
            for photo_url in blog_response["photo_url_list"]:
                self.main_thread_check()  # 检测主线程运行状态
                self.step("开始下载第%s张图片 %s" % (photo_index, photo_url))

                file_extension = net.get_file_extension(photo_url)
                photo_file_path = os.path.join(self.main_thread.photo_download_path, self.index_key, "%04d.%s" % (photo_index, file_extension))
                download_return = net.Download(photo_url, photo_file_path)
                if download_return.status == net.Download.DOWNLOAD_SUCCEED:
                    # 设置临时目录
                    self.temp_path_list.append(photo_file_path)
                    self.step("第%s张图片下载成功" % photo_index)
                    photo_index += 1
                else:
                    self.error("第%s张图片 %s 下载失败，原因：%s" % (photo_index, photo_url, crawler.download_failre(download_return.code)))

        # todo 视频下载逻辑
        # 视频下载
        video_index = self.single_save_data[2] + 1
        if self.main_thread.is_download_video:
            for video_url in blog_response["video_url_list"]:
                self.main_thread_check()  # 检测主线程运行状态
                self.step("开始下载第%s个视频 %s" % (video_index, video_url))

                file_extension = net.get_file_extension(video_url)
                video_file_path = os.path.join(self.main_thread.video_download_path, self.index_key, "%04d.%s" % (video_index, file_extension))
                download_return = net.Download(video_url, video_file_path)
                if download_return.status == net.Download.DOWNLOAD_SUCCEED:
                    # 设置临时目录
                    self.temp_path_list.append(video_file_path)
                    self.step("第%s个视频下载成功" % video_index)
                    video_index += 1
                else:
                    self.error("第%s个视频 %s 下载失败，原因：%s" % (video_index, video_url, crawler.download_failre(download_return.code)))

        # todo 音频下载逻辑
        # 音频下载
        audio_index = self.single_save_data[2] + 1
        if self.main_thread.is_download_audio:
            for audio_url in blog_response["audio_url_list"]:
                self.main_thread_check()  # 检测主线程运行状态
                self.step("开始下载第%s个音频 %s" % (audio_index, audio_url))

                file_extension = net.get_file_extension(audio_url)
                audio_file_path = os.path.join(self.main_thread.audio_download_path, self.index_key, "%04d.%s" % (audio_index, file_extension))
                download_return = net.Download(audio_url, audio_file_path)
                if download_return.status == net.Download.DOWNLOAD_SUCCEED:
                    # 设置临时目录
                    self.temp_path_list.append(audio_file_path)
                    self.step("第%s个音频下载成功" % audio_index)
                    audio_index += 1
                else:
                    self.error("第%s个音频 %s 下载失败，原因：%s" % (audio_index, audio_url, crawler.download_failre(download_return.code)))

        # 日志内图片、视频和音频全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.total_photo_count += (photo_index - 1) - int(self.single_save_data[1])  # 计数累加
        self.total_video_count += (video_index - 1) - int(self.single_save_data[2])  # 计数累加
        self.total_audio_count += (audio_index - 1) - int(self.single_save_data[3])  # 计数累加
        self.single_save_data[1] = str(photo_index - 1)  # 设置存档记录
        self.single_save_data[2] = str(video_index - 1)  # 设置存档记录
        self.single_save_data[3] = str(audio_index - 1)  # 设置存档记录
        self.single_save_data[4] = ""  # 设置存档记录


if __name__ == "__main__":
    Template().main()
