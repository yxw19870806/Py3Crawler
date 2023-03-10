# -*- coding:UTF-8  -*-
"""
nico nico视频列表（My List）视频爬虫
https://www.nicovideo.jp/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import html
import os
import time
from pyquery import PyQuery as pq
from common import *

COOKIE_INFO = {}
EACH_PAGE_VIDEO_COUNT = 100


# 检测登录状态
def check_login():
    if not COOKIE_INFO:
        return False
    index_url = "https://www.nicovideo.jp/my"
    index_response = net.request(index_url, method="GET", cookies_list=COOKIE_INFO, is_auto_redirect=False)
    if index_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        return True
    return False


# 获取指定账号下的所有视频列表
def get_account_mylist(account_id):
    account_mylist_url = "https://www.nicovideo.jp/user/%s/mylist" % account_id
    account_mylist_response = net.request(account_mylist_url, method="GET", is_auto_retry=False)
    result = {
        "list_id_list": [],  # 全部视频列表id
        "is_private": False,  # 是否未公开
    }
    if account_mylist_response.status in [404, 500]:
        raise crawler.CrawlerException("账号不存在")
    elif account_mylist_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(account_mylist_response.status))
    account_mylist_response_content = account_mylist_response.data.decode(errors="ignore")
    if pq(account_mylist_response_content).find(".articleBody .noListMsg").length == 1:
        message = pq(account_mylist_response_content).find(".articleBody .noListMsg .att").text()
        if message == "非公開です":
            result["is_private"] = True
            return result
        elif message == "公開マイリストはありません":
            return result
        else:
            raise crawler.CrawlerException("未知视频列表状态: %s" % message)
    mylist_list_selector = pq(account_mylist_response_content).find(".articleBody .outer")
    for mylist_index in range(mylist_list_selector.length):
        mylist_selector = mylist_list_selector.eq(mylist_index)
        mylist_url = mylist_selector.find(".section h4 a").attr("href")
        if mylist_url is None:
            raise crawler.CrawlerException("视频列表信息截取视频列表地址失败\n" + mylist_selector.html())
        list_id = tool.find_sub_string(mylist_url, "mylist/")
        if not tool.is_integer(list_id):
            raise crawler.CrawlerException("视频列表地址截取视频列表id失败\n" + mylist_selector.html())
        result["list_id_list"].append(int(list_id))
    return result


# 获取指定账号下的一页投稿视频
def get_one_page_account_video(account_id, page_count):
    video_index_url = "https://www.nicovideo.jp/user/%s/video" % account_id
    query_data = {"page": page_count}
    video_index_response = net.request(video_index_url, method="GET", fields=query_data)
    result = {
        "video_info_list": [],  # 全部视频信息
        "is_over": False,  # 是否最后页
        "is_private": False,  # 是否未公开
    }
    if video_index_response.status == 404:
        raise crawler.CrawlerException("账号不存在")
    elif video_index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_index_response.status))
    video_index_response_content = video_index_response.data.decode(errors="ignore")
    if pq(video_index_response_content).find(".articleBody .noListMsg").length == 1:
        message = pq(video_index_response_content).find(".articleBody .noListMsg .att").text()
        if message == "非公開です":
            result["is_private"] = True
            return result
        else:
            raise crawler.CrawlerException("未知视频列表状态: %s" % message)
    video_list_selector = pq(video_index_response_content).find(".articleBody .outer")
    # 第一个是排序选择框，跳过
    for video_index in range(1, video_list_selector.length):
        result_video_info = {
            "video_id": 0,  # 视频id
            "video_title": "",  # 视频标题
        }
        video_selector = video_list_selector.eq(video_index)
        # 获取视频id
        video_url = video_selector.find(".section h5 a").attr("href")
        if not video_url:
            raise crawler.CrawlerException("视频信息截取视频地址失败\n" + video_selector.html())
        video_id = tool.find_sub_string(video_url, "watch/sm", "?")
        if not tool.is_integer(video_id):
            raise crawler.CrawlerException("视频地址截取视频id失败\n" + video_selector.html())
        result_video_info["video_id"] = int(video_id)
        # 获取视频标题
        video_title = video_selector.find(".section h5 a").text()
        if not video_title:
            raise crawler.CrawlerException("视频信息截取视频标题失败\n" + video_selector.html())
        result_video_info["video_title"] = video_title
        result["video_info_list"].append(result_video_info)
    # 判断是不是最后页
    if pq(video_index_response_content).find(".articleBody .pager a:last").text() != "次へ":
        result["is_over"] = True
    return result


# 获取视频列表全部视频信息
# list_id => 15614906
def get_one_page_mylist_video(list_id, page_count):
    # http://www.nicovideo.jp/mylist/15614906
    api_url = "https://nvapi.nicovideo.jp/v2/mylists/%s" % list_id
    post_data = {
        "pageSize": EACH_PAGE_VIDEO_COUNT,
        "page": page_count,
    }
    header_list = {
        "X-Frontend-Id": "6",
        "X-Frontend-Version": "0",
        "X-Niconico-Language": "ja-jp",
    }
    mylist_pagination_response = net.request(api_url, method="GET", fields=post_data, cookies_list=COOKIE_INFO, header_list=header_list, json_decode=True)
    result = {
        "video_info_list": [],  # 全部视频信息
    }
    if mylist_pagination_response.status == 404:
        raise crawler.CrawlerException("视频列表不存在")
    elif mylist_pagination_response.status == 403:
        raise crawler.CrawlerException("视频列表未公开")
    elif mylist_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(mylist_pagination_response.status))

    for video_info in crawler.get_json_value(mylist_pagination_response.json_data, "data", "mylist", "items", type_check=list):
        result_video_info = {
            "video_id": 0,  # 视频id
            "video_title": "",  # 视频标题
        }
        # 判断类型
        crawler.get_json_value(video_info, "video", "type", type_check=str, value_check="essential")
        # 获取视频id
        video_id = crawler.get_json_value(video_info, "video", "id", type_check=str).replace("sm", "")
        if not tool.is_integer(video_id):
            raise crawler.CrawlerException("视频信息%s中'watchId'字段类型不正确" % video_info)
        result_video_info["video_id"] = int(video_id)
        # 获取视频辩题
        result_video_info["video_title"] = crawler.get_json_value(video_info, "video", "title", type_check=str)
        result["video_info_list"].append(result_video_info)
    return result


# 根据视频id，获取视频的下载地址
def get_video_info(video_id):
    video_play_url = "http://www.nicovideo.jp/watch/sm%s" % video_id
    video_play_response = net.request(video_play_url, method="GET", cookies_list=COOKIE_INFO)
    result = {
        "extra_cookie": {},  # 额外的cookie
        "is_delete": False,  # 是否已删除
        "is_private": False,  # 是否未公开
        "video_title": "",  # 视频标题
        "video_url": "",  # 视频地址
    }
    if video_play_response.status == 403:
        log.info("视频%s访问异常，重试" % video_id)
        time.sleep(30)
        return get_video_info(video_id)
    elif video_play_response.status == 404:
        result["is_delete"] = True
        return result
    elif video_play_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException("视频播放页访问失败，" + crawler.request_failre(video_play_response.status))
    video_play_response_content = video_play_response.data.decode(errors="ignore")
    script_json_html = tool.find_sub_string(video_play_response_content, 'data-api-data="', '" data-environment="')
    if not script_json_html:
        # 播放页面提示flash没有安装，重新访问
        if pq(video_play_response_content).find("div.notify_update_flash_player").length > 0:
            return get_video_info(video_id)
        if video_play_response_content.find("<p>この動画が投稿されている公開コミュニティはありません。</p>") > 0:
            result["is_private"] = True
            return result
        raise crawler.CrawlerException("视频信息截取失败\n" + video_play_response_content)
    script_json = tool.json_decode(html.unescape(script_json_html))
    if script_json is None:
        raise crawler.CrawlerException("视频信息加载失败\n" + video_play_response_content)
    # 获取视频标题
    result["video_title"] = crawler.get_json_value(script_json, "video", "title", type_check=str)
    # 获取视频地址
    result["video_url"] = crawler.get_json_value(script_json, "video", "smileInfo", "url", type_check=str)
    # 返回的cookies
    result["extra_cookie"] = net.get_cookies_from_response_header(video_play_response.headers)
    return result


class NicoNico(crawler.Crawler):
    def __init__(self, **kwargs):
        global COOKIE_INFO

        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler_enum.SysConfigKey.DOWNLOAD_VIDEO: True,
            crawler_enum.SysConfigKey.SET_PROXY: True,
            crawler_enum.SysConfigKey.GET_COOKIE: ("nicovideo.jp",),
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 设置全局变量，供子线程调用
        COOKIE_INFO = self.cookie_value

        # 解析存档文件
        # mylist_id  last_video_id
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

        # 下载线程
        self.crawler_thread = CrawlerThread

    def init(self):
        # 检测登录状态
        if not check_login():
            log.error("没有检测到账号登录状态，退出程序！")
            tool.process_exit()


class CrawlerThread(crawler.CrawlerThread):
    def __init__(self, main_thread, single_save_data):
        self.index_key = single_save_data[0]  # list id
        if len(single_save_data) >= 3 and single_save_data[2]:
            self.display_name = single_save_data[2]
        else:
            self.display_name = single_save_data[0]
        crawler.CrawlerThread.__init__(self, main_thread, single_save_data)

    def _run(self):
        # 获取所有可下载视频
        video_info_list = self.get_crawl_list()
        self.info("需要下载的全部视频解析完毕，共%s个" % len(video_info_list))

        # 从最早的视频开始下载
        while len(video_info_list) > 0:
            self.crawl_video(video_info_list.pop())
            self.main_thread_check()  # 检测主线程运行状态

    # 获取所有可下载图片
    def get_crawl_list(self):
        page_count = 1
        video_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的视频
        while not is_over:
            mylist_pagination_description = "第%s页视频" % page_count
            self.start_parse(mylist_pagination_description)
            try:
                mylist_pagination_response = get_one_page_mylist_video(self.index_key, page_count)
            except crawler.CrawlerException as e:
                self.error(e.http_error(mylist_pagination_description))
                raise
            self.parse_result(mylist_pagination_description, mylist_pagination_response["video_info_list"])

            # 寻找这一页符合条件的视频
            for video_info in mylist_pagination_response["video_info_list"]:
                # 检查是否达到存档记录
                if video_info["video_id"] > int(self.single_save_data[1]):
                    video_info_list.append(video_info)
                else:
                    break

            if not is_over:
                if mylist_pagination_response["is_over"]:
                    is_over = True
                else:
                    page_count += 1

        return video_info_list

    # 解析单个视频
    def crawl_video(self, video_info):
        video_description = "%s 《%s》" % (video_info["video_id"], video_info["video_title"])
        self.start_parse(video_description)
        try:
            video_info_response = get_video_info(video_info["video_id"])
        except crawler.CrawlerException as e:
            self.error(e.http_error(video_description))
            raise
        if video_info_response["is_delete"]:
            self.error("视频%s 《%s》已删除，跳过" % (video_info["video_id"], video_info["video_title"]))
            return
        if video_info_response["is_private"]:
            self.error("视频%s 《%s》未公开，跳过" % (video_info["video_id"], video_info["video_title"]))
            return

        self.info("视频%s 《%s》 %s 开始下载" % (video_info["video_id"], video_info["video_title"], video_info_response["video_url"]))
        video_file_path = os.path.join(self.main_thread.video_download_path, self.display_name, "%08d - %s.mp4" % (video_info["video_id"], path.filter_text(video_info["video_title"])))
        cookies_list = COOKIE_INFO
        if video_info_response["extra_cookie"]:
            cookies_list.update(video_info_response["extra_cookie"])
        download_return = net.Download(video_info_response["video_url"], video_file_path, cookies_list=cookies_list)
        if download_return.status == net.Download.DOWNLOAD_SUCCEED:
            self.total_video_count += 1  # 计数累加
            self.info("视频%s 《%s》下载成功" % (video_info["video_id"], video_info["video_title"]))
        else:
            self.error("视频%s 《%s》 %s 下载失败，原因：%s" % (video_info["video_id"], video_info["video_title"], video_info_response["video_url"], crawler.download_failre(download_return.code)))
            self.check_download_failure_exit()

        # 视频下载完毕
        self.single_save_data[1] = str(video_info["video_id"])  # 设置存档记录


if __name__ == "__main__":
    NicoNico().main()
