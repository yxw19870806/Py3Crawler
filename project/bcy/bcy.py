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
import urllib.parse
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
    api_response = net.request(api_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "album_id_list": [],  # 全部作品id
    }
    if api_response.status != net.HTTP_RETURN_CODE_SUCCEED:
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
    album_url = f"https://bcy.net/item/detail/{album_id}"
    album_response = net.request(album_url, method="GET")
    result = {
        "photo_url_list": [],  # 全部图片地址
        "video_id": None,  # 视频id
    }
    if album_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_response.status))
    album_response_content = album_response.data.decode(errors="ignore")
    script_json_html = tool.find_sub_string(album_response_content, "JSON.parse(", ");\n")
    if not script_json_html:
        raise crawler.CrawlerException("页面截取作品信息失败\n" + album_response_content)
    script_json = tool.json_decode(tool.json_decode(script_json_html))
    if not script_json:
        raise crawler.CrawlerException("作品信息加载失败\n" + album_response_content)
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
        raise crawler.CrawlerException(f"未知的作品类型：{album_type}")
    # 获取全部图片
    for photo_info in crawler.get_json_value(script_json, "detail", "post_data", "multi", type_check=list):
        result["photo_url_list"].append(crawler.get_json_value(photo_info, "original", type_check=str))
    if not is_skip and len(result["photo_url_list"]) == 0:
        raise crawler.CrawlerException("页面匹配图片地址失败\n" + album_response_content)
    return result


# 使用selenium获取指定id的作品
def get_album_page_by_selenium(album_id):
    result = {
        "video_url": None,  # 视频地址
        "video_type": None,  # 视频类型
    }
    desired_capabilities = DesiredCapabilities.CHROME
    desired_capabilities['loggingPrefs'] = {'performance': 'ALL'}  # 记录所有日志
    album_url = f"https://bcy.net/item/detail/{album_id}"
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
    video_info_response = net.request(video_info_url, method="GET", json_decode=True)
    if video_info_response.status != net.HTTP_RETURN_CODE_SUCCEED:
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
        crawler.CrawlerException("视频信息截取加密视频地址失败\n" + video_info_response.json_data)
    try:
        result["video_url"] = base64.b64decode(encryption_video_url).decode(errors="ignore")
    except TypeError:
        raise crawler.CrawlerException(f"歌曲加密地址{encryption_video_url}解密失败")
    return result


class Bcy(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_DOWNLOAD_VIDEO: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 解析存档文件
        # account_id  last_album_id
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

        # 下载线程
        self.download_thread = Download


class Download(crawler.DownloadThread):
    def __init__(self, single_save_data, main_thread):
        self.index_key = single_save_data[0]  # account id
        if len(single_save_data) >= 3:
            self.display_name = single_save_data[2]
        else:
            self.display_name = single_save_data[0]
        crawler.DownloadThread.__init__(self, single_save_data, main_thread)

    def _run(self):
        # 获取所有可下载作品
        album_id_list = self.get_crawl_list()
        self.step(f"需要下载的全部作品解析完毕，共{len(album_id_list)}个")

        # 从最早的作品开始下载
        while len(album_id_list) > 0:
            self.crawl_album(album_id_list.pop())
            self.main_thread_check()  # 检测主线程运行状态

    # 获取所有可下载作品
    def get_crawl_list(self):
        page_since_id = 0
        album_id_list = []
        is_over = False
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step(f"开始解析since {page_since_id}后一页作品")

            # 获取一页作品
            try:
                album_pagination_response = get_one_page_album(self.index_key, page_since_id)
            except crawler.CrawlerException as e:
                self.error(e.http_error(f"since: {page_since_id}后一页作品"))
                raise

            self.trace(f"since {page_since_id}后一页解析的全部作品：{album_pagination_response['album_id_list']}")
            self.step(f"since {page_since_id}后一页解析获取{len(album_pagination_response['album_id_list'])}个作品")

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
        self.step(f"开始解析作品{album_id}")

        # 获取作品
        try:
            album_response = get_album_page(album_id)
        except crawler.CrawlerException as e:
            self.error(e.http_error(f"作品{album_id}"))
            raise

        # 图片
        if self.main_thread.is_download_photo:
            self.crawl_photo(album_id, album_response["photo_url_list"])

        # 视频
        if self.main_thread.is_download_video and album_response["video_id"] is not None:
            self.crawl_video(album_id)

        # 作品内图片下全部载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.single_save_data[1] = str(album_id)  # 设置存档记录

    def crawl_photo(self, album_id, photo_url_list):
        self.trace(f"作品{album_id}解析的全部图片：{photo_url_list}")
        self.step(f"作品{album_id}解析获取{len(photo_url_list)}张图片")

        album_path = os.path.join(self.main_thread.photo_download_path, self.display_name, str(album_id))
        # 设置临时目录
        self.temp_path_list.append(album_path)
        photo_index = 1
        for photo_url in photo_url_list:
            self.main_thread_check()  # 检测主线程运行状态
            # 禁用指定分辨率
            self.step(f"作品{album_id}开始下载第{photo_index}张图片 {photo_url}")

            file_extension = net.get_file_extension(photo_url, "jpg")
            if file_extension == 'image':
                file_extension = "jpg"
            file_path = os.path.join(album_path, f"%03d.{file_extension}" % photo_index)
            for retry_count in range(10):
                download_return = net.Download(photo_url, file_path)
                if download_return.status == net.Download.DOWNLOAD_SUCCEED:
                    self.total_photo_count += 1  # 计数累加
                    self.step(f"作品{album_id}第{photo_index}张图片下载成功")
                else:
                    # 560报错，重新下载
                    if download_return.code == 404 and retry_count < 4:
                        log.step(f"图片 {photo_url} 访问异常，重试")
                        time.sleep(5)
                        continue
                    self.error(f"作品{album_id}第{photo_index}张图片 {photo_url}，下载失败，原因：{crawler.download_failre(download_return.code)}")
                    self.check_download_failure_exit()
                break
            photo_index += 1

    def crawl_video(self, album_id):
        self.step(f"开始解析作品{album_id}的视频")
        try:
            video_response = get_album_page_by_selenium(album_id)
        except crawler.CrawlerException as e:
            self.error(e.http_error(f"作品{album_id}"))
            raise

        self.step(f"作品{album_id}开始下载视频 {video_response['video_url']}")

        file_path = os.path.join(self.main_thread.photo_download_path, self.display_name, f"{album_id}.{video_response['video_type']}")
        download_return = net.Download(video_response["video_url"], file_path)
        if download_return.status == net.Download.DOWNLOAD_SUCCEED:
            self.total_video_count += 1  # 计数累加
            self.step(f"作品{album_id}视频下载成功")
        else:
            self.error(f"作品{album_id}视频 {video_response['video_url']}，下载失败，原因：{crawler.download_failre(download_return.code)}")
            self.check_download_failure_exit()


if __name__ == "__main__":
    Bcy().main()
