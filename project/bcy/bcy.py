# -*- coding:UTF-8  -*-
"""
半次元图片爬虫
https://bcy.net/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import base64
import os
import time
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from common import *
from common import browser

EACH_PAGE_ALBUM_COUNT = 20


# 获取指定页数的全部作品
def get_one_page_album(account_id, since_id):
    # https://bcy.net/apiv3/user/selfPosts?uid=50220&since=6059553291006664462
    api_url = "https://bcy.net/apiv3/user/selfPosts"
    query_data = {
        "since": since_id,
        "uid": account_id,
    }
    api_response = net.Request(api_url, method="GET", fields=query_data).enable_json_decode()
    result = {
        "album_id_list": [],  # 全部作品id
    }
    if api_response.status != const.ResponseCode.SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(api_response.status))
    try:
        album_info_list = crawler.get_json_value(api_response.json_data, "data", "items", type_check=list)
    except crawler.CrawlerException:
        album_info_list = crawler.get_json_value(api_response.json_data, "data", value_check={})
    for album_info in album_info_list:
        result["album_id_list"].append(crawler.get_json_value(album_info, "item_detail", "item_id", type_check=int))
    return result


# 获取指定id的作品
def get_album_page(album_id):
    # https://bcy.net/item/detail/6383727612803440398
    # https://bcy.net/item/detail/5969608017174355726 该作品已被作者设置为只有粉丝可见
    # https://bcy.net/item/detail/6363512825238806286 该作品已被作者设置为登录后可见
    album_url = "https://bcy.net/item/detail/%s" % album_id
    album_response = net.Request(album_url, method="GET")
    result = {
        "photo_url_list": [],  # 全部图片地址
        "video_id": "",  # 视频id
    }
    if album_response.status != const.ResponseCode.SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_response.status))
    script_json_html = tool.find_sub_string(album_response.content, "JSON.parse(", ");\n")
    if not script_json_html:
        raise crawler.CrawlerException("页面截取作品信息失败\n" + album_response.content)
    script_json = tool.json_decode(tool.json_decode(script_json_html))
    if not script_json:
        raise crawler.CrawlerException("作品信息加载失败\n" + album_response.content)
    is_skip = False
    album_type = crawler.get_json_value(script_json, "detail", "post_data", "type", type_check=str)
    # 问答
    # https://bcy.net/item/detail/6115326868729126670
    if album_type == "ganswer":
        is_skip = True
    # 文章
    # https://bcy.net/item/detail/6162547130750754574
    elif album_type == "article":
        is_skip = True
    # 视频
    # https://bcy.net/item/detail/6610952986225017096
    elif album_type == "video":
        is_skip = True
        result["video_id"] = crawler.get_json_value(script_json, "detail", "post_data", "video_info", "vid", type_check=str)
    elif album_type == "note":
        pass
    else:
        raise crawler.CrawlerException("未知的作品类型：%s" % album_type)
    # 获取全部图片
    for photo_info in crawler.get_json_value(script_json, "detail", "post_data", "multi", type_check=list):
        result["photo_url_list"].append(crawler.get_json_value(photo_info, "original_path", type_check=str))
    if not is_skip and len(result["photo_url_list"]) == 0:
        raise crawler.CrawlerException("页面匹配图片地址失败\n" + album_response.content)
    return result


# 使用selenium获取指定id的作品
def get_album_page_by_selenium(album_id):
    result = {
        "video_url": "",  # 视频地址
        "video_type": "",  # 视频类型
    }
    desired_capabilities = DesiredCapabilities.CHROME
    desired_capabilities["loggingPrefs"] = {"performance": "ALL"}  # 记录所有日志
    album_url = "https://bcy.net/item/detail/%s" % album_id
    with browser.Chrome(album_url, desired_capabilities=desired_capabilities) as chrome:
        for log_info in chrome.get_log("performance"):
            log_message = tool.json_decode(crawler.get_json_value(log_info, "message", type_check=str))
            if crawler.get_json_value(log_message, "message", "method", default_value="", type_check=str) == "Network.requestWillBeSent":
                video_info_url = crawler.get_json_value(log_message, "message", "params", "request", "url", default_value="", type_check=str)
                if video_info_url.find("//ib.365yg.com/video/urls/") > 0:
                    video_info_url = video_info_url.replace("&callback=axiosJsonpCallback1", "")
                    break
        else:
            raise crawler.CrawlerException("播放页匹配视频信息地址失败")
    # 获取视频信息
    video_info_response = net.Request(video_info_url, method="GET").enable_json_decode()
    if video_info_response.status != const.ResponseCode.SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_info_response.status))
    video_info_list = crawler.get_json_value(video_info_response.json_data, "data", "video_list", type_check=dict)
    max_resolution = 0
    encryption_video_url = None
    for video_info in video_info_list.values():
        resolution = crawler.get_json_value(video_info, "vwidth", type_check=int) * crawler.get_json_value(video_info, "vheight", type_check=int)
        if resolution > max_resolution:
            encryption_video_url = crawler.get_json_value(video_info, "main_url", type_check=str)
            result["video_type"] = crawler.get_json_value(video_info, "vtype", type_check=str)
    if encryption_video_url is None:
        raise crawler.CrawlerException("视频信息%s中截取加密视频地址失败\n" % video_info_response.json_data)
    try:
        result["video_url"] = base64.b64decode(encryption_video_url).decode(errors="ignore")
    except TypeError:
        raise crawler.CrawlerException("歌曲加密地址%s解密失败" % encryption_video_url)
    return result


class Bcy(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            const.SysConfigKey.DOWNLOAD_PHOTO: True,
            const.SysConfigKey.DOWNLOAD_VIDEO: True,
            const.SysConfigKey.SAVE_DATA_FORMATE: (0, ["", "0"]),  # account_id  last_album_id
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 下载线程
        self.set_crawler_thread(CrawlerThread)


class CrawlerThread(crawler.CrawlerThread):
    def __init__(self, main_thread, single_save_data):
        self.index_key = single_save_data[0]  # account id
        if len(single_save_data) >= 3:
            self.display_name = single_save_data[2]
        else:
            self.display_name = single_save_data[0]
        crawler.CrawlerThread.__init__(self, main_thread, single_save_data)

    # 获取所有可下载作品
    def get_crawl_list(self):
        page_since_id = 0
        album_id_list = []
        is_over = False
        while not is_over:
            album_pagination_description = "since %s后一页作品" % page_since_id
            self.start_parse(album_pagination_description)
            try:
                album_pagination_response = get_one_page_album(self.index_key, page_since_id)
            except crawler.CrawlerException as e:
                self.error(e.http_error(album_pagination_description))
                raise
            self.parse_result(album_pagination_description, album_pagination_response["album_id_list"])

            # 寻找这一页符合条件的作品
            for album_id in album_pagination_response["album_id_list"]:
                # 检查是否达到存档记录
                if album_id > int(self.single_save_data[1]):
                    album_id_list.append(album_id)
                    page_since_id = str(album_id)
                else:
                    is_over = True
                    break

            if not is_over:
                if len(album_pagination_response["album_id_list"]) < EACH_PAGE_ALBUM_COUNT:
                    is_over = True

        return album_id_list

    # 解析单个作品
    def crawl_album(self, album_id):
        album_description = "作品%s" % album_id
        self.start_parse(album_description)
        try:
            album_response = get_album_page(album_id)
        except crawler.CrawlerException as e:
            self.error(e.http_error(album_description))
            raise

        # 图片
        if self.main_thread.is_download_photo:
            self.crawl_photo(album_id, album_response["photo_url_list"])

        # 视频
        if self.main_thread.is_download_video and album_response["video_id"]:
            self.crawl_video(album_id)

        # 作品内图片下全部载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.single_save_data[1] = str(album_id)  # 设置存档记录

    def crawl_photo(self, album_id, photo_url_list):
        album_description = "作品%s" % album_id
        self.parse_result(album_description, photo_url_list)

        album_path = os.path.join(self.main_thread.photo_download_path, self.display_name, str(album_id))
        # 设置临时目录
        self.temp_path_list.append(album_path)
        photo_index = 1
        for photo_url in photo_url_list:
            file_extension = url.get_file_ext(photo_url, "jpg")
            if file_extension == "image":
                file_extension = "jpg"
            photo_path = os.path.join(album_path, "%03d.%s" % (photo_index, file_extension))
            photo_description = "作品%s第%s张图片" % (album_id, photo_index)
            if self.download(photo_url, photo_path, photo_description, failure_callback=self.photo_download_failure_callback):
                self.total_photo_count += 1  # 计数累加
            photo_index += 1

    def crawl_video(self, album_id):
        video_description = "作品%s视频" % album_id
        self.start_parse(video_description)
        try:
            video_response = get_album_page_by_selenium(album_id)
        except crawler.CrawlerException as e:
            self.error(e.http_error(video_description))
            raise

        video_path = os.path.join(self.main_thread.photo_download_path, self.display_name, "%s.%s" % (album_id, video_response["video_type"]))
        if self.download(video_response["video_url"], video_path, video_description):
            self.total_video_count += 1  # 计数累加

    def photo_download_failure_callback(self, photo_url, photo_path, photo_description, download_return: net.Download):
        while download_return.code == 404 and (retry_count := 1) <= 9:
            time.sleep(3)
            self.main_thread_check()
            download_return.update(net.Download(photo_url, photo_path))
            if download_return:
                self.info("%s 下载成功" % photo_description)
                return False
            else:
                self.info("%s 访问异常，重试" % photo_description)
            retry_count += 1
        return True

    def _run(self):
        # 获取所有可下载作品
        album_id_list = self.get_crawl_list()
        self.info("需要下载的全部作品解析完毕，共%s个" % len(album_id_list))

        # 从最早的作品开始下载
        while len(album_id_list) > 0:
            self.crawl_album(album_id_list.pop())


if __name__ == "__main__":
    Bcy().main()
