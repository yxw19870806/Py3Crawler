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
import traceback
from common import *

INIT_TARGET_ID = "99999"
MESSAGE_COUNT_PER_PAGE = 30


# 获取talk首页
def get_index_page(account_name):
    index_url = "https://7gogo.jp/%s" % account_name
    index_response = net.http_request(index_url, method="GET")
    if index_response.status == 404:
        raise crawler.CrawlerException("talk已被删除")
    return index_response


# 获取指定页数的全部日志信息
def get_one_page_blog(account_name, target_id):
    blog_pagination_url = "https://api.7gogo.jp/web/v2/talks/%s/images" % account_name
    query_data = {
        "targetId": target_id,
        "limit": MESSAGE_COUNT_PER_PAGE,
        "direction": "PREV",
    }
    blog_pagination_response = net.http_request(blog_pagination_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "blog_info_list": [],  # 全部日志信息
    }
    if target_id == INIT_TARGET_ID and blog_pagination_response.status == 400:
        raise crawler.CrawlerException("talk不存在")
    elif blog_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(blog_pagination_response.status))
    if not crawler.check_sub_key(("data",), blog_pagination_response.json_data):
        raise crawler.CrawlerException("返回信息'data'字段不存在\n%s" % blog_pagination_response.json_data)
    if not isinstance(blog_pagination_response.json_data["data"], list):
        raise crawler.CrawlerException("返回信息'data'字段类型不正确\n%s" % blog_pagination_response.json_data)
    for blog_info in blog_pagination_response.json_data["data"]:
        result_blog_info = {
            "blog_id": None,  # 日志id
            "photo_url_list": [],  # 全部图片地址
            "video_url_list": [],  # 全部视频地址
        }
        if not crawler.check_sub_key(("post",), blog_info):
            raise crawler.CrawlerException("日志信息'post'字段不存在\n%s" % blog_info)
        # 获取日志id
        if not crawler.check_sub_key(("postId",), blog_info["post"]):
            raise crawler.CrawlerException("日志信息'postId'字段不存在\n%s" % blog_info)
        if not crawler.is_integer(blog_info["post"]["postId"]):
            raise crawler.CrawlerException("日志信息'postId'类型不正确n%s" % blog_info)
        result_blog_info["blog_id"] = int(blog_info["post"]["postId"])
        # 获取日志内容
        if not crawler.check_sub_key(("body",), blog_info["post"]):
            raise crawler.CrawlerException("日志信息'body'字段不存在\n%s" % blog_info)
        for blog_body in blog_info["post"]["body"]:
            if not crawler.check_sub_key(("bodyType",), blog_body):
                raise crawler.CrawlerException("日志信息'bodyType'字段不存在\n%s" % blog_body)
            if not crawler.is_integer(blog_body["bodyType"]):
                raise crawler.CrawlerException("日志信息'bodyType'字段类型不正确\n%s" % blog_body)
            # bodyType = 1: text, bodyType = 3: photo, bodyType = 8: video
            body_type = int(blog_body["bodyType"])
            if body_type == 1:  # 文本
                continue
            elif body_type == 2:  # 表情
                continue
            elif body_type == 3:  # 图片
                if not crawler.check_sub_key(("image",), blog_body):
                    raise crawler.CrawlerException("日志信息'image'字段不存在\n%s" % blog_body)
                result_blog_info["photo_url_list"].append(blog_body["image"])
            elif body_type == 7:  # 转发
                continue
            elif body_type == 8:  # video
                if not crawler.check_sub_key(("movieUrlHq",), blog_body):
                    raise crawler.CrawlerException("日志信息'movieUrlHq'字段不存在\n%s" % blog_body)
                result_blog_info["video_url_list"].append(blog_body["movieUrlHq"])
            else:
                raise crawler.CrawlerException("日志信息'bodyType'字段取值不正确\n%s" % blog_body)
        result["blog_info_list"].append(result_blog_info)
    return result


class NanaGoGo(crawler.Crawler):
    def __init__(self):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_DOWNLOAD_VIDEO: True,
            crawler.SYS_SET_PROXY: True,
        }
        crawler.Crawler.__init__(self, sys_config)

        # 解析存档文件
        # account_name  last_post_id
        self.account_list = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

    def main(self):
        # 循环下载每个id
        thread_list = []
        for account_name in sorted(self.account_list.keys()):
            # 提前结束
            if not self.is_running():
                break

            # 开始下载
            thread = Download(self.account_list[account_name], self)
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

        log.step("全部下载完毕，耗时%s秒，共计图片%s张，视频%s个" % (self.get_run_time(), self.total_photo_count, self.total_video_count))


