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
import time
import traceback
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
    script_json_html = tool.find_sub_string(index_page_response_content, "var __PLAYER_CONFIG__ = ", ";</script>\n")
    if not script_json_html:
        raise crawler.CrawlerException("页面信息截取失败\n" + index_page_response_content)
    script_json = tool.json_decode(script_json_html)
    if script_json is None:
        raise crawler.CrawlerException("页面信息加载失败\n" + index_page_response_content)
    post_data = {
        "client_id": crawler.get_json_value(script_json, "context", "api", "client_id", type_check=str),
        "client_secret": crawler.get_json_value(script_json, "context", "api", "client_secret", type_check=str),
        "grant_type": "client_credentials",
        "visitor_id": tool.generate_random_string(32, 6),
        "traffic_segment": random.randint(100000, 999999)
    }
    oauth_response = net.request(crawler.get_json_value(script_json, "context", "api", "auth_url", type_check=str), method="POST", fields=post_data, json_decode=True)
    if oauth_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(f"获取token页，{crawler.request_failre(oauth_response.status)}\n" + str(post_data))
    AUTHORIZATION = crawler.get_json_value(oauth_response.json_data, "access_token", type_check=str)


# 获取视频列表
def get_one_page_video(account_id, page_count):
    api_url = "https://graphql.api.dailymotion.com/"
    post_data = {
        "operationName": "CHANNEL_VIDEOS_QUERY",
        "variables": {
            "channel_xid": account_id,
            "uri": f"/{account_id}/videos",
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
            "video_id": None,  # 视频id
            "video_time": None,  # 视频上传时间
            "video_title": "",  # 视频标题
        }
        # 获取视频id
        result_video_info["video_id"] = crawler.get_json_value(video_info, "node", "xid", type_check=str)
        # 获取视频上传时间
        result_video_info["video_time"] = int(time.mktime(time.strptime(crawler.get_json_value(video_info, "node", "createdAt", type_check=str), "%Y-%m-%dT%H:%M:%S+00:00")))
        # 获取视频标题
        result_video_info["video_title"] = crawler.get_json_value(video_info, "node", "title", type_check=str)
        result["video_info_list"].append(result_video_info)
    # 判断是不是最后一页
    if crawler.get_json_value(api_response.json_data, "data", "channel", "channel_videos_all_videos", "pageInfo", "hasNextPage", type_check=bool) is False:
        result["is_over"] = True
    # API只能查询100页的视频，可以测试账号 usatodaysports
    if page_count == 100:
        result["is_over"] = True
    return result


# 获取指定视频
def get_video_page(video_id):
    # 获取视频播放页
    # https://www.dailymotion.com/player/metadata/video/x6lgrfa
    video_info_url = f"https://www.dailymotion.com/player/metadata/video/{video_id}"
    video_info_response = net.request(video_info_url, method="GET", json_decode=True)
    result = {
        "is_delete": False,  # 是否已删除
        "video_title": "",  # 视频标题
        "video_url": None,  # 视频地址
    }
    if video_info_response.status == 404:
        result["is_delete"] = True
        return result
    elif video_info_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_info_response.status))
    # 获取视频标题
    result["video_title"] = crawler.get_json_value(video_info_response.json_data, "title", type_check=str)
    # 查找最高分辨率的视频源地址
    resolution_to_url = {}  # 各个分辨率下的视频地址
    for video_resolution, video_info_list in crawler.get_json_value(video_info_response.json_data, "qualities", type_check=dict).items():
        if not tool.is_integer(video_resolution):
            continue
        video_resolution = int(video_resolution)
        if video_resolution not in [144, 240, 380, 480, 720, 1080]:
            log.notice(f"未知视频分辨率：{video_resolution}")
        for video_info in video_info_list:
            if crawler.get_json_value(video_info, "type", type_check=str) == "video/mp4":
                resolution_to_url[video_resolution] = crawler.get_json_value(video_info, "url", type_check=str)
    if len(resolution_to_url) == 0:
        raise crawler.CrawlerException("匹配不同分辨率视频源失败\n" + video_info_response.json_data)
    # 优先使用配置中的分辨率
    if FIRST_CHOICE_RESOLUTION in resolution_to_url:
        result["video_url"] = resolution_to_url[FIRST_CHOICE_RESOLUTION]
    # 如果没有这个分辨率的视频
    else:
        # 大于配置中分辨率的所有视频中分辨率最小的那个
        for resolution in sorted(resolution_to_url.keys()):
            if resolution > FIRST_CHOICE_RESOLUTION:
                result["video_url"] = resolution_to_url[resolution]
                break
        # 如果还是没有，则所有视频中分辨率最大的那个
        if result["video_url"] is None:
            result["video_url"] = resolution_to_url[max(resolution_to_url)]
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

        # 生成authorization，用于访问视频页
        try:
            init_session()
        except crawler.CrawlerException as e:
            log.error(f"生成authorization失败，原因：{e.message}")
            raise

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
    is_find = False

    def __init__(self, single_save_data, main_thread):
        crawler.DownloadThread.__init__(self, single_save_data, main_thread)
        self.account_id = self.single_save_data[0]
        self.display_name = self.account_id
        self.step("开始")

    # 获取所有可下载视频
    def get_crawl_list(self):
        page_count = 1
        video_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的相册
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step(f"开始解析第{page_count}页视频")

            try:
                blog_pagination_response = get_one_page_video(self.account_id, page_count)
            except crawler.CrawlerException as e:
                self.error(f"第{page_count}页视频解析失败，原因：{e.message}")
                raise

            self.trace(f"第{page_count}页解析的全部视频：{blog_pagination_response['video_info_list']}")
            self.step(f"第{page_count}页解析获取{len(blog_pagination_response['video_info_list'])}个视频")

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
        self.step(f"开始解析视频{video_info['video_id']}")

        # 获取指定视频信息
        try:
            video_response = get_video_page(video_info["video_id"])
        except crawler.CrawlerException as e:
            self.error(f"视频{video_info['video_id']}解析失败，原因：{e.message}")
            raise

        self.step(f"开始下载视频{video_info['video_id']} 《{video_info['video_title']}》 {video_response['video_url']}")

        video_file_path = os.path.join(self.main_thread.video_download_path, self.account_id, f"{video_info['video_id']} - {path.filter_text(video_info['video_title'])}.mp4")
        save_file_return = net.download(video_response["video_url"], video_file_path, head_check=True)
        if save_file_return["status"] == 1:
            self.total_video_count += 1  # 计数累加
            self.step(f"视频{video_info['video_id']} 《{video_info['video_title']}》下载成功")
        else:
            self.error(f"视频{video_info['video_id']} 《{video_info['video_title']}》 {video_response['video_url']} 下载失败，原因：{crawler.download_failre(save_file_return['code'])}")
            self.check_download_failure_exit()

        # 视频全部下载完毕
        self.single_save_data[1] = str(video_info["video_time"])  # 设置存档记录

    def run(self):
        try:
            # 获取所有可下载视频
            video_info_list = self.get_crawl_list()
            self.step(f"需要下载的全部视频解析完毕，共{len(video_info_list)}个")

            # 从最早的视频开始下载
            while len(video_info_list) > 0:
                self.crawl_video(video_info_list.pop())
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
    DailyMotion().main()
