# -*- coding:UTF-8  -*-
"""
lofter图片爬虫
http://www.lofter.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import re
import time
from common import *

USER_AGENT = net._random_user_agent()
COOKIE_INFO = {}


def init_session():
    index_url = "http://www.lofter.com"
    header_list = {
        "User-Agent": USER_AGENT,
    }
    index_response = net.request(index_url, method="GET", header_list=header_list, is_auto_redirect=False, is_random_ip=False)
    if index_response.status in [net.HTTP_RETURN_CODE_SUCCEED, 302]:
        COOKIE_INFO.update(net.get_cookies_from_response_header(index_response.headers))


# 获取指定页数的全部日志
def get_one_page_blog(account_name, page_count):
    # http://moexia.lofter.com/?page=1
    blog_pagination_url = f"http://{account_name}.lofter.com/"
    query_data = {"page": page_count}
    header_list = {
        "User-Agent": USER_AGENT,
    }
    blog_pagination_response = net.request(blog_pagination_url, method="GET", fields=query_data, header_list=header_list, cookies_list=COOKIE_INFO, is_auto_redirect=False, is_random_ip=False)
    result = {
        "blog_url_list": [],  # 全部日志地址
    }
    if blog_pagination_response.status == 302:
        COOKIE_INFO.update(net.get_cookies_from_response_header(blog_pagination_response.headers))
        return get_one_page_blog(account_name, page_count)
    if page_count == 1 and blog_pagination_response.status == 404:
        raise crawler.CrawlerException("账号不存在")
    elif blog_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(blog_pagination_response.status))
    # 获取全部日志地址
    blog_url_list = re.findall('"(http://' + account_name + '.lofter.com/post/[^"]*)"', blog_pagination_response.data.decode(errors="ignore"))
    # 去重排序
    result["blog_url_list"] = sorted(list(set(blog_url_list)), reverse=True)
    return result


# 获取日志
def get_blog_page(blog_url):
    header_list = {
        "User-Agent": USER_AGENT,
    }
    blog_response = net.request(blog_url, method="GET", header_list=header_list, cookies_list=COOKIE_INFO, is_random_ip=False)
    result = {
        "photo_url_list": [],  # 全部图片地址
    }
    if blog_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(blog_response.status))
    # 获取全部图片地址
    result["photo_url_list"] = re.findall('bigimgsrc="([^"]*)"', blog_response.data.decode(errors="ignore"))
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
def check_photo_invalid(file_path):
    # http://imglf.nosdn.127.net/img/WWpvYmlBb3BlNCt0clU3WUNVb2U5UmhjMW56ZEh1TVFuc1BMVTI4aUR4OG0rNUdIK2xTbzNRPT0.jpg
    if os.path.getsize(file_path) == 31841 and file.get_file_md5(file_path) == "e4e09c4989d0f4db68610195b97688bf":
        return True
    return False


class Lofter(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 解析存档文件
        # account_name  last_blog_id
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

        init_session()

    def main(self):
        try:
            # 循环下载每个id
            thread_list = []
            for account_name in sorted(self.save_data.keys()):
                # 提前结束
                if not self.is_running():
                    break

                # 开始下载
                thread = Download(self.save_data[account_name], self)
                thread.start()
                thread_list.append(thread)

                time.sleep(1)

            # 等待子线程全部完成
            while len(thread_list) > 0:
                thread_list.pop().join()
        except KeyboardInterrupt:
            self.stop_process()

        # 未完成的数据保存
        self.write_remaining_save_data()

        # 重新排序保存存档文件
        self.rewrite_save_file()

        self.end_message()


class Download(crawler.DownloadThread):
    def __init__(self, single_save_data, main_thread):
        crawler.DownloadThread.__init__(self, single_save_data, main_thread)
        self.index_key = self.display_name = self.single_save_data[0]  # account name
        self.step("开始")

    def _run(self):
        # 获取所有可下载日志
        blog_url_list = self.get_crawl_list()
        self.step(f"需要下载的全部日志解析完毕，共{len(blog_url_list)}个")

        # 从最早的日志开始下载
        while len(blog_url_list) > 0:
            self.crawl_blog(blog_url_list.pop())
            self.main_thread_check()  # 检测主线程运行状态

    # 获取所有可下载日志
    def get_crawl_list(self):
        page_count = 1
        unique_list = []
        blog_url_list = []
        is_over = False
        # 获取全部还未下载过需要解析的日志
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step(f"开始解析第{page_count}页日志")

            try:
                blog_pagination_response = get_one_page_blog(self.index_key, page_count)
            except crawler.CrawlerException as e:
                self.error(e.http_error(f"第{page_count}页日志"))
                raise

            self.trace(f"第{page_count}页解析的全部日志：{blog_pagination_response['blog_url_list']}")
            self.step(f"第{page_count}页解析获取{len(blog_pagination_response['blog_url_list'])}个日志")

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
        self.step(f"开始解析日志 {blog_url}")

        # 获取日志
        try:
            blog_response = get_blog_page(blog_url)
        except crawler.CrawlerException as e:
            self.error(e.http_error(f"日志 {blog_url}"))
            raise

        self.trace(f"日志 {blog_url} 解析的全部图片：{blog_response['photo_url_list']}")
        self.step(f"日志 {blog_url} 解析获取{len(blog_response['photo_url_list'])}张图片")

        blog_id = get_blog_id(blog_url)
        photo_index = 1
        for photo_url in blog_response["photo_url_list"]:
            self.main_thread_check()  # 检测主线程运行状态
            # 去除图片地址的参数
            photo_url = get_photo_url(photo_url)
            self.step(f"开始下载日志{blog_id}的第{photo_index}张图片 {photo_url}")

            file_path = os.path.join(self.main_thread.photo_download_path, self.index_key, f"%09d_%02d.{net.get_file_extension(photo_url)}" % (blog_id, photo_index))
            save_file_return = net.download(photo_url, file_path)
            if save_file_return["status"] == 1:
                if check_photo_invalid(save_file_return["file_path"]):
                    path.delete_dir_or_file(save_file_return["file_path"])
                    self.error(f"日志{blog_id}({blog_url}) 第{photo_index}张图片 {photo_url} 已被屏蔽，删除")
                else:
                    self.temp_path_list.append(file_path)  # 设置临时目录
                    self.total_photo_count += 1  # 计数累加
                    self.step(f"日志{blog_id}的第{photo_index}张图片下载成功")
            else:
                self.error(f"日志{blog_id}({blog_url}) 第{photo_index}张图片 {photo_url} 下载失败，原因：{crawler.download_failre(save_file_return['code'])}")
                self.check_download_failure_exit()
            photo_index += 1

        # 日志内图片全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.single_save_data[1] = str(blog_id)  # 设置存档记录


if __name__ == "__main__":
    Lofter().main()
