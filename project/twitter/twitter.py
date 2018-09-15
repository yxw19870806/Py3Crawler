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
import traceback
import urllib.parse
from pyquery import PyQuery as pq
from common import *

COOKIE_INFO = {}
AUTHORIZATION = ""
thread_event = threading.Event()
thread_event.set()


# 初始化session。获取authorization
def init_session():
    global AUTHORIZATION
    global COOKIE_INFO
    index_url = "https://twitter.com/"
    index_page_response = net.http_request(index_url, method="GET", cookies_list=COOKIE_INFO, header_list={"referer": "https://twitter.com"})
    if index_page_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(index_page_response.status))
    index_page_response_content = index_page_response.data.decode(errors="ignore")
    # 没有登录状态
    if not COOKIE_INFO or index_page_response_content.find('<div class="StaticLoggedOutHomePage-login">') >= 0:
        COOKIE_INFO = net.get_cookies_from_response_header(index_page_response.headers)
    init_js_url_find = re.findall('<script src="(https://abs.twimg.com/k/[^/]*/init.[^\.]*.[\w]*.js)" async></script>', index_page_response_content)
    if len(init_js_url_find) != 1:
        raise crawler.CrawlerException("初始化JS地址截取失败\n%s" % index_page_response_content)
    init_js_response = net.http_request(init_js_url_find[0], method="GET")
    if init_js_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException("初始化JS文件，" + crawler.request_failre(init_js_response.status))
    init_js_response_content = init_js_response.data.decode(errors="ignore")
    authorization_string = tool.find_sub_string(init_js_response_content, '="AAAAAAAAAA', '"', )
    if not authorization_string:
        raise crawler.CrawlerException("初始化JS中截取authorization失败\n%s" % init_js_response_content)
    AUTHORIZATION = "AAAAAAAAAA" + authorization_string


# 根据账号名字获得账号id（字母账号->数字账号)
def get_account_index_page(account_name):
    account_index_url = "https://twitter.com/%s" % account_name
    header_list = {"referer": "https://twitter.com/%s" % account_name}
    account_index_response = net.http_request(account_index_url, method="GET", cookies_list=COOKIE_INFO, header_list=header_list)
    result = {
        "account_id": None,  # account id
    }
    if account_index_response.status == 404:
        raise crawler.CrawlerException("账号不存在")
    elif account_index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(account_index_response.status))
    account_index_response_content = account_index_response.data.decode(errors="ignore")
    # 重新访问
    if account_index_response_content.find("captureMessage( 'Failed to load source'") >= 0:
        return get_account_index_page(account_name)
    if account_index_response_content.find('<div class="ProtectedTimeline">') >= 0:
        raise crawler.CrawlerException("私密账号，需要关注才能访问")
    if account_index_response_content.find('<a href="https://support.twitter.com/articles/15790"') >= 0:
        raise crawler.CrawlerException("账号已被冻结")
    account_id = tool.find_sub_string(account_index_response_content, '<div class="ProfileNav" role="navigation" data-user-id="', '">')
    if not crawler.is_integer(account_id):
        raise crawler.CrawlerException("页面截取用户id失败\n%s" % account_index_response_content)
    result["account_id"] = account_id
    return result


