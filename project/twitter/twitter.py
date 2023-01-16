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
import urllib.parse
import xml.etree.ElementTree as ElementTree
from common import *

AUTHORIZATION = ""
QUERY_ID = ""
COOKIE_INFO = {}
IS_LOGIN = False
thread_event = threading.Event()
thread_event.set()


# 初始化session。获取authorization。并检测登录状态
def check_login():
    global AUTHORIZATION, COOKIE_INFO, IS_LOGIN, QUERY_ID
    index_url = "https://twitter.com/home"
    header_list = {"referer": "https://twitter.com"}
    index_page_response = net.request(index_url, method="GET", cookies_list=COOKIE_INFO, header_list=header_list, is_auto_redirect=False)
    if index_page_response.status == 200:
        IS_LOGIN = True
    elif index_page_response.status == 302 and index_page_response.getheader("Location") == "/login?redirect_after_login=%2Fhome":
        pass
    else:
        raise crawler.CrawlerException(crawler.request_failre(index_page_response.status))
    index_page_response_content = index_page_response.data.decode(errors="ignore")
    # 更新cookies
    COOKIE_INFO.update(net.get_cookies_from_response_header(index_page_response.headers))
    init_js_url_find = re.findall(r'href="(https://abs.twimg.com/responsive-web/client-web-legacy/main.[^\.]*.[\w]*.js)"', index_page_response_content)
    if len(init_js_url_find) != 1:
        raise crawler.CrawlerException("初始化JS地址截取失败\n" + index_page_response_content)
    init_js_response = net.request(init_js_url_find[0], method="GET")
    if init_js_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException("初始化JS文件，" + crawler.request_failre(init_js_response.status))
    init_js_response_content = init_js_response.data.decode(errors="ignore")
    # 截取authorization
    authorization_string = tool.find_sub_string(init_js_response_content, '="AAAAAAAAAA', '"')
    if not authorization_string:
        raise crawler.CrawlerException("初始化JS中截取authorization失败\n" + init_js_response_content)
    AUTHORIZATION = "AAAAAAAAAA" + authorization_string
    # 截取query id
    query_id_find = re.findall(r'queryId:"([\w-]*)",operationName:"UserByScreenName",operationType:"query"', init_js_response_content)
    if len(query_id_find) != 1:
        raise crawler.CrawlerException("初始化JS中截取queryId失败\n" + init_js_response_content)
    QUERY_ID = query_id_find[0]
    return IS_LOGIN


# 根据账号名字获得账号id（字母账号->数字账号)
def get_account_index_page(account_name):
    account_index_url = "https://api.twitter.com/graphql/%s/UserByScreenName" % QUERY_ID
    query_data = {
        "variables": '{"screen_name":"%s","withSafetyModeUserFields":true,"withSuperFollowsUserFields":true}' % account_name
    }
    header_list = {
        "referer": "https://twitter.com/%s" % account_name,
        "authorization": "Bearer %s" % AUTHORIZATION,
    }
    if "ct0" in COOKIE_INFO:
        header_list["x-csrf-token"] = COOKIE_INFO["ct0"]
    account_index_response = net.request(account_index_url, method="GET", fields=query_data, cookies_list=COOKIE_INFO, header_list=header_list, json_decode=True)
    result = {
        "account_id": None,  # account id
    }
    if account_index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(account_index_response.status))
    result["account_id"] = crawler.get_json_value(account_index_response.json_data, "data", "user", "result", "rest_id", type_check=str, default_value=0)
    if result["account_id"] == 0:
        if crawler.get_json_value(account_index_response.json_data, "data", type_check=dict) is {}:
            raise crawler.CrawlerException("账号不存在")
        error_message = crawler.get_json_value(account_index_response.json_data, "data", "user", "result", "reason", type_check=str, default_value="")
        if error_message == "Suspended":
            raise crawler.CrawlerException("账号已封禁")
        else:
            raise crawler.CrawlerException(account_index_response.data)
    result["account_id"] = str(result["account_id"])
    return result


