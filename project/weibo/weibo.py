# -*- coding:UTF-8  -*-
"""
微博图片爬虫
https://www.weibo.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import time
import urllib.parse
from common import *

EACH_PAGE_PHOTO_COUNT = 20  # 每次请求获取的图片数量
COOKIE_INFO = {}


# 检测登录状态
def check_login():
    if "SUB" not in COOKIE_INFO or not COOKIE_INFO["SUB"]:
        return False
    index_url = "https://weibo.com/"
    index_response = net.request(index_url, method="GET", cookies_list=COOKIE_INFO)
    if index_response.status == const.ResponseCode.SUCCEED:
        index_response_content = index_response.data.decode(errors="ignore")
        return index_response_content.find("$CONFIG[\'uid\']=\'") >= 0 or index_response_content.find('"uid":') >= 0
    return False


# 使用浏览器保存的cookie模拟登录请求，获取一个session级别的访问cookie
def init_session():
    login_url = "https://login.sina.com.cn/sso/login.php"
    query_data = {"url": "https://weibo.com"}
    login_response = net.request(login_url, method="GET", fields=query_data, cookies_list=COOKIE_INFO)
    if login_response.status == const.ResponseCode.SUCCEED:
        COOKIE_INFO.update(net.get_cookies_from_response_header(login_response.headers))
        return True
    return False


# 检测图片是不是被微博自动删除的文件
def check_photo_invalid(photo_path):
    file_md5 = file.get_file_md5(photo_path)
    if file_md5 in ["14f2559305a6c96608c474f4ca47e6b0", "37b9e6dec174b68a545c852c63d4645a", "4cf24fe8401f7ab2eba2c6cb82dffb0e",
                    "78b5b9e32f3b30b088fef0e6c5ed0901", "7bd88df2b5be33e1a79ac91e7d0376b5", "7e80fb31ec58b1ca2fb3548480e1b95e",
                    "82af4714a8b2a5eea3b44726cfc9920d"]:
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
    if photo_pagination_response.status == const.ResponseCode.JSON_DECODE_ERROR and photo_pagination_response.data.find('<p class="txt M_txtb">用户不存在或者获取用户信息失败</p>'.encode()) >= 0:
        raise crawler.CrawlerException("账号不存在")
    elif photo_pagination_response.status != const.ResponseCode.SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(photo_pagination_response.status))
    for photo_info in crawler.get_json_value(photo_pagination_response.json_data, "data", "photo_list", type_check=list):
        result_photo_info = {
            "photo_id": 0,  # 图片id
            "photo_time": "",  # 图片上传时间
            "photo_url": "",  # 图片地址
        }
        # 获取图片上传时间
        result_photo_info["photo_time"] = crawler.get_json_value(photo_info, "timestamp", type_check=int)
        # 获取图片id
        result_photo_info["photo_id"] = crawler.get_json_value(photo_info, "photo_id", type_check=int)
        # 获取图片地址
        photo_host = crawler.get_json_value(photo_info, "pic_host", type_check=str)
        photo_name = crawler.get_json_value(photo_info, "pic_name", type_check=str)
        result_photo_info["photo_url"] = photo_host + "/large/" + photo_name
        result["photo_info_list"].append(result_photo_info)
    # 检测是不是还有下一页 总的图片数量 / 每页显示的图片数量 = 总的页数
    total_photo_count = crawler.get_json_value(photo_pagination_response.json_data, "data", "total", type_check=int)
    result["is_over"] = len(result["photo_info_list"]) == 0 or page_count >= (total_photo_count / EACH_PAGE_PHOTO_COUNT)
    return result


# 获取一页的视频信息
def get_one_page_video(account_id, since_id, retry_count=0):
    # https://weibo.com/ajax/profile/getWaterFallContent?uid=5948281315&cursor=0
    video_pagination_url = "https://weibo.com/ajax/profile/getWaterFallContent"
    query_data = {
        "uid": account_id,
        "cursor": since_id,
    }
    result = {
        "next_page_since_id": 0,  # 下一页视频指针
        "video_info_list": [],  # 全部视频地址
    }
    video_pagination_response = net.request(video_pagination_url, method="GET", fields=query_data, cookies_list=COOKIE_INFO, json_decode=True)
    if video_pagination_response.status == 400:
        # 第一次失败，判断账号是否存在
        if retry_count == 1 and since_id == 0:
            account_info_url = "https://weibo.com/ajax/profile/info"
            query_data = {
                "uid": account_id
            }
            header_list = {
                "Accept": "application/json, text/plain, */*",
            }
            account_info_response = net.request(account_info_url, method="GET", fields=query_data, cookies_list=COOKIE_INFO, header_list=header_list, json_decode=True)
            if account_info_response.status == const.ResponseCode.SUCCEED and crawler.get_json_value(account_info_response.json_data, "msg", type_check=str, value_check="该用户不存在(20003)"):
                raise crawler.CrawlerException("账号不存在")
        if retry_count < 3:
            time.sleep(1)
            return get_one_page_video(account_id, since_id, retry_count + 1)
        else:
            if since_id == 0:
                result["next_page_since_id"] = -1
                return result
    if video_pagination_response.status != const.ResponseCode.SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_pagination_response.status))
    # 获取视频id
    for video_info in crawler.get_json_value(video_pagination_response.json_data, "data", "list", type_check=list):
        result_video_info_list = {
            "video_id": 0,  # 视频id
            "video_title": "",  # 视频标题
            "video_url": "",  # 视频地址
        }
        # 获取视频id
        result_video_info_list["video_id"] = crawler.get_json_value(video_info, "id", type_check=int)
        try:
            page_type = crawler.get_json_value(video_info, "page_info", "type", type_check=int)
        except crawler.CrawlerException:
            if crawler.get_json_value(video_info, "text", type_check=str).find("根据博主设置，此内容无法访问") >= 0:
                continue
            raise
        if page_type in [2, 5, 11]:
            # 获取视频标题
            result_video_info_list["video_title"] = crawler.get_json_value(video_info, "page_info", "media_info", "video_title", type_check=str, default_value="")
            try:
                video_detail_info_list = crawler.get_json_value(video_info, "page_info", "media_info", "playback_list", type_check=list)
            except crawler.CrawlerException:
                video_url = crawler.get_json_value(video_info, "page_info", "media_info", "stream_url_hd", type_check=str)
                if not video_url:
                    raise
                result_video_info_list["video_url"] = video_url
                continue
        elif page_type == 31:
            # 获取视频标题
            result_video_info_list["video_title"] = crawler.get_json_value(video_info, "page_info", "page_desc", type_check=str)
            video_detail_info_list = crawler.get_json_value(video_info, "page_info", "slide_cover", "playback_list", type_check=list)
        else:
            raise crawler.CrawlerException("未知信息类型%s" % page_type)
        # 获取视频地址
        max_resolution = 0
        video_url = ""
        for single_video_info in video_detail_info_list:
            video_type = crawler.get_json_value(single_video_info, "play_info", "type", type_check=int)
            if video_type == 1:
                video_width = crawler.get_json_value(single_video_info, "play_info", "width", type_check=int)
                video_height = crawler.get_json_value(single_video_info, "play_info", "height", type_check=int)
                resolution = video_width * video_height
                if resolution > max_resolution:
                    video_url = crawler.get_json_value(single_video_info, "play_info", "url", type_check=str)
                    max_resolution = resolution
            elif video_type == 3:  # 图片
                continue
            else:
                raise crawler.CrawlerException("未知视频类型%s" % video_type)
        if not video_url:
            raise crawler.CrawlerException("媒体信息%s获取最大分辨率视频地址失败" % video_info)
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
            const.SysConfigKey.DOWNLOAD_PHOTO: True,
            const.SysConfigKey.DOWNLOAD_VIDEO: True,
            const.SysConfigKey.GET_COOKIE: ("weibo.com",),
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 设置全局变量，供子线程调用
        COOKIE_INFO.update(self.cookie_value)

        # 解析存档文件
        # account_id  last_photo_id  last_video_id  (account_name)
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "0", "0"])

        # 下载线程
        self.crawler_thread = CrawlerThread

    def init(self):
        # 检测登录状态
        if check_login():
            return

        # 如果没有获得登录相关的cookie，则模拟登录并更新cookie
        if init_session() and check_login():
            pass
        else:
            log.error("没有检测到登录信息")
            tool.process_exit()


class CrawlerThread(crawler.CrawlerThread):
    def __init__(self, main_thread, single_save_data):
        self.index_key = single_save_data[0]  # account id
        if len(single_save_data) >= 4 and single_save_data[3]:
            self.display_name = single_save_data[3]
        else:
            self.display_name = single_save_data[0]
        crawler.CrawlerThread.__init__(self, main_thread, single_save_data)

    # 获取所有可下载图片
    def get_crawl_photo_list(self):
        page_count = 1
        unique_list = []
        photo_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的图片
        while not is_over:
            photo_pagination_description = "第%s页图片" % page_count
            self.start_parse(photo_pagination_description)
            try:
                photo_pagination_response = get_one_page_photo(self.index_key, page_count)
            except crawler.CrawlerException as e:
                self.error(e.http_error(photo_pagination_description))
                raise
            self.parse_result(photo_pagination_description, photo_pagination_response["photo_info_list"])

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
            video_pagination_description = "since_id：%s后一页视频" % since_id
            self.start_parse(video_pagination_description)
            try:
                video_pagination_response: dict = get_one_page_video(self.index_key, since_id)
            except crawler.CrawlerException as e:
                self.error(e.http_error(video_pagination_description))
                raise
            self.parse_result(video_pagination_description, video_pagination_response["video_info_list"])

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
        photo_name = "%16d.%s" % (photo_info["photo_id"], net.get_file_extension(photo_info["photo_url"], "jpg"))
        photo_path = os.path.join(self.main_thread.photo_download_path, self.display_name, photo_name)
        photo_description = "图片%s" % photo_info["photo_id"]
        download_return = self.download(photo_info["photo_url"], photo_path, photo_description, success_callback=self.photo_download_success_callback,
                                        failure_callback=self.photo_download_failure_callback, is_failure_exit=False, header_list={"Referer": "https://weibo.com/"})
        if download_return:
            if not download_return["is_invalid_photo"]:
                self.total_photo_count += 1  # 计数累加
        else:
            if not download_return["is_invalid_photo"]:
                return False

        # 图片下载完毕
        self.single_save_data[1] = str(photo_info["photo_id"])  # 设置存档记录
        return True

    # 解析单个视频
    def crawl_video(self, video_info):
        video_title = path.filter_text(video_info["video_title"])
        if video_title:
            video_name = "%s %s.mp4" % (video_info["video_id"], video_title)
        else:
            video_name = "%s.mp4" % video_info["video_id"]
        video_path = os.path.join(self.main_thread.video_download_path, self.display_name, video_name)
        header_list = {"Host": urllib.parse.urlparse(video_info["video_url"])[1]}
        video_description = "视频%s《%s》" % (video_info["video_id"], video_info["video_title"])
        download_return = self.download(video_info["video_url"], video_path, video_description, failure_callback=self.video_download_failure_callback, is_failure_exit=False,
                                        header_list=header_list, auto_multipart_download=True)
        if download_return:
            self.total_video_count += 1  # 计数累加
        else:
            if not download_return["is_deleted"]:
                return False

        # 视频下载完毕
        self.single_save_data[2] = str(video_info["video_id"])  # 设置存档记录
        return True

    def photo_download_success_callback(self, photo_url, photo_path, photo_description, download_return: net.Download):
        if check_photo_invalid(photo_path):
            download_return["is_invalid_photo"] = True
            path.delete_dir_or_file(photo_path)
            self.error("%s %s 资源已被限制，跳过" % (photo_description, photo_url))
            return False
        download_return["is_invalid_photo"] = False
        return True

    def photo_download_failure_callback(self, photo_url, photo_path, photo_description, download_return: net.Download):
        if download_return.code == 403:
            download_return["is_invalid_photo"] = True
            self.error("%s %s 资源已被限制，跳过" % (photo_description, photo_url))
            return False
        download_return["is_invalid_photo"] = False
        return True

    def video_download_failure_callback(self, photo_url, photo_path, photo_description, download_return: net.Download):
        if download_return.code == 404:
            download_return["is_deleted"] = True
            return False
        download_return["is_deleted"] = False
        return True

    def _run(self):
        # 图片下载
        if self.main_thread.is_download_photo:
            # 获取所有可下载图片
            photo_info_list = self.get_crawl_photo_list()
            self.info("需要下载的全部图片解析完毕，共%s张" % len(photo_info_list))

            # 从最早的图片开始下载
            while len(photo_info_list) > 0:
                if not self.crawl_photo(photo_info_list.pop()):
                    break

        # 视频下载
        if self.main_thread.is_download_video:
            # 获取所有可下载视频
            video_info_list = self.get_crawl_video_list()
            self.info("需要下载的全部视频片解析完毕，共%s个" % len(video_info_list))

            # 从最早的视频开始下载
            while len(video_info_list) > 0:
                if not self.crawl_video(video_info_list.pop()):
                    break


if __name__ == "__main__":
    Weibo().main()
