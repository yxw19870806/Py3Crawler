# -*- coding:UTF-8  -*-
"""
Instagram图片&视频爬虫
https://www.instagram.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import json
import os
import time
from common import *
from common import crypto

IS_LOCAL_SAVE_SESSION = False
EACH_PAGE_PHOTO_COUNT = 12  # 每次请求获取的媒体数量
QUERY_ID = "17859156310193001"
COOKIE_INFO = {"csrftoken": "", "mid": "", "sessionid": ""}
REQUEST_LIMIT_DURATION = 10  # 请求统计的分钟数量
REQUEST_LIMIT_COUNT = 300  # 一定时间范围内的请求次数限制
REQUEST_MINTER_COUNT = {}  # 每分钟的请求次数
SESSION_DATA_PATH = ''


# 生成session cookies
def init_session():
    # 如果有登录信息（初始化时从浏览器中获得）
    if COOKIE_INFO["sessionid"]:
        return True
    home_url = "https://www.instagram.com/"
    home_response = net.request(home_url, method="GET")
    if home_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        set_cookie = net.get_cookies_from_response_header(home_response.headers)
        if "csrftoken" in set_cookie and "mid" in set_cookie:
            COOKIE_INFO["csrftoken"] = set_cookie["csrftoken"]
            COOKIE_INFO["mid"] = set_cookie["mid"]
            return True
    return False


# 检测登录状态
def check_login():
    if not COOKIE_INFO["sessionid"] and SESSION_DATA_PATH:
        # 从文件中读取账号密码
        account_data = tool.json_decode(crypto.Crypto().decrypt(file.read_file(SESSION_DATA_PATH)), {})
        if crawler.check_sub_key(("email", "password"), account_data):
            if _do_login(account_data["email"], account_data["password"]):
                return True
    else:
        index_url = "https://www.instagram.com/"
        index_response = net.request(index_url, method="GET", cookies_list=COOKIE_INFO)
        if index_response.status == net.HTTP_RETURN_CODE_SUCCEED:
            return index_response.data.decode(errors="ignore").find('"viewerId":"') >= 0
    return False


# 登录
def login_from_console():
    # 从命令行中输入账号密码
    while True:
        email = input(tool.get_time() + " 请输入邮箱: ")
        password = input(tool.get_time() + " 请输入密码: ")
        while True:
            input_str = input(tool.get_time() + " 是否使用这些信息(Y)es或重新输入(N)o: ")
            input_str = input_str.lower()
            if input_str in ["y", "yes"]:
                if _do_login(email, password):
                    if IS_LOCAL_SAVE_SESSION and SESSION_DATA_PATH:
                        file.write_file(crypto.Crypto().encrypt(json.dumps({"email": email, "password": password})), SESSION_DATA_PATH, file.WRITE_FILE_TYPE_REPLACE)
                    return True
                return False
            elif input_str in ["n", "no"]:
                break


# 模拟登录请求
def _do_login(email, password):
    login_url = "https://www.instagram.com/accounts/login/ajax/"
    login_post = {"username": email, "password": password, "next": "/"}
    header_list = {"referer": "https://www.instagram.com/", "x-csrftoken": COOKIE_INFO["csrftoken"]}
    login_response = net.request(login_url, method="POST", fields=login_post, cookies_list=COOKIE_INFO, header_list=header_list, json_decode=True)
    if login_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        if crawler.get_json_value(login_response.json_data, "authenticated", default_value=False, type_check=bool) is True:
            set_cookie = net.get_cookies_from_response_header(login_response.headers)
            if "sessionid" in set_cookie:
                COOKIE_INFO["sessionid"] = set_cookie["sessionid"]
                return True
    return False


# 根据账号名字获得账号id（字母账号->数字账号)
def get_account_index_page(account_name):
    account_index_url = f"https://i.instagram.com/api/v1/users/web_profile_info/"
    query_data = {
        "username": account_name
    }
    header_list = {
        "X-CSRFToken": COOKIE_INFO["csrftoken"],
        "X-IG-App-ID": "936619743392459",
    }
    account_index_response = net.request(account_index_url, method="GET", fields=query_data, cookies_list=COOKIE_INFO, header_list=header_list, json_decode=True)
    result = {
        "account_id": None,  # account id
    }
    if account_index_response.status == 404:
        raise crawler.CrawlerException("账号不存在")
    elif account_index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(account_index_response.status))
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
    media_pagination_response = net.request(api_url, method="GET", fields=query_data, cookies_list=COOKIE_INFO, json_decode=True)
    result = {
        "media_info_list": [],  # 全部媒体信息
        "next_page_cursor": None,  # 下一页媒体信息的指针
    }
    if media_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(media_pagination_response.status))
    response_media = crawler.get_json_value(media_pagination_response.json_data, "data", "user", "edge_owner_to_timeline_media", type_check=dict)
    media_info_list = crawler.get_json_value(response_media, "edges", type_check=list)
    if len(media_info_list) == 0:
        if cursor == "":
            if crawler.get_json_value(response_media, "count", type_check=int) > 0:
                raise crawler.CrawlerException("私密账号，需要关注才能访问")
            else:  # 没有发布任何帖子
                return result
        else:
            raise crawler.CrawlerException("'edges'字段长度不正确\n" + media_pagination_response.json_data)
    for media_info in media_info_list:
        result_media_info = {
            "photo_url": None,  # 图片地址
            "is_group": False,  # 是不是图片/视频组
            "is_video": False,  # 是不是视频
            "page_id": None,  # 媒体详情界面id
            "time": None,  # 媒体上传时间
        }
        media_type = crawler.get_json_value(media_info, "node", "__typename", type_check=str)
        # GraphImage 单张图片、GraphSidecar 多张图片、GraphVideo 视频
        if media_type not in ["GraphImage", "GraphSidecar", "GraphVideo"]:
            raise crawler.CrawlerException(f"媒体信息：{media_info}中'__typename'取值范围不正确")
        # 获取图片地址
        result_media_info["photo_url"] = crawler.get_json_value(media_info, "node", "display_url", type_check=str)
        # 判断是不是图片/视频组
        result_media_info["is_group"] = media_type == "GraphSidecar"
        # 判断是否有视频
        result_media_info["is_video"] = media_type == "GraphVideo"
        # 获取图片上传时间
        result_media_info["media_time"] = crawler.get_json_value(media_info, "node", "taken_at_timestamp", type_check=int)
        # 获取媒体详情界面id
        result_media_info["page_id"] = media_info["node"]["shortcode"]
        result["media_info_list"].append(result_media_info)
    # 获取下一页的指针
    if crawler.get_json_value(response_media, "page_info", "has_next_page", type_check=bool):
        result["next_page_cursor"] = crawler.get_json_value(response_media, "page_info", "end_cursor", type_check=str)
    return result


# 获取媒体详细页
def get_media_page(page_id):
    media_url = f"https://www.instagram.com/p/{page_id}"
    media_response = net.request(media_url, method="GET", cookies_list=COOKIE_INFO)
    result = {
        "photo_url_list": [],  # 全部图片地址
        "video_url_list": [],  # 全部视频地址
    }
    if media_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(media_response.status))
    media_response_content = media_response.data.decode(errors="ignore")
    script_json_html = tool.find_sub_string(media_response_content, f"window.__additionalDataLoaded('/p/{page_id}/',", ");</script>")
    if script_json_html:
        script_json = tool.json_decode(script_json_html)
        if script_json is None:
            raise crawler.CrawlerException("媒体信息加载失败\n" + script_json_html)
        media_info = crawler.get_json_value(script_json, "graphql", "shortcode_media", type_check=dict)
    else:
        script_json_html = tool.find_sub_string(media_response_content, "window._sharedData = ", ";</script>")
        if not script_json_html:
            crawler.CrawlerException("页面截取媒体信息失败\n" + media_response_content)
        script_json = tool.json_decode(script_json_html)
        if script_json is None:
            raise crawler.CrawlerException("媒体信息加载失败\n" + script_json_html)
        media_info = crawler.get_json_value(script_json, "entry_data", "PostPage", 0, "graphql", "shortcode_media", type_check=dict)
    media_type = crawler.get_json_value(media_info, "__typename", type_check=str)
    # 多张图片/视频
    if media_type == "GraphSidecar":
        edge_info_list = crawler.get_json_value(media_info, "edge_sidecar_to_children", "edges", type_check=list)
        if len(edge_info_list) < 2:
            raise crawler.CrawlerException(f"媒体信息：{script_json}中'edges'长度不正确")
        for edge_info in edge_info_list:
            # 获取图片地址
            result["photo_url_list"].append(crawler.get_json_value(edge_info, "node", "display_url", type_check=str))
            # 获取视频地址
            if crawler.get_json_value(edge_info, "node", "__typename", type_check=str) == "GraphVideo":
                result["video_url_list"].append(crawler.get_json_value(edge_info, "node", "video_url", type_check=str))
    # 视频
    elif media_type == "GraphVideo":
        # 获取视频地址
        result["video_url_list"].append(crawler.get_json_value(media_info, "video_url", type_check=str))
    else:
        raise crawler.CrawlerException(f"媒体信息：{script_json}中'__typename'取值范围不正确")
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
        for i in range(0, REQUEST_LIMIT_DURATION):
            if (hour_minuter - i) in REQUEST_MINTER_COUNT:
                total_request_count += REQUEST_MINTER_COUNT[hour_minuter - i]
        if total_request_count > REQUEST_LIMIT_COUNT:
            time.sleep(120)


class Instagram(crawler.Crawler):
    def __init__(self, **kwargs):
        global COOKIE_INFO, IS_LOCAL_SAVE_SESSION, SESSION_DATA_PATH

        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_DOWNLOAD_VIDEO: True,
            crawler.SYS_SET_PROXY: True,
            crawler.SYS_GET_COOKIE: ("instagram.com",),
            crawler.SYS_APP_CONFIG: (
                ("IS_LOCAL_SAVE_SESSION", False, crawler.CONFIG_ANALYSIS_MODE_BOOLEAN),
            ),
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 设置全局变量，供子线程调用
        COOKIE_INFO.update(self.cookie_value)
        IS_LOCAL_SAVE_SESSION = self.app_config["IS_LOCAL_SAVE_SESSION"]
        SESSION_DATA_PATH = self.session_data_path

        # 解析存档文件
        # account_name  account_id  photo_count  video_count  last_created_time
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "", "0", "0", "0"])

        # 生成session信息
        init_session()

        # 检测登录状态
        if not check_login():
            while True:
                input_str = input(tool.get_time() + " 没有检测到账号登录状态，手动输入账号密码登录继续(C)ontinue？或者退出程序(E)xit？:")
                input_str = input_str.lower()
                if input_str in ["c", "yes"]:
                    if login_from_console():
                        break
                    else:
                        log.step("登录失败！")
                elif input_str in ["e", "exit"]:
                    tool.process_exit()

        # 下载线程
        self.download_thread = Download


class Download(crawler.DownloadThread):
    def __init__(self, single_save_data, main_thread):
        self.index_key = self.display_name = single_save_data[0]  # account name
        crawler.DownloadThread.__init__(self, single_save_data, main_thread)

    def _run(self):
        # 获取首页
        try:
            account_index_response = get_account_index_page(self.index_key)
        except crawler.CrawlerException as e:
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
        self.step(f"需要下载的全部媒体解析完毕，共{len(media_info_list)}个")

        # 从最早的媒体开始下载
        while len(media_info_list) > 0:
            self.crawl_media(media_info_list.pop())
            self.main_thread_check()  # 检测主线程运行状态

    # 获取所有可下载媒体
    def get_crawl_list(self):
        cursor = ""
        media_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的媒体
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step(f"开始解析cursor：{cursor}页媒体")

            # 增加请求计数
            add_request_count(self.thread_lock)
            # 获取指定时间后的一页媒体信息
            try:
                media_pagination_response = get_one_page_media(self.single_save_data[1], cursor)
            except crawler.CrawlerException as e:
                self.error(e.http_error(f"cursor：{cursor}后一页媒体"))
                raise

            self.trace(f"cursor：{cursor}页解析的全部媒体：{media_pagination_response['media_info_list']}")
            self.step(f"cursor：{cursor}页解析获取{len(media_pagination_response['media_info_list'])}个媒体")

            # 寻找这一页符合条件的媒体
            for media_info in media_pagination_response["media_info_list"]:
                # 检查是否达到存档记录
                if media_info["media_time"] > int(self.single_save_data[4]):
                    media_info_list.append(media_info)
                else:
                    is_over = True
                    break

            if not is_over:
                if media_pagination_response["next_page_cursor"] is None:
                    is_over = True
                else:
                    # 设置下一页指针
                    cursor = media_pagination_response["next_page_cursor"]

        return media_info_list

    # 解析单个媒体
    def crawl_media(self, media_info):
        self.step(f"开始解析媒体{media_info['page_id']}")

        media_response = None
        # 图片下载
        photo_index = int(self.single_save_data[2]) + 1
        if self.main_thread.is_download_photo:
            # 多张图片
            if media_info["is_group"]:
                # 增加请求计数
                add_request_count(self.thread_lock)

                # 获取媒体详细页
                try:
                    media_response = get_media_page(media_info["page_id"])
                except crawler.CrawlerException as e:
                    self.error(e.http_error(f"媒体{media_info['page_id']}"))
                    raise
                photo_url_list = media_response["photo_url_list"]
            # 单张图片 或者 视频的预览图片
            else:
                photo_url_list = [media_info["photo_url"]]

            self.trace(f"媒体{media_info['page_id']}解析的全部图片：{photo_url_list}")
            self.step(f"媒体{media_info['page_id']}解析获取{len(photo_url_list)}张图片")

            for photo_url in photo_url_list:
                self.main_thread_check()  # 检测主线程运行状态
                # 去除特效，获取原始路径
                self.step(f"开始下载第{photo_index}张图片 {photo_url}")

                photo_file_path = os.path.join(self.main_thread.photo_download_path, self.index_key, f"%04d.{net.get_file_extension(photo_url)}" % photo_index)
                download_return = net.Download(photo_url, photo_file_path)
                if download_return.status == net.Download.DOWNLOAD_SUCCEED:
                    self.temp_path_list.append(photo_file_path)  # 设置临时目录
                    self.total_photo_count += 1  # 计数累加
                    self.step(f"第{photo_index}张图片下载成功")
                else:
                    self.error(f"第{photo_index}张图片 {photo_url} 下载失败，原因：{crawler.download_failre(download_return.code)}")
                    self.check_download_failure_exit()
                photo_index += 1

        # 视频下载
        video_index = int(self.single_save_data[3]) + 1
        if self.main_thread.is_download_video and (media_info["is_group"] or media_info["is_video"]):
            # 如果图片那里没有获取过媒体页面，需要重新获取一下
            if media_response is None:
                # 获取媒体详细页
                try:
                    media_response = get_media_page(media_info["page_id"])
                except crawler.CrawlerException as e:
                    self.error(e.http_error(f"媒体{media_info['page_id']}"))
                    raise

            self.trace(f"媒体{media_info['page_id']}解析的全部视频：{media_response['video_url_list']}")
            self.step(f"媒体{media_info['page_id']}解析获取{len(media_response['video_url_list'])}个视频")

            for video_url in media_response["video_url_list"]:
                self.main_thread_check()  # 检测主线程运行状态
                self.step(f"开始下载第{video_index}个视频 {video_url}")

                video_file_path = os.path.join(self.main_thread.video_download_path, self.index_key, f"%04d.{net.get_file_extension(video_url)}" % video_index)
                download_return = net.Download(video_url, video_file_path, auto_multipart_download=True)
                if download_return.status == net.Download.DOWNLOAD_SUCCEED:
                    self.temp_path_list.append(video_file_path)  # 设置临时目录
                    self.total_video_count += 1  # 计数累加
                    self.step(f"第{video_index}个视频下载成功")
                else:
                    self.error(f"第{video_index}个视频 {video_url} 下载失败，原因：{crawler.download_failre(download_return.code)}")
                    self.check_download_failure_exit()
                video_index += 1

        # 媒体内图片和视频全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.single_save_data[2] = str(photo_index - 1)  # 设置存档记录
        self.single_save_data[3] = str(video_index - 1)  # 设置存档记录
        self.single_save_data[4] = str(media_info["media_time"])


if __name__ == "__main__":
    Instagram().main()
