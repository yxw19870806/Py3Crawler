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
import time
from pyquery import PyQuery as pq
from common import *


# 获取全部图片地址列表
def get_photo_index_page(account_id):
    # https://www.yizhibo.com/member/personel/user_photos?memberid=6066534
    photo_index_url = "https://www.yizhibo.com/member/personel/user_photos"
    query_data = {"memberid": account_id}
    photo_index_response = net.request(photo_index_url, method="GET", fields=query_data)
    result = {
        "photo_url_list": [],  # 全部图片地址
    }
    if photo_index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(photo_index_response.status))
    photo_index_response_content = photo_index_response.data.decode(errors="ignore")
    if photo_index_response_content == '<script>window.location.href="/404.html";</script>':
        raise crawler.CrawlerException("账号不存在")
    # 获取全部图片地址
    if pq(photo_index_response_content).find(".index_all_list p").html() != "还没有照片哦":
        video_list_selector = pq(photo_index_response_content).find("img.index_img_main")
        for video_index in range(0, video_list_selector.length):
            photo_url = video_list_selector.eq(video_index).attr("src")
            result["photo_url_list"].append(photo_url.split("@")[0])
        if len(result["photo_url_list"]) == 0:
            raise crawler.CrawlerException("页面匹配图片地址失败\n" + photo_index_response_content)
    return result


#  获取图片的header
def get_photo_header(photo_url):
    photo_head_response = net.request(photo_url, method="HEAD")
    result = {
        "photo_time": None,  # 图片上传时间
    }
    if photo_head_response.status == 404:
        return result
    elif photo_head_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(photo_head_response.status))
    last_modified = photo_head_response.headers.get("Last-Modified")
    if last_modified is None:
        raise crawler.CrawlerException(f"图片header{photo_head_response.headers}中'Last-Modified'字段不存在")
    try:
        last_modified_time = time.strptime(last_modified, "%a, %d %b %Y %H:%M:%S %Z")
    except ValueError:
        raise crawler.CrawlerException(f"图片上传时间{last_modified}的格式不正确")
    result["photo_time"] = int(time.mktime(last_modified_time)) - time.timezone
    return result


# 获取全部视频ID列表
def get_video_index_page(account_id):
    # https://www.yizhibo.com/member/personel/user_videos?memberid=6066534
    video_pagination_url = "https://www.yizhibo.com/member/personel/user_videos"
    query_data = {"memberid": account_id}
    video_pagination_response = net.request(video_pagination_url, method="GET", fields=query_data)
    result = {
        "is_exist": True,  # 是否存在视频
        "video_id_list": [],  # 全部视频id
    }
    if video_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_pagination_response.status))
    video_pagination_response_content = video_pagination_response.data.decode(errors="ignore")
    if video_pagination_response_content == '<script>window.location.href="/404.html";</script>':
        raise crawler.CrawlerException("账号不存在")
    if pq(video_pagination_response_content).find(".index_all_list p").html() != "还没有直播哦":
        video_list_selector = pq(video_pagination_response_content).find("div.scid")
        for video_index in range(0, video_list_selector.length):
            result["video_id_list"].append(video_list_selector.eq(video_index).html())
        if len(result["video_id_list"]) == 0:
            raise crawler.CrawlerException("页面匹配视频id失败\n" + video_pagination_response_content)
    return result


# 根据video id获取指定视频的详细信息（上传时间、视频列表的下载地址等）
# video_id -> qxonW5XeZru03nUB
def get_video_info_page(video_id):
    # https://api.xiaoka.tv/live/web/get_play_live?scid=xX9-TLVx0xTiSZ69
    video_info_url = "https://api.xiaoka.tv/live/web/get_play_live"
    query_data = {"scid": video_id}
    video_info_response = net.request(video_info_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "video_time": False,  # 视频上传时间
        "video_url_list": [],  # 全部视频分集地址
    }
    if video_info_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_info_response.status))
    # 获取视频上传时间
    result["video_time"] = crawler.get_json_value(video_info_response.json_data, "data", "createtime", type_check=int)
    # 获取视频地址所在文件地址
    video_file_url = crawler.get_json_value(video_info_response.json_data, "data", "linkurl", type_check=str)
    video_file_response = net.request(video_file_url, method="GET")
    if video_file_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_info_response.status))
    video_file_response_content = video_file_response.data.decode(errors="ignore")
    ts_id_list = re.findall(r"([\S]*.ts)", video_file_response_content)
    if len(ts_id_list) == 0:
        raise crawler.CrawlerException("分集文件匹配视频地址失败\n" + video_file_response_content)
    # http://alcdn.hls.xiaoka.tv/20161122/6b6/c5f/xX9-TLVx0xTiSZ69/
    prefix_url = video_file_url[:video_file_url.rfind("/") + 1]
    for ts_id in ts_id_list:
        result["video_url_list"].append(prefix_url + ts_id)
    return result


