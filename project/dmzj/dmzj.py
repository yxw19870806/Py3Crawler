# -*- coding:UTF-8  -*-
"""
动漫之家漫画爬虫
https://manhua.dmzj.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from common import *

COOKIES = {}


# 获取指定一页的图集
def get_comic_index_page(comic_name):
    # https://m.dmzj.com/info/yiquanchaoren.html
    index_url = f"https://m.dmzj.com/info/{comic_name}.html"
    index_response = net.Request(index_url, method="GET")
    result = {
        "comic_info_list": {},  # 漫画列表信息
    }
    if index_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(index_response.status))
    comic_info_html = tool.find_sub_string(index_response.content, "initIntroData(", ");\n")
    if not comic_info_html:
        raise CrawlerException("漫画信息截取失败\n" + index_response.content)
    comic_info_data = tool.json_decode(comic_info_html)
    if not comic_info_data:
        raise CrawlerException("漫画信息加载失败\n" + comic_info_html)
    for chapter_info in comic_info_data:
        # 获取版本名字
        version_name = crawler.get_json_value(chapter_info, "title", type_check=str).strip()
        # 获取版本下各个章节
        for comic_info in crawler.get_json_value(chapter_info, "data", type_check=list):
            result_comic_info = {
                "chapter_name": "",  # 漫画章节名字
                "comic_id": 0,  # 漫画id
                "page_id": 0,  # 页面id
                "version_name": version_name,  # 漫画版本名字
            }
            # 获取漫画id
            result_comic_info["comic_id"] = crawler.get_json_value(comic_info, "comic_id", type_check=int)
            # 获取页面id
            result_comic_info["page_id"] = crawler.get_json_value(comic_info, "id", type_check=int)
            # 获取章节名字
            result_comic_info["chapter_name"] = crawler.get_json_value(comic_info, "chapter_name", type_check=str).strip()
            result["comic_info_list"][result_comic_info["page_id"]] = result_comic_info
    return result


# 获取漫画指定章节
def get_chapter_page(comic_id, page_id):
    # https://m.dmzj.com/view/9949/19842.html
    chapter_url = f"https://m.dmzj.com/view/{comic_id}/{page_id}.html"
    chapter_response = net.Request(chapter_url, method="GET", cookies=COOKIES)
    result = {
        "photo_url_list": [],  # 全部漫画图片地址
    }
    if chapter_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(chapter_response.status))
    script_json_html = tool.find_sub_string(chapter_response.content, "mReader.initData(", ");")
    script_json_html = script_json_html[0:script_json_html.rfind("},") + 1]
    if not script_json_html:
        raise CrawlerException("章节信息截取失败\n" + chapter_response.content)
    script_json = tool.json_decode(script_json_html)
    if not script_json:
        raise CrawlerException("章节信息加载失败\n" + script_json_html)
    for photo_url in crawler.get_json_value(script_json, "page_url", type_check=list):
        result["photo_url_list"].append(photo_url)
    return result


class DMZJ(crawler.Crawler):
    def __init__(self, **kwargs):
        global COOKIES

        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            const.SysConfigKey.DOWNLOAD_PHOTO: True,
            const.SysConfigKey.GET_COOKIE: ("manhua.dmzj.com", "dmzj.com"),
            const.SysConfigKey.SAVE_DATA_FORMATE: (0, ["", "0"]),  # comic_id  last_page_id
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        COOKIES = self.cookie_value

        # 下载线程
        self.set_crawler_thread(CrawlerThread)


class CrawlerThread(crawler.CrawlerThread):
    def __init__(self, main_thread, single_save_data):
        self.index_key = single_save_data[0]  # comic id
        if len(single_save_data) >= 3 and single_save_data[2]:
            self.display_name = single_save_data[2]
        else:
            self.display_name = single_save_data[0]
        crawler.CrawlerThread.__init__(self, main_thread, single_save_data)

    # 获取所有可下载章节
    def get_crawl_list(self):
        comic_info_list = []

        index_description = "漫画首页"
        self.start_parse(index_description)
        try:
            blog_pagination_response = get_comic_index_page(self.index_key)
        except CrawlerException as e:
            self.error(e.http_error(index_description))
            raise
        self.parse_result(index_description, blog_pagination_response["comic_info_list"])

        # 寻找符合条件的章节
        for page_id in sorted(list(blog_pagination_response["comic_info_list"].keys()), reverse=True):
            comic_info = blog_pagination_response["comic_info_list"][page_id]
            # 检查是否达到存档记录
            if page_id > int(self.single_save_data[1]):
                comic_info_list.append(comic_info)
            else:
                break

        return comic_info_list

    # 解析单章节漫画
    def crawl_comic(self, comic_info):
        comic_description = f"漫画{comic_info['page_id']} {comic_info['version_name']}《{comic_info['chapter_name']}》"
        self.start_parse(comic_description)
        try:
            chapter_response = get_chapter_page(comic_info["comic_id"], comic_info["page_id"])
        except CrawlerException as e:
            self.error(e.http_error(comic_description))
            raise
        self.parse_result(comic_description, chapter_response["photo_url_list"])

        # 图片下载
        photo_index = 1
        chapter_name = "%06d %s" % (comic_info["page_id"], comic_info["chapter_name"])
        chapter_path = os.path.join(self.main_thread.photo_download_path, self.display_name, comic_info["version_name"], chapter_name)
        # 设置临时目录
        self.temp_path_list.append(chapter_path)
        for photo_url in chapter_response["photo_url_list"]:
            photo_path = os.path.join(chapter_path, f"%03d.{url.get_file_ext(photo_url)}" % photo_index)
            photo_description = f"{comic_description} 第{photo_index}/{chapter_response['photo_url_list']}张图片"
            if self.download(photo_url, photo_path, photo_description, headers={"Referer": "https://m.dmzj.com/"}):
                self.total_photo_count += 1  # 计数累加
            photo_index += 1

        # 章节内图片全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.single_save_data[1] = str(comic_info["page_id"])  # 设置存档记录

    def _run(self):
        # 获取所有可下载章节
        comic_info_list = self.get_crawl_list()
        self.info(f"需要下载的全部漫画解析完毕，共{len(comic_info_list)}个")

        # 从最早的章节开始下载
        while len(comic_info_list) > 0:
            self.crawl_comic(comic_info_list.pop())


if __name__ == "__main__":
    DMZJ().main()
