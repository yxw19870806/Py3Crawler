# -*- coding:UTF-8  -*-
"""
漫画柜漫画爬虫
https://www.manhuagui.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import lzstring
import os
import time
import traceback
from pyquery import PyQuery as pq
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from common import *

CACHE_FILE_PATH = os.path.join(os.path.dirname(__file__), "cache")
TEMPLATE_HTML_PATH = os.path.join(os.path.dirname(__file__), "template.html")


# 获取指定一页的图集
def get_comic_index_page(comic_id):
    # https://www.manhuagui.com/comic/21175/
    index_url = "https://www.manhuagui.com/comic/%s/" % comic_id
    index_response = net.request(index_url, method="GET")
    result = {
        "chapter_info_list": [],  # 漫画列表信息
    }
    if index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(index_response.status))
    index_response_content = index_response.data.decode(errors="ignore")
    chapter_info_selector = pq(index_response_content).find("div.chapter")
    if chapter_info_selector.length != 1:
        raise crawler.CrawlerException("页面截取漫画列表失败\n%s" % index_response_content)
    group_name_selector = chapter_info_selector.find("h4")
    if group_name_selector.length == 0:
        if pq(index_response_content).find("#__VIEWSTATE").length == 1:
            decompress_string = pq(index_response_content).find("#__VIEWSTATE").val()
            if decompress_string:
                decompress_html = lzstring.LZString().decompressFromBase64(decompress_string)
                chapter_info_selector.html(decompress_html)
                group_name_selector = chapter_info_selector.find("h4")
    group_chapter_list_selector = chapter_info_selector.find(".chapter-list")
    if group_name_selector.length != group_chapter_list_selector.length:
        raise crawler.CrawlerException("页面截取章节数量异常\n%s" % index_response_content)
    for group_index in range(0, group_name_selector.length):
        # 　获取分组名字
        group_name = group_name_selector.eq(group_index).text().strip()
        if not group_name:
            raise crawler.CrawlerException("章节信息截取章节名失败\n%s" % group_name_selector.eq(group_index).html())
        chapter_list_selector = group_chapter_list_selector.eq(group_index).find("li")
        if chapter_list_selector.length == 0:
            raise crawler.CrawlerException("章节信息截取章节内容失败\n%s" % group_chapter_list_selector.eq(group_index).html())
        for page_index in range(0, chapter_list_selector.length):
            result_comic_info = {
                "chapter_id": None,  # 章节id
                "chapter_name": None,  # 章节名
                "group_name": group_name,  # 漫画分组名字
            }
            chapter_selector = chapter_list_selector.eq(page_index)
            # 获取章节ID
            page_url = chapter_selector.find("a").attr("href")
            chapter_id = tool.find_sub_string(page_url, "/comic/%s/" % comic_id, ".html")
            if not crawler.is_integer(chapter_id):
                raise crawler.CrawlerException("页面地址截取页面id失败\n%s" % page_url)
            result_comic_info["chapter_id"] = int(chapter_id)
            # 获取章节名称
            chapter_name = chapter_selector.find("a").attr("title")
            if not chapter_name:
                raise crawler.CrawlerException("页面地址截取章节名失败\n%s" % page_url)
            result_comic_info["chapter_name"] = chapter_name.strip()
            result["chapter_info_list"].append(result_comic_info)
    return result


# 获取漫画指定章节
def get_chapter_page(comic_id, chapter_id):
    # https://www.manhuagui.com/comic/7580/562894.html
    chapter_url = "https://www.manhuagui.com/comic/%s/%s.html" % (comic_id, chapter_id)
    chapter_response = net.request(chapter_url, method="GET")
    result = {
        "photo_url_list": [],  # 全部漫画图片地址
    }
    if chapter_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(chapter_response.status))
    chapter_response_content = chapter_response.data.decode(errors="ignore")
    script_code = tool.find_sub_string(chapter_response_content, 'window["\\x65\\x76\\x61\\x6c"]', "</script>", 1)
    if not script_code:
        raise crawler.CrawlerException("页面截取脚本代码失败\n%s" % chapter_response_content)
    template_html = file.read_file(TEMPLATE_HTML_PATH)
    template_html = template_html.replace("%%SCRIPT_CODE%%", script_code)
    cache_html_path = os.path.realpath(os.path.join(CACHE_FILE_PATH, "%s.html" % comic_id))
    file.write_file(template_html, cache_html_path, file.WRITE_FILE_TYPE_REPLACE)
    chrome_options = webdriver.ChromeOptions()
    chrome_options.headless = True  # 不打开浏览器
    try:
        chrome = webdriver.Chrome(executable_path=crawler.CHROME_WEBDRIVER_PATH, options=chrome_options)
    except WebDriverException as e:
        message = str(e)
        if message.find("chrome not reachable") >= 0:
            return get_chapter_page(comic_id, chapter_id)
        else:
            raise
    chrome.get("file:///" + cache_html_path)
    result_photo_list = chrome.find_element(by=By.ID, value="result").text
    chrome.quit()
    path.delete_dir_or_file(cache_html_path)
    photo_list = result_photo_list.split("\n")
    for photo_url in photo_list:
        result["photo_url_list"].append("https://i.hamreus.com" + photo_url)
    return result


class ManHuaGui(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_NOT_CHECK_SAVE_DATA: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 解析存档文件
        # comic_name  last_chapter_id
        self.account_list = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

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

        # 删除临时缓存目录
        path.delete_dir_or_file(CACHE_FILE_PATH)

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

    # 获取所有可下载章节
    def get_crawl_list(self):
        chapter_info_list = {}

        # 获取漫画首页
        self.step("开始解析漫画首页")
        try:
            blog_pagination_response = get_comic_index_page(self.comic_id)
        except crawler.CrawlerException as e:
            self.error("漫画首页解析失败，原因：%s" % e.message)
            raise

        self.trace("漫画首页解析的全部章节：%s" % blog_pagination_response["chapter_info_list"])
        self.step("漫画首页解析获取%s个章节" % len(blog_pagination_response["chapter_info_list"]))

        # 寻找符合条件的章节
        for chapter_info in blog_pagination_response["chapter_info_list"]:
            # 检查是否达到存档记录
            if chapter_info["chapter_id"] > int(self.account_info[1]):
                chapter_info_list[chapter_info["chapter_id"]] = chapter_info

        return [chapter_info_list[key] for key in sorted(chapter_info_list.keys(), reverse=True)]

    # 解析单章节漫画
    def crawl_comic(self, chapter_info):
        self.step("开始解析漫画%s %s《%s》" % (chapter_info["chapter_id"], chapter_info["group_name"], chapter_info["chapter_name"]))

        # 获取指定漫画章节
        try:
            chapter_response = get_chapter_page(self.comic_id, chapter_info["chapter_id"])
        except crawler.CrawlerException as e:
            self.error("漫画%s %s《%s》解析失败，原因：%s" % (chapter_info["chapter_id"], chapter_info["group_name"], chapter_info["chapter_name"], e.message))
            raise

        # 图片下载
        photo_index = 1
        chapter_path = os.path.join(self.main_thread.photo_download_path, self.display_name, chapter_info["group_name"], "%06d %s" % (chapter_info["chapter_id"], path.filter_text(chapter_info["chapter_name"])))
        # 设置临时目录
        self.temp_path_list.append(chapter_path)
        for photo_url in chapter_response["photo_url_list"]:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("漫画%s %s《%s》开始下载第%s张图片 %s" % (chapter_info["chapter_id"], chapter_info["group_name"], chapter_info["chapter_name"], photo_index, photo_url))

            photo_file_path = os.path.join(chapter_path, "%03d.%s" % (photo_index, net.get_file_type(photo_url)))
            save_file_return = net.download(photo_url, photo_file_path, header_list={"Referer": "https://www.manhuagui.com/comic/%s/%s.html" % (self.comic_id, chapter_info["chapter_id"])}, is_auto_proxy=False)
            if save_file_return["status"] == 1:
                self.step("漫画%s %s《%s》第%s张图片下载成功" % (chapter_info["chapter_id"], chapter_info["group_name"], chapter_info["chapter_name"], photo_index))
            else:
                self.error("漫画%s %s《%s》第%s张图片 %s 下载失败，原因：%s" % (chapter_info["chapter_id"], chapter_info["group_name"], chapter_info["chapter_name"], photo_index, photo_url, crawler.download_failre(save_file_return["code"])))
            photo_index += 1

        # 媒体内图片全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.total_photo_count += photo_index - 1  # 计数累加
        self.account_info[1] = str(chapter_info["chapter_id"])  # 设置存档记录

    def run(self):
        try:
            # 获取所有可下载章节
            chapter_info_list = self.get_crawl_list()
            self.step("需要下载的全部漫画解析完毕，共%s个" % len(chapter_info_list))
            # 从最早的章节开始下载
            while len(chapter_info_list) > 0:
                self.crawl_comic(chapter_info_list.pop())
                self.main_thread_check()  # 检测主线程运行状态
        except (SystemExit, KeyboardInterrupt) as e:
            if isinstance(e, SystemExit) and e.code == 1:
                self.error("异常退出")
            else:
                self.step("提前退出")
            # 如果临时目录变量不为空，表示某个章节正在下载中，需要把下载了部分的内容给清理掉
            self.clean_temp_path()
        except Exception as e:
            self.error("未知异常")
            self.error(str(e) + "\n" + traceback.format_exc(), False)

        # 保存最后的信息
        with self.thread_lock:
            file.write_file("\t".join(self.account_info), self.main_thread.temp_save_data_path)
            self.main_thread.total_photo_count += self.total_photo_count
            self.main_thread.account_list.pop(self.comic_id)
        self.step("下载完毕，总共获得%s张图片" % self.total_photo_count)
        self.notify_main_thread()


if __name__ == "__main__":
    ManHuaGui().main()