class YiZhiBo(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_DOWNLOAD_VIDEO: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 解析存档文件
        # account_id  video_count  last_video_time  photo_count  last_photo_time(account_name)
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "0", "0", "0", "0"])

        # 下载线程
        self.download_thread = Download


class Download(crawler.DownloadThread):
    def __init__(self, single_save_data, main_thread):
        self.index_key = single_save_data[0]  # account id
        if len(single_save_data) >= 6 and single_save_data[5]:
            self.display_name = single_save_data[5]
        else:
            self.display_name = single_save_data[0]
        crawler.DownloadThread.__init__(self, single_save_data, main_thread)

    def _run(self):
        # 图片下载
        if self.main_thread.is_download_photo:
            # 获取所有可下载图片
            photo_info_list = self.get_crawl_photo_list()
            self.step(f"需要下载的全部图片解析完毕，共{len(photo_info_list)}张")

            # 从最早的图片开始下载
            while len(photo_info_list) > 0:
                if not self.crawl_photo(photo_info_list.pop()):
                    break
                self.main_thread_check()  # 检测主线程运行状态

        # 视频下载
        if self.main_thread.is_download_video:
            # 获取所有可下载视频
            video_info_list = self.get_crawl_video_list()
            self.step(f"需要下载的全部视频解析完毕，共{len(video_info_list)}个")

            # 从最早的视频开始下载
            while len(video_info_list) > 0:
                if not self.crawl_video(video_info_list.pop()):
                    break
                self.main_thread_check()  # 检测主线程运行状态

    # 获取所有可下载图片
    def get_crawl_photo_list(self):
        # 获取全部图片地址列表
        try:
            photo_index_response = get_photo_index_page(self.index_key)
        except crawler.CrawlerException as e:
            self.error(e.http_error("图片首页"))
            return []

        self.trace(f"解析的全部图片：{photo_index_response['photo_url_list']}")
        self.step(f"解析获取{len(photo_index_response['photo_url_list'])}张图片")

        # 寻找这一页符合条件的图片
        photo_info_list = []
        for photo_url in photo_index_response["photo_url_list"]:
            self.main_thread_check()  # 检测主线程运行状态
            self.step(f"开始解析图片{photo_url}")

            try:
                photo_head_response = get_photo_header(photo_url)
            except crawler.CrawlerException as e:
                self.error(e.http_error(f"图片{photo_url}"))
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
        self.step(f"开始下载第{photo_index}张图片 {photo_info['photo_url']}")

        photo_file_path = os.path.join(self.main_thread.photo_download_path, self.display_name, f"%04d.{net.get_file_extension(photo_info['photo_url'])}" % photo_index)
        download_return = net.Download(photo_info["photo_url"], photo_file_path)
        if download_return.status == net.Download.DOWNLOAD_SUCCEED:
            self.total_photo_count += 1  # 计数累加
            self.step(f"第{photo_index}张图片下载成功")
        else:
            self.error(f"第{photo_index}张图片 {photo_info['photo_url']} 下载失败，原因：{crawler.download_failre(download_return.code)}")
            if self.check_download_failure_exit(False):
                return False

        # 图片下载完毕
        self.single_save_data[3] = str(photo_index)  # 设置存档记录
        self.single_save_data[4] = str(photo_info["photo_time"])  # 设置存档记录
        return True

    # 获取所有可下载视频
    def get_crawl_video_list(self):
        video_info_list = []
        # 获取全部视频ID列表
        try:
            video_pagination_response = get_video_index_page(self.index_key)
        except crawler.CrawlerException as e:
            self.error(e.http_error("视频首页"))
            return []

        self.trace(f"解析的全部视频：{video_pagination_response['video_id_list']}")
        self.step(f"解析获取{len(video_pagination_response['video_id_list'])}个视频")

        # 寻找这一页符合条件的视频
        for video_id in video_pagination_response["video_id_list"]:
            self.main_thread_check()  # 检测主线程运行状态
            self.step(f"开始解析视频{video_id}")

            # 获取视频的时间和下载地址
            try:
                video_info_response = get_video_info_page(video_id)
            except crawler.CrawlerException as e:
                self.error(e.http_error(f"视频{video_id}"))
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
        self.step(f"开始下载第{video_index}个视频 {video_info['video_url_list']}")

        video_file_path = os.path.join(self.main_thread.video_download_path, self.display_name, "%04d.ts" % video_index)
        download_return = net.download_from_list(video_info["video_url_list"], video_file_path)
        if download_return:
            self.total_video_count += 1  # 计数累加
            self.step(f"第{video_index}个视频下载成功")
        else:
            self.error(f"第{video_index}个视频 {video_info['video_url_list']} 下载失败")
            if self.check_download_failure_exit(False):
                return False

        # 视频下载完毕
        self.single_save_data[1] = str(video_index)  # 设置存档记录
        self.single_save_data[2] = str(video_info["video_time"])  # 设置存档记录
        return True


if __name__ == "__main__":
    YiZhiBo().main()
