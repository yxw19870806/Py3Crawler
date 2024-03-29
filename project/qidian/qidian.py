# -*- coding:UTF-8  -*-
"""
起点网小说爬虫
https://book.qidian.com/
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
    index_response = net.Request(index_url, method="GET")
    result = {
        "chapter_info_list": [],  # 章节信息列表
    }
    if index_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(index_response.status))
    chapter_info_list_selector = pq(index_response.content).find(".catalog-content-wrap .cf li")
    if chapter_info_list_selector.length == 0:
        raise CrawlerException("页面截取章节列表失败\n" + index_response.content)
    for chapter_index in range(chapter_info_list_selector.length):
        result_chapter_info = {
            "chapter_url": "",  # 章节地址
            "chapter_id": "",  # 章节id
            "chapter_time": "",  # 章节发布时间
            "chapter_time_string": "",  # 章节发布时间
            "chapter_title": "",  # 章节标题
        }
        chapter_info_selector = chapter_info_list_selector.eq(chapter_index)
        # 获取章节地址
        result_chapter_info["chapter_url"] = chapter_info_selector.find("a").attr("href")
        if result_chapter_info["chapter_url"].startswith("//"):
            result_chapter_info["chapter_url"] = "https:" + result_chapter_info["chapter_url"]
        # //vipreader.qidian.com/chapter/2597043/391650828/
        chapter_id = url.get_basename(result_chapter_info["chapter_url"])
        if result_chapter_info["chapter_url"].find("//read.qidian.com") >= 0:
            pass
        elif result_chapter_info["chapter_url"].find("//vipreader.qidian.com/") >= 0:
            if not tool.is_integer(chapter_id):
                raise CrawlerException(f"章节地址 {result_chapter_info['chapter_url']} 截取章节id失败")
        else:
            raise CrawlerException(f"未知的章节域名: {result_chapter_info['chapter_url']}")
        # 获取章节id
        result_chapter_info["chapter_id"] = chapter_id
        # 获取章节标题
        result_chapter_info["chapter_title"] = chapter_info_selector.find("a").html()
        # 获取章节发布时间
        result_chapter_info["chapter_time_string"] = tool.find_sub_string(chapter_info_selector.find("a").attr("title"), "首发时间：", " 章节字数")
        try:
            result_chapter_info["chapter_time"] = tool.convert_formatted_time_to_timestamp(result_chapter_info["chapter_time_string"], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise CrawlerException(f"日志时间{result_chapter_info['chapter_time_string']}的格式不正确")
        result["chapter_info_list"].insert(0, result_chapter_info)
    return result


# 获取章节内容
def get_chapter_page(chapter_url):
    # https://book.qidian.com/info/1016397637/
    # https://read.qidian.com/chapter/q2B9dFLoeqU3v1oFI-DX8Q2/yyg9pjNdd3y2uJcMpdsVgA2/
    chapter_response = net.Request(chapter_url, method="GET")
    result = {
        "content": "",  # 文章内容
        "is_vip": False,  # 是否需要vip解锁
    }
    if chapter_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(chapter_response.status))
    # 判断是否是vip解锁
    if chapter_response.content.find("<i>这是VIP章节</i>需要订阅后才能阅读") >= 0:
        result["is_vip"] = True
        return result
    chapter_info_list_selector = pq(chapter_response.content).find(".read-content")
    if chapter_info_list_selector.length != 1:
        if chapter_response.content.find("<title>502 Bad Gateway</title>") >= 0:
            time.sleep(3)
            return get_chapter_page(chapter_url)
        raise CrawlerException("页面截取文章内容失败\n" + chapter_response.content)
    # 文章内容
    result["content"] = chapter_info_list_selector.text().strip()
    if not result["content"]:
        raise CrawlerException("页面截取文章为空失败\n" + chapter_response.content)
    return result


class QiDian(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            const.SysConfigKey.DOWNLOAD_CONTENT: True,
            const.SysConfigKey.SAVE_DATA_FORMATE: (0, ["", ""]),  # book_id  last_chapter_id
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 下载线程
        self.set_crawler_thread(CrawlerThread)


class CrawlerThread(crawler.CrawlerThread):
    def __init__(self, main_thread, single_save_data):
        self.index_key = single_save_data[0]  # book id
        if len(single_save_data) >= 3 and single_save_data[2]:
            self.display_name = single_save_data[2]
        else:
            self.display_name = single_save_data[0]
        crawler.CrawlerThread.__init__(self, main_thread, single_save_data)

    def _run(self):
        # 获取所有可下载章节
        chapter_info_list = self.get_crawl_list()
        self.info(f"需要下载的全部小说解析完毕，共{len(chapter_info_list)}个")

        # 从最早的章节开始下载
        while len(chapter_info_list) > 0:
            self.crawl_chapter(chapter_info_list.pop())
            self.main_thread_check()  # 检测主线程运行状态

    # 获取所有可下载章节
    def get_crawl_list(self):
        chapter_info_list = []

        # 获取小说首页
        index_description = "小说首页"
        self.start_parse(index_description)
        try:
            index_response = get_book_index(self.index_key)
        except CrawlerException as e:
            self.error(e.http_error(index_description))
            raise
        self.parse_result(index_description, index_response["chapter_info_list"])

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
        chapter_description = f"章节《{chapter_info['chapter_title']}》 {chapter_info['chapter_url']}"
        self.start_parse(chapter_description)

        # 获取指定小说章节
        try:
            chapter_response = get_chapter_page(chapter_info["chapter_url"])
        except CrawlerException as e:
            self.error(e.http_error(chapter_description))
            raise

        if chapter_response["is_vip"]:
            raise CrawlerException(f"{chapter_description} 需要vip才能解锁")

        content_file_name = f"{chapter_info['chapter_time_string'].replace(':', '_')} {chapter_info['chapter_title']}.txt"
        content_file_path = os.path.join(self.main_thread.content_download_path, self.display_name, content_file_name)
        file.write_file(chapter_response["content"], content_file_path)
        self.info(f"{chapter_description} 下载成功")

        # 章节内图片全部下载完毕
        self.total_content_count += 1  # 计数累加
        self.single_save_data[1] = chapter_info["chapter_id"]  # 设置存档记录


if __name__ == "__main__":
    QiDian().main()
