# -*- coding:UTF-8  -*-
"""
欅坂46公式Blog图片爬虫
https://www.keyakizaka46.com/mob/news/diarShw.php?cd=member
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import re
import time
import traceback
from common import *

PHOTO_COUNT_PER_PAGE = 20


# 获取指定页数的全部日志
def get_one_page_blog(account_id, page_count):
    # https://www.keyakizaka46.com/mob/news/diarKiji.php?cd=member&ct=01&page=0&rw=20
    blog_pagination_url = "https://www.keyakizaka46.com/mob/news/diarKiji.php"
    query_data = {
        "cd": "member",
        "ct": "%02d" % int(account_id),
        "page": str(page_count - 1),
        "rw": str(PHOTO_COUNT_PER_PAGE),
    }
    blog_pagination_response = net.http_request(blog_pagination_url, method="GET", fields=query_data)
    result = {
        "blog_info_list": [],  # 全部日志信息
    }
    if blog_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(blog_pagination_response.status))
    blog_pagination_response_content = blog_pagination_response.data.decode(errors="ignore")
    if len(tool.find_sub_string(blog_pagination_response_content, '<div class="box-profile">', "</div>").strip()) < 10:
        raise crawler.CrawlerException("账号不存在")
    # 日志正文部分
    blog_article_html = tool.find_sub_string(blog_pagination_response_content, '<div class="box-main">', '<div class="box-sideMember">')
    if not blog_article_html:
        raise crawler.CrawlerException("页面正文截取失败\n%s" % blog_pagination_response_content)
    blog_list = re.findall("<article>([\s|\S]*?)</article>", blog_article_html)
    for blog_info in blog_list:
        result_blog_info = {
            "blog_id" : None,  # 日志id
            "photo_url_list": [],  # 全部图片地址
        }
        # 获取日志id
        blog_id = tool.find_sub_string(blog_info, "/diary/detail/", "?")
        if not crawler.is_integer(blog_id):
            raise crawler.CrawlerException("日志页面截取日志id失败\n%s" % blog_info)
        result_blog_info["blog_id"] = int(blog_id)
        # 获取全部图片地址
        result_blog_info["photo_url_list"] = re.findall('<img[\S|\s]*?src="([^"]+)"', blog_info)
        result["blog_info_list"].append(result_blog_info)
    return result


# 检测图片地址是否包含域名，如果没有则补上
def get_photo_url(photo_url):
    # 如果图片地址没有域名，表示直接使用当前域名下的资源，需要拼接成完整的地址
    if photo_url[:7] != "http://" and photo_url[:8] != "https://":
        if photo_url[0] == "/":
            photo_url = "https://www.keyakizaka46.com%s" % photo_url
        else:
            photo_url = "https://www.keyakizaka46.com/%s" % photo_url
    return photo_url


class Diary(crawler.Crawler):
    def __init__(self):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
        }
        crawler.Crawler.__init__(self, sys_config)

        # 解析存档文件
        # account_id  last_blog_id
        self.account_list = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

    def main(self):
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

        # 未完成的数据保存
        if len(self.account_list) > 0:
            file.write_file(tool.list_to_string(list(self.account_list.values())), self.temp_save_data_path)

        # 重新排序保存存档文件
        crawler.rewrite_save_file(self.temp_save_data_path, self.save_data_path)

        log.step("全部下载完毕，耗时%s秒，共计图片%s张" % (self.get_run_time(), self.total_photo_count))


class Download(crawler.DownloadThread):
    def __init__(self, account_info, main_thread):
        crawler.DownloadThread.__init__(self, account_info, main_thread)
        self.account_id = self.account_info[0]
        if len(self.account_info) >= 4 and self.account_info[3]:
            self.display_name = self.account_info[3]
        else:
            self.display_name = self.account_info[0]
        self.step("开始")

    # 获取所有可下载日志
    def get_crawl_list(self):
        page_count = 1
        blog_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的日志
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析第%s页日志" % page_count)

            # 获取一页博客信息
            try:
                blog_pagination_response = get_one_page_blog(self.account_id, page_count)
            except crawler.CrawlerException as e:
                self.error("第%s页日志解析失败，原因：%s" % (page_count, e.message))
                raise

            # 没有获取到任何日志，全部日志已经全部获取完毕了
            if len(blog_pagination_response["blog_info_list"]) == 0:
                break

            self.trace("第%s页解析的全部日志：%s" % (page_count, blog_pagination_response["blog_info_list"]))
            self.step("第%s页解析获取%s个日志" % (page_count, len(blog_pagination_response["blog_info_list"])))

            # 寻找这一页符合条件的日志
            for blog_info in blog_pagination_response["blog_info_list"]:
                # 检查是否达到存档记录
                if blog_info["blog_id"] > int(self.account_info[1]):
                    blog_info_list.append(blog_info)
                else:
                    is_over = True
                    break

            if not is_over:
                page_count += 1

        return blog_info_list

    # 解析单个日志
    def crawl_blog(self, blog_info):
        photo_index = 1
        for photo_url in blog_info["photo_url_list"]:
            self.main_thread_check()  # 检测主线程运行状态
            # 检测图片地址是否包含域名
            photo_url = get_photo_url(photo_url)
            self.step("开始下载日志%s的第%s张图片 %s" % (blog_info["blog_id"], photo_index, photo_url))

            file_path = os.path.join(self.main_thread.photo_download_path, self.display_name, "%05d_%02d.%s" % (blog_info["blog_id"], photo_index, net.get_file_type(photo_url)))
            save_file_return = net.save_net_file(photo_url, file_path)
            if save_file_return["status"] == 1:
                self.temp_path_list.append(file_path)
                self.step("日志%s的第%s张图片下载成功" % (blog_info["blog_id"], photo_index))
            else:
                self.error("日志%s的第%s张图片 %s 下载失败，原因：%s" % (blog_info["blog_id"], photo_index, photo_url, crawler.download_failre(save_file_return["code"])))
            photo_index += 1

        # 日志内图片全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.total_photo_count += photo_index - 1  # 计数累加
        self.account_info[1] = str(blog_info["blog_id"])  # 设置存档记录

    def run(self):
        try:
            # 获取所有可下载日志
            blog_info_list = self.get_crawl_list()
            self.step("需要下载的全部日志解析完毕，共%s个" % len(blog_info_list))

            # 从最早的日志开始下载
            while len(blog_info_list) > 0:
                blog_info =  blog_info_list.pop()
                self.step("开始解析日志%s" % blog_info["blog_id"])
                self.trace("日志%s解析的全部图片：%s" % (blog_info["blog_id"], blog_info["photo_url_list"]))
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
            self.main_thread.account_list.pop(self.account_id)
        self.step("下载完毕，总共获得%s张图片" % self.total_photo_count)
        self.notify_main_thread()


if __name__ == "__main__":
    Diary().main()
