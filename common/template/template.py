# -*- coding:UTF-8  -*-
"""
模板
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
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
            const.SysConfigKey.DOWNLOAD_PHOTO: True,
            const.SysConfigKey.DOWNLOAD_VIDEO: True,
            const.SysConfigKey.DOWNLOAD_AUDIO: True,
            const.SysConfigKey.SET_PROXY: True,
            const.SysConfigKey.NOT_CHECK_SAVE_DATA: True,
            const.SysConfigKey.SAVE_DATA_FORMATE: (0, ["", "0"]),  # account_id, blog_id
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 下载线程
        self.set_crawler_thread(CrawlerThread)

    def init(self):
        # 检测登录状态
        if check_login():
            return

        while True:
            input_str = input(tool.convert_timestamp_to_formatted_time() + " 没有检测到账号登录状态，可能无法解析只对会员开放的日志，继续程序(C)ontinue？或者退出程序(E)xit？:")
            input_str = input_str.lower()
            if input_str in ["e", "exit"]:
                tool.process_exit()
            elif input_str in ["c", "continue"]:
                break


class CrawlerThread(crawler.CrawlerThread):
    def __init__(self, main_thread, single_save_data):
        crawler.CrawlerThread.__init__(self, main_thread, single_save_data)
        self.index_key = self.single_save_data[0]
        # 日志前缀
        self.display_name = self.single_save_data[0]
        self.info("开始")

    def _run(self):
        # 获取所有可下载日志
        blog_id_list = self.get_crawl_list()
        self.info("需要下载的全部日志解析完毕，共%s个" % len(blog_id_list))

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
            blog_pagination_description = "第%s页日志" % page_count
            self.start_parse(blog_pagination_description)
            try:
                blog_pagination_response = get_one_page_blog(self.index_key, page_count)
            except crawler.CrawlerException as e:
                self.error(e.http_error(blog_pagination_description))
                raise
            self.parse_result(blog_pagination_description, blog_pagination_response["blog_id_list"])

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
        blog_description = "日志%s" % blog_id
        self.start_parse(blog_description)
        # 获取指定日志
        try:
            blog_response = get_blog_page(self.index_key, blog_id)
        except crawler.CrawlerException as e:
            self.error(e.http_error(blog_description))
            raise

        # todo 图片下载逻辑
        # 图片下载
        if self.main_thread.is_download_photo:
            self.parse_result(blog_description + "图片", blog_response["photo_url_list"])

            photo_index = 1
            for photo_url in blog_response["photo_url_list"]:
                file_extension = net.get_file_extension(photo_url)
                photo_file_path = os.path.join(self.main_thread.photo_download_path, self.index_key, "%04d.%s" % (photo_index, file_extension))
                photo_file_description = "第%s张图片" % photo_index
                if self.download(photo_url, photo_file_path, photo_file_description):
                    self.temp_path_list.append(photo_file_path)  # 设置临时目录
                    self.total_photo_count += 1  # 计数累加
                photo_index += 1

        # todo 视频下载逻辑
        # 视频下载
        if self.main_thread.is_download_video:
            self.parse_result(blog_description + "视频", blog_response["video_url_list"])

            video_index = 1
            for video_url in blog_response["video_url_list"]:
                file_extension = net.get_file_extension(video_url)
                video_file_path = os.path.join(self.main_thread.video_download_path, self.index_key, "%04d.%s" % (video_index, file_extension))
                video_file_description = "第%s个视频" % video_index
                if self.download(video_url, video_file_path, video_file_description):
                    self.temp_path_list.append(video_file_path)  # 设置临时目录
                    self.total_video_count += 1  # 计数累加
                video_index += 1

        # todo 音频下载逻辑
        # 音频下载
        if self.main_thread.is_download_audio:
            self.parse_result(blog_description + "音频", blog_response["audio_url_list"])

            audio_index = 1
            for audio_url in blog_response["audio_url_list"]:
                file_extension = net.get_file_extension(audio_url)
                audio_file_path = os.path.join(self.main_thread.audio_download_path, self.index_key, "%04d.%s" % (audio_index, file_extension))
                audio_file_description = "第%s个音频" % audio_index
                if self.download(audio_url, audio_file_path, audio_file_description):
                    self.temp_path_list.append(audio_file_path)  # 设置临时目录
                    self.total_audio_count += 1  # 计数累加
                audio_index += 1

        # 日志内图片、视频和音频全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.single_save_data[1] = str(blog_id)  # 设置存档记录

    def done(self):
        if self.temp_path_list:
            for temp_path in self.temp_path_list:
                path.delete_dir_or_file(temp_path)


if __name__ == "__main__":
    Template().main()
