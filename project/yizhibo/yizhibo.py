# -*- coding:UTF-8  -*-
"""
一直播图片&视频爬虫
http://www.yizhibo.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import re
import urllib.parse
from pyquery import PyQuery as pq
from common import *


# 获取全部图片地址列表
def get_photo_index_page(account_id):
    # https://www.yizhibo.com/member/personel/user_photos?memberid=334262811
    photo_index_url = "https://www.yizhibo.com/member/personel/user_photos"
    query_data = {"memberid": account_id}
    photo_index_response = net.Request(photo_index_url, method="GET", fields=query_data)
    result = {
        "photo_url_list": [],  # 全部图片地址
    }
    if photo_index_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(photo_index_response.status))
    if photo_index_response.content == '<script>window.location.href="/404.html";</script>':
        raise CrawlerException("账号不存在")
    # 获取全部图片地址
    if pq(photo_index_response.content).find(".index_all_list p").html() == "还没有照片哦":
        return result
    video_list_selector = pq(photo_index_response.content).find("img.index_img_main")
    for video_index in range(video_list_selector.length):
        photo_url = video_list_selector.eq(video_index).attr("src")
        result["photo_url_list"].append(photo_url.split("@")[0])
    if len(result["photo_url_list"]) == 0:
        raise CrawlerException("页面匹配图片地址失败\n" + photo_index_response.content)
    return result


#  获取图片的header
def get_photo_header(photo_url):
    photo_head_response = net.Request(photo_url, method="HEAD")
    result = {
        "photo_time": 0,  # 图片上传时间
    }
    if photo_head_response.status == 404:
        return result
    elif photo_head_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(photo_head_response.status))
    last_modified = photo_head_response.headers.get("Last-Modified")
    if not last_modified:
        raise CrawlerException(f"图片header {photo_head_response.headers}中'Last-Modified'字段不存在")
    try:
        result["photo_time"] = tool.convert_formatted_time_to_timestamp(last_modified, "%a, %d %b %Y %H:%M:%S %Z")
    except ValueError:
        raise CrawlerException(f"图片上传时间{last_modified}的格式不正确")
    return result


# 获取全部视频ID列表
def get_video_index_page(account_id):
    # https://www.yizhibo.com/member/personel/user_videos?memberid=334262811
    video_pagination_url = "https://www.yizhibo.com/member/personel/user_videos"
    query_data = {"memberid": account_id}
    video_pagination_response = net.Request(video_pagination_url, method="GET", fields=query_data)
    result = {
        "is_exist": True,  # 是否存在视频
        "video_id_list": [],  # 全部视频id
    }
    if video_pagination_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(video_pagination_response.status))
    if video_pagination_response.content == '<script>window.location.href="/404.html";</script>':
        raise CrawlerException("账号不存在")
    if pq(video_pagination_response.content).find(".index_all_list p").html() == "还没有直播哦":
        return result
    video_list_selector = pq(video_pagination_response.content).find("div.scid")
    for video_index in range(video_list_selector.length):
        result["video_id_list"].append(video_list_selector.eq(video_index).html())
    if len(result["video_id_list"]) == 0:
        raise CrawlerException("页面匹配视频id失败\n" + video_pagination_response.content)
    return result


# 根据video id获取指定视频的详细信息（上传时间、视频列表的下载地址等）
# video_id -> bVFjTEK9nYTEqQ6p
def get_video_info_page(video_id):
    # https://www.yizhibo.com/l/bVFjTEK9nYTEqQ6p.html
    video_info_url = f"https://www.yizhibo.com/l/{video_id}.html"
    video_info_response = net.Request(video_info_url, method="GET")
    result = {
        "m3u8_file_url": "",  # 分段文件地址
        "video_time": 0,  # 视频上传时间
        "video_url_list": [],  # 全部视频分集地址
    }
    if video_info_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(video_info_response.status))
    # 获取视频上传时间
    video_time = tool.find_sub_string(video_info_response.content, "starttime:", ",")
    if not tool.is_integer(video_time):
        raise CrawlerException("页面截取直播开始时间失败\n" + video_info_response.content)
    result["video_time"] = int(video_time)
    # 获取视频地址所在文件地址
    result["m3u8_file_url"] = tool.find_sub_string(video_info_response.content, 'play_url:"', '",')
    if not result["m3u8_file_url"]:
        raise CrawlerException("分集文件地址截取失败\n" + video_info_response.content)
    return result


class YiZhiBo(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            const.SysConfigKey.DOWNLOAD_PHOTO: True,
            const.SysConfigKey.DOWNLOAD_VIDEO: True,
            const.SysConfigKey.SAVE_DATA_FORMATE: (0, ["", "0", "0", "0", "0"]),  # account_id  video_count  last_video_time  photo_count  last_photo_time  (account_name)
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 下载线程
        self.set_crawler_thread(CrawlerThread)


class CrawlerThread(crawler.CrawlerThread):
    def __init__(self, main_thread, single_save_data):
        self.index_key = single_save_data[0]  # account id
        if len(single_save_data) >= 6 and single_save_data[5]:
            self.display_name = single_save_data[5]
        else:
            self.display_name = single_save_data[0]
        crawler.CrawlerThread.__init__(self, main_thread, single_save_data)

    # 获取所有可下载图片
    def get_crawl_photo_list(self):
        index_description = "图片首页"
        self.start_parse(index_description)
        try:
            photo_index_response = get_photo_index_page(self.index_key)
        except CrawlerException as e:
            self.error(e.http_error(index_description))
            return []
        self.parse_result(index_description, photo_index_response["photo_url_list"])

        # 寻找这一页符合条件的图片
        photo_info_list = []
        for photo_url in photo_index_response["photo_url_list"]:
            photo_description = f"图片 {photo_url}"
            self.start_parse(photo_description)
            try:
                photo_head_response = get_photo_header(photo_url)
            except CrawlerException as e:
                self.error(e.http_error(photo_description))
                return []

            # 检查是否达到存档记录
            if photo_head_response["photo_time"] > int(self.single_save_data[4]):
                photo_info_list.append({"photo_url": photo_url, "photo_time": photo_head_response["photo_time"]})
            else:
                break

        return photo_info_list

    # 解析单张图片
    def crawl_photo(self, photo_info):
        photo_index = int(self.single_save_data[3]) + 1

        photo_name = f"%04d.{url.get_file_ext(photo_info['photo_url'])}" % photo_index
        photo_path = os.path.join(self.main_thread.photo_download_path, self.display_name, photo_name)
        photo_description = f"第{photo_index}张图片"
        if self.download(photo_info["photo_url"], photo_path, photo_description, is_failure_exit=False):
            self.total_photo_count += 1  # 计数累加
        else:
            return False

        # 图片下载完毕
        self.single_save_data[3] = str(photo_index)  # 设置存档记录
        self.single_save_data[4] = str(photo_info["photo_time"])  # 设置存档记录
        return True

    # 获取所有可下载视频
    def get_crawl_video_list(self):
        index_description = "视频首页"
        self.start_parse(index_description)
        try:
            video_pagination_response = get_video_index_page(self.index_key)
        except CrawlerException as e:
            self.error(e.http_error(index_description))
            return []
        self.parse_result(index_description, video_pagination_response["video_id_list"])

        # 寻找这一页符合条件的视频
        video_info_list = []
        for video_id in video_pagination_response["video_id_list"]:
            video_description = f"视频{video_id}"
            self.start_parse(video_description)
            try:
                video_info_response = get_video_info_page(video_id)
            except CrawlerException as e:
                self.error(e.http_error(video_description))
                return []

            # 检查是否达到存档记录
            if video_info_response["video_time"] > int(self.single_save_data[2]):
                video_info_list.append(video_info_response)
            else:
                break

        return video_info_list

    # 解析单个视频
    def crawl_video(self, video_info):
        video_index = int(self.single_save_data[1]) + 1
        video_description = f"第{video_index}个视频"
        self.info(f"开始下载 {video_description} {video_info['m3u8_file_url']}")

        video_path = os.path.join(self.main_thread.video_download_path, self.display_name, "%04d.ts" % video_index)
        download_return = net.DownloadHls(video_info["m3u8_file_url"], video_path)
        if download_return.status == const.DownloadStatus.SUCCEED:
            self.total_video_count += 1  # 计数累加
            self.info(f"{video_description} 下载成功")
        else:
            self.error(f"{video_description} {video_info['m3u8_file_url']} 下载失败")
            if self.check_download_failure_exit(False):
                return False

        # 视频下载完毕
        self.single_save_data[1] = str(video_index)  # 设置存档记录
        self.single_save_data[2] = str(video_info["video_time"])  # 设置存档记录
        return True

    def _run(self):
        # 图片下载
        if self.main_thread.is_download_photo:
            # 获取所有可下载图片
            photo_info_list = self.get_crawl_photo_list()
            self.info(f"需要下载的全部图片解析完毕，共{len(photo_info_list)}张")

            # 从最早的图片开始下载
            while len(photo_info_list) > 0:
                if not self.crawl_photo(photo_info_list.pop()):
                    break

        # 视频下载
        if self.main_thread.is_download_video:
            # 获取所有可下载视频
            video_info_list = self.get_crawl_video_list()
            self.info(f"需要下载的全部视频解析完毕，共{len(video_info_list)}个")

            # 从最早的视频开始下载
            while len(video_info_list) > 0:
                if not self.crawl_video(video_info_list.pop()):
                    break


if __name__ == "__main__":
    YiZhiBo().main()
