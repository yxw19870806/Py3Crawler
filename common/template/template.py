# -*- coding:UTF-8  -*-
"""
模板
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import json
import os
import re
import time
import traceback
from common import *


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
        self.account_list = crawler.read_save_data(self.save_data_path, 0, ["", ])

    def main(self):
        try:
            # 循环下载每个id
            thread_list = []
            for account_id in sorted(self.account_list.keys()):
                # 提前结束
                if not self.is_running():
                    break

                # 开始下载
                thread = Download(self.account_list[account_id], self)
                thread.start()
                thread_list.append(thread)

                time.sleep(1)

            # 等待子线程全部完成
            while len(thread_list) > 0:
                thread_list.pop().join()
        except KeyboardInterrupt:
            self.stop_process()

        # 未完成的数据保存
        if len(self.account_list) > 0:
            file.write_file(tool.list_to_string(list(self.account_list.values())), self.temp_save_data_path)

        # 重新排序保存存档文件
        crawler.rewrite_save_file(self.temp_save_data_path, self.save_data_path)

        # todo 是否需要下载图片或视频
        log.step("全部下载完毕，耗时%s秒，共计图片%s张，视频%s个，音频%s个" % (self.get_run_time(), self.total_photo_count, self.total_video_count, self.total_audio_count))


class Download(crawler.DownloadThread):
    def __init__(self, account_info, main_thread):
        crawler.DownloadThread.__init__(self, account_info, main_thread)
        self.account_id = self.account_info[0]
        # 日志前缀
        self.display_name = self.account_info[0]
        self.step("开始")

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
                blog_pagination_response = get_one_page_blog(self.account_id, page_count)
            except crawler.CrawlerException as e:
                self.error("第%s页日志解析失败，原因：%s" % (page_count, e.message))
                raise

            self.trace("第%s页解析的全部日志：%s" % (page_count, blog_pagination_response["blog_id_list"]))

            # 寻找这一页符合条件的媒体
            for blog_id in blog_pagination_response["blog_id_list"]:
                # 检查是否达到存档记录
                if int(blog_id) > int(self.account_info[3]):
                    blog_id_list.append(blog_id)
                else:
                    is_over = True
                    break

        return blog_id_list

    # 解析单个日志
    def crawl_blog(self, blog_id):
        # todo 日志解析规则
        # 获取指定日志
        try:
            blog_response = get_blog_page(self.account_id, blog_id)
        except crawler.CrawlerException as e:
            self.error("日志%s解析失败，原因：%s" % (blog_id, e.message))
            raise

        # todo 图片下载逻辑
        # 图片下载
        photo_index = self.account_info[1] + 1
        if self.main_thread.is_download_photo:
            for photo_url in blog_response["photo_url_list"]:
                self.main_thread_check()  # 检测主线程运行状态
                self.step("开始下载第%s张图片 %s" % (photo_index, photo_url))

                file_type = net.get_file_type(photo_url)
                photo_file_path = os.path.join(self.main_thread.photo_download_path, self.account_id, "%04d.%s" % (photo_index, file_type))
                save_file_return = net.save_net_file(photo_url, photo_file_path)
                if save_file_return["status"] == 1:
                    # 设置临时目录
                    self.temp_path_list.append(photo_file_path)
                    self.step("第%s张图片下载成功" % photo_index)
                    photo_index += 1
                else:
                    self.error("第%s张图片 %s 下载失败，原因：%s" % (photo_index, photo_url, crawler.download_failre(save_file_return["code"])))

        # todo 视频下载逻辑
        # 视频下载
        video_index = self.account_info[2] + 1
        if self.main_thread.is_download_video:
            for video_url in blog_response["video_url_list"]:
                self.main_thread_check()  # 检测主线程运行状态
                self.step("开始下载第%s个视频 %s" % (video_index, video_url))

                file_type = net.get_file_type(video_url)
                video_file_path = os.path.join(self.main_thread.video_download_path, self.account_id, "%04d.%s" % (video_index, file_type))
                save_file_return = net.save_net_file(video_url, video_file_path)
                if save_file_return["status"] == 1:
                    # 设置临时目录
                    self.temp_path_list.append(video_file_path)
                    self.step("第%s个视频下载成功" % video_index)
                    video_index += 1
                else:
                    self.error("第%s个视频 %s 下载失败，原因：%s" % (video_index, video_url, crawler.download_failre(save_file_return["code"])))

        # todo 音频下载逻辑
        # 音频下载
        audio_index = self.account_info[2] + 1
        if self.main_thread.is_download_audio:
            for audio_url in blog_response["audio_url_list"]:
                self.main_thread_check()  # 检测主线程运行状态
                self.step("开始下载第%s个音频 %s" % (audio_index, audio_url))

                file_type = net.get_file_type(audio_url)
                audio_file_path = os.path.join(self.main_thread.audio_download_path, self.account_id, "%04d.%s" % (audio_index, file_type))
                save_file_return = net.save_net_file(audio_url, audio_file_path)
                if save_file_return["status"] == 1:
                    # 设置临时目录
                    self.temp_path_list.append(audio_file_path)
                    self.step("第%s个音频下载成功" % audio_index)
                    audio_index += 1
                else:
                    self.error("第%s个音频 %s 下载失败，原因：%s" % (audio_index, audio_url, crawler.download_failre(save_file_return["code"])))

        # 日志内图片、视频和音频全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.total_photo_count += (photo_index - 1) - int(self.account_info[1])  # 计数累加
        self.total_video_count += (video_index - 1) - int(self.account_info[2])  # 计数累加
        self.total_audio_count += (audio_index - 1) - int(self.account_info[3])  # 计数累加
        self.account_info[1] = str(photo_index - 1)  # 设置存档记录
        self.account_info[2] = str(video_index - 1)  # 设置存档记录
        self.account_info[3] = str(audio_index - 1)  # 设置存档记录
        self.account_info[4] = ""  # 设置存档记录

    def run(self):
        try:
            # 获取所有可下载日志
            blog_id_list = self.get_crawl_list()
            self.step("需要下载的全部日志解析完毕，共%s个" % len(blog_id_list))

            # 从最早的日志开始下载
            while len(blog_id_list) > 0:
                blog_id = blog_id_list.pop()
                self.step("开始解析日志%s" % blog_id)
                self.crawl_blog(blog_id)
                self.main_thread_check()  # 检测主线程运行状态
        except (SystemExit, KeyboardInterrupt) as e:
            if isinstance(e, SystemExit) and e.code == 1:
                self.error("异常退出")
            else:
                self.step("提前退出")
            # 如果临时目录变量不为空，表示某个日志正在下载中，需要把下载了部分的内容给清理掉
            self.clean_temp_path()
        except Exception as e:
            self.error("未知异常")
            self.error(str(e) + "\n" + traceback.format_exc(), False)

        # 保存最后的信息
        with self.thread_lock:
            file.write_file("\t".join(self.account_info), self.main_thread.temp_save_data_path)
            self.main_thread.total_photo_count += self.total_photo_count
            self.main_thread.total_video_count += self.total_video_count
            self.main_thread.total_audio_count += self.total_audio_count
            self.main_thread.account_list.pop(self.account_id)
        self.step("下载完毕，总共获得%s张图片、%s个视频、%s个音频" % (self.total_photo_count, self.total_video_count, self.total_audio_count))
        self.notify_main_thread()


if __name__ == "__main__":
    Template().main()
