# -*- coding:UTF-8  -*-
"""
TikTok视频爬虫
https://www.tiktok.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import urllib.parse
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from common import *
from common import browser

EACH_PAGE_VIDEO_COUNT = 48


# 获取账号首页
def get_account_index_page(account_id):
    account_index_url = "https://www.tiktok.com/share/user/%s" % account_id
    result = {
        "signature": "",  # 加密串（请求参数）
    }
    desired_capabilities = DesiredCapabilities.CHROME
    desired_capabilities['loggingPrefs'] = {'performance': 'ALL'}  # 记录所有日志
    chrome_options_argument = ["user-agent=" + net.DEFAULT_USER_AGENT]
    with browser.Chrome(account_index_url, desired_capabilities=desired_capabilities, add_argument=chrome_options_argument) as chrome:
        for log_info in chrome.get_log("performance"):
            log_message = tool.json_decode(crawler.get_json_value(log_info, "message", type_check=str))
            if crawler.get_json_value(log_message, "message", "method", type_check=str, default_value="") == "Network.requestWillBeSent":
                video_info_url = crawler.get_json_value(log_message, "message", "params", "request", "url", default_value="", type_check=str)
                if video_info_url.find("//www.tiktok.com/share/item/list?") > 0:
                    break
        else:
            raise crawler.CrawlerException("账号首页匹配视频信息地址失败")
    video_info_param = urllib.parse.parse_qs(urllib.parse.urlparse(video_info_url)[4])
    result["signature"] = crawler.get_json_value(video_info_param, "_signature", 0, type_check=str, default_value="")
    if not result["signature"]:
        raise crawler.CrawlerException("视频信息地址匹配视频加密串失败")
    return result


# 获取指定页数的全部视频
def get_one_page_video(account_id, cursor_id, signature):
    api_url = "https://www.tiktok.com/share/item/list"
    query_data = {
        "id": account_id,
        "type": "1",
        "count": EACH_PAGE_VIDEO_COUNT,
        "maxCursor": cursor_id,
        "minCursor": 0,
        "_signature": signature,
    }
    headers = {
        "Referer": "https://www.tiktok.com/share/user/%s" % account_id,
    }
    video_pagination_response = net.Request(api_url, method="GET", fields=query_data, headers=headers).enable_json_decode()
    result = {
        "is_over": False,  # 是否最后一页视频
        "next_page_cursor_id": 0,  # 下一页视频指针
        "video_info_list": [],  # 全部视频信息
    }
    if video_pagination_response.status != const.ResponseCode.SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_pagination_response.status))
    # 判断是不是最后一页
    result["is_over"] = crawler.get_json_value(video_pagination_response.json_data, "body", "hasMore", type_check=bool) is True
    # 判断是不是最后一页
    if not result["is_over"]:
        result["next_page_cursor_id"] = crawler.get_json_value(video_pagination_response.json_data, "body", "maxCursor", type_check=int)
    # 获取全部视频id
    for video_info in crawler.get_json_value(video_pagination_response.json_data, "body", "itemListData", type_check=list):
        result_video_info = {
            "video_id": 0,  # 视频id
            "video_url": "",  # 视频地址
        }
        # 获取视频id
        result_video_info["video_id"] = crawler.get_json_value(video_info, "itemInfos", "id", type_check=int)
        # 获取视频地址
        result_video_info["video_url"] = crawler.get_json_value(video_info, "itemInfos", "video", "urls", 0, type_check=str)
        result["video_info_list"].append(result_video_info)
    return result


class TikTok(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        sys_config = {
            const.SysConfigKey.DOWNLOAD_VIDEO: True,
            const.SysConfigKey.SAVE_DATA_FORMATE: (0, ["", "0"]),  # account_id last_video_id
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 下载线程
        self.set_crawler_thread(CrawlerThread)

    def init(self):
        net.set_default_user_agent()


class CrawlerThread(crawler.CrawlerThread):
    def __init__(self, main_thread, single_save_data):
        self.index_key = single_save_data[0]  # account id
        if len(single_save_data) >= 3 and single_save_data[2]:
            self.display_name = single_save_data[2]
        else:
            self.display_name = single_save_data[0]
        crawler.CrawlerThread.__init__(self, main_thread, single_save_data)

    # 获取所有可下载视频
    def get_crawl_list(self):
        # 获取指定一页的视频信息
        try:
            account_index_response = get_account_index_page(self.index_key)
        except crawler.CrawlerException as e:
            self.error(e.http_error("账号首页"))
            raise

        cursor_id = 0
        video_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的视频
        while not is_over:
            video_pagination_description = "cursor %s后的一页视频" % cursor_id
            self.start_parse(video_pagination_description)
            try:
                video_pagination_response = get_one_page_video(self.index_key, cursor_id, account_index_response["signature"])
            except crawler.CrawlerException as e:
                self.error(e.http_error(video_pagination_description))
                raise
            self.parse_result(video_pagination_description, video_pagination_response["video_info_list"])

            # 寻找这一页符合条件的视频
            for video_info in video_pagination_response["video_info_list"]:
                # 检查是否达到存档记录
                if video_info["video_id"] > int(self.single_save_data[1]):
                    video_info_list.append(video_info)
                else:
                    is_over = True
                    break

            # 没有视频了
            if video_pagination_response["is_over"]:
                is_over = True
            else:
                cursor_id = video_pagination_response["next_page_cursor_id"]
        return video_info_list

    # 解析单个视频
    def crawl_video(self, video_info):
        video_path = os.path.join(self.main_thread.video_download_path, self.display_name, "%020d.mp4" % video_info["video_id"])
        video_description = "视频%s" % video_info["video_id"]
        if self.download(video_info["video_url"], video_path, video_description, auto_multipart_download=True):
            self.total_video_count += 1  # 计数累加

        # 视频下载完毕
        self.single_save_data[1] = str(video_info["video_id"])  # 设置存档记录

    def _run(self):
        # 获取所有可下载视频
        video_id_list = self.get_crawl_list()
        self.info("需要下载的全部视频解析完毕，共%s个" % len(video_id_list))

        # 从最早的视频开始下载
        while len(video_id_list) > 0:
            self.crawl_video(video_id_list.pop())


if __name__ == "__main__":
    TikTok().main()
