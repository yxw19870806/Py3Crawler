# -*- coding:UTF-8  -*-
"""
漫画柜漫画爬虫
https://www.manhuagui.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import subprocess
from functools import partial

# execjs.compile() will raise exception when js code include none-unicode character
# UnicodeDecodeError: 'gbk' codec can't decode byte 0xac in position 33: illegal multibyte sequence
subprocess.Popen = partial(subprocess.Popen, encoding="utf-8")

import execjs
import lzstring
import os
from pyquery import PyQuery as pq
from common import *


# 获取指定一页的图集
def get_comic_index_page(comic_id):
    # https://www.manhuagui.com/comic/21175/
    index_url = f"https://www.manhuagui.com/comic/{comic_id}/"
    index_response = net.Request(index_url, method="GET")
    result = {
        "chapter_info_list": [],  # 漫画列表信息
    }
    if index_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(index_response.status))
    chapter_info_selector = pq(index_response.content).find("div.chapter")
    if chapter_info_selector.length != 1:
        raise CrawlerException("页面截取漫画列表失败\n" + index_response.content)
    group_name_selector = chapter_info_selector.find("h4")
    if group_name_selector.length == 0:
        if pq(index_response.content).find("#__VIEWSTATE").length == 1:
            decompress_string = pq(index_response.content).find("#__VIEWSTATE").val()
            if decompress_string:
                decompress_html = lzstring.LZString().decompressFromBase64(decompress_string)
                chapter_info_selector.html(decompress_html)
                group_name_selector = chapter_info_selector.find("h4")
    group_chapter_list_selector = chapter_info_selector.find(".chapter-list")
    if group_name_selector.length != group_chapter_list_selector.length:
        raise CrawlerException("页面截取章节数量异常\n" + index_response.content)
    for group_index in range(group_name_selector.length):
        # 　获取分组名字
        group_name = group_name_selector.eq(group_index).text().strip()
        if not group_name:
            raise CrawlerException("章节信息截取章节名失败\n" + group_name_selector.eq(group_index).html())
        chapter_list_selector = group_chapter_list_selector.eq(group_index).find("li")
        if chapter_list_selector.length == 0:
            raise CrawlerException("章节信息截取章节内容失败\n" + group_chapter_list_selector.eq(group_index).html())
        for page_index in range(chapter_list_selector.length):
            result_comic_info = {
                "chapter_id": 0,  # 章节id
                "chapter_name": "",  # 章节名
                "group_name": group_name,  # 漫画分组名字
            }
            chapter_selector = chapter_list_selector.eq(page_index)
            # 获取章节ID
            chapter_url = chapter_selector.find("a").attr("href")
            chapter_id = tool.find_sub_string(chapter_url, f"/comic/{comic_id}/", ".html")
            if not tool.is_integer(chapter_id):
                raise CrawlerException(f"页面地址 {chapter_url} 截取页面id失败")
            result_comic_info["chapter_id"] = int(chapter_id)
            # 获取章节名称
            chapter_name = chapter_selector.find("a").attr("title")
            if not chapter_name:
                raise CrawlerException(f"页面地址 {chapter_url} 截取章节名失败")
            result_comic_info["chapter_name"] = chapter_name.strip()
            result["chapter_info_list"].append(result_comic_info)
    return result


# 获取漫画指定章节
def get_chapter_page(comic_id, chapter_id):
    # https://www.manhuagui.com/comic/7580/562894.html
    chapter_url = f"https://www.manhuagui.com/comic/{comic_id}/{chapter_id}.html"
    chapter_response = net.Request(chapter_url, method="GET")
    result = {
        "photo_url_list": [],  # 全部漫画图片地址
    }
    if chapter_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(chapter_response.status))
    script_code = tool.find_sub_string(chapter_response.content, r'window["\x65\x76\x61\x6c"]', "</script>")
    if not script_code:
        raise CrawlerException("页面截取脚本代码失败\n" + chapter_response.content)

    # 使用网站的加密JS方法解密图片地址
    js_code = file.read_file(os.path.join(crawler.PROJECT_APP_PATH, "js", "lz-string.js"))
    js_code += """
    var photoList = [];
    var SMH = {
        'imgData': function (e) {
            for(var i=0; i< e.files.length; i++) {
                photoList.push(e.path + e.files[i]);
            }
            return SMH;
        },
        'preInit': function (e) {}
    }
    function getPhotoLists() {
        return photoList;
    }    
    """
    js_code += "eval" + script_code
    try:
        photo_list = execjs.compile(js_code).call("getPhotoLists")
    except execjs.ProgramError:
        raise CrawlerException("脚本执行失败\n" + js_code)
    if len(photo_list) == 0:
        raise CrawlerException("脚本执行失败\n" + js_code)
    for photo_url in photo_list:
        result["photo_url_list"].append("https://i.hamreus.com" + photo_url)

    return result


class ManHuaGui(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            const.SysConfigKey.DOWNLOAD_PHOTO: True,
            const.SysConfigKey.SAVE_DATA_FORMATE: (0, ["", "0"]),  # comic_name  last_chapter_id
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

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
        chapter_info_list = {}

        index_description = "漫画首页"
        self.start_parse(index_description)
        try:
            blog_pagination_response = get_comic_index_page(self.index_key)
        except CrawlerException as e:
            self.error(e.http_error(index_description))
            raise
        self.parse_result(index_description, blog_pagination_response["chapter_info_list"])

        # 寻找符合条件的章节
        for chapter_info in blog_pagination_response["chapter_info_list"]:
            # 检查是否达到存档记录
            if chapter_info["chapter_id"] > int(self.single_save_data[1]):
                chapter_info_list[chapter_info["chapter_id"]] = chapter_info

        return [chapter_info_list[key] for key in sorted(chapter_info_list.keys(), reverse=True)]

    # 解析单章节漫画
    def crawl_comic(self, chapter_info):
        comic_description = f"漫画{chapter_info['chapter_id']} {chapter_info['group_name']}《{chapter_info['chapter_name']}》"
        self.start_parse(comic_description)
        try:
            chapter_response = get_chapter_page(self.index_key, chapter_info["chapter_id"])
        except CrawlerException as e:
            self.error(e.http_error(comic_description))
            raise
        self.parse_result(comic_description, chapter_response["photo_url_list"])

        # 图片下载
        photo_index = 1
        chapter_name = "%06d %s" % (chapter_info["chapter_id"], chapter_info["chapter_name"])
        chapter_path = os.path.join(self.main_thread.photo_download_path, self.display_name, chapter_info["group_name"], chapter_name)
        # 设置临时目录
        self.temp_path_list.append(chapter_path)
        for photo_url in chapter_response["photo_url_list"]:
            photo_path = os.path.join(chapter_path, f"%03d.{url.get_file_ext(photo_url)}" % photo_index)
            photo_description = f"漫画{chapter_info['chapter_id']} {chapter_info['group_name']}《{chapter_info['chapter_name']}》第{photo_index}张图片"
            headers = {"Referer": f"https://www.manhuagui.com/comic/{self.index_key}/{chapter_info['chapter_id']}.html"}
            if self.download(photo_url, photo_path, photo_description, headers=headers):
                self.total_photo_count += 1  # 计数累加
            photo_index += 1

        # 媒体内图片全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.single_save_data[1] = str(chapter_info["chapter_id"])  # 设置存档记录

    def _run(self):
        # 获取所有可下载章节
        chapter_info_list = self.get_crawl_list()
        self.info(f"需要下载的全部漫画解析完毕，共{len(chapter_info_list)}个")

        # 从最早的章节开始下载
        while len(chapter_info_list) > 0:
            self.crawl_comic(chapter_info_list.pop())


if __name__ == "__main__":
    ManHuaGui().main()