# 获取一页的推特信息
def get_one_page_media(account_name, account_id, cursor):
    media_pagination_url = "https://twitter.com/i/api/2/timeline/media/%s.json" % account_id
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
    header_list = {
        "referer": "https://twitter.com/%s" % account_name,
        "authorization": "Bearer %s" % AUTHORIZATION,
    }
    if "ct0" in COOKIE_INFO:
        header_list["x-csrf-token"] = COOKIE_INFO["ct0"]
    media_pagination_response = net.request(media_pagination_url, method="GET", fields=query_data, cookies_list=COOKIE_INFO, header_list=header_list, json_decode=True)
    result = {
        "is_over": False,  # 是否最后一页推特（没有获取到任何内容）
        "media_info_list": [],  # 全部推特信息
        "next_page_cursor": None  # 下一页指针
    }
    if media_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(media_pagination_response.status))
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
            # log.notice(tweet_id)
            # log.notice(tweet_info)
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
                    raise crawler.CrawlerException("媒体信息%s中获取视频地址失败" % media_info)
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
                    raise crawler.CrawlerException("媒体信息%s中获取视频地址失败" % media_info)
                result_media_info["video_url_list"].append(video_url)
            else:
                raise crawler.CrawlerException("未知media类型：%s" % media_info)
        result["media_info_list"].append(result_media_info)
    # 判断是不是还有下一页
    for page_info in crawler.get_json_value(media_pagination_response.json_data, "timeline", "instructions", 0, "addEntries", "entries", type_check=list):
        if crawler.get_json_value(page_info, "content", "operation", "cursor", "cursorType", type_check=str, default_value="") == "Bottom":
            result["next_page_cursor"] = crawler.get_json_value(page_info, "content", "operation", "cursor", "value", type_check=str)
    if result["next_page_cursor"] is None:
        raise crawler.CrawlerException("返回信息%s中获取下一页cursor获取失败" % media_pagination_response.json_data)
    else:
        # 和当前cursor一致表示到底了
        if cursor == result["next_page_cursor"]:
            result["next_page_cursor"] = None
    return result


