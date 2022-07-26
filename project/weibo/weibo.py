# -*- coding:UTF-8  -*-
"""
微博图片爬虫
https://www.weibo.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import re
import time
import urllib.parse
from common import *
from project.meipai import meipai

EACH_PAGE_PHOTO_COUNT = 20  # 每次请求获取的图片数量
COOKIE_INFO = {}


# 检测登录状态
def check_login():
    if "SUB" not in COOKIE_INFO or not COOKIE_INFO["SUB"]:
        return False
    index_url = "https://weibo.com/"
    index_response = net.request(index_url, method="GET", cookies_list=COOKIE_INFO)
    if index_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        index_response_content = index_response.data.decode(errors="ignore")
        return index_response_content.find("$CONFIG[\'uid\']=\'") >= 0 or index_response_content.find('"uid":') >= 0
    return False


# 使用浏览器保存的cookie模拟登录请求，获取一个session级别的访问cookie
def init_session():
    login_url = "https://login.sina.com.cn/sso/login.php"
    query_data = {"url": "https://weibo.com"}
    login_response = net.request(login_url, method="GET", fields=query_data, cookies_list=COOKIE_INFO)
    if login_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        COOKIE_INFO.update(net.get_cookies_from_response_header(login_response.headers))
        return True
    return False


# 检测图片是不是被微博自动删除的文件
def check_photo_invalid(file_path):
    file_md5 = file.get_file_md5(file_path)
    if file_md5 in ["14f2559305a6c96608c474f4ca47e6b0", "37b9e6dec174b68a545c852c63d4645a", "4cf24fe8401f7ab2eba2c6cb82dffb0e", "78b5b9e32f3b30b088fef0e6c5ed0901",
                    "7bd88df2b5be33e1a79ac91e7d0376b5", "7e80fb31ec58b1ca2fb3548480e1b95e", "82af4714a8b2a5eea3b44726cfc9920d"]:
        return True
    return False


# 获取一页的图片信息
def get_one_page_photo(account_id, page_count):
    photo_pagination_url = "https://photo.weibo.com/photos/get_all"
    query_data = {
        "uid": account_id,
        "count": EACH_PAGE_PHOTO_COUNT,
        "page": page_count,
        "type": "3",
    }
    result = {
        "photo_info_list": [],  # 全部图片信息
        "is_over": False,  # 是否最后一页图片
    }
    photo_pagination_response = net.request(photo_pagination_url, method="GET", fields=query_data, cookies_list=COOKIE_INFO, json_decode=True)
    if photo_pagination_response.status == net.HTTP_RETURN_CODE_JSON_DECODE_ERROR and photo_pagination_response.data.find('<p class="txt M_txtb">用户不存在或者获取用户信息失败</p>'.encode()) >= 0:
        raise crawler.CrawlerException("账号不存在")
    elif photo_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(photo_pagination_response.status))
    for photo_info in crawler.get_json_value(photo_pagination_response.json_data, "data", "photo_list", type_check=list):
        result_photo_info = {
            "photo_id": None,  # 图片上传时间
            "photo_time": None,  # 图片上传时间
            "photo_url": None,  # 图片地址
        }
        # 获取图片上传时间
        result_photo_info["photo_time"] = crawler.get_json_value(photo_info, "timestamp", type_check=int)
        # 获取图片id
        result_photo_info["photo_id"] = crawler.get_json_value(photo_info, "photo_id", type_check=int)
        # 获取图片地址
        result_photo_info["photo_url"] = crawler.get_json_value(photo_info, "pic_host", type_check=str) + "/large/" + crawler.get_json_value(photo_info, "pic_name", type_check=str)
        result["photo_info_list"].append(result_photo_info)
    # 检测是不是还有下一页 总的图片数量 / 每页显示的图片数量 = 总的页数
    result["is_over"] = len(result["photo_info_list"]) == 0 or page_count >= (crawler.get_json_value(photo_pagination_response.json_data, "data", "total", type_check=int) / EACH_PAGE_PHOTO_COUNT)
    return result


# 获取一页的视频信息
def get_one_page_video(account_id, since_id):
    # https://weibo.com/ajax/profile/getWaterFallContent?uid=5948281315&cursor=0
    video_pagination_url = "https://weibo.com/ajax/profile/getWaterFallContent"
    query_data = {
        "uid": account_id,
        "cursor": since_id,
    }
    result = {
        "next_page_since_id": None,  # 下一页视频指针
        "video_info_list": [],  # 全部视频地址
    }
    video_pagination_response = net.request(video_pagination_url, method="GET", fields=query_data, cookies_list=COOKIE_INFO, json_decode=True)
    if video_pagination_response.status == 400:
        time.sleep(5)
        return get_one_page_video(account_id, since_id)
    elif video_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_pagination_response.status))
    # 获取视频id
    for video_info in crawler.get_json_value(video_pagination_response.json_data, "data", "list", type_check=list):
        result_video_info_list = {
            "video_id": "",  # 视频id
            "video_title": "",  # 视频标题
            "video_url": "",  # 视频地址
        }
        # 获取视频id
        result_video_info_list["video_id"] = crawler.get_json_value(video_info, "id", type_check=int)
        page_type = crawler.get_json_value(video_info, "page_info", "type", type_check=int)
        if page_type == 11 or page_type == 5:
            # 获取视频标题
            result_video_info_list["video_title"] = crawler.get_json_value(video_info, "page_info", "media_info", "video_title", type_check=str, default_value="")
            video_detail_info_list = crawler.get_json_value(video_info, "page_info", "media_info", "playback_list", type_check=list)
        elif page_type == 31:
            # 获取视频标题
            result_video_info_list["video_title"] = crawler.get_json_value(video_info, "page_info", "page_desc", type_check=str)
            video_detail_info_list = crawler.get_json_value(video_info, "page_info", "slide_cover", "playback_list", type_check=list)
        else:
            raise crawler.CrawlerException(f"未知信息类型{page_type}")
        # 获取视频地址
        max_resolution = 0
        video_url = ""
        for single_video_info in video_detail_info_list:
            video_type = crawler.get_json_value(single_video_info, "play_info", "type", type_check=int)
            if video_type == 1:
                resolution = crawler.get_json_value(single_video_info, "play_info", "width", type_check=int) * crawler.get_json_value(single_video_info, "play_info", "height", type_check=int)
                if resolution > max_resolution:
                    video_url = crawler.get_json_value(single_video_info, "play_info", "url", type_check=str)
                    max_resolution = resolution
            elif video_type == 3:  # 图片
                continue
            else:
                raise crawler.CrawlerException(f"未知视频类型{video_type}")
        if not video_url:
            raise crawler.CrawlerException(f"媒体信息{video_info}获取最大分辨率视频地址失败")
        result_video_info_list["video_url"] = video_url
        result["video_info_list"].append(result_video_info_list)
    # 获取下一页视频的指针
    result["next_page_since_id"] = crawler.get_json_value(video_pagination_response.json_data, "data", "next_cursor", type_check=int)
    return result


class Weibo(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_DOWNLOAD_VIDEO: True,
            crawler.SYS_GET_COOKIE: ("sina.com.cn", "login.sina.com.cn"),
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 设置全局变量，供子线程调用
        COOKIE_INFO.update(self.cookie_value)

        # 解析存档文件
        # account_id  last_photo_id  last_video_id  (account_name)
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "0", "0"])

        # 检测登录状态
        if not check_login():
            # 如果没有获得登录相关的cookie，则模拟登录并更新cookie
            if init_session() and check_login():
                pass
            else:
                log.error("没有检测到登录信息")
                tool.process_exit()

        # 下载线程
        self.download_thread = Download


class Download(crawler.DownloadThread):
    def __init__(self, single_save_data, main_thread):
        self.index_key = single_save_data[0]  # account id
        if len(single_save_data) >= 4 and single_save_data[3]:
            self.display_name = single_save_data[3]
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
            self.step(f"需要下载的全部视频片解析完毕，共{len(video_info_list)}个")

            # 从最早的视频开始下载
            while len(video_info_list) > 0:
                if not self.crawl_video(video_info_list.pop()):
                    break
                self.main_thread_check()  # 检测主线程运行状态

    # 获取所有可下载图片
    def get_crawl_photo_list(self):
        page_count = 1
        unique_list = []
        photo_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的图片
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step(f"开始解析第{page_count}页图片")

            # 获取指定一页图片的信息
            try:
                photo_pagination_response = get_one_page_photo(self.index_key, page_count)
            except crawler.CrawlerException as e:
                self.error(e.http_error(f"第{page_count}页图片"))
                raise

            self.trace(f"第{page_count}页解析的全部图片：{photo_pagination_response['photo_info_list']}")
            self.step(f"第{page_count}页解析获取{len(photo_pagination_response['photo_info_list'])}张图片")

            # 寻找这一页符合条件的图片
            for photo_info in photo_pagination_response["photo_info_list"]:
                # 检查是否达到存档记录
                if photo_info["photo_id"] > int(self.single_save_data[1]):
                    # 新增图片导致的重复判断
                    if photo_info["photo_id"] in unique_list:
                        continue
                    else:
                        photo_info_list.append(photo_info)
                        unique_list.append(photo_info["photo_id"])
                else:
                    is_over = True
                    break

            if not is_over:
                if photo_pagination_response["is_over"]:
                    is_over = True
                else:
                    page_count += 1

        return photo_info_list

    # 获取所有可下载视频
    def get_crawl_video_list(self):
        video_info_list = []
        since_id = 0
        is_over = False
        # 获取全部还未下载过需要解析的视频
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step(f"开始解析since_id：{since_id}页视频")

            # 获取指定时间点后的一页视频信息
            try:
                video_pagination_response = get_one_page_video(self.index_key, since_id)
            except crawler.CrawlerException as e:
                self.error(e.http_error(f"since_id：{since_id}后一页视频"))
                raise

            self.trace(f"since_id：{since_id}页解析的全部视频：{video_pagination_response['video_info_list']}")
            self.step(f"since_id：{since_id}页解析获取{len(video_pagination_response['video_info_list'])}个视频")

            # 寻找这一页符合条件的视频
            for video_info in video_pagination_response["video_info_list"]:
                # 检查是否达到存档记录
                if video_info["video_id"] > int(self.single_save_data[2]):
                    video_info_list.append(video_info)
                else:
                    is_over = True
                    break

            if not is_over:
                if video_pagination_response["next_page_since_id"] == -1:
                    is_over = True
                else:
                    # 设置下一页指针
                    since_id = video_pagination_response["next_page_since_id"]

        return video_info_list

    # 下载图片
    def crawl_photo(self, photo_info):
        self.step(f"开始下载图片{photo_info['photo_id']} {photo_info['photo_url']}")

        photo_file_path = os.path.join(self.main_thread.photo_download_path, self.display_name, f"%16d.{net.get_file_extension(photo_info['photo_url'], 'jpg')}" % photo_info["photo_id"])
        download_return = net.Download(photo_info["photo_url"], photo_file_path)
        if download_return.status == net.Download.DOWNLOAD_SUCCEED:
            if check_photo_invalid(photo_file_path):
                path.delete_dir_or_file(photo_file_path)
                self.error(f"图片{photo_info['photo_id']} {photo_info['photo_url']} 资源已被限制，跳过")
            else:
                self.total_photo_count += 1  # 计数累加
                self.step(f"图片{photo_info['photo_id']}下载成功")
        else:
            if download_return.code == 403:
                self.error(f"图片{photo_info['photo_id']} {photo_info['photo_url']} 资源已被限制，跳过")
            else:
                self.error(f"图片{photo_info['photo_id']} {photo_info['photo_url']} 下载失败，原因：{crawler.download_failre(download_return.code)}")
                if self.check_download_failure_exit(False):
                    return False

        # 图片下载完毕
        self.single_save_data[1] = str(photo_info["photo_id"])  # 设置存档记录
        return True

    # 解析单个视频
    def crawl_video(self, video_info):
        self.step(f"开始解析视频{video_info['video_id']}")

        self.step(f"开始下载视频{video_info['video_id']} {video_info['video_url']}")

        video_file_path = os.path.join(self.main_thread.video_download_path, self.display_name, f"{video_info['video_id']}.mp4")
        header_list = {
            "Host": "f.us.sinaimg.cn",
        }
        download_return = net.Download(video_info["video_url"], video_file_path, header_list=header_list, auto_multipart_download=True)
        if download_return.status == net.Download.DOWNLOAD_SUCCEED:
            self.total_video_count += 1  # 计数累加
            self.step(f"视频{video_info['video_id']}下载成功")
        else:
            self.error(f"视频{video_info['video_id']}（{video_info['video_url']}) 下载失败，原因：{crawler.download_failre(download_return.code)}")
            if self.check_download_failure_exit(False):
                return False

        # 视频下载完毕
        self.single_save_data[2] = str(video_info['video_id'])  # 设置存档记录
        return True


if __name__ == "__main__":
    Weibo().main()
