# -*- coding:UTF-8  -*-
"""
起点网小说爬虫
https://manhua.dmzj.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import time
from pyquery import PyQuery as pq
from common import *


# 获取指定一页的章节
def get_book_index(book_id):
    # https://book.qidian.com/info/1016397637/
    index_url = f"https://book.qidian.com/info/{book_id}/"
    index_response = net.request(index_url, method="GET")
    result = {
        "chapter_info_list": [],  # 章节信息列表
    }
    if index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(index_response.status))
    index_response_content = index_response.data.decode(errors="ignore")
    chapter_info_list_selector = pq(index_response_content).find(".catalog-content-wrap .cf li")
    if chapter_info_list_selector.length == 0:
        raise crawler.CrawlerException("页面截取章节列表失败\n" + index_response_content)
    for chapter_index in range(0, chapter_info_list_selector.length):
        result_chapter_info = {
            "chapter_url": None,  # 章节地址
            "chapter_id": None,  # 章节id
            "chapter_time": None,  # 章节发布时间
            "chapter_time_string": None,  # 章节发布时间
            "chapter_title": "",  # 章节标题
        }
        chapter_info_selector = chapter_info_list_selector.eq(chapter_index)
        # 获取章节地址
        result_chapter_info["chapter_url"] = chapter_info_selector.find("a").attr("href")
        if result_chapter_info["chapter_url"][:2] == "//":
            result_chapter_info["chapter_url"] = "https:" + result_chapter_info["chapter_url"]
        result_chapter_info["chapter_id"] = result_chapter_info["chapter_url"].rstrip("/").split("/")[-1]
        if result_chapter_info["chapter_url"].find("//read.qidian.com") >= 0:
            pass
        elif result_chapter_info["chapter_url"].find("//vipreader.qidian.com/") >= 0:
            if not tool.is_integer(result_chapter_info["chapter_id"]):
                raise crawler.CrawlerException(f"章节地址 {result_chapter_info['chapter_url']} 截取章节id失败")
        else:
            raise crawler.CrawlerException(f"未知的章节域名: {result_chapter_info['chapter_url']}")
        # 获取章节id
        result_chapter_info["chapter_id"] = result_chapter_info["chapter_id"]
        # 获取章节标题
        result_chapter_info["chapter_title"] = chapter_info_selector.find("a").html()
        # 获取章节发布时间
        result_chapter_info["chapter_time_string"] = tool.find_sub_string(chapter_info_selector.find("a").attr("alt"), "首发时间：", " 章节字数")
        try:
            result_chapter_info["chapter_time"] = int(time.mktime(time.strptime(result_chapter_info["chapter_time_string"], "%Y-%m-%d %H:%M:%S")))
            result_chapter_info["chapter_time_string"] = result_chapter_info["chapter_time_string"].replace(":", "_")
        except ValueError:
            raise crawler.CrawlerException(f"日志时间{result_chapter_info['chapter_time_string']}的格式不正确")
        result["chapter_info_list"].insert(0, result_chapter_info)
    return result


# 获取章节内容
def get_chapter_page(chapter_url):
    # https://book.qidian.com/info/1016397637/
    # https://read.qidian.com/chapter/q2B9dFLoeqU3v1oFI-DX8Q2/yyg9pjNdd3y2uJcMpdsVgA2/
    chapter_response = net.request(chapter_url, method="GET")
    result = {
        "content": "",  # 文章内容
        "is_vip": False,  # 是否需要vip解锁
    }
    if chapter_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(chapter_response.status))
    chapter_response_content = chapter_response.data.decode(errors="ignore")
    # 判断是否是vip解锁
    if chapter_response_content.find("<i>这是VIP章节</i>需要订阅后才能阅读") >= 0:
        result["is_vip"] = True
        return result
    chapter_info_list_selector = pq(chapter_response_content).find(".read-content")
    if chapter_info_list_selector.length != 1:
        if chapter_response_content.find("<title>502 Bad Gateway</title>") >= 0:
            time.sleep(3)
            return get_chapter_page(chapter_url)
        raise crawler.CrawlerException("页面截取文章内容失败\n" + chapter_response_content)
    # 文章内容
    result["content"] = chapter_info_list_selector.text().strip()
    if not result["content"]:
        raise crawler.CrawlerException("页面截取文章为空失败\n" + chapter_response_content)
    return result


class QiDian(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_CONTENT: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 解析存档文件
        # book_id  chapter_id
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

        # 下载线程
        self.download_thread = Download


class Download(crawler.DownloadThread):
    def __init__(self, single_save_data, main_thread):
        self.index_key = single_save_data[0]  # book id
        if len(single_save_data) >= 3 and single_save_data[2]:
            self.display_name = single_save_data[2]
        else:
            self.display_name = single_save_data[0]
        crawler.DownloadThread.__init__(self, single_save_data, main_thread)

    def _run(self):
        # 获取所有可下载章节
        chapter_info_list = self.get_crawl_list()
        self.step(f"需要下载的全部小说解析完毕，共{len(chapter_info_list)}个")

        # 从最早的章节开始下载
        while len(chapter_info_list) > 0:
            self.crawl_chapter(chapter_info_list.pop())
            self.main_thread_check()  # 检测主线程运行状态

    # 获取所有可下载章节
    def get_crawl_list(self):
        chapter_info_list = []

        # 获取小说首页
        self.step("开始解析小说首页")
        try:
            index_response = get_book_index(self.index_key)
        except crawler.CrawlerException as e:
            self.error(f"小说首页解析失败，原因：{e.message}")
            raise

        self.trace(f"小说首页解析的全部章节：{index_response['chapter_info_list']}")
        self.step(f"小说首页解析获取{len(index_response['chapter_info_list'])}个章节")

        # 寻找符合条件的章节
        for chapter_info in index_response["chapter_info_list"]:
            # 检查是否达到存档记录
            if chapter_info["chapter_id"] != self.single_save_data[1]:
                chapter_info_list.append(chapter_info)
            else:
                break

        return chapter_info_list

    # 解析单章节小说
    def crawl_chapter(self, chapter_info):
        self.step(f"开始解析章节《{chapter_info['chapter_title']}》 {chapter_info['chapter_url']}")

        # 获取指定小说章节
        try:
            chapter_response = get_chapter_page(chapter_info["chapter_url"])
        except crawler.CrawlerException as e:
            self.error(f"章节《{chapter_info['chapter_title']}》 {chapter_info['chapter_url']}解析失败，原因：{e.message}")
            raise

        if chapter_response["is_vip"]:
            self.error(f"章节《{chapter_info['chapter_title']}》 {chapter_info['chapter_url']}需要vip才能解锁")
            raise

        content_file_path = os.path.join(self.main_thread.content_download_path, self.display_name, f"{chapter_info['chapter_time_string']} {chapter_info['chapter_title']}.txt")
        file.write_file(chapter_response['content'], content_file_path)
        self.step(f"章节《{chapter_info['chapter_title']}》下载成功")

        # 章节内图片全部下载完毕
        self.total_content_count += 1  # 计数累加
        self.single_save_data[1] = chapter_info["chapter_id"]  # 设置存档记录


if __name__ == "__main__":
    QiDian().main()
