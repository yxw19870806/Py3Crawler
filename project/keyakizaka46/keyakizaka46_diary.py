# -*- coding:UTF-8  -*-
"""
欅坂46公式Blog图片爬虫
https://www.keyakizaka46.com/mob/news/diarShw.php?cd=member
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import time
import traceback
from pyquery import PyQuery as pq
from common import *

EACH_PAGE_BLOG_COUNT = 20  # 每次请求获取的日志数量


# 获取指定页数的全部日志
def get_one_page_blog(account_id, page_count):
    # https://www.keyakizaka46.com/s/k46o/diary/member/list?ima=0000&page=1&cd=member&ct=13
    blog_pagination_url = "https://www.keyakizaka46.com/s/k46o/diary/member/list"
    query_data = {
        "cd": "member",
        "ct": "%02d" % int(account_id),
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
    account_info_html = pq(blog_pagination_response_content).find(".box-profile").html()
    if account_info_html is None or not account_info_html.strip():
        raise crawler.CrawlerException("账号不存在")
    # 日志正文部分
    blog_list_selector = pq(blog_pagination_response_content).find(".box-main article")
    if blog_list_selector.length == 0:
        raise crawler.CrawlerException("页面截取日志列表失败\n" + blog_pagination_response_content)
    for blog_index in range(0, blog_list_selector.length):
        result_blog_info = {
            "blog_id": None,  # 日志id
            "photo_url_list": [],  # 全部图片地址
        }
        blog_selector = blog_list_selector.eq(blog_index)
        # 获取日志id
        blog_url = blog_selector.find(".box-ttl h3 a").attr("href")
        if not blog_url:
            raise crawler.CrawlerException("日志信息截取日志地址失败\n" + blog_selector.html())
        blog_id = blog_url.split("/")[-1].split("?")[0]
        if not tool.is_integer(blog_id):
            raise crawler.CrawlerException(f"日志地址 {blog_url} 截取日志id失败\n")
        result_blog_info["blog_id"] = int(blog_id)
        # 获取图片地址
        photo_list_selector = pq(blog_selector).find("img")
        for photo_index in range(0, photo_list_selector.length):
            photo_selector = photo_list_selector.eq(photo_index)
            # 跳过表情
            if photo_selector.has_class("emoji"):
                continue
            photo_url = photo_selector.attr("src")
            if not photo_url:
                continue
            result_blog_info["photo_url_list"].append(photo_url)
        result["blog_info_list"].append(result_blog_info)
    last_pagination_html = pq(blog_pagination_response_content).find(".pager li:last").text()
    if not last_pagination_html and pq(blog_pagination_response_content).find(".pager").length > 0:
        raise crawler.CrawlerException("页面截取下一页按钮失败\n" + blog_pagination_response_content)
    result["is_over"] = last_pagination_html != ">"
    return result


class Keyakizaka46Diary(crawler.Crawler):
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

    def main(self):
        try:
            # 循环下载每个id
            thread_list = []
            for account_id in sorted(self.save_data.keys()):
                # 提前结束
                if not self.is_running():
                    break

                # 开始下载
                thread = Download(self.save_data[account_id], self)
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
        self.account_id = self.single_save_data[0]
        if len(self.single_save_data) >= 3 and self.single_save_data[2]:
            self.display_name = self.single_save_data[2]
        else:
            self.display_name = self.single_save_data[0]
        self.step("开始")

    # 获取所有可下载日志
    def get_crawl_list(self):
        page_count = 1
        blog_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的日志
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step(f"开始解析第{page_count}页日志")

            # 获取一页博客信息
            try:
                blog_pagination_response = get_one_page_blog(self.account_id, page_count)
            except crawler.CrawlerException as e:
                self.error(e.http_error(f"第{page_count}页日志"))
                raise

            self.trace(f"第{page_count}页解析的全部日志：{blog_pagination_response['blog_info_list']}")
            self.step(f"第{page_count}页解析获取{len(blog_pagination_response['blog_info_list'])}个日志")

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
        self.step(f"开始解析日志{blog_info['blog_id']}")

        self.trace(f"日志{blog_info['blog_id']}解析的全部图片：{blog_info['photo_url_list']}")
        self.step(f"日志{blog_info['blog_id']}解析获取{len(blog_info['photo_url_list'])}张图片")

        photo_index = 1
        for photo_url in blog_info["photo_url_list"]:
            self.main_thread_check()  # 检测主线程运行状态
            self.step(f"开始下载日志{blog_info['blog_id']}的第{photo_index}张图片 {photo_url}")

            file_path = os.path.join(self.main_thread.photo_download_path, self.display_name, f"%05d_%02d.{net.get_file_extension(photo_url)}" % (blog_info["blog_id"], photo_index))
            save_file_return = net.download(photo_url, file_path)
            if save_file_return["status"] == 1:
                self.temp_path_list.append(file_path)  # 设置临时目录
                self.total_photo_count += 1  # 计数累加
                self.step(f"日志{blog_info['blog_id']}的第{photo_index}张图片下载成功")
            else:
                self.error(f"日志{blog_info['blog_id']}的第{photo_index}张图片 {photo_url} 下载失败，原因：{crawler.download_failre(save_file_return['code'])}")
                self.check_download_failure_exit()
            photo_index += 1

        # 日志内图片全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.single_save_data[1] = str(blog_info["blog_id"])  # 设置存档记录

    def run(self):
        try:
            # 获取所有可下载日志
            blog_info_list = self.get_crawl_list()
            self.step(f"需要下载的全部日志解析完毕，共{len(blog_info_list)}个")

            # 从最早的日志开始下载
            while len(blog_info_list) > 0:
                self.crawl_blog(blog_info_list.pop())
                self.main_thread_check()  # 检测主线程运行状态
        except (SystemExit, KeyboardInterrupt) as e:
            if isinstance(e, SystemExit) and e.code == 1:
                self.error("异常退出")
            else:
                self.step("提前退出")
        except Exception as e:
            self.error("未知异常")
            self.error(str(e) + "\n" + traceback.format_exc(), False)

        self.main_thread.save_data.pop(self.account_id)
        self.done()


if __name__ == "__main__":
    Keyakizaka46Diary().main()
