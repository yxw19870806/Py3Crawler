# -*- coding:UTF-8  -*-
"""
Twitter图片&视频爬虫
https://twitter.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import re
import threading
import time
import urllib.parse
import xml.etree.ElementTree as ElementTree
from common import *

AUTHORIZATION = ""
QUERY_ID = ""
COOKIES = {}
IS_LOGIN = False
thread_event = threading.Event()
thread_event.set()


# 初始化session。获取authorization。并检测登录状态
def check_login():
    global AUTHORIZATION, COOKIES, IS_LOGIN, QUERY_ID
    index_url = "https://twitter.com/home"
    headers = {"referer": "https://twitter.com"}
    index_response = net.Request(index_url, method="GET", cookies=COOKIES, headers=headers).disable_redirect()
    if index_response.status == const.ResponseCode.SUCCEED:
        IS_LOGIN = True
    elif index_response.status == 302 and index_response.headers.get("Location") == "/login?redirect_after_login=%2Fhome":
        pass
    else:
        raise CrawlerException(crawler.request_failre(index_response.status))
    # 更新cookies
    COOKIES.update(net.get_cookies_from_response_header(index_response.headers))
    init_js_url_find = re.findall(r'href="(https://abs.twimg.com/responsive-web/client-web-legacy/main.[^\.]*.[\w]*.js)"', index_response.content)
    if len(init_js_url_find) != 1:
        raise CrawlerException("初始化JS地址截取失败\n" + index_response.content)
    init_js_response = net.Request(init_js_url_find[0], method="GET")
    if init_js_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException("初始化JS文件，" + crawler.request_failre(init_js_response.status))
    # 截取authorization
    authorization_string = tool.find_sub_string(init_js_response.content, '="AAAAAAAAAA', '"')
    if not authorization_string:
        raise CrawlerException("初始化JS中截取authorization失败\n" + init_js_response.content)
    AUTHORIZATION = "AAAAAAAAAA" + authorization_string
    # 截取query id
    query_id_find = re.findall(r'queryId:"([\w-]*)",operationName:"UserByScreenName",operationType:"query"', init_js_response.content)
    if len(query_id_find) != 1:
        raise CrawlerException("初始化JS中截取queryId失败\n" + init_js_response.content)
    QUERY_ID = query_id_find[0]
    return IS_LOGIN


# 根据账号名字获得账号id（字母账号->数字账号)
def get_account_index_page(account_name):
    account_index_url = f"https://api.twitter.com/graphql/{QUERY_ID}/UserByScreenName"
    query_data = {
        "variables": '{"screen_name":"%s","withSafetyModeUserFields":true,"withSuperFollowsUserFields":true}' % account_name
    }
    headers = {
        "referer": f"https://twitter.com/{account_name}",
        "authorization": f"Bearer {AUTHORIZATION}",
    }
    if "ct0" in COOKIES:
        headers["x-csrf-token"] = COOKIES["ct0"]
    account_index_response = net.Request(account_index_url, method="GET", fields=query_data, cookies=COOKIES, headers=headers).enable_json_decode()
    result = {
        "account_id": None,  # account id
    }
    if account_index_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(account_index_response.status))
    result["account_id"] = crawler.get_json_value(account_index_response.json_data, "data", "user", "result", "rest_id", type_check=str, default_value=0)
    if result["account_id"] == 0:
        if crawler.get_json_value(account_index_response.json_data, "data", type_check=dict) is {}:
            raise CrawlerException("账号不存在")
        error_message = crawler.get_json_value(account_index_response.json_data, "data", "user", "result", "reason", type_check=str, default_value="")
        if error_message == "Suspended":
            raise CrawlerException("账号已封禁")
        else:
            raise CrawlerException(account_index_response.content)
    result["account_id"] = str(result["account_id"])
    return result


# 获取一页的推特信息
def get_one_page_media(account_name, account_id, cursor):
    media_pagination_url = f"https://twitter.com/i/api/2/timeline/media/{account_id}.json"
    query_data = {
        "include_profile_interstitial_type": "1",
        "include_blocking": "1",
        "include_blocked_by": "1",
        "include_followed_by": "1",
        # "include_want_retweets": "1",
        "include_mute_edge": "1",
        "include_can_dm": "1",
        # "include_can_media_tag": "1",
        "skip_status": "1",
        "cards_platform": "Web-12",
        "include_cards": "1",
        "include_composer_source": "true",
        "include_ext_alt_text": "true",
        # "include_reply_count": "1",
        "tweet_mode": "extended",
        "include_entities": "false",
        # "include_user_entities": "true",
        # "include_ext_media_color": "true",
        # "include_ext_media_availability": "true",
        "send_error_codes": "1",
        "simple_quoted_tweets": "1",
        "count": "20",
        "ext": "mediaStats,highlightedLabel",
    }
    if cursor:
        query_data["cursor"] = cursor
    headers = {
        "referer": f"https://twitter.com/{account_name}",
        "authorization": f"Bearer {AUTHORIZATION}",
    }
    if "ct0" in COOKIES:
        headers["x-csrf-token"] = COOKIES["ct0"]
    media_pagination_response = net.Request(media_pagination_url, method="GET", fields=query_data, cookies=COOKIES, headers=headers).enable_json_decode()
    result = {
        "is_over": False,  # 是否最后一页推特（没有获取到任何内容）
        "media_info_list": [],  # 全部推特信息
        "next_page_cursor": None  # 下一页指针
    }
    if media_pagination_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(media_pagination_response.status))
    tweet_list = crawler.get_json_value(media_pagination_response.json_data, "globalObjects", "tweets", type_check=dict)
    for tweet_id in sorted(tweet_list.keys(), reverse=True):
        result_media_info = {
            "blog_id": None,  # 推特id
            "photo_url_list": [],  # 全部图片地址
            "video_url_list": [],  # 全部视频地址
        }
        tweet_info = tweet_list[tweet_id]
        # 获取日志id
        result_media_info["blog_id"] = int(tweet_id)
        if "extended_entities" not in tweet_info:
            # log.warning(tweet_id)
            # log.warning(tweet_info)
            continue
        for media_info in crawler.get_json_value(tweet_info, "extended_entities", "media", type_check=list):
            media_type = crawler.get_json_value(media_info, "type", type_check=str)
            # 获取图片地址
            if media_type == "photo":
                result_media_info["photo_url_list"].append(crawler.get_json_value(media_info, "media_url_https", type_check=str))
            # 获取视频地址
            elif media_type == "video":
                max_bit_rate = 0
                video_url = ""
                for video_info in crawler.get_json_value(media_info, "video_info", "variants", type_check=list):
                    bit_rate = crawler.get_json_value(video_info, "bitrate", type_check=int, default_value=0)
                    if bit_rate == 0 and "application/x-mpegURL" == crawler.get_json_value(video_info, "content_type", type_check=str):
                        continue
                    if bit_rate > max_bit_rate:
                        max_bit_rate = bit_rate
                        video_url = crawler.get_json_value(video_info, "url", type_check=str)
                if not video_url:
                    raise CrawlerException(f"媒体信息 {media_info} 中获取视频地址失败")
                result_media_info["video_url_list"].append(video_url)
            # animated gif
            elif media_type == "animated_gif":
                max_bit_rate = -1
                video_url = ""
                for video_info in crawler.get_json_value(media_info, "video_info", "variants", type_check=list):
                    bit_rate = crawler.get_json_value(video_info, "bitrate", type_check=int, default_value=0)
                    if bit_rate == 0 and "application/x-mpegURL" == crawler.get_json_value(video_info, "content_type", type_check=str):
                        continue
                    if bit_rate > max_bit_rate:
                        max_bit_rate = bit_rate
                        video_url = crawler.get_json_value(video_info, "url", type_check=str)
                if not video_url:
                    raise CrawlerException(f"媒体信息 {media_info} 中获取视频地址失败")
                result_media_info["video_url_list"].append(video_url)
            else:
                raise CrawlerException(f"未知media类型：{media_info}")
        result["media_info_list"].append(result_media_info)
    # 判断是不是还有下一页
    for page_info in crawler.get_json_value(media_pagination_response.json_data, "timeline", "instructions", 0, "addEntries", "entries", type_check=list):
        if crawler.get_json_value(page_info, "content", "operation", "cursor", "cursorType", type_check=str, default_value="") == "Bottom":
            result["next_page_cursor"] = crawler.get_json_value(page_info, "content", "operation", "cursor", "value", type_check=str)
    if result["next_page_cursor"] is None:
        raise CrawlerException(f"返回信息 {media_pagination_response.json_data} 中获取下一页cursor获取失败")
    else:
        # 和当前cursor一致表示到底了
        if cursor == result["next_page_cursor"]:
            result["next_page_cursor"] = None
    return result


# 根据视频所在推特的ID，获取视频的下载地址
def get_video_play_page(tweet_id):
    thread_event.wait()
    thread_event.clear()
    video_play_url = f"https://api.twitter.com/1.1/videos/tweet/config/{tweet_id}.json"
    headers = {
        "authorization": f"Bearer {AUTHORIZATION}",
        "x-csrf-token": COOKIES["ct0"],
    }
    if IS_LOGIN:
        headers["x-twitter-auth-type"] = "OAuth2Session"
    video_play_response = net.Request(video_play_url, method="GET", cookies=COOKIES, headers=headers).enable_json_decode()
    result = {
        "video_url": "",  # 视频地址
    }
    thread_event.set()
    if video_play_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(video_play_response.status))
    # 获取m3u8或视频文件
    try:
        file_url = crawler.get_json_value(video_play_response.json_data, "track", "playbackUrl", type_check=str)
    except CrawlerException:
        file_url = crawler.get_json_value(video_play_response.json_data, "track", "vmapUrl", default_value="", type_check=str)
        if not file_url:
            raise
    file_extension = url.get_file_ext(file_url)
    if file_extension == "m3u8":  # https://api.twitter.com/1.1/videos/tweet/config/996368816174084097.json
        file_url_protocol, file_url_host = urllib.parse.urlparse(file_url)[:2]
        m3u8_file_response = net.Request(file_url, method="GET")
        # 没有权限（可能是地域限制）或者已删除
        if m3u8_file_response.status in [403, 404]:
            return result
        elif m3u8_file_response.status != const.ResponseCode.SUCCEED:
            raise CrawlerException(f"m3u8文件 {file_url} 访问失败，{crawler.request_failre(m3u8_file_response.status)}")
        include_m3u8_file_list = re.findall(r"(/\S*.m3u8)", m3u8_file_response.content)
        if len(include_m3u8_file_list) > 0:
            # 生成最高分辨率视频所在的m3u8文件地址
            file_url = f"{file_url_protocol}://{file_url_host}{include_m3u8_file_list[-1]}"
            m3u8_file_response = net.Request(file_url, method="GET")
            if m3u8_file_response.status != const.ResponseCode.SUCCEED:
                raise CrawlerException(f"最高分辨率m3u8文件 {file_url} 访问失败，{crawler.request_failre(m3u8_file_response.status)}")
        # 包含分P视频文件名的m3u8文件
        ts_url_find = re.findall(r"(/\S*.ts)", m3u8_file_response.content)
        if len(ts_url_find) == 0:
            raise CrawlerException(f"m3u8文件{file_url}截取视频地址失败\n{m3u8_file_response.content}")
        result["video_url"] = []
        for ts_video_path in ts_url_find:
            result["video_url"].append(f"{file_url_protocol}://{file_url_host}{ts_video_path}")
    elif file_extension == "vmap":
        vmap_file_response = net.Request(file_url, method="GET")
        if vmap_file_response.status != const.ResponseCode.SUCCEED:
            raise CrawlerException(f"vmap文件 {file_url} 访问失败，{crawler.request_failre(vmap_file_response.status)}")
        tw_namespace = tool.find_sub_string(vmap_file_response.content, 'xmlns:tw="', '"')
        if not tw_namespace:
            raise CrawlerException(f"vmap文件 {file_url} 截取xmlns:tw命名空间失败\n{vmap_file_response.content}")
        media_file_elements = ElementTree.fromstring(vmap_file_response.content.strip()).iter("{%s}videoVariant" % tw_namespace)
        # 获取最高bit rate的视频地址
        bit_rate_to_url = {}
        for media_file_element in media_file_elements:
            # 没有bit rate可能是m3u8文件
            bit_rate = media_file_element.get("bit_rate")
            if not tool.is_integer(bit_rate):
                continue
            video_url = media_file_element.get("url")
            if not video_url:
                raise CrawlerException("视频节点解析视频地址失败\n" + vmap_file_response.content)
            bit_rate_to_url[int(bit_rate)] = urllib.parse.unquote(url)
        if len(bit_rate_to_url) == 0:
            raise CrawlerException(f"vmap文件 {file_url} 解析全部视频文件失败\n{vmap_file_response.content}")
        result["video_url"] = bit_rate_to_url[max(bit_rate_to_url)]
    # 直接是视频地址
    else:  # https://api.twitter.com/1.1/videos/tweet/config/996368816174084097.json
        result["video_url"] = file_url
    return result


class Twitter(crawler.Crawler):
    def __init__(self, **kwargs):
        global COOKIES

        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            const.SysConfigKey.DOWNLOAD_PHOTO: True,
            const.SysConfigKey.DOWNLOAD_VIDEO: True,
            const.SysConfigKey.SET_PROXY: True,
            const.SysConfigKey.GET_COOKIE: ("twitter.com",),
            const.SysConfigKey.SAVE_DATA_FORMATE: (0, ["", "", "0"]),  # account_name  account_id  last_tweet_id
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 设置全局变量，供子线程调用
        COOKIES = self.cookie_value
        if "_twitter_sess" not in COOKIES or "ct0" not in COOKIES:
            COOKIES = {}

        # 下载线程
        self.set_crawler_thread(CrawlerThread)

    def init(self):
        # 生成authorization，用于访问视频页
        try:
            if check_login():
                return
        except CrawlerException as e:
            log.error(e.http_error("生成authorization"))
            tool.process_exit()

        while True:
            input_str = input(tool.convert_timestamp_to_formatted_time() + " 没有检测到账号登录状态，是否继续(C)ontinue？或者退出程序(E)xit？:")
            input_str = input_str.lower()
            if input_str in ["c", "yes"]:
                break
            elif input_str in ["e", "exit"]:
                tool.process_exit()


class CrawlerThread(crawler.CrawlerThread):
    def __init__(self, main_thread, single_save_data):
        self.index_key = self.display_name = single_save_data[0]  # account name
        crawler.CrawlerThread.__init__(self, main_thread, single_save_data)

    # 获取所有可下载推特
    def get_crawl_list(self):
        cursor = ""
        media_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的推特
        while not is_over:
            media_pagination_description = f"cursor：{cursor}后一页推特"
            self.start_parse(media_pagination_description)
            try:
                media_pagination_response = get_one_page_media(self.index_key, self.single_save_data[1], cursor)
            except CrawlerException as e:
                self.error(e.http_error(media_pagination_description))
                raise
            self.parse_result(media_pagination_description, media_pagination_response["media_info_list"])

            # 寻找这一页符合条件的推特
            for media_info in media_pagination_response["media_info_list"]:
                # 检查是否达到存档记录
                if media_info["blog_id"] > int(self.single_save_data[2]):
                    media_info_list.append(media_info)
                else:
                    is_over = True
                    break

            if not is_over:
                # 下一页的指针
                if media_pagination_response["next_page_cursor"] is None:
                    is_over = True
                else:
                    # 设置下一页
                    cursor = media_pagination_response["next_page_cursor"]

        return media_info_list

    # 解析单个推特
    def crawl_media(self, media_info):
        media_description = f"推特{media_info['blog_id']}"
        self.start_parse(media_description)

        # 图片下载
        if self.main_thread.is_download_photo:
            self.parse_result(media_description + "图片", media_info["photo_url_list"])
            self.crawl_photo(media_info)

        # 视频下载
        if self.main_thread.is_download_video:
            self.parse_result(media_description + "视频", media_info["video_url_list"])
            self.crawl_video(media_info)

        # 推特内图片和视频全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.single_save_data[2] = str(media_info["blog_id"])

    def crawl_photo(self, media_info):
        photo_index = 1
        for photo_url in media_info["photo_url_list"]:
            photo_name = f"%019d_%02d.{url.get_file_ext(photo_url)}" % (media_info["blog_id"], photo_index)
            photo_path = os.path.join(self.main_thread.photo_download_path, self.index_key, photo_name)
            photo_description = f"推特{media_info['blog_id']}第{photo_index}张图片"
            if self.download(photo_url, photo_path, photo_description, failure_callback=self.photo_download_failure_callback):
                self.temp_path_list.append(photo_path)  # 设置临时目录
                self.total_photo_count += 1  # 计数累加
            photo_index += 1

    def crawl_video(self, media_info):
        video_index = 1
        for video_url in media_info["video_url_list"]:
            if len(media_info["video_url_list"]) > 1:
                video_file_name = f"%019d_%02d.{url.get_file_ext(video_url)}" % (media_info["blog_id"], video_index)
            else:
                video_file_name = f"%019d.{url.get_file_ext(video_url)}" % media_info["blog_id"]
            video_path = os.path.join(self.main_thread.video_download_path, self.index_key, video_file_name)
            video_description = f"推特{media_info['blog_id']}第{video_index}个视频"
            if self.download(video_url, video_path, video_description, auto_multipart_download=True):
                self.temp_path_list.append(video_path)  # 设置临时目录
                self.total_video_count += 1  # 计数累加
            video_index += 1

    def photo_download_failure_callback(self, photo_url, photo_path, photo_description, download_return: net.Download):
        while download_return.code == 502 and (retry_count := 1) <= 4:
            time.sleep(3)
            self.main_thread_check()
            download_return.update(net.Download(photo_url, photo_path))
            if download_return:
                self.info(f"{photo_description} 下载成功")
                return False
            else:
                self.info(f"{photo_description} 访问异常，重试")
            retry_count += 1
        return True

    def _run(self):
        try:
            account_index_response = get_account_index_page(self.index_key)
        except CrawlerException as e:
            self.error(e.http_error("首页"))
            raise

        if self.single_save_data[1] == "":
            self.single_save_data[1] = account_index_response["account_id"]
        else:
            if self.single_save_data[1] != account_index_response["account_id"]:
                self.error("account id 不符合，原账号已改名")
                tool.process_exit()

        # 获取所有可下载推特
        media_info_list = self.get_crawl_list()
        self.info(f"需要下载的全部推特解析完毕，共{len(media_info_list)}个")

        # 从最早的推特开始下载
        while len(media_info_list) > 0:
            self.crawl_media(media_info_list.pop())


if __name__ == "__main__":
    Twitter().main()