class Download(crawler.DownloadThread):
    def __init__(self, account_info, main_thread):
        crawler.DownloadThread.__init__(self, account_info, main_thread)
        self.account_name = self.account_info[0]
        self.display_name = self.account_name
        self.step("开始")

    # 获取所有可下载日志
    def get_crawl_list(self):
        target_id = INIT_TARGET_ID
        blog_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的日志
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析target：%s页" % target_id)

            # 获取一页日志信息
            try:
                blog_pagination_response = get_one_page_blog(self.account_name, target_id)
            except crawler.CrawlerException as e:
                self.error("target：%s页解析失败，原因：%s" % (target_id, e.message))
                raise

            # 如果为空，表示已经取完了
            if len(blog_pagination_response["blog_info_list"]) == 0:
                break

            self.trace("target：%s页解析的全部日志：%s" % (target_id, blog_pagination_response["blog_info_list"]))
            self.step("target：%s页解析获取%s个日志" % (target_id, len(blog_pagination_response["blog_info_list"])))

            # 寻找这一页符合条件的日志
            for blog_info in blog_pagination_response["blog_info_list"]:
                # 检查是否达到存档记录
                if blog_info["blog_id"] > int(self.account_info[1]):
                    blog_info_list.append(blog_info)
                    # 设置下一页指针
                    target_id = blog_info["blog_id"]
                else:
                    is_over = True
                    break

        return blog_info_list

    # 解析单个日志
    def crawl_blog(self, blog_info):
        # 图片下载
        photo_index = 1
        if self.main_thread.is_download_photo:
            self.trace("日志%s解析的全部图片：%s" % (blog_info["blog_id"], blog_info["photo_url_list"]))
            self.step("日志%s解析获取%s张图片" % (blog_info["blog_id"], len(blog_info["photo_url_list"])))

            for photo_url in blog_info["photo_url_list"]:
                self.main_thread_check()  # 检测主线程运行状态
                self.step("开始下载日志%s的第%s张图片 %s" % (blog_info["blog_id"], photo_index, photo_url))

                photo_file_path = os.path.join(self.main_thread.photo_download_path, self.account_name, "%05d_%02d.%s" % (blog_info["blog_id"], photo_index, net.get_file_type(photo_url)))
                save_file_return = net.save_net_file(photo_url, photo_file_path)
                if save_file_return["status"] == 1:
                    self.temp_path_list.append(photo_file_path)
                    self.step("日志%s的第%s张图片下载成功" % (blog_info["blog_id"], photo_index))
                else:
                    self.error("日志%s第%s张图片 %s 下载失败，原因：%s" % (blog_info["blog_id"], photo_index, photo_url, crawler.download_failre(save_file_return["code"])))
                photo_index += 1

        # 视频下载
        video_index = 1
        if self.main_thread.is_download_video:
            self.trace("日志%s解析的全部视频：%s" % (blog_info["blog_id"], blog_info["video_url_list"]))
            self.step("日志%s解析获取%s个视频" % (blog_info["blog_id"], len(blog_info["video_url_list"])))

            for video_url in blog_info["video_url_list"]:
                self.main_thread_check()  # 检测主线程运行状态
                self.step("开始下载日志%s的第%s个视频 %s" % (blog_info["blog_id"], video_index, video_url))

                video_file_path = os.path.join(self.main_thread.video_download_path, self.account_name, "%05d_%02d.%s" % (blog_info["blog_id"], video_index, net.get_file_type(video_url)))
                save_file_return = net.save_net_file(video_url, video_file_path)
                if save_file_return["status"] == 1:
                    self.temp_path_list.append(video_file_path)
                    self.step("日志%s的第%s个视频下载成功" % (blog_info["blog_id"], video_index))
                else:
                    self.error("日志%s的第%s个视频 %s 下载失败，原因：%s" % (blog_info["blog_id"], video_index, video_url, crawler.download_failre(save_file_return["code"])))
                video_index += 1

        # 日志内图片和视频全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.total_photo_count += photo_index - 1  # 计数累加
        self.total_video_count += video_index - 1  # 计数累加
        self.account_info[1] = str(blog_info["blog_id"])

    def run(self):
        try:
            # 获取首页
            try:
                get_index_page(self.account_name)
            except crawler.CrawlerException as e:
                self.error("首页访问失败，原因：%s" % e.message)
                raise

            # 获取所有可下载日志
            blog_info_list = self.get_crawl_list()
            self.step("需要下载的全部日志解析完毕，共%s个" % len(blog_info_list))

            # 从最早的日志开始下载
            while len(blog_info_list) > 0:
                blog_info = blog_info_list.pop()
                self.step("开始解析日志%s" % blog_info["blog_id"])
                self.crawl_blog(blog_info)
                self.main_thread_check()  # 检测主线程运行状态
        except SystemExit as se:
            if se.code == 0:
                self.step("提前退出")
            else:
                self.error("异常退出")
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
            self.main_thread.account_list.pop(self.account_name)
        self.step("下载完毕，总共获得%s张图片，%s个视频" % (self.total_photo_count, self.total_video_count))
        self.notify_main_thread()


if __name__ == "__main__":
    NanaGoGo().main()
