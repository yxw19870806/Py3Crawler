# -*- coding:UTF-8  -*-
"""
dailymotion视频爬虫
https://www.dailymotion.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import random
import re
from common import *

AUTHORIZATION = ""
FIRST_CHOICE_RESOLUTION = 720


# 初始化session。获取authorization
def init_session():
    global AUTHORIZATION
    index_url = "https://www.dailymotion.com"
    index_response = net.Request(index_url, method="GET")
    if index_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException("首页，" + crawler.request_failre(index_response.status))
    client_id_and_secret_find = re.findall(r'var r="(\w{20,})",o="(\w{40,})"', index_response.content)
    if len(client_id_and_secret_find) != 1 or len(client_id_and_secret_find[0]) != 2:
        raise CrawlerException("页面截取client_id和client_secret失败\n" + index_response.content)
    post_data = {
        "client_id": client_id_and_secret_find[0][0],
        "client_secret": client_id_and_secret_find[0][1],
        "grant_type": "client_credentials",
        "visitor_id": tool.generate_random_string(32, 6),
        "traffic_segment": random.randint(100000, 999999)
    }
    oauth_response = net.Request("https://graphql.api.dailymotion.com/oauth/token", method="POST", fields=post_data).enable_json_decode()
    if oauth_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException("获取token页，%s\n%s" % (crawler.request_failre(oauth_response.status), str(post_data)))
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
        "query": 'fragment CHANNEL_BASE_FRAGMENT on Channel{id xid name displayName isArtist logoURL(size:"x60") isFollowed accountType __typename}fragment CHANNEL_IMAGES_FRAGMENT on Channel{coverURLx375:coverURL(size:"x375") __typename}fragment CHANNEL_UPDATED_FRAGMENT on Channel{isFollowed stats{views{total __typename}followers{total __typename}videos{total __typename}__typename}__typename}fragment CHANNEL_COMPLETE_FRAGMENT on Channel{...CHANNEL_BASE_FRAGMENT ...CHANNEL_IMAGES_FRAGMENT ...CHANNEL_UPDATED_FRAGMENT description coverURL1024x:coverURL(size:"1024x") coverURL1920x:coverURL(size:"1920x") externalLinks{facebookURL twitterURL websiteURL instagramURL __typename}__typename}fragment CHANNEL_FRAGMENT on Channel{id xid name displayName isArtist logoURL(size:"x60") coverURLx375:coverURL(size:"x375") isFollowed __typename}fragment VIDEO_FRAGMENT on Video{id xid title viewCount duration createdAt channel{...CHANNEL_FRAGMENT __typename}thumbURLx240:thumbnailURL(size:"x240") thumbURLx360:thumbnailURL(size:"x360") thumbURLx480:thumbnailURL(size:"x480") thumbURLx720:thumbnailURL(size:"x720") __typename}fragment METADATA_FRAGMENT on Neon{web(uri:$uri){author description title metadatas{attributes{name content __typename}__typename}language{codeAlpha2 __typename}country{codeAlpha2 __typename}__typename}__typename}fragment LOCALIZATION_FRAGMENT on Localization{me{id country{codeAlpha2 name __typename}__typename}__typename}query CHANNEL_VIDEOS_QUERY($channel_xid:String!, $sort:String, $page:Int!, $uri:String!){localization{...LOCALIZATION_FRAGMENT __typename}views{id neon{id ...METADATA_FRAGMENT __typename}__typename}channel(xid:$channel_xid){...CHANNEL_COMPLETE_FRAGMENT channel_videos_all_videos:videos(sort:$sort, page:$page, first:30){pageInfo{hasNextPage nextPage __typename}edges{node{...VIDEO_FRAGMENT __typename}__typename}__typename}__typename}}'
    }
    headers = {
        "authorization": "Bearer " + AUTHORIZATION,
        "origin": "https://www.dailymotion.com",
    }
    result = {
        "is_over": False,  # 是否最后一页视频
        "video_info_list": [],  # 全部视频信息
    }
    api_response = net.Request(api_url, method="POST", fields=tool.json_encode(post_data), headers=headers).enable_json_decode()
    if api_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(api_response.status))
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
        result_video_info["video_time"] = tool.convert_formatted_time_to_timestamp(video_time, "%Y-%m-%dT%H:%M:%S+00:00")
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
    video_info_response = net.Request(video_info_url, method="GET").enable_json_decode()
    result = {
        "is_delete": False,  # 是否已删除
        "video_title": "",  # 视频标题
        "video_url": "",  # 视频地址
    }
    if video_info_response.status == 404:
        result["is_delete"] = True
        return result
    elif video_info_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(video_info_response.status))
    # 获取视频标题
    result["video_title"] = crawler.get_json_value(video_info_response.json_data, "title", type_check=str)
    # 查找最高分辨率的视频源地址
    m3u8_file_url = crawler.get_json_value(video_info_response.json_data, "qualities", "auto", 0, "url", type_check=str)
    m3u8_file_response = net.Request(m3u8_file_url, method="GET")
    max_resolution = 0
    video_url = ""
    for line in m3u8_file_response.content.split("\n"):
        if not line.startswith("#EXT-X-STREAM-INF:"):
            continue
        resolution_find = re.findall(r"RESOLUTION=(\d*)x(\d*)", line)
        if len(resolution_find) != 1 or len(resolution_find[0]) != 2:
            raise CrawlerException("视频信息截取分辨率失败\n" + line)
        resolution = int(resolution_find[0][0]) * int(resolution_find[0][1])
        if resolution > max_resolution:
            video_url = tool.find_sub_string(line, 'PROGRESSIVE-URI="', '"')
            if not video_url:
                raise CrawlerException("视频信息截取视频地址失败\n" + line)
    if not video_url:
        raise CrawlerException("视频信息截取最大分辨率视频地址失败\n" + m3u8_file_response.content)
    result["video_url"] = video_url
    return result


class DailyMotion(crawler.Crawler):
    def __init__(self, **kwargs):
        global FIRST_CHOICE_RESOLUTION

        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            const.SysConfigKey.DOWNLOAD_VIDEO: True,
            const.SysConfigKey.APP_CONFIG: (
                ("VIDEO_QUALITY", 6, const.ConfigAnalysisMode.INTEGER),
            ),
            const.SysConfigKey.SAVE_DATA_FORMATE: (0, ["", "0"]),  # account_id  last_video_time
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

        # 下载线程
        self.set_crawler_thread(CrawlerThread)

    def init(self):
        # 生成authorization，用于访问视频页
        try:
            init_session()
        except CrawlerException as e:
            log.error(e.http_error("生成authorization"))
            raise


class CrawlerThread(crawler.CrawlerThread):
    def __init__(self, main_thread, single_save_data):
        self.index_key = self.display_name = single_save_data[0]  # account id
        crawler.CrawlerThread.__init__(self, main_thread, single_save_data)

    # 获取所有可下载视频
    def get_crawl_list(self):
        page_count = 1
        video_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的相册
        while not is_over:
            blog_pagination_description = "第%s页视频" % page_count
            self.start_parse(blog_pagination_description)
            try:
                blog_pagination_response = get_one_page_video(self.index_key, page_count)
            except CrawlerException as e:
                self.error(e.http_error(blog_pagination_description))
                raise
            self.parse_result(blog_pagination_description, blog_pagination_response["video_info_list"])

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
        try:
            video_response = get_video_page(video_info["video_id"])
        except CrawlerException as e:
            self.error(e.http_error(video_description))
            raise

        video_name = "%s - %s.mp4" % (video_info["video_id"], path.filter_text(video_info["video_title"]))
        video_path = os.path.join(self.main_thread.video_download_path, self.index_key, video_name)
        if self.download(video_response["video_url"], video_path, video_description, auto_multipart_download=True, is_url_encode=False):
            self.total_video_count += 1  # 计数累加

        # 视频全部下载完毕
        self.single_save_data[1] = str(video_info["video_time"])  # 设置存档记录

    def _run(self):
        # 获取所有可下载视频
        video_info_list = self.get_crawl_list()
        self.info("需要下载的全部视频解析完毕，共%s个" % len(video_info_list))

        # 从最早的视频开始下载
        while len(video_info_list) > 0:
            self.crawl_video(video_info_list.pop())


if __name__ == "__main__":
    DailyMotion().main()
