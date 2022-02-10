# -*- coding:UTF-8  -*-
"""
TikTok视频爬虫
https://www.tiktok.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import time
import traceback
import urllib.parse
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from common import *
from common import browser

EACH_PAGE_VIDEO_COUNT = 48
USER_AGENT = net._random_user_agent()


# 获取账号首页
def get_account_index_page(account_id):
    account_index_url = f"https://www.tiktok.com/share/user/{account_id}"
    result = {
        "signature": "",  # 加密串（请求参数）
    }
    desired_capabilities = DesiredCapabilities.CHROME
    desired_capabilities['loggingPrefs'] = {'performance': 'ALL'}  # 记录所有日志
    chrome_options_argument = ["user-agent=" + USER_AGENT]
    with browser.Chrome(account_index_url, desired_capabilities=desired_capabilities, add_argument=chrome_options_argument) as chrome:
        for log_info in chrome.get_log("performance"):
            log_message = tool.json_decode(crawler.get_json_value(log_info, "message", type_check=str))
            if crawler.get_json_value(log_message, "message", "method", default_value="", type_check=str) == "Network.requestWillBeSent":
                video_info_url = crawler.get_json_value(log_message, "message", "params", "request", "url", default_value="", type_check=str)
                if video_info_url.find("//www.tiktok.com/share/item/list?") > 0:
                    break
        else:
            raise crawler.CrawlerException("账号首页匹配视频信息地址失败")
    video_info_param = urllib.parse.parse_qs(urllib.parse.urlparse(video_info_url)[4])
    result["signature"] = crawler.get_json_value(video_info_param, "_signature", 0, default_value="")
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
    header_list = {
        "Referer": f"https://www.tiktok.com/share/user/{account_id}",
        "User-Agent": USER_AGENT,
    }
    video_pagination_response = net.request(api_url, method="GET", fields=query_data, header_list=header_list, json_decode=True)
    result = {
        "is_over": False,  # 是否最后一页视频
        "next_page_cursor_id": None,  # 下一页视频指针
        "video_info_list": [],  # 全部视频信息
    }
    if video_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_pagination_response.status))
    # 判断是不是最后一页
    result["is_over"] = crawler.get_json_value(video_pagination_response.json_data, "body", "hasMore", type_check=bool) is True
    # 判断是不是最后一页
    if not result["is_over"]:
        result["next_page_cursor_id"] = crawler.get_json_value(video_pagination_response.json_data, "body", "maxCursor", type_check=int)
    # 获取全部视频id
    for video_info in crawler.get_json_value(video_pagination_response.json_data, "body", "itemListData", type_check=list):
        result_video_info = {
            "video_id": None,  # 视频id
            "video_url": None,  # 视频地址
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
            crawler.SYS_DOWNLOAD_VIDEO: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 解析存档文件
        # account_id last_video_id
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

    def main(self):
        try:
            # 循环下载每个id
            thread_list = []
            for account_id in sorted(self.save_data.keys()):
                # 提前结束
                if not self.is_running():
                    break

                # 开始下载
                thread = Download(self.save_data[account_id], self)
                thread.start()
                thread_list.append(thread)

                time.sleep(1)

            # 等待子线程全部完成
            while len(thread_list) > 0:
                thread_list.pop().join()
        except KeyboardInterrupt:
            self.stop_process()

        # 未完成的数据保存
        self.write_remaining_save_data()

        # 重新排序保存存档文件
        self.rewrite_save_file()

        self.end_message()


class Download(crawler.DownloadThread):
    def __init__(self, single_save_data, main_thread):
        crawler.DownloadThread.__init__(self, single_save_data, main_thread)
        self.account_id = self.single_save_data[0]
        if len(self.single_save_data) >= 3 and self.single_save_data[2]:
            self.display_name = self.single_save_data[2]
        else:
            self.display_name = self.single_save_data[0]
        self.step("开始")

    # 获取所有可下载视频
    def get_crawl_list(self):
        # 获取指定一页的视频信息
        try:
            account_index_response = get_account_index_page(self.account_id)
        except crawler.CrawlerException as e:
            self.error(e.http_error("账号首页"))
            raise

        cursor_id = 0
        video_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的视频
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step(f"开始解析cursor {cursor_id}后的一页视频")

            # 获取指定一页的视频信息
            try:
                video_pagination_response = get_one_page_video(self.account_id, cursor_id, account_index_response["signature"])
            except crawler.CrawlerException as e:
                self.error(e.http_error(f"cursor: {cursor_id}后一页视频"))
                raise

            self.trace(f"cursor {cursor_id}页获取的全部视频：{video_pagination_response['video_info_list']}")
            self.step(f"cursor {cursor_id}页获取{len(video_pagination_response['video_info_list'])}个视频")

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
        self.step(f"开始下载视频{video_info['video_id']} {video_info['video_url']}")

        file_path = os.path.join(self.main_thread.video_download_path, self.display_name, "%020d.mp4" % video_info["video_id"])
        save_file_return = net.download(video_info["video_url"], file_path)
        if save_file_return["status"] == 1:
            self.total_video_count += 1  # 计数累加
            self.step(f"视频{video_info['video_id']}下载成功")
        else:
            self.error(f"视频{video_info['video_id']} {video_info['video_url']} 下载失败，原因：{crawler.download_failre(save_file_return['code'])}")
            self.check_download_failure_exit()

        # 视频下载完毕
        self.single_save_data[1] = str(video_info["video_id"])  # 设置存档记录

    def run(self):
        try:
            # 获取所有可下载视频
            video_id_list = self.get_crawl_list()
            self.step(f"需要下载的全部视频解析完毕，共{len(video_id_list)}个")

            # 从最早的视频开始下载
            while len(video_id_list) > 0:
                self.crawl_video(video_id_list.pop())
                self.main_thread_check()  # 检测主线程运行状态
        except (SystemExit, KeyboardInterrupt) as e:
            if isinstance(e, SystemExit) and e.code == 1:
                self.error("异常退出")
            else:
                self.step("提前退出")
        except Exception as e:
            self.error("未知异常")
            self.error(str(e) + "\n" + traceback.format_exc(), False)

        self.main_thread.save_data.pop(self.account_id)
        self.done()


if __name__ == "__main__":
    TikTok().main()
