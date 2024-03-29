# -*- coding:UTF-8  -*-
"""
Instagram图片&视频爬虫
https://www.instagram.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import time
from common import *
from common import crypto

IS_LOCAL_SAVE_SESSION = False
EACH_PAGE_PHOTO_COUNT = 12  # 每次请求获取的媒体数量
QUERY_ID = "17859156310193001"
COOKIES = {"csrftoken": "", "mid": "", "sessionid": ""}
REQUEST_LIMIT_DURATION = 10  # 请求统计的分钟数量
REQUEST_LIMIT_COUNT = 180  # 一定时间范围内的请求次数限制（API限制应该是200次/10分钟）
REQUEST_MINTER_COUNT = {}  # 每分钟的请求次数
SESSION_DATA_PATH = ""


# 生成session cookies
def init_session():
    # 如果有登录信息（初始化时从浏览器中获得）
    if COOKIES["sessionid"]:
        return True
    home_url = "https://www.instagram.com/"
    home_response = net.Request(home_url, method="GET")
    if home_response.status == const.ResponseCode.SUCCEED:
        set_cookie = net.get_cookies_from_response_header(home_response.headers)
        if "csrftoken" in set_cookie and "mid" in set_cookie:
            COOKIES["csrftoken"] = set_cookie["csrftoken"]
            COOKIES["mid"] = set_cookie["mid"]
            return True
    return False


# 检测登录状态
def check_login():
    if not COOKIES["sessionid"] and SESSION_DATA_PATH:
        # 从文件中读取账号密码
        account_data = tool.json_decode(crypto.Crypto().decrypt(file.read_file(SESSION_DATA_PATH)), {})
        if tool.check_dict_sub_key(["email", "password"], account_data):
            if _do_login(account_data["email"], account_data["password"]):
                return True
    else:
        index_url = "https://www.instagram.com/"
        index_response = net.Request(index_url, method="GET", cookies=COOKIES)
        if index_response.status == const.ResponseCode.SUCCEED:
            return index_response.content.find('"viewerId":"') >= 0
    return False


# 登录
def login_from_console():
    # 从命令行中输入账号密码
    while True:
        email = input(tool.convert_timestamp_to_formatted_time() + " 请输入邮箱: ")
        password = input(tool.convert_timestamp_to_formatted_time() + " 请输入密码: ")
        while True:
            input_str = input(tool.convert_timestamp_to_formatted_time() + " 是否使用这些信息(Y)es或重新输入(N)o: ")
            input_str = input_str.lower()
            if input_str in ["y", "yes"]:
                if _do_login(email, password):
                    if IS_LOCAL_SAVE_SESSION and SESSION_DATA_PATH:
                        encrypt_string = crypto.Crypto().encrypt(tool.json_encode({"email": email, "password": password}))
                        file.write_file(encrypt_string, SESSION_DATA_PATH, const.WriteFileMode.REPLACE)
                    return True
                return False
            elif input_str in ["n", "no"]:
                break


# 模拟登录请求
def _do_login(email, password):
    login_url = "https://www.instagram.com/accounts/login/ajax/"
    login_post = {"username": email, "password": password, "next": "/"}
    headers = {"referer": "https://www.instagram.com/", "x-csrftoken": COOKIES["csrftoken"]}
    login_response = net.Request(login_url, method="POST", fields=login_post, cookies=COOKIES, headers=headers).enable_json_decode()
    if login_response.status == const.ResponseCode.SUCCEED:
        if crawler.get_json_value(login_response.json_data, "authenticated", default_value=False, type_check=bool) is True:
            set_cookie = net.get_cookies_from_response_header(login_response.headers)
            if "sessionid" in set_cookie:
                COOKIES["sessionid"] = set_cookie["sessionid"]
                return True
    return False


# 根据账号名字获得账号id（字母账号->数字账号)
def get_account_index_page(account_name):
    account_index_url = "https://i.instagram.com/api/v1/users/web_profile_info/"
    query_data = {
        "username": account_name
    }
    headers = {
        "X-CSRFToken": COOKIES["csrftoken"],
        "X-IG-App-ID": "936619743392459",
    }
    account_index_response = net.Request(account_index_url, method="GET", fields=query_data, cookies=COOKIES, headers=headers).enable_json_decode()
    result = {
        "account_id": 0,  # account id
    }
    if account_index_response.status == 404:
        raise CrawlerException("账号不存在")
    elif account_index_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(account_index_response.status))
    result["account_id"] = crawler.get_json_value(account_index_response.json_data, "data", "user", "id", type_check=int)
    return result


# 获取指定页数的全部媒体
# account_id -> 490060609
def get_one_page_media(account_id, cursor):
    api_url = "https://www.instagram.com/graphql/query/"
    query_data = {
        "query_hash": "69cba40317214236af40e7efa697781d",
        "variables": tool.json_encode(
            {
                "id": account_id,
                "first": EACH_PAGE_PHOTO_COUNT,
                "after": cursor
            }
        )
    }
    media_pagination_response = net.Request(api_url, method="GET", fields=query_data, cookies=COOKIES).enable_json_decode()
    result = {
        "media_info_list": [],  # 全部媒体信息
        "next_page_cursor": "",  # 下一页媒体信息的指针
    }
    if media_pagination_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(media_pagination_response.status))
    response_media = crawler.get_json_value(media_pagination_response.json_data, "data", "user", "edge_owner_to_timeline_media", type_check=dict)
    media_info_list = crawler.get_json_value(response_media, "edges", type_check=list)
    if len(media_info_list) == 0:
        if cursor == "":
            if crawler.get_json_value(response_media, "count", type_check=int) > 0:
                raise CrawlerException("私密账号，需要关注才能访问")
            else:  # 没有发布任何帖子
                return result
        else:
            raise CrawlerException("'edges'字段长度不正确\n" + str(media_pagination_response.json_data))
    for media_info in media_info_list:
        result_media_info = {
            "photo_url": "",  # 图片地址
            "is_group": False,  # 是不是图片/视频组
            "is_video": False,  # 是不是视频
            "page_id": 0,  # 媒体详情界面id
            "page_code": "",  # 媒体详情界面code
            "time": "",  # 媒体上传时间
        }
        media_type = crawler.get_json_value(media_info, "node", "__typename", type_check=str)
        # GraphImage 单张图片、GraphSidecar 多张图片、GraphVideo 视频
        if media_type not in ["GraphImage", "GraphSidecar", "GraphVideo"]:
            raise CrawlerException(f"媒体信息：{media_info}中'__typename'取值范围不正确")
        # 获取图片地址
        result_media_info["photo_url"] = crawler.get_json_value(media_info, "node", "display_url", type_check=str)
        # 判断是不是图片/视频组
        result_media_info["is_group"] = media_type == "GraphSidecar"
        # 判断是否有视频
        result_media_info["is_video"] = media_type == "GraphVideo"
        # 获取图片上传时间
        result_media_info["media_time"] = crawler.get_json_value(media_info, "node", "taken_at_timestamp", type_check=int)
        # 获取媒体详情界面id
        result_media_info["page_id"] = crawler.get_json_value(media_info, "node", "id", type_check=int)
        # 获取媒体详情界面code
        result_media_info["page_code"] = crawler.get_json_value(media_info, "node", "shortcode", type_check=str)
        result["media_info_list"].append(result_media_info)
    # 获取下一页的指针
    if crawler.get_json_value(response_media, "page_info", "has_next_page", type_check=bool):
        result["next_page_cursor"] = crawler.get_json_value(response_media, "page_info", "end_cursor", type_check=str)
    return result


# 获取媒体详细页
def get_media_page(page_id):
    media_url = f"https://i.instagram.com/api/v1/media/{page_id}/info/"
    headers = {
        "X-CSRFToken": COOKIES["csrftoken"],
        "X-IG-App-ID": "936619743392459",
    }
    media_response = net.Request(media_url, method="GET", cookies=COOKIES, headers=headers).enable_json_decode()
    result = {
        "photo_url_list": [],  # 全部图片地址
        "video_url_list": [],  # 全部视频地址
    }
    if media_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(media_response.status))
    media_item_list = crawler.get_json_value(media_response.json_data, "items", type_check=list)
    if len(media_item_list) != 1:
        raise CrawlerException("items字段长度不为1")
    for media_item in media_item_list:
        media_type = crawler.get_json_value(media_item, "media_type", type_check=int)
        # 图片
        # https://i.instagram.com/api/v1/media/2887939807062643658/info/
        if media_type == 1:
            original_height = crawler.get_json_value(media_item, "original_height", type_check=int)
            original_width = crawler.get_json_value(media_item, "original_width", type_check=int)
            photo_url = ""
            max_resolution = 0
            for photo_info in crawler.get_json_value(media_item, "image_versions2", "candidates", type_check=list):
                width = crawler.get_json_value(photo_info, "width", type_check=int)
                height = crawler.get_json_value(photo_info, "height", type_check=int)
                if original_width == width and original_height == height:
                    photo_url = crawler.get_json_value(photo_info, "url", type_check=str)
                    break
                else:
                    resolution = width * height
                    if resolution > max_resolution:
                        photo_url = crawler.get_json_value(photo_info, "url", type_check=str)
                        max_resolution = resolution
            if not photo_url:
                raise CrawlerException(f"媒体信息{media_item}获取图片地址失败")
            result["photo_url_list"].append(photo_url)
        elif media_type == 2:  # 视频
            video_url = ""
            max_resolution = 0
            for video_version in crawler.get_json_value(media_item, "video_versions", type_check=list):
                width = crawler.get_json_value(video_version, "width", type_check=int)
                height = crawler.get_json_value(video_version, "height", type_check=int)
                resolution = width * height
                if resolution > max_resolution:
                    video_url = crawler.get_json_value(video_version, "url", type_check=str)
                    max_resolution = resolution
            if not video_url:
                raise CrawlerException(f"媒体信息{media_item}获取视频地址失败")
            result["video_url_list"].append(video_url)
        elif media_type == 8:  # 轮播
            for carousel_media in crawler.get_json_value(media_item, "carousel_media", type_check=list):
                sub_media_type = crawler.get_json_value(carousel_media, "media_type", type_check=int)
                # https://i.instagram.com/api/v1/media/2885474284266640152/info/
                if sub_media_type == 1:  # 图片
                    original_height = crawler.get_json_value(carousel_media, "original_height", type_check=int)
                    original_width = crawler.get_json_value(carousel_media, "original_width", type_check=int)
                    photo_url = ""
                    max_resolution = 0
                    for photo_info in crawler.get_json_value(carousel_media, "image_versions2", "candidates", type_check=list):
                        width = crawler.get_json_value(photo_info, "width", type_check=int)
                        height = crawler.get_json_value(photo_info, "height", type_check=int)
                        if original_width == width and original_height == height:
                            photo_url = crawler.get_json_value(photo_info, "url", type_check=str)
                            break
                        else:
                            width = crawler.get_json_value(photo_info, "width", type_check=int)
                            height = crawler.get_json_value(photo_info, "height", type_check=int)
                            resolution = width * height
                            if resolution > max_resolution:
                                photo_url = crawler.get_json_value(photo_info, "url", type_check=str)
                                max_resolution = resolution
                    if not photo_url:
                        raise CrawlerException(f"子媒体信息{carousel_media}获取图片地址失败")
                    result["photo_url_list"].append(photo_url)
                # https://i.instagram.com/api/v1/media/1845507605951424933/info/
                elif sub_media_type == 2:  # 视频
                    video_url = ""
                    max_resolution = 0
                    for video_version in crawler.get_json_value(carousel_media, "video_versions", type_check=list):
                        width = crawler.get_json_value(video_version, "width", type_check=int)
                        height = crawler.get_json_value(video_version, "height", type_check=int)
                        resolution = width * height
                        if resolution > max_resolution:
                            video_url = crawler.get_json_value(video_version, "url", type_check=str)
                            max_resolution = resolution
                    if not video_url:
                        raise CrawlerException(f"子媒体信息{carousel_media}获取视频地址失败")
                    result["video_url_list"].append(video_url)
                else:
                    raise CrawlerException(f"不支持子媒体信息{carousel_media}获取的媒体类型{sub_media_type}")
        else:
            raise CrawlerException(f"不支持的媒体类型{media_type}")
    return result


# 限制一定时间范围内的请求次数
def add_request_count(thread_lock):
    struct_time = time.gmtime()
    hour_minuter = struct_time[3] * 60 + struct_time[4]
    with thread_lock:
        if hour_minuter not in REQUEST_MINTER_COUNT:
            REQUEST_MINTER_COUNT[hour_minuter] = 0
        REQUEST_MINTER_COUNT[hour_minuter] += 1
        total_request_count = 0
        for i in range(REQUEST_LIMIT_DURATION):
            if (hour_minuter - i) in REQUEST_MINTER_COUNT:
                total_request_count += REQUEST_MINTER_COUNT[hour_minuter - i]
        if total_request_count > REQUEST_LIMIT_COUNT:
            time.sleep(120)


class Instagram(crawler.Crawler):
    def __init__(self, **kwargs):
        global COOKIES, IS_LOCAL_SAVE_SESSION, SESSION_DATA_PATH

        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            const.SysConfigKey.DOWNLOAD_PHOTO: True,
            const.SysConfigKey.DOWNLOAD_VIDEO: True,
            const.SysConfigKey.SET_PROXY: True,
            const.SysConfigKey.GET_COOKIE: ("instagram.com",),
            const.SysConfigKey.APP_CONFIG: (
                ("IS_LOCAL_SAVE_SESSION", False, const.ConfigAnalysisMode.BOOLEAN),
            ),
            const.SysConfigKey.SAVE_DATA_FORMATE: (0, ["", "", "0"]),  # account_name  account_id  last_page_id
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 设置全局变量，供子线程调用
        COOKIES.update(self.cookie_value)
        IS_LOCAL_SAVE_SESSION = self.app_config["IS_LOCAL_SAVE_SESSION"]
        SESSION_DATA_PATH = self.session_data_path

        # 下载线程
        self.set_crawler_thread(CrawlerThread)

    def init(self):
        # 生成session信息
        init_session()

        # 检测登录状态
        if check_login():
            return

        while True:
            input_str = input(tool.convert_timestamp_to_formatted_time() + " 没有检测到账号登录状态，手动输入账号密码登录继续(C)ontinue？或者退出程序(E)xit？:")
            input_str = input_str.lower()
            if input_str in ["c", "yes"]:
                if login_from_console():
                    break
                else:
                    log.info("登录失败！")
            elif input_str in ["e", "exit"]:
                tool.process_exit()


class CrawlerThread(crawler.CrawlerThread):
    def __init__(self, main_thread, single_save_data):
        self.index_key = self.display_name = single_save_data[0]  # account name
        crawler.CrawlerThread.__init__(self, main_thread, single_save_data)

    # 获取所有可下载媒体
    def get_crawl_list(self):
        cursor = ""
        media_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的媒体
        while not is_over:
            media_pagination_description = f"cursor：{cursor}后一页媒体"
            self.start_parse(media_pagination_description)
            add_request_count(self.thread_lock)  # 增加请求计数
            try:
                media_pagination_response: dict = get_one_page_media(self.single_save_data[1], cursor)
            except CrawlerException as e:
                self.error(e.http_error(media_pagination_description))
                raise
            self.parse_result(media_pagination_description, media_pagination_response["media_info_list"])

            # 寻找这一页符合条件的媒体
            for media_info in media_pagination_response["media_info_list"]:
                # 检查是否达到存档记录
                if media_info["page_id"] > int(self.single_save_data[2]):
                    media_info_list.append(media_info)
                else:
                    is_over = True
                    break

            if not is_over:
                if not media_pagination_response["next_page_cursor"]:
                    is_over = True
                else:
                    # 设置下一页指针
                    cursor = media_pagination_response["next_page_cursor"]
                    time.sleep(5)

        return media_info_list

    # 解析单个媒体
    def crawl_media(self, media_info):
        media_description = f"媒体{media_info['page_id']}/{media_info['page_code']}"
        self.start_parse(media_description)
        try:
            media_response = get_media_page(media_info["page_id"])
        except CrawlerException as e:
            self.error(e.http_error(media_description))
            raise

        # 图片下载
        if self.main_thread.is_download_photo:
            self.parse_result(media_description + "图片", media_response["photo_url_list"])

            photo_index = 1
            for photo_url in media_response["photo_url_list"]:
                photo_name = f"%019d_%02d.{url.get_file_ext(photo_url)}" % (media_info["page_id"], photo_index)
                photo_path = os.path.join(self.main_thread.photo_download_path, self.index_key, photo_name)
                photo_description = f"媒体{media_info['page_id']}/{media_info['page_code']}第{photo_index}张图片"
                if self.download(photo_url, photo_path, photo_description):
                    self.temp_path_list.append(photo_path)  # 设置临时目录
                    self.total_photo_count += 1  # 计数累加
                photo_index += 1

        # 视频下载
        if self.main_thread.is_download_video:
            self.parse_result(media_description + "视频", media_response["video_url_list"])

            video_index = 1
            for video_url in media_response["video_url_list"]:
                video_name = f"%019d_%02d.{url.get_file_ext(video_url)}" % (media_info["page_id"], video_index)
                video_path = os.path.join(self.main_thread.video_download_path, self.index_key, video_name)
                video_description = f"媒体{media_info['page_id']}/{media_info['page_code']}第{video_index}个视频"
                if self.download(video_url, video_path, video_description, auto_multipart_download=True):
                    self.temp_path_list.append(video_path)  # 设置临时目录
                    self.total_video_count += 1  # 计数累加
                video_index += 1

        # 媒体内图片和视频全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.single_save_data[2] = str(media_info["page_id"])  # 设置存档记录

    def _run(self):
        # 获取首页
        try:
            account_index_response = get_account_index_page(self.index_key)
        except CrawlerException as e:
            self.error(e.http_error("首页"))
            raise

        if self.single_save_data[1] == "":
            self.single_save_data[1] = str(account_index_response["account_id"])
        else:
            if self.single_save_data[1] != str(account_index_response["account_id"]):
                self.error("account id 不符合，原账号已改名")
                tool.process_exit()

        # 获取所有可下载媒体
        media_info_list = self.get_crawl_list()
        self.info(f"需要下载的全部媒体解析完毕，共{len(media_info_list)}个")

        # 从最早的媒体开始下载
        while len(media_info_list) > 0:
            self.crawl_media(media_info_list.pop())


if __name__ == "__main__":
    Instagram().main()
