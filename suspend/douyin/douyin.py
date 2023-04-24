# -*- coding:UTF-8  -*-
"""
抖音视频爬虫
https://www.douyin.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from common import *
from common import browser
from selenium.webdriver.common.by import By

EACH_PAGE_VIDEO_COUNT = 21
CACHE_FILE_PATH = os.path.join(os.path.dirname(__file__), "cache")
TEMPLATE_HTML_PATH = os.path.join(os.path.dirname(__file__), "html/template.html")


# 获取账号首页
def get_account_index_page(account_id):
    account_index_url = "https://www.douyin.com/share/user/%s" % account_id
    account_index_response = net.Request(account_index_url, method="GET")
    result = {
        "dytk": "",  # 账号dytk值（请求参数）
        "signature": "",  # 加密串（请求参数）
    }
    if account_index_response.status != const.ResponseCode.SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(account_index_response.status))
    script_tac = tool.find_sub_string(account_index_response.content, "<script>tac='", "'</script>")
    if not script_tac:
        raise crawler.CrawlerException("页面截取tac参数失败\n" + account_index_response.content)
    script_dytk = tool.find_sub_string(account_index_response.content, "dytk: '", "'")
    if not script_dytk:
        raise crawler.CrawlerException("页面截取dytk参数失败\n" + account_index_response.content)
    result["dytk"] = script_dytk
    # 读取模板并替换相关参数
    template_html = file.read_file(TEMPLATE_HTML_PATH)
    template_html = template_html.replace("%%USER_AGENT%%", net.DEFAULT_USER_AGENT).replace("%%TAC%%", script_tac).replace("%%UID%%", str(account_id))
    cache_html_path = os.path.join(CACHE_FILE_PATH, "%s.html" % account_id)
    file.write_file(template_html, cache_html_path, const.WriteFileMode.REPLACE)
    # 使用抖音的加密JS方法算出signature的值
    chrome_options_argument = ["user-agent=" + net.DEFAULT_USER_AGENT]
    with browser.Chrome("file:///" + os.path.realpath(cache_html_path), add_argument=chrome_options_argument) as chrome:
        signature = chrome.find_element(by=By.ID, value="result").text
    # 删除临时模板文件
    path.delete_dir_or_file(cache_html_path)
    if not signature:
        raise crawler.CrawlerException("signature参数计算失败\n" + account_index_response.content)
    result["signature"] = signature
    return result


# 获取指定页数的全部视频
def get_one_page_video(account_id, cursor_id, dytk, signature):
    api_url = "https://www.douyin.com/aweme/v1/aweme/post/"
    query_data = {
        "_signature": signature,
        "count": EACH_PAGE_VIDEO_COUNT,
        "dytk": dytk,
        "max_cursor": cursor_id,
        "user_id": account_id,
    }
    headers = {
        "Referer": "https://www.douyin.com/share/user/%s" % account_id,
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
    result["is_over"] = crawler.get_json_value(video_pagination_response.json_data, "has_more", type_check=int) == 0
    # 判断是不是最后一页
    if not result["is_over"]:
        result["next_page_cursor_id"] = crawler.get_json_value(video_pagination_response.json_data, "max_cursor", type_check=int)
    # 获取全部视频id
    for video_info in crawler.get_json_value(video_pagination_response.json_data, "aweme_list", type_check=list):
        result_video_info = {
            "video_id": 0,  # 视频id
            "video_url": "",  # 视频地址
        }
        # 获取视频id
        result_video_info["video_id"] = crawler.get_json_value(video_info, "aweme_id", type_check=int)
        # 获取视频地址
        result_video_info["video_url"] = crawler.get_json_value(video_info, "video", "play_addr", "url_list", 0, type_check=str)
        result["video_info_list"].append(result_video_info)
    return result


class DouYin(crawler.Crawler):
    def __init__(self, **kwargs):
        global CACHE_FILE_PATH
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        sys_config = {
            const.SysConfigKey.DOWNLOAD_VIDEO: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 解析存档文件
        # account_id last_video_id
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

        # 临时文件目录
        CACHE_FILE_PATH = self.cache_data_path

        # 下载线程
        self.crawler_thread = CrawlerThread

    def init(self):
        net.set_default_user_agent()

    def done(self):
        # 删除临时缓存目录
        path.delete_dir_or_file(CACHE_FILE_PATH)


class CrawlerThread(crawler.CrawlerThread):
    def __init__(self, main_thread, single_save_data):
        self.index_key = single_save_data[0]  # account id
        if len(single_save_data) >= 3 and single_save_data[2]:
            self.display_name = single_save_data[2]
        else:
            self.display_name = single_save_data[0]
        crawler.CrawlerThread.__init__(self, main_thread, single_save_data)

    def _run(self):
        # 获取所有可下载视频
        video_id_list = self.get_crawl_list()
        self.info("需要下载的全部视频解析完毕，共%s个" % len(video_id_list))

        # 从最早的视频开始下载
        while len(video_id_list) > 0:
            self.crawl_video(video_id_list.pop())
            self.main_thread_check()  # 检测主线程运行状态

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
                video_pagination_response = get_one_page_video(self.index_key, cursor_id, account_index_response["dytk"], account_index_response["signature"])
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
        self.info("开始下载视频%s %s" % (video_info["video_id"], video_info["video_url"]))

        file_path = os.path.join(self.main_thread.video_download_path, self.display_name, "%020d.mp4" % video_info["video_id"])
        download_return = net.Download(video_info["video_url"], file_path, auto_multipart_download=True)
        if download_return.status == const.DownloadStatus.SUCCEED:
            self.total_video_count += 1  # 计数累加
            self.info("视频%s下载成功" % video_info["video_id"])
        else:
            self.error("视频%s %s 下载失败，原因：%s" % (video_info["video_id"], video_info["video_url"], crawler.download_failre(download_return.code)))
            self.check_download_failure_exit()

        # 视频下载完毕
        self.single_save_data[1] = str(video_info["video_id"])  # 设置存档记录


if __name__ == "__main__":
    DouYin().main()
