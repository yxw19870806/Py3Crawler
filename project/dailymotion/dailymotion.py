# -*- coding:UTF-8  -*-
"""
dailymotion视频爬虫
https://www.dailymotion.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import json
import os
import random
import re
import time
from common import *

AUTHORIZATION = ""
FIRST_CHOICE_RESOLUTION = 720


# 初始化session。获取authorization
def init_session():
    global AUTHORIZATION
    index_url = "https://www.dailymotion.com"
    index_page_response = net.request(index_url, method="GET")
    if index_page_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException("首页，" + crawler.request_failre(index_page_response.status))
    index_page_response_content = index_page_response.data.decode(errors="ignore")
    client_id_and_secret_find = re.findall(r'var r="(\w{20,})",o="(\w{40,})"', index_page_response_content)
    if len(client_id_and_secret_find) != 1 or len(client_id_and_secret_find[0]) != 2:
        raise crawler.CrawlerException("页面截取client_id和client_secret失败\n" + index_page_response_content)
    post_data = {
        "client_id": client_id_and_secret_find[0][0],
        "client_secret": client_id_and_secret_find[0][1],
        "grant_type": "client_credentials",
        "visitor_id": tool.generate_random_string(32, 6),
        "traffic_segment": random.randint(100000, 999999)
    }
    oauth_response = net.request("https://graphql.api.dailymotion.com/oauth/token", method="POST", fields=post_data, json_decode=True)
    if oauth_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException("获取token页，%s\n%s" % (crawler.request_failre(oauth_response.status), str(post_data)))
    AUTHORIZATION = crawler.get_json_value(oauth_response.json_data, "access_token", type_check=str)


# 获取视频列表
def get_one_page_video(account_id, page_count):
    api_url = "https://graphql.api.dailymotion.com/"
    post_data = {
        "operationName": "CHANNEL_VIDEOS_QUERY",
        "variables": {
            "channel_xid": account_id,
            "uri": "/%s/videos" % account_id,
            "page": page_count,
            "sort": "recent",
        },
        "query": "fragment CHANNEL_BASE_FRAGMENT on Channel {\n  id\n  xid\n  name\n  displayName\n  isArtist\n  logoURL(size: \"x60\")\n  isFollowed\n  accountType\n  __typename\n}\n\nfragment CHANNEL_IMAGES_FRAGMENT on Channel {\n  coverURLx375: coverURL(size: \"x375\")\n  __typename\n}\n\nfragment CHANNEL_UPDATED_FRAGMENT on Channel {\n  isFollowed\n  stats {\n    views {\n      total\n      __typename\n    }\n    followers {\n      total\n      __typename\n    }\n    videos {\n      total\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment CHANNEL_COMPLETE_FRAGMENT on Channel {\n  ...CHANNEL_BASE_FRAGMENT\n  ...CHANNEL_IMAGES_FRAGMENT\n  ...CHANNEL_UPDATED_FRAGMENT\n  description\n  coverURL1024x: coverURL(size: \"1024x\")\n  coverURL1920x: coverURL(size: \"1920x\")\n  externalLinks {\n    facebookURL\n    twitterURL\n    websiteURL\n    instagramURL\n    __typename\n  }\n  __typename\n}\n\nfragment CHANNEL_FRAGMENT on Channel {\n  id\n  xid\n  name\n  displayName\n  isArtist\n  logoURL(size: \"x60\")\n  coverURLx375: coverURL(size: \"x375\")\n  isFollowed\n  __typename\n}\n\nfragment VIDEO_FRAGMENT on Video {\n  id\n  xid\n  title\n  viewCount\n  duration\n  createdAt\n  channel {\n    ...CHANNEL_FRAGMENT\n    __typename\n  }\n  thumbURLx240: thumbnailURL(size: \"x240\")\n  thumbURLx360: thumbnailURL(size: \"x360\")\n  thumbURLx480: thumbnailURL(size: \"x480\")\n  thumbURLx720: thumbnailURL(size: \"x720\")\n  __typename\n}\n\nfragment METADATA_FRAGMENT on Neon {\n  web(uri: $uri) {\n    author\n    description\n    title\n    metadatas {\n      attributes {\n        name\n        content\n        __typename\n      }\n      __typename\n    }\n    language {\n      codeAlpha2\n      __typename\n    }\n    country {\n      codeAlpha2\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment LOCALIZATION_FRAGMENT on Localization {\n  me {\n    id\n    country {\n      codeAlpha2\n      name\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nquery CHANNEL_VIDEOS_QUERY($channel_xid: String!, $sort: String, $page: Int!, $uri: String!) {\n  localization {\n    ...LOCALIZATION_FRAGMENT\n    __typename\n  }\n  views {\n    id\n    neon {\n      id\n      ...METADATA_FRAGMENT\n      __typename\n    }\n    __typename\n  }\n  channel(xid: $channel_xid) {\n    ...CHANNEL_COMPLETE_FRAGMENT\n    channel_videos_all_videos: videos(sort: $sort, page: $page, first: 30) {\n      pageInfo {\n        hasNextPage\n        nextPage\n        __typename\n      }\n      edges {\n        node {\n          ...VIDEO_FRAGMENT\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n"
    }
    header_list = {
        "authorization": "Bearer " + AUTHORIZATION,
        "origin": "https://www.dailymotion.com",
    }
    result = {
        "is_over": False,  # 是否最后一页视频
        "video_info_list": [],  # 全部视频信息
    }
    api_response = net.request(api_url, method="POST", binary_data=json.dumps(post_data), header_list=header_list, json_decode=True)
    if api_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(api_response.status))
    # 获取所有视频
    for video_info in crawler.get_json_value(api_response.json_data, "data", "channel", "channel_videos_all_videos", "edges", type_check=list):
        result_video_info = {
            "video_id": "",  # 视频id
            "video_time": "",  # 视频上传时间
            "video_title": "",  # 视频标题
        }
        # 获取视频id
        result_video_info["video_id"] = crawler.get_json_value(video_info, "node", "xid", type_check=str)
        # 获取视频上传时间
        video_time = crawler.get_json_value(video_info, "node", "createdAt", type_check=str)
        result_video_info["video_time"] = int(time.mktime(time.strptime(video_time, "%Y-%m-%dT%H:%M:%S+00:00")))
        # 获取视频标题
        result_video_info["video_title"] = crawler.get_json_value(video_info, "node", "title", type_check=str)
        result["video_info_list"].append(result_video_info)
    # 判断是不是最后一页
    # 另API最多只能查询33页（990个）的视频，可以测试的账号 usatodaysports
    if crawler.get_json_value(api_response.json_data, "data", "channel", "channel_videos_all_videos", "pageInfo", "hasNextPage", type_check=bool) is False:
        result["is_over"] = True
    return result


# 获取指定视频
def get_video_page(video_id):
    # 获取视频播放页
    # https://www.dailymotion.com/player/metadata/video/x6lgrfa
    video_info_url = "https://www.dailymotion.com/player/metadata/video/%s" % video_id
    video_info_response = net.request(video_info_url, method="GET", json_decode=True)
    result = {
        "is_delete": False,  # 是否已删除
        "video_title": "",  # 视频标题
        "video_url": "",  # 视频地址
    }
    if video_info_response.status == 404:
        result["is_delete"] = True
        return result
    elif video_info_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_info_response.status))
    # 获取视频标题
    result["video_title"] = crawler.get_json_value(video_info_response.json_data, "title", type_check=str)
    # 查找最高分辨率的视频源地址
    m3u8_file_url = crawler.get_json_value(video_info_response.json_data, "qualities", "auto", 0, "url", type_check=str)
    m3u8_file_response = net.request(m3u8_file_url, method="GET")
    m3u8_file_response_content = m3u8_file_response.data.decode(errors="ignore")
    max_resolution = 0
    video_url = ""
    for line in m3u8_file_response_content.split("\n"):
        if line[:len("#EXT-X-STREAM-INF:")] != "#EXT-X-STREAM-INF:":
            continue
        resolution_find = re.findall(r"RESOLUTION=(\d*)x(\d*)", line)
        if len(resolution_find) != 1 or len(resolution_find[0]) != 2:
            raise crawler.CrawlerException("视频信息截取分辨率失败\n" + line)
        resolution = int(resolution_find[0][0]) * int(resolution_find[0][1])
        if resolution > max_resolution:
            video_url = tool.find_sub_string(line, 'PROGRESSIVE-URI="', '"')
            if not video_url:
                raise crawler.CrawlerException("视频信息截取视频地址失败\n" + line)
    if not video_url:
        raise crawler.CrawlerException("视频信息截取最大分辨率视频地址失败\n" + m3u8_file_response_content)
    result["video_url"] = video_url
    return result


class DailyMotion(crawler.Crawler):
    def __init__(self, **kwargs):
        global FIRST_CHOICE_RESOLUTION

        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_VIDEO: True,
            crawler.SYS_APP_CONFIG: (
                ("VIDEO_QUALITY", 6, crawler.CONFIG_ANALYSIS_MODE_INTEGER),
            ),
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 设置全局变量，供子线程调用
        video_quality = self.app_config["VIDEO_QUALITY"]
        if video_quality == 1:
            FIRST_CHOICE_RESOLUTION = 144
        elif video_quality == 2:
            FIRST_CHOICE_RESOLUTION = 240
        elif video_quality == 3:
            FIRST_CHOICE_RESOLUTION = 380
        elif video_quality == 4:
            FIRST_CHOICE_RESOLUTION = 480
        elif video_quality == 5:
            FIRST_CHOICE_RESOLUTION = 720
        elif video_quality == 6:
            FIRST_CHOICE_RESOLUTION = 1080
        else:
            log.error("配置文件config.ini中key为'video_quality'的值必须是一个1~6的整数，使用程序默认设置")

        # 解析存档文件
        # account_id  video_time
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

        # 下载线程
        self.crawler_thread = CrawlerThread

    def init(self):
        # 生成authorization，用于访问视频页
        try:
            init_session()
        except crawler.CrawlerException as e:
            log.error(e.http_error("生成authorization"))
            raise


class CrawlerThread(crawler.CrawlerThread):
    def __init__(self, single_save_data, main_thread):
        self.index_key = self.display_name = single_save_data[0]  # account id
        crawler.CrawlerThread.__init__(self, single_save_data, main_thread)

    def _run(self):
        # 获取所有可下载视频
        video_info_list = self.get_crawl_list()
        self.step("需要下载的全部视频解析完毕，共%s个" % len(video_info_list))

        # 从最早的视频开始下载
        while len(video_info_list) > 0:
            self.crawl_video(video_info_list.pop())
            self.main_thread_check()  # 检测主线程运行状态

    # 获取所有可下载视频
    def get_crawl_list(self):
        page_count = 1
        video_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的相册
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态

            pagination_description = "第%s页视频" % page_count
            self.start_parse(pagination_description)

            try:
                blog_pagination_response = get_one_page_video(self.index_key, page_count)
            except crawler.CrawlerException as e:
                self.error(e.http_error(pagination_description))
                raise

            self.parse_result(pagination_description, blog_pagination_response["video_info_list"])

            # 寻找这一页符合条件的日志
            for video_info in blog_pagination_response["video_info_list"]:
                # 检查是否达到存档记录
                if video_info["video_time"] > int(self.single_save_data[1]):
                    video_info_list.append(video_info)
                else:
                    is_over = True

            if not is_over:
                if blog_pagination_response["is_over"]:
                    is_over = True
                else:
                    page_count += 1
        return video_info_list

    # 解析单个视频
    def crawl_video(self, video_info):
        video_description = "视频%s 《%s》" % (video_info["video_id"], video_info["video_title"])
        self.start_parse(video_description)

        # 获取指定视频信息
        try:
            video_response = get_video_page(video_info["video_id"])
        except crawler.CrawlerException as e:
            self.error(e.http_error(video_description))
            raise

        video_name = "%s - %s.mp4" % (video_info["video_id"], path.filter_text(video_info["video_title"]))
        video_path = os.path.join(self.main_thread.video_download_path, self.index_key, video_name)
        if self.download(video_response["video_url"], video_path, video_description, auto_multipart_download=True, is_url_encode=False).is_success():
            self.total_video_count += 1  # 计数累加

        # 视频全部下载完毕
        self.single_save_data[1] = str(video_info["video_time"])  # 设置存档记录


if __name__ == "__main__":
    DailyMotion().main()
