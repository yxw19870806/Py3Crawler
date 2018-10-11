# -*- coding:UTF-8  -*-
"""
新浪博客图片爬虫
http://blog.sina.com.cn/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import re
import time
import traceback
from pyquery import PyQuery as pq
from common import *
from project.weibo import weibo


# 获取指定页数的全部日志
def get_one_page_blog(account_id, page_count):
    # http://moexia.lofter.com/?page=1
    blog_pagination_url = "http://blog.sina.com.cn/s/articlelist_%s_0_%s.html" % (account_id, page_count)
    blog_pagination_response = net.http_request(blog_pagination_url, method="GET")
    result = {
        "blog_info_list": [],  # 全部日志地址
        "is_over": False,  # 是否最后一页日志
    }
    if blog_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(blog_pagination_response.status))
    blog_pagination_response_content = blog_pagination_response.data.decode(errors="ignore")
    if page_count == 1 and blog_pagination_response_content.find("抱歉，您要访问的页面不存在或被删除！") >= 0:
        raise crawler.CrawlerException("账号不存在")
    article_list_selector = pq(blog_pagination_response_content).find(".articleList .articleCell")
    if article_list_selector.length == 0:
        raise crawler.CrawlerException("页面截取日志列表失败\n%s" % blog_pagination_response_content)
    for article_index in range(article_list_selector.length):
        result_blog_info = {
            "blog_url": None,  # 日志地址
            "blog_time": None,  # 日志时间
            "blog_title": "",  # 日志标题
        }
        article_selector = article_list_selector.eq(article_index)
        # 获取日志地址
        blog_url = article_selector.find("span.atc_title a").attr("href")
        if not blog_url:
            raise crawler.CrawlerException("日志列表解析日志地址失败\n%s" % article_selector.html())
        result_blog_info["blog_url"] = blog_url
        # 获取日志标题
        blog_title = article_selector.find("span.atc_title a").text()
        if not blog_title:
            raise crawler.CrawlerException("日志列表解析日志标题失败\n%s" % article_selector.html())
        result_blog_info["blog_title"] = blog_title
        # 获取日志时间
        blog_time = article_selector.find("span.atc_tm").text()
        if not blog_time:
            raise crawler.CrawlerException("日志列表解析日志时间失败\n%s" % article_selector.html())
        try:
            result_blog_info["blog_time"] = int(time.mktime(time.strptime(blog_time, "%Y-%m-%d %H:%M")))
        except ValueError:
            raise crawler.CrawlerException("日志时间格式不正确\n%s" % blog_time)
        result["blog_info_list"].append(result_blog_info)
    # 获取分页信息
    pagination_selector = pq(blog_pagination_response_content).find("ul.SG_pages span")
    if pagination_selector.length == 0:
        if pq(blog_pagination_response_content).find("ul.SG_pages").length == 0:
            raise crawler.CrawlerException("页面截取分页信息失败\n%s" % blog_pagination_response_content)
        else:
            result["is_over"] = True
    else:
        max_page_count_find = re.findall("共(\d*)页", pagination_selector.html())
        if len(max_page_count_find) != 1:
            raise crawler.CrawlerException("分页信息截取总页数失败\n%s" % blog_pagination_response_content)
        result["is_over"] = page_count >= int(max_page_count_find[0])
    return result


# 获取日志
def get_blog_page(blog_url):
    blog_response = net.http_request(blog_url, method="GET")
    result = {
        "photo_url_list": [],  # 全部图片地址
    }
    if blog_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(blog_response.status))
    # 获取博客正文
    article_html = tool.find_sub_string(blog_response.data.decode(errors="ignore"), "<!-- 正文开始 -->", "<!-- 正文结束 -->")
    # 获取图片地址
    result["photo_url_list"] = re.findall('real_src ="([^"]*)"', article_html)
    # 获取全部图片地址
    return result


# 获取日志id
def get_blog_id(blog_url):
    return tool.find_sub_string(blog_url.split("/")[-1], "blog_", ".html")


# 获取图片原始地址
def get_photo_url(photo_url):
    if photo_url.find("&amp") >= 0:
        temp_list = photo_url.split("&amp")[0].split("/")
        temp_list[-2] = "orignal"
        photo_url = "/".join(temp_list)
    return photo_url


class SinaBlog(crawler.Crawler):
    def __init__(self):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
        }
        crawler.Crawler.__init__(self, sys_config)

        # 解析存档文件
        # account_name  last_blog_id
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

        log.step("全部下载完毕，耗时%s秒，共计图片%s张" % (self.get_run_time(), self.total_photo_count))


class Download(crawler.DownloadThread):
    def __init__(self, account_info, main_thread):
        crawler.DownloadThread.__init__(self, account_info, main_thread)
        self.account_id = self.account_info[0]
        if len(self.account_info) > 2 and self.account_info[2]:
            self.display_name = self.account_info[2]
        else:
            self.display_name = self.account_id
        self.step("开始")

    # 获取所有可下载日志
    def get_crawl_list(self):
        page_count = 1
        unique_list = []
        blog_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的日志
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析第%s页日志" % page_count)

            try:
                blog_pagination_response = get_one_page_blog(self.account_id, page_count)
            except crawler.CrawlerException as e:
                self.error("第%s页日志解析失败，原因：%s" % (page_count, e.message))
                raise

            self.trace("第%s页解析的全部日志：%s" % (page_count, blog_pagination_response["blog_info_list"]))
            self.step("第%s页解析获取%s个日志" % (page_count, len(blog_pagination_response["blog_info_list"])))

            # 寻找这一页符合条件的日志
            for blog_info in blog_pagination_response["blog_info_list"]:
                # 检查是否达到存档记录
                if blog_info["blog_time"] > int(self.account_info[1]):
                    # 新增日志导致的重复判断
                    if blog_info["blog_url"] in unique_list:
                        continue
                    else:
                        blog_info_list.append(blog_info)
                        unique_list.append(blog_info["blog_url"])
                else:
                    is_over = True
                    break

            if not is_over:
                if blog_pagination_response["is_over"]:
                    is_over = blog_pagination_response["is_over"]
                else:
                    page_count += 1

        return blog_info_list

    # 解析单个日志
    def crawl_blog(self, blog_info):
        # 获取日志
        try:
            blog_response = get_blog_page(blog_info["blog_url"])
        except crawler.CrawlerException as e:
            self.error("日志《%s》 %s 解析失败，原因：%s" % (blog_info["blog_title"], blog_info["blog_url"], e.message))
            raise

        self.trace("日志《%s》 %s 解析的全部图片：%s" % (blog_info["blog_title"], blog_info["blog_url"], blog_response["photo_url_list"]))
        self.step("日志《%s》 %s 解析获取%s张图片" % (blog_info["blog_title"], blog_info["blog_url"], len(blog_response["photo_url_list"])))

        photo_index = 1
        blog_id = get_blog_id(blog_info["blog_url"])
        # 过滤标题中不支持的字符
        blog_title = path.filter_text(blog_info["blog_title"])
        if blog_title:
            photo_path = os.path.join(self.main_thread.photo_download_path, self.display_name, "%s %s" % (blog_id, blog_title))
        else:
            photo_path = os.path.join(self.main_thread.photo_download_path, self.display_name, blog_id)
        self.temp_path_list.append(photo_path)
        for photo_url in blog_response["photo_url_list"]:
            self.main_thread_check()  # 检测主线程运行状态
            # 获取图片原始地址
            photo_url = get_photo_url(photo_url)
            self.step("日志《%s》 开始下载第%s张图片 %s" % (blog_info["blog_title"], photo_index, photo_url))

            file_path = os.path.join(photo_path, "%02d.%s" % (photo_index, net.get_file_type(photo_url, "jpg")))
            save_file_return = net.save_net_file(photo_url, file_path)
            if save_file_return["status"] == 1:
                if weibo.check_photo_invalid(file_path):
                    path.delete_dir_or_file(file_path)
                    self.error("第%s张图片 %s 资源已被删除，跳过" % (photo_index, photo_url))
                    continue
                else:
                    self.step("日志《%s》 第%s张图片下载成功" % (blog_info["blog_title"], photo_index))
                    photo_index += 1
            else:
                self.error("日志《%s》 第%s张图片 %s 下载失败，原因：%s" % (blog_info["blog_title"], photo_index, photo_url, crawler.download_failre(save_file_return["code"])))

        # 日志内图片全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.total_photo_count += photo_index - 1  # 计数累加
        self.account_info[1] = str(blog_info["blog_time"])  # 设置存档记录

    def run(self):
        try:
            # 获取所有可下载日志
            blog_info_list = self.get_crawl_list()
            self.step("需要下载的全部日志解析完毕，共%s个" % len(blog_info_list))

            # 从最早的日志开始下载
            while len(blog_info_list) > 0:
                blog_info = blog_info_list.pop()
                self.step("开始解析日志《%s》 %s" % (blog_info["blog_title"], blog_info["blog_url"]))
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
    SinaBlog().main()