# 根据视频所在推特的ID，获取视频的下载地址
def get_video_play_page(tweet_id):
    thread_event.wait()
    thread_event.clear()
    video_play_url = "https://api.twitter.com/1.1/videos/tweet/config/%s.json" % tweet_id
    header_list = {
        "authorization": "Bearer %s" % AUTHORIZATION,
        "x-csrf-token": COOKIE_INFO["ct0"],
    }
    if IS_LOGIN:
        header_list["x-twitter-auth-type"] = "OAuth2Session"
    video_play_response = net.request(video_play_url, method="GET", cookies_list=COOKIE_INFO, header_list=header_list, json_decode=True)
    result = {
        "video_url": "",  # 视频地址
    }
    thread_event.set()
    if video_play_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_play_response.status))
    # 获取m3u8或视频文件
    try:
        file_url = crawler.get_json_value(video_play_response.json_data, "track", "playbackUrl", type_check=str)
    except crawler.CrawlerException:
        file_url = crawler.get_json_value(video_play_response.json_data, "track", "vmapUrl", default_value="", type_check=str)
        if not file_url:
            raise
    file_extension = net.get_file_extension(file_url)
    if file_extension == "m3u8":  # https://api.twitter.com/1.1/videos/tweet/config/996368816174084097.json
        file_url_protocol, file_url_path = urllib.parse.splittype(file_url)
        file_url_host = urllib.parse.splithost(file_url_path)[0]
        m3u8_file_response = net.request(file_url, method="GET")
        # 没有权限（可能是地域限制）或者已删除
        if m3u8_file_response.status in [403, 404]:
            return result
        elif m3u8_file_response.status != net.HTTP_RETURN_CODE_SUCCEED:
            raise crawler.CrawlerException("m3u8文件 %s 访问失败，%s" % (file_url, crawler.request_failre(m3u8_file_response.status)))
        m3u8_file_response_content = m3u8_file_response.data.decode(errors="ignore")
        include_m3u8_file_list = re.findall(r"(/\S*.m3u8)", m3u8_file_response_content)
        if len(include_m3u8_file_list) > 0:
            # 生成最高分辨率视频所在的m3u8文件地址
            file_url = "%s://%s%s" % (file_url_protocol, file_url_host, include_m3u8_file_list[-1])
            m3u8_file_response = net.request(file_url, method="GET")
            if m3u8_file_response.status != net.HTTP_RETURN_CODE_SUCCEED:
                raise crawler.CrawlerException("最高分辨率m3u8文件 %s 访问失败，%s" % (file_url, crawler.request_failre(m3u8_file_response.status)))
            m3u8_file_response_content = m3u8_file_response.data.decode(errors="ignore")
        # 包含分P视频文件名的m3u8文件
        ts_url_find = re.findall(r"(/\S*.ts)", m3u8_file_response_content)
        if len(ts_url_find) == 0:
            raise crawler.CrawlerException("m3u8文件%s截取视频地址失败\n%s" % (file_url, m3u8_file_response_content))
        result["video_url"] = []
        for ts_video_path in ts_url_find:
            result["video_url"].append("%s://%s%s" % (file_url_protocol, file_url_host, ts_video_path))
    elif file_extension == "vmap":
        vmap_file_response = net.request(file_url, method="GET")
        if vmap_file_response.status != net.HTTP_RETURN_CODE_SUCCEED:
            raise crawler.CrawlerException("vmap文件 %s 访问失败，%s" % (file_url, crawler.request_failre(vmap_file_response.status)))
        vmap_file_response_content = vmap_file_response.data.decode(errors="ignore")
        tw_namespace = tool.find_sub_string(vmap_file_response_content, 'xmlns:tw="', '"')
        if not tw_namespace:
            raise crawler.CrawlerException("vmap文件 %s 截取xmlns:tw命名空间失败\n%s" % (file_url, vmap_file_response_content))
        media_file_elements = ElementTree.fromstring(vmap_file_response_content.strip()).iter("{%s}videoVariant" % tw_namespace)
        # 获取最高bit rate的视频地址
        bit_rate_to_url = {}
        for media_file_element in media_file_elements:
            # 没有bit rate可能是m3u8文件
            bit_rate = media_file_element.get("bit_rate")
            if not tool.is_integer(bit_rate):
                continue
            url = media_file_element.get("url")
            if not url:
                raise crawler.CrawlerException("视频节点解析url失败\n" + vmap_file_response_content)
            bit_rate_to_url[int(bit_rate)] = urllib.parse.unquote(url)
        if len(bit_rate_to_url) == 0:
            raise crawler.CrawlerException("vmap文件 %s 解析全部视频文件失败\n%s" % (file_url, vmap_file_response_content))
        result["video_url"] = bit_rate_to_url[max(bit_rate_to_url)]
    # 直接是视频地址
    else:  # https://api.twitter.com/1.1/videos/tweet/config/996368816174084097.json
        result["video_url"] = file_url
    return result


class Twitter(crawler.Crawler):
    def __init__(self, **kwargs):
        global COOKIE_INFO

        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_DOWNLOAD_VIDEO: True,
            crawler.SYS_SET_PROXY: True,
            crawler.SYS_GET_COOKIE: ("twitter.com",),
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 设置全局变量，供子线程调用
        COOKIE_INFO = self.cookie_value
        if "_twitter_sess" not in COOKIE_INFO or "ct0" not in COOKIE_INFO:
            COOKIE_INFO = {}

        # 解析存档文件
        # account_name  account_id  last_tweet_id
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "", "0"])

        # 下载线程
        self.crawler_thread = CrawlerThread

    def init(self):
        # 生成authorization，用于访问视频页
        try:
            if not check_login():
                while True:
                    input_str = input(tool.get_time() + " 没有检测到账号登录状态，是否继续(C)ontinue？或者退出程序(E)xit？:")
                    input_str = input_str.lower()
                    if input_str in ["c", "yes"]:
                        break
                    elif input_str in ["e", "exit"]:
                        tool.process_exit()
        except crawler.CrawlerException as e:
            log.error(e.http_error("生成authorization"))
            tool.process_exit()