# 获取一页的推特信息
def get_one_page_media(account_name, position_blog_id):
    media_pagination_url = "https://twitter.com/i/profiles/show/%s/media_timeline" % account_name
    query_data = {
        "include_available_features": "1",
        "include_entities": "1",
        "max_position": position_blog_id,
    }
    header_list = {"referer": "https://twitter.com/%s" % account_name}
    media_pagination_response = net.http_request(media_pagination_url, method="GET", fields=query_data, cookies_list=COOKIE_INFO, header_list=header_list, json_decode=True)
    result = {
        "is_over": False,  # 是否最后一页推特（没有获取到任何内容）
        "media_info_list": [],  # 全部推特信息
        "next_page_position": None  # 下一页指针
    }
    if media_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(media_pagination_response.status))
    if not crawler.check_sub_key(("has_more_items",), media_pagination_response.json_data):
        raise crawler.CrawlerException("返回信息'has_more_items'字段不存在\n%s" % media_pagination_response.json_data)
    if not crawler.check_sub_key(("items_html",), media_pagination_response.json_data):
        raise crawler.CrawlerException("返回信息'items_html'字段不存在\n%s" % media_pagination_response.json_data)
    if not crawler.check_sub_key(("new_latent_count",), media_pagination_response.json_data):
        raise crawler.CrawlerException("返回信息'new_latent_count'字段不存在\n%s" % media_pagination_response.json_data)
    if not crawler.is_integer(media_pagination_response.json_data["new_latent_count"]):
        raise crawler.CrawlerException("返回信息'new_latent_count'字段类型不正确\n%s" % media_pagination_response.json_data)
    if not crawler.check_sub_key(("min_position",), media_pagination_response.json_data):
        raise crawler.CrawlerException("返回信息'min_position'字段不存在\n%s" % media_pagination_response.json_data)
    if not crawler.is_integer(media_pagination_response.json_data["min_position"]) and media_pagination_response.json_data["min_position"] is not None:
        raise crawler.CrawlerException("返回信息'min_position'字段类型不正确\n%s" % media_pagination_response.json_data)
    # 没有任何内容
    if int(media_pagination_response.json_data["new_latent_count"]) == 0 and not media_pagination_response.json_data["items_html"].strip():
        result["is_skip"] = True
        return result
    tweet_list_selector = pq("<ul id=\"py3crawler\">" + media_pagination_response.json_data["items_html"].strip() + "</ul>").children("li.js-stream-item")
    if int(media_pagination_response.json_data["new_latent_count"]) != tweet_list_selector.length:
        raise crawler.CrawlerException("tweet分组数量和返回数据中不一致\n%s\n%s" % (tweet_list_selector.length, media_pagination_response.json_data["new_latent_count"]))
    for tweet_index in range(0, tweet_list_selector.length):
        result_media_info = {
            "blog_id": None,  # 推特id
            "has_video": False,  # 是不是包含视频
            "photo_url_list": [],  # 全部图片地址
        }
        tweet_selector = tweet_list_selector.eq(tweet_index)
        # 获取推特id
        tweet_id = tweet_selector.attr("data-item-id")
        if not crawler.is_integer(tweet_id):
            raise crawler.CrawlerException("推特信息截取推特id败\n%s" % tweet_selector.html())
        result_media_info["blog_id"] = int(tweet_id)
        # 获取图片地址
        photo_list_selector = tweet_selector.find("div.js-adaptive-photo")
        for photo_index in range(0, photo_list_selector.length):
            result_media_info["photo_url_list"].append(photo_list_selector.eq(photo_index).attr("data-image-url"))
        # 判断是不是有视频
        result_media_info["has_video"] = tweet_selector.find("div.AdaptiveMedia-video").length > 0
        result["media_info_list"].append(result_media_info)
    # 判断是不是还有下一页
    if media_pagination_response.json_data["has_more_items"]:
        result["next_page_position"] = media_pagination_response.json_data["min_position"]
    return result


# 根据视频所在推特的ID，获取视频的下载地址
def get_video_play_page(tweet_id):
    thread_event.wait()
    thread_event.clear()
    video_play_url = "https://api.twitter.com/1.1/videos/tweet/config/%s.json" % tweet_id
    header_list = {
        "authorization": "Bearer " + AUTHORIZATION,
        "x-csrf-token": COOKIE_INFO["ct0"],
    }
    video_play_response = net.http_request(video_play_url, method="GET", cookies_list=COOKIE_INFO, header_list=header_list, json_decode=True)
    result = {
        "video_url": None,  # 视频地址
    }
    thread_event.set()
    if video_play_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_play_response.status))
    if not crawler.check_sub_key(("track",), video_play_response.json_data):
        raise crawler.CrawlerException("返回信息'track'字段不存在\n%s" % video_play_response.json_data)
    if not crawler.check_sub_key(("playbackUrl",), video_play_response.json_data["track"]):
        raise crawler.CrawlerException("返回信息'playbackUrl'字段不存在\n%s" % video_play_response.json_data["track"])
    file_url = video_play_response.json_data["track"]["playbackUrl"]
    file_type = net.get_file_type(file_url)
    # m3u8文件，需要再次访问获取真实视频地址
    # https://api.twitter.com/1.1/videos/tweet/config/996368816174084097.json
    if file_type == "m3u8":
        file_url_protocol, file_url_path = urllib.parse.splittype(file_url)
        file_url_host = urllib.parse.splithost(file_url_path)[0]
        m3u8_file_response = net.http_request(file_url, method="GET")
        # 没有权限（可能是地域限制）或者已删除
        if m3u8_file_response.status in [403, 404]:
            return result
        elif m3u8_file_response.status != net.HTTP_RETURN_CODE_SUCCEED:
            raise crawler.CrawlerException("m3u8文件 %s 访问失败，%s" % (file_url, crawler.request_failre(m3u8_file_response.status)))
        m3u8_file_response_content = m3u8_file_response.data.decode(errors="ignore")
        include_m3u8_file_list = re.findall("(/[\S]*.m3u8)", m3u8_file_response_content)
        if len(include_m3u8_file_list) > 0:
            # 生成最高分辨率视频所在的m3u8文件地址
            file_url = "%s://%s%s" % (file_url_protocol, file_url_host, include_m3u8_file_list[-1])
            m3u8_file_response = net.http_request(file_url, method="GET")
            if m3u8_file_response.status != net.HTTP_RETURN_CODE_SUCCEED:
                raise crawler.CrawlerException("最高分辨率m3u8文件 %s 访问失败，%s" % (file_url, crawler.request_failre(m3u8_file_response.status)))
            m3u8_file_response_content = m3u8_file_response.data.decode(errors="ignore")
        # 包含分P视频文件名的m3u8文件
        ts_url_find = re.findall("(/[\S]*.ts)", m3u8_file_response_content)
        if len(ts_url_find) == 0:
            raise crawler.CrawlerException("m3u8文件截取视频地址失败\n%s\n%s" % (file_url, m3u8_file_response_content))
        result["video_url"] = []
        for ts_file_path in ts_url_find:
            result["video_url"].append("%s://%s%s" % (file_url_protocol, file_url_host, ts_file_path))
    # 直接是视频地址
    # https://api.twitter.com/1.1/videos/tweet/config/996368816174084097.json
    else:
        result["video_url"] = file_url
    return result


