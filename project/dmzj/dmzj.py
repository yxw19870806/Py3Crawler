# -*- coding:UTF-8  -*-
"""
动漫之家漫画爬虫
https://manhua.dmzj.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import threading
import time
import traceback
import urllib.parse
from common import *


# 获取指定一页的图集
def get_comic_index_page(comic_name):
    # https://m.dmzj.com/info/yiquanchaoren.html
    index_url = "https://m.dmzj.com/info/%s.html" % comic_name
    index_response = net.http_request(index_url, method="GET")
    result = {
        "comic_info_list": {},  # 漫画列表信息
    }
    if index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(index_response.status))
    index_response_content = index_response.data.decode(errors="ignore")
    comic_info_html = tool.find_sub_string(index_response_content, "initIntroData(", ");\n")
    if not comic_info_html:
        raise crawler.CrawlerException("漫画信息截取失败\n%s" % index_response_content)
    comic_info_data = tool.json_decode(comic_info_html)
    if not comic_info_data:
        raise crawler.CrawlerException("漫画信息加载失败\n%s" % comic_info_html)
    for chapter_info in comic_info_data:
        # 获取版本名字
        if not crawler.check_sub_key(("title",), chapter_info):
            raise crawler.CrawlerException("漫画版本信息'title'字段不存在\n%s" % chapter_info)
        version_name = chapter_info["title"]
        # 获取版本下各个章节
        if not crawler.check_sub_key(("data",), chapter_info):
            raise crawler.CrawlerException("漫画版本信息'data'字段不存在\n%s" % chapter_info)
        for comic_info in chapter_info["data"]:
            result_comic_info = {
                "comic_id": None,  # 漫画id
                "page_id": None,  # 页面id
                "chapter_name": "",  # 漫画章节名字
                "version_name": version_name,  # 漫画版本名字
            }
            # 获取漫画id
            if not crawler.check_sub_key(("comic_id",), comic_info):
                raise crawler.CrawlerException("漫画章节信息'comic_id'字段不存在\n%s" % comic_info)
            if not crawler.is_integer(comic_info["comic_id"]):
                raise crawler.CrawlerException("漫画章节信息'id'字段类型不正确在\n%s" % comic_info)
            result_comic_info["comic_id"] = int(comic_info["comic_id"])
            # 获取页面id
            if not crawler.check_sub_key(("id",), comic_info):
                raise crawler.CrawlerException("漫画章节信息'id'字段不存在\n%s" % comic_info)
            if not crawler.is_integer(comic_info["id"]):
                raise crawler.CrawlerException("漫画章节信息'id'字段类型不正确在\n%s" % comic_info)
            result_comic_info["page_id"] = int(comic_info["id"])
            # 获取章节名字
            if not crawler.check_sub_key(("chapter_name",), comic_info):
                raise crawler.CrawlerException("漫画章节信息'chapter_name'字段不存在\n%s" % comic_info)
            result_comic_info["chapter_name"] = comic_info["chapter_name"]
            result["comic_info_list"][result_comic_info["page_id"]] = result_comic_info
    return result


# 获取漫画指定章节
def get_chapter_page(comic_id, page_id):
    # https://m.dmzj.com/view/9949/19842.html
    chapter_url = "https://m.dmzj.com/view/%s/%s.html" % (comic_id, page_id)
    chapter_response = net.http_request(chapter_url, method="GET")
    result = {
        "photo_url_list": [],  # 全部漫画图片地址
    }
    if chapter_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(chapter_response.status))
    chapter_response_content = chapter_response.data.decode(errors="ignore")
    chapter_info_html = tool.find_sub_string(chapter_response_content, "mReader.initData(", ");")
    chapter_info_html = chapter_info_html[0:chapter_info_html.rfind("},") + 1]
    if not chapter_info_html:
        raise crawler.CrawlerException("章节信息截取失败\n%s" % chapter_response_content)
    chapter_info_data = tool.json_decode(chapter_info_html)
    if not chapter_info_data:
        raise crawler.CrawlerException("章节信息加载失败\n%s" % chapter_info_html)
    if not crawler.check_sub_key(("page_url",), chapter_info_data):
        raise crawler.CrawlerException("章节信息'page_url'字段不存在\n%s" % chapter_info_data)
    if not isinstance(chapter_info_data["page_url"], list):
        raise crawler.CrawlerException("章节信息'id'字段类型不正确在\n%s" % chapter_info_data)
    for photo_url in chapter_info_data["page_url"]:
        result["photo_url_list"].append(photo_url)
    return result


# 特殊符号转义
def get_photo_url(photo_url):
    photo_url_split = urllib.parse.urlsplit(photo_url)
    return photo_url_split[0] + "://" + photo_url_split[1] + urllib.parse.quote(photo_url_split[2])


class DMZJ(crawler.Crawler):
    def __init__(self):
        # 设置APP目录
        tool.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_NOT_CHECK_SAVE_DATA: True,
        }
        crawler.Crawler.__init__(self, sys_config)

        # 解析存档文件
        # comic_name  last_page_id
        self.account_list = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

    def main(self):
        # 循环下载每个id
        main_thread_count = threading.activeCount()
        for account_id in sorted(self.account_list.keys()):
            # 检查正在运行的线程数
            if threading.activeCount() >= self.thread_count + main_thread_count:
                self.wait_sub_thread()

            # 提前结束
            if not self.is_running():
                break

            # 开始下载
            thread = Download(self.account_list[account_id], self)
            thread.start()

            time.sleep(1)

        # 检查除主线程外的其他所有线程是不是全部结束了
        while threading.activeCount() > main_thread_count:
            self.wait_sub_thread()

        # 未完成的数据保存
        if len(self.account_list) > 0:
            tool.write_file(tool.list_to_string(list(self.account_list.values())), self.temp_save_data_path)

        # 重新排序保存存档文件
        crawler.rewrite_save_file(self.temp_save_data_path, self.save_data_path)

        log.step("全部下载完毕，耗时%s秒，共计图片%s张" % (self.get_run_time(), self.total_photo_count))


class Download(crawler.DownloadThread):
    def __init__(self, account_info, main_thread):
        crawler.DownloadThread.__init__(self, account_info, main_thread)
        self.comic_id = self.account_info[0]
        if len(self.account_info) >= 3 and self.account_info[2]:
            self.display_name = self.account_info[2]
        else:
            self.display_name = self.comic_id
        self.step("开始")

    # 获取所有可下载日志
    def get_crawl_list(self):
        comic_info_list = []

        # 获取漫画首页
        self.step("开始解析漫画首页")
        try:
            blog_pagination_response = get_comic_index_page(self.comic_id)
        except crawler.CrawlerException as e:
            self.error("漫画首页解析失败，原因：%s" % e.message)
            raise

        self.trace("漫画首页解析的全部漫画：%s" % blog_pagination_response["comic_info_list"])
        self.step("漫画首页解析获取%s个漫画" % len(blog_pagination_response["comic_info_list"]))

        # 寻找这一页符合条件的媒体
        for page_id in sorted(list(blog_pagination_response["comic_info_list"].keys()), reverse=True):
            comic_info = blog_pagination_response["comic_info_list"][page_id]
            # 检查是否达到存档记录
            if page_id > int(self.account_info[1]):
                comic_info_list.append(comic_info)
            else:
                break

        return comic_info_list

    # 解析单章节漫画
    def crawl_comic(self, comic_info):
        # 获取指定漫画章节
        try:
            chapter_response = get_chapter_page(comic_info["comic_id"], comic_info["page_id"])
        except crawler.CrawlerException as e:
            self.error("漫画%s %s《%s》解析失败，原因：%s" % (comic_info["page_id"], comic_info["version_name"], comic_info["chapter_name"], e.message))
            raise

        # 图片下载
        photo_index = 1
        chapter_path = os.path.join(self.main_thread.photo_download_path, self.display_name, comic_info["version_name"], "%06d %s" % (comic_info["page_id"], comic_info["chapter_name"]))
        # 设置临时目录
        self.temp_path_list.append(chapter_path)
        for photo_url in chapter_response["photo_url_list"]:
            photo_url = get_photo_url(photo_url)
            self.main_thread_check()  # 检测主线程运行状态
            self.step("漫画%s %s《%s》开始下载第%s张图片 %s" % (comic_info["page_id"], comic_info["version_name"], comic_info["chapter_name"], photo_index, photo_url))

            photo_file_path = os.path.join(chapter_path, "%03d.%s" % (photo_index, net.get_file_type(photo_url)))
            save_file_return = net.save_net_file(photo_url, photo_file_path, header_list={"Referer": "https://m.dmzj.com/"})
            if save_file_return["status"] == 1:
                self.step("漫画%s %s《%s》第%s张图片下载成功" % (comic_info["page_id"], comic_info["version_name"], comic_info["chapter_name"], photo_index))
                photo_index += 1
            else:
                self.error("漫画%s %s《%s》第%s张图片 %s 下载失败，原因：%s" % (comic_info["page_id"], comic_info["version_name"], comic_info["chapter_name"], photo_index, photo_url, crawler.download_failre(save_file_return["code"])))

        # 媒体内图片全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.total_photo_count += photo_index - 1  # 计数累加
        self.account_info[1] = str(comic_info["comic_id"])  # 设置存档记录

    def run(self):
        try:
            # 获取所有可下载日志
            comic_info_list = self.get_crawl_list()
            self.step("需要下载的全部漫画解析完毕，共%s个" % len(comic_info_list))

            # 从最早的日志开始下载
            while len(comic_info_list) > 0:
                comic_info = comic_info_list.pop()
                self.step("开始解析漫画%s %s《%s》" % (comic_info["page_id"], comic_info["version_name"], comic_info["chapter_name"]))
                self.crawl_comic(comic_info)
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
            tool.write_file("\t".join(self.account_info), self.main_thread.temp_save_data_path)
            self.main_thread.total_photo_count += self.total_photo_count
            self.main_thread.account_list.pop(self.comic_id)
        self.step("下载完毕，总共获得%s张图片" % self.total_photo_count)
        self.notify_main_thread()


if __name__ == "__main__":
    DMZJ().main()