class CrawlerThread(crawler.CrawlerThread):
    def __init__(self, single_save_data, main_thread):
        self.index_key = self.display_name = single_save_data[0]  # account name
        crawler.CrawlerThread.__init__(self, single_save_data, main_thread)

    def _run(self):
        try:
            account_index_response = get_account_index_page(self.index_key)
        except crawler.CrawlerException as e:
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
        self.step("需要下载的全部推特解析完毕，共%s个" % len(media_info_list))

        # 从最早的推特开始下载
        while len(media_info_list) > 0:
            self.crawl_media(media_info_list.pop())
            self.main_thread_check()  # 检测主线程运行状态

    # 获取所有可下载推特
    def get_crawl_list(self):
        cursor = ""
        media_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的推特
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态

            pagination_description = "cursor：%s后一页推特" % cursor
            self.start_parse(pagination_description)

            # 获取指定时间点后的一页图片信息
            try:
                media_pagination_response = get_one_page_media(self.index_key, self.single_save_data[1], cursor)
            except crawler.CrawlerException as e:
                self.error(e.http_error(pagination_description))
                raise

            if media_pagination_response["is_over"]:
                break

            self.parse_result(pagination_description, media_pagination_response["media_info_list"])

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
        media_description = "推特%s" % media_info["blog_id"]
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
            self.main_thread_check()  # 检测主线程运行状态

            photo_description = "推特%s第%s张图片" % (media_info["blog_id"], photo_index)
            self.step("开始下载 %s %s" % (photo_description, photo_url))

            photo_name = "%019d_%02d.%s" % (media_info["blog_id"], photo_index, net.get_file_extension(photo_url))
            photo_path = os.path.join(self.main_thread.photo_download_path, self.index_key, photo_name)
            for retry_count in range(5):
                download_return = net.Download(photo_url, photo_path)
                if download_return.status == net.Download.DOWNLOAD_SUCCEED:
                    self.temp_path_list.append(photo_path)  # 设置临时目录
                    self.total_photo_count += 1  # 计数累加
                    self.step("%s 下载成功" % photo_description)
                else:
                    # 502报错，重新下载
                    if download_return.code == 502:
                        self.error("%s %s 下载失败，重试" % (photo_description, photo_url))
                        continue
                    self.error("%s %s 下载失败，原因：%s" % (photo_description, photo_url, crawler.download_failre(download_return.code)))
                    self.check_download_failure_exit()
                break
            photo_index += 1

    def crawl_video(self, media_info):
        video_index = 1
        for video_url in media_info["video_url_list"]:
            self.main_thread_check()  # 检测主线程运行状态

            if len(media_info["video_url_list"]) > 1:
                video_file_name = "%019d_%02d.%s" % (media_info["blog_id"], video_index, net.get_file_extension(video_url))
            else:
                video_file_name = "%019d.%s" % (media_info["blog_id"], net.get_file_extension(video_url))
            video_path = os.path.join(self.main_thread.video_download_path, self.index_key, video_file_name)
            self.temp_path_list.append(video_path)  # 设置临时目录
            video_description = "推特%s第%s个视频" % (media_info["blog_id"], video_index)
            if self.download(video_url, video_path, video_description, auto_multipart_download=True).is_success():
                self.total_video_count += 1  # 计数累加
            video_index += 1


if __name__ == "__main__":
    Twitter().main()