class Twitter(crawler.Crawler):
    def __init__(self, extra_config=None):
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
        crawler.Crawler.__init__(self, sys_config, extra_config)

        # 设置全局变量，供子线程调用
        COOKIE_INFO = self.cookie_value
        if "_twitter_sess" not in COOKIE_INFO or "ct0" not in COOKIE_INFO:
            COOKIE_INFO = {}

        # 解析存档文件
        # account_name  account_id  last_tweet_id
        self.account_list = crawler.read_save_data(self.save_data_path, 0, ["", "", "0"])

        # 生成authorization，用于访问视频页
        try:
            init_session()
        except crawler.CrawlerException as e:
            log.error("生成authorization失败，原因：%s" % e.message)
            raise

    def main(self):
        # 循环下载每个id
        thread_list = []
        for account_name in sorted(self.account_list.keys()):
            # 提前结束
            if not self.is_running():
                break

            # 开始下载
            thread = Download(self.account_list[account_name], self)
            thread.start()
            thread_list.append(thread)

            time.sleep(1)

        # 等待子线程全部完成
        while len(thread_list) > 0:
            thread_list.pop().join()

        # 未完成的数据保存
        if len(self.account_list) > 0:
            file.write_file(tool.list_to_string(list(self.account_list.values())), self.temp_save_data_path)

        # 重新排序保存存档文件
        crawler.rewrite_save_file(self.temp_save_data_path, self.save_data_path)

        log.step("全部下载完毕，耗时%s秒，共计图片%s张，视频%s个" % (self.get_run_time(), self.total_photo_count, self.total_video_count))


class Download(crawler.DownloadThread):
    init_position_blog_id = "1999999999999999999"

    def __init__(self, account_info, main_thread):
        crawler.DownloadThread.__init__(self, account_info, main_thread)
        self.account_name = self.account_info[0]
        self.display_name = self.account_name
        self.step("开始")

    # 获取所有可下载推特
    def get_crawl_list(self):
        position_blog_id = self.init_position_blog_id
        media_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的推特
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析position：%s页推特" % position_blog_id)

            # 获取指定时间点后的一页图片信息
            try:
                media_pagination_response = get_one_page_media(self.account_name, position_blog_id)
            except crawler.CrawlerException as e:
                self.error("position：%s页推特解析失败，原因：%s" % (position_blog_id, e.message))
                raise

            if media_pagination_response["is_over"]:
                break

            self.trace("position：%s页解析的全部推特：%s" % (position_blog_id, media_pagination_response["media_info_list"]))
            self.step("position：%s页解析获取%s个推特" % (position_blog_id, len(media_pagination_response["media_info_list"])))

            # 寻找这一页符合条件的推特
            for media_info in media_pagination_response["media_info_list"]:
                # 检查是否达到存档记录
                if media_info["blog_id"] > int(self.account_info[2]):
                    media_info_list.append(media_info)
                else:
                    is_over = True
                    break

            if not is_over:
                # 下一页的指针
                if media_pagination_response["next_page_position"] is None:
                    is_over = True
                else:
                    # 设置下一页
                    position_blog_id = media_pagination_response["next_page_position"]

        return media_info_list

    # 解析单个推特
    def crawl_media(self, media_info):
        # 图片下载
        photo_index = 1
        if self.main_thread.is_download_photo:
            self.trace("推特%s解析的全部图片：%s" % (media_info["blog_id"], media_info["photo_url_list"]))
            self.step("推特%s解析获取%s张图片" % (media_info["blog_id"], len(media_info["photo_url_list"])))

            for photo_url in media_info["photo_url_list"]:
                self.main_thread_check()  # 检测主线程运行状态
                self.step("开始下载推特%s的第%s张图片 %s" % (media_info["blog_id"], photo_index, photo_url))

                photo_file_path = os.path.join(self.main_thread.photo_download_path, self.account_name, "%019d_%02d.%s" % (media_info["blog_id"], photo_index, net.get_file_type(photo_url)))
                save_file_return = net.save_net_file(photo_url, photo_file_path)
                if save_file_return["status"] == 1:
                    self.temp_path_list.append(photo_file_path)
                    self.step("推特%s的第%s张图片下载成功" % (media_info["blog_id"], photo_index))
                else:
                    self.error("推特%s的第%s张图片 %s 下载失败，原因：%s" % (media_info["blog_id"], photo_index, photo_url, crawler.download_failre(save_file_return["code"])))
                photo_index += 1

        # 视频下载
        download_complete = False
        if self.main_thread.is_download_video and media_info["has_video"]:
            self.main_thread_check()  # 检测主线程运行状态
            # 获取视频播放地址
            try:
                video_play_response = get_video_play_page(media_info["blog_id"])
            except crawler.CrawlerException as e:
                self.error("推特%s的视频解析失败，原因：%s" % (media_info["blog_id"], e.message))
                raise

            if video_play_response["video_url"] is None:
                self.error("推特%s的视频无法访问，跳过" % media_info["blog_id"])
            else:
                self.trace("推特%s解析的视频：%s" % (media_info["blog_id"], video_play_response["video_url"]))

                self.main_thread_check()  # 检测主线程运行状态
                self.step("开始下载推特%s的视频 %s" % (media_info["blog_id"], video_play_response["video_url"]))
                
                # 分割后的ts格式视频
                if isinstance(video_play_response["video_url"], list):
                    video_file_path = os.path.join(self.main_thread.video_download_path, self.account_name, "%019d.ts" % media_info["blog_id"])
                    save_file_return = net.save_net_file_list(video_play_response["video_url"], video_file_path)
                # 其他格式的视频
                else:
                    video_file_path = os.path.join(self.main_thread.video_download_path, self.account_name, "%019d.%s" % (media_info["blog_id"], net.get_file_type(video_play_response["video_url"])))
                    save_file_return = net.save_net_file(video_play_response["video_url"], video_file_path)
                if save_file_return["status"] == 1:
                    self.temp_path_list.append(video_file_path)
                    self.step("推特%s的视频下载成功" % media_info["blog_id"])
                    download_complete = True
                else:
                    self.error("推特%s的视频 %s 下载失败，原因：%s" % (media_info["blog_id"], video_play_response["video_url"], crawler.download_failre(save_file_return["code"])))

        # 推特内图片和视频全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.total_photo_count += photo_index - 1  # 计数累加
        if download_complete:
            self.total_video_count += 1  # 计数累加
        self.account_info[2] = str(media_info["blog_id"])

    def run(self):
        try:
            try:
                account_index_response = get_account_index_page(self.account_name)
            except crawler.CrawlerException as e:
                self.error("首页解析失败，原因：%s" % e.message)
                raise

            if self.account_info[1] == "":
                self.account_info[1] = account_index_response["account_id"]
            else:
                if self.account_info[1] != account_index_response["account_id"]:
                    self.error("account id 不符合，原账号已改名")
                    tool.process_exit()

            # 获取所有可下载推特
            media_info_list = self.get_crawl_list()
            self.step("需要下载的全部推特解析完毕，共%s个" % len(media_info_list))

            # 从最早的推特开始下载
            while len(media_info_list) > 0:
                media_info = media_info_list.pop()
                self.step("开始解析推特%s" % media_info["blog_id"])
                self.crawl_media(media_info)
                self.main_thread_check()  # 检测主线程运行状态
        except SystemExit as se:
            if se.code == 0:
                self.step("提前退出")
            else:
                self.error("异常退出")
            # 如果临时目录变量不为空，表示某个日志正在下载中，需要把下载了部分的内容给清理掉
            self.clean_temp_path()
        except Exception as e:
            self.error("未知异常")
            self.error(str(e) + "\n" + traceback.format_exc(), False)

        # 保存最后的信息
        with self.thread_lock:
            file.write_file("\t".join(self.account_info), self.main_thread.temp_save_data_path)
            self.main_thread.total_photo_count += self.total_photo_count
            self.main_thread.total_video_count += self.total_video_count
            self.main_thread.account_list.pop(self.account_name)
        self.step("下载完毕，总共获得%s张图片和%s个视频" % (self.total_photo_count, self.total_video_count))
        self.notify_main_thread()


if __name__ == "__main__":
    Twitter().main()
