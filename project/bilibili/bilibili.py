# -*- coding:UTF-8  -*-
"""
bilibili用户投稿视频/音频/相册爬虫
https://www.bilibili.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import math
import os
import time
from common import *

COOKIES = {}
IS_LOGIN = False
EACH_PAGE_COUNT = 30
SECRET_KEY = ""

string_table = "fZodR9XQDSUm21yCkr6zBqiveYah8bt4xsWpHnJE7jL5VG3guMTKNPAwcF"
id_index = [11, 10, 3, 8, 4, 6]
secret_key_index_list = [46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
                         37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52]
xor = 177451812
add = 8728348608


# av id转bv id
def av_id_2_bv_id(av_id):
    if isinstance(av_id, str) and av_id.lower().startswith("av"):
        av_id = av_id[len("av"):]
    av_id = (av_id ^ xor) + add
    result = list("BV1  4 1 7  ")
    for i in range(6):
        result[id_index[i]] = string_table[math.floor(av_id / 58 ** i) % 58]
    return "".join(result)


# bv id转av id
def bv_id_2_av_id(bv_id):
    result = 0
    for i in range(6):
        result += string_table.find(bv_id[id_index[i]]) * 58 ** i
    return result - add ^ xor


def calc_w_rid(query_data: dict):
    sign_string = []
    query_data["wts"] = int(time.time())
    for key in sorted(query_data.keys()):
        sign_string.append(f"{key}={query_data[key]}")
    if not SECRET_KEY:
        generate_sign_secret()
    query_data["w_rid"] = tool.string_md5("&".join(sign_string) + SECRET_KEY)


# 检测是否已登录
def check_login():
    if not COOKIES:
        return False
    api_url = "https://api.bilibili.com/x/member/web/account"
    api_response = net.Request(api_url, method="GET", cookies=COOKIES).enable_json_decode()
    if api_response.status == const.ResponseCode.SUCCEED:
        return crawler.get_json_value(api_response.json_data, "data", "mid", type_check=int, default_value=0) != 0
    return False


def generate_sign_secret():
    api_url = "https://api.bilibili.com/x/web-interface/nav"
    api_response = net.Request(api_url, method="GET", cookies=COOKIES).enable_json_decode()
    if api_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException("sign_secret，" + crawler.request_failre(api_response.status))
    img_key = url.get_file_name(crawler.get_json_value(api_response.json_data, "data", "wbi_img", "img_url", type_check=str))
    sub_key = url.get_file_name(crawler.get_json_value(api_response.json_data, "data", "wbi_img", "sub_url", type_check=str))
    sign_string = img_key + sub_key
    key_index_list = [46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
                      37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52]
    signed_string = []
    for key_index in key_index_list:
        signed_string.append(sign_string[key_index])
    global SECRET_KEY
    SECRET_KEY = "".join(signed_string)[:32]


def get_favorites_list(favorites_id):
    # https://api.bilibili.com/x/v2/medialist/resource/list?type=3&otype=2&biz_id=1100799539&bvid=&with_current=true&mobi_app=web&ps=20&direction=false
    bv_id = ""
    result = {
        "video_info_list": [],  # 全部视频信息
    }
    while True:
        api_url = "https://api.bilibili.com/x/v2/medialist/resource/list"
        query_data = {
            "type": "3",
            "otype": "2",
            "biz_id": favorites_id,
            "bvid": bv_id,
            "with_current": "true",
            "mobi_app": "web",
            "ps": EACH_PAGE_COUNT,
            "direction": "false",
        }
        api_response = net.Request(api_url, method="GET", fields=query_data, cookies=COOKIES).enable_json_decode()
        video_info_list = []
        try:
            video_info_list = crawler.get_json_value(api_response.json_data, "data", "media_list", type_check=list)
        except CrawlerException:
            if crawler.get_json_value(api_response.json_data, "data", "media_list", value_check=None) is not None:
                raise
        for video_info in video_info_list:
            result_video_info = {
                "video_id": 0,  # 视频id
                "video_title": "",  # 视频标题
            }
            # bv id
            bv_id = crawler.get_json_value(video_info, "bv_id", type_check=str)
            # 获取视频id
            result_video_info["video_id"] = crawler.get_json_value(video_info, "id", type_check=int)
            # 获取视频标题
            result_video_info["video_title"] = crawler.get_json_value(video_info, "title", type_check=str)
            result["video_info_list"].append(result_video_info)
        if not crawler.get_json_value(api_response.json_data, "data", "has_more", type_check=bool):
            break
    return result


# 获取指定页数的全部视频
def get_one_page_video(account_id, page_count):
    # https://api.bilibili.com/x/space/wbi/arc/search?mid=2026561407&ps=30&tid=0&pn=1&keyword=&order=pubdate&platform=web&web_location=1550101&order_avoided=true&w_rid=8c57e654e483627aed4f8554d5e18950&wts=1678460182
    api_url = "https://api.bilibili.com/x/space/wbi/arc/search"
    query_data = {
        "keyword": "",
        "mid": account_id,
        "order": "pubdate",
        "pn": page_count,
        "ps": EACH_PAGE_COUNT,
        "tid": "0",
        "platform": "web",
        "web_location": "1550101",
        "order_avoided": "true",
        "w_rid": tool.string_md5(str(time.time())),
        "wts": time.time(),
    }
    header_list = {
        "referer": f"https://space.bilibili.com/{account_id}/video"
    }
    calc_w_rid(query_data)
    api_response = net.Request(api_url, method="GET", fields=query_data, cookies=COOKIES, headers=header_list).enable_json_decode()
    result = {
        "video_info_list": [],  # 全部视频信息
    }
    if api_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(api_response.status))
    try:
        video_info_list = crawler.get_json_value(api_response.json_data, "data", "list", "vlist", type_check=list)
    except CrawlerException:
        if crawler.get_json_value(api_response.json_data, "code", type_check=int) == -401:
            net.set_default_user_agent()
            time.sleep(10)
            return get_one_page_video(account_id, page_count)
        raise
    for video_info in video_info_list:
        result_video_info = {
            "video_id": 0,  # 视频id
            "video_time": 0,  # 视频上传时间
            "video_title": "",  # 视频标题
        }
        # 获取视频id
        result_video_info["video_id"] = crawler.get_json_value(video_info, "aid", type_check=int)
        # 获取视频标题
        result_video_info["video_title"] = crawler.get_json_value(video_info, "title", type_check=str)
        # 获取视频上传时间
        result_video_info["video_time"] = crawler.get_json_value(video_info, "created", type_check=int)
        result["video_info_list"].append(result_video_info)
    return result


# 获取指定页数的全部短视频
def get_one_page_short_video(account_id, nex_offset):
    # http://api.vc.bilibili.com/clip/v1/video/blist?uid=21687662&next_offset=413361
    api_url = "http://api.vc.bilibili.com/clip/v1/video/blist"
    query_data = {
        "uid": account_id,
        "next_offset": nex_offset,
    }
    api_response = net.Request(api_url, method="GET", fields=query_data).enable_json_decode()
    result = {
        "video_info_list": [],  # 全部视频信息
        "next_page_offset": "",  # 下一页指针
    }
    if api_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(api_response.status))
    if crawler.get_json_value(api_response.json_data, "msg", type_check=str) != "success":
        raise CrawlerException("返回信息'msg'字段取值不正确\n" + str(api_response.json_data))
    # 获取下一页指针
    result["next_page_offset"] = crawler.get_json_value(api_response.json_data, "data", "next_offset", type_check=str)
    for video_info in crawler.get_json_value(api_response.json_data, "data", "items", type_check=list):
        result_video_info = {
            "video_id": 0,  # 视频id
            "video_title": "",  # 视频标题
            "video_url": "",  # 视频地址
        }
        # 获取视频id
        result_video_info["video_id"] = crawler.get_json_value(video_info, "id", type_check=int)
        # 获取视频标题
        result_video_info["video_title"] = crawler.get_json_value(video_info, "title", type_check=str)
        # 获取视频地址
        result_video_info["video_url"] = crawler.get_json_value(video_info, "playurl", type_check=str)
        result["video_info_list"].append(result_video_info)
    return result


# 获取指定页数的全部相簿
def get_one_page_album(account_id, page_count):
    # https://api.bilibili.com/x/dynamic/feed/draw/doc_list?uid=2026561407&page_num=0&page_size=30&biz=all&jsonp=jsonp
    api_url = "https://api.bilibili.com/x/dynamic/feed/draw/doc_list"
    query_data = {
        "uid": account_id,
        "page_num": page_count - 1,
        "page_size": EACH_PAGE_COUNT,
        "biz": "all",
    }
    api_response = net.Request(api_url, method="GET", fields=query_data, cookies=COOKIES).enable_json_decode()
    result = {
        "album_id_list": [],  # 全部相簿id
    }
    if api_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(api_response.status))

    album_info_list = []
    try:
        album_info_list = crawler.get_json_value(api_response.json_data, "data", "items", type_check=list)
    except CrawlerException:
        if crawler.get_json_value(api_response.json_data, "data", "items", value_check=None) is not None:
            raise
    for album_info in album_info_list:
        # 获取相簿id
        result["album_id_list"].append(crawler.get_json_value(album_info, "doc_id", type_check=int))
    return result


# 获取指定页数的全部视频
def get_one_page_audio(account_id, page_count):
    # https://api.bilibili.com/audio/music-service/web/song/upper?uid=234782&pn=3&ps=30&order=1&jsonp=jsonp
    api_url = "https://api.bilibili.com/audio/music-service/web/song/upper"
    query_data = {
        "order": "1",
        "pn": page_count,
        "ps": EACH_PAGE_COUNT,
        "uid": account_id,
    }
    api_response = net.Request(api_url, method="GET", fields=query_data).enable_json_decode()
    result = {
        "audio_info_list": [],  # 全部视频信息
    }
    if api_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(api_response.status))
    audio_info_list = []
    try:
        audio_info_list = crawler.get_json_value(api_response.json_data, "data", "data", type_check=list)
    except CrawlerException:
        if crawler.get_json_value(api_response.json_data, "data", "data", value_check=None) is not None:
            raise
    for audio_info in audio_info_list:
        result_audio_info = {
            "audio_id": 0,  # 音频id
            "audio_title": "",  # 音频标题
        }
        # 获取音频id
        result_audio_info["audio_id"] = crawler.get_json_value(audio_info, "id", type_check=int)
        # 获取音频标题
        result_audio_info["audio_title"] = crawler.get_json_value(audio_info, "title", type_check=str)
        result["audio_info_list"].append(result_audio_info)
    return result


# 获取指定视频
def get_video_page(video_id):
    video_play_url = f"https://www.bilibili.com/video/av{video_id}"
    video_play_response = net.Request(video_play_url, method="GET", cookies=COOKIES)
    result = {
        "is_private": False,  # 是否需要登录
        "video_part_info_list": [],  # 全部视频地址
        "video_title": "",  # 视频标题
    }
    if video_play_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(video_play_response.status))
    script_json = tool.json_decode(tool.find_sub_string(video_play_response.content, "window.__INITIAL_STATE__=", ";(function()"))
    if script_json is None:
        raise CrawlerException("页面截取视频信息失败\n" + video_play_response.content)
    try:
        video_part_info_list = crawler.get_json_value(script_json, "videoData", "pages", type_check=list)
        # 获取视频标题
        result["video_title"] = crawler.get_json_value(script_json, "videoData", "title", type_check=str).strip()
    except CrawlerException:
        # https://www.bilibili.com/video/av256978
        if crawler.get_json_value(script_json, "error", "message", type_check=str, default_value="") == "访问权限不足":
            if not IS_LOGIN:
                result["is_private"] = True
                return result
            else:
                raise
        else:
            # 特殊live回放
            # https://www.bilibili.com/festival/VSF2022live?bvid=BV1VF411E7zu
            try:
                video_info = crawler.get_json_value(script_json, "videoInfo", type_check=dict)
                video_info["part"] = ""
                video_part_info_list = [video_info]
                # 获取视频标题
                result["video_title"] = crawler.get_json_value(script_json, "videoInfo", "title", type_check=str).strip()
            except CrawlerException:
                # 剧集
                # https://www.bilibili.com/video/av256978
                video_part_info_list = crawler.get_json_value(script_json, "mediaInfo", "episodes", type_check=list)
                # 获取视频标题
                result["video_title"] = crawler.get_json_value(script_json, "h1Title", type_check=str).strip()
    # 分P https://www.bilibili.com/video/av33131459
    for video_part_info in video_part_info_list:
        result_video_info = {
            "video_url_list": [],  # 视频地址
            "video_part_title": "",  # 视频分P标题
        }
        # https://api.bilibili.com/x/player/playurl?avid=149236&cid=246864&qn=112&otype=json
        video_info_url = "https://api.bilibili.com/x/player/playurl"
        query_data = {
            "avid": video_id,
            "cid": crawler.get_json_value(video_part_info, "cid", type_check=int),
            "qn": "116",  # 上限 高清 1080P+: 116, 高清 1080P: 80, 高清 720P: 64, 清晰 480P: 32, 流畅 360P: 16
            "otype": "json",
        }
        headers = {"Referer": f"https://www.bilibili.com/video/av{video_id}"}
        video_info_response = net.Request(video_info_url, method="GET", fields=query_data, cookies=COOKIES, headers=headers).enable_json_decode()
        if video_info_response.status != const.ResponseCode.SUCCEED:
            raise CrawlerException("视频信息，" + crawler.request_failre(video_info_response.status))
        try:
            video_info_list = crawler.get_json_value(video_info_response.json_data, "data", "durl", type_check=list)
        except CrawlerException:
            # https://www.bilibili.com/video/av116528/?p=2
            if crawler.get_json_value(video_info_response.json_data, "data", "message", default_value="", type_check=str) == "No video info.":
                continue
            # https://www.bilibili.com/video/av44067
            else:
                error_message = crawler.get_json_value(video_info_response.json_data, "message", default_value="", type_check=str)
                if error_message == "啥都木有":
                    continue
                elif crawler.get_json_value(video_info_response.json_data, "message", default_value="", type_check=str) == "87007":
                    # 充电专属视频
                    continue
            raise
        if IS_LOGIN:
            max_resolution = max(crawler.get_json_value(video_info_response.json_data, "data", "accept_quality", type_check=list))
            current_resolution = crawler.get_json_value(video_info_response.json_data, "data", "quality", type_check=int)
            if max_resolution != current_resolution:
                raise CrawlerException("返回的视频分辨率不是最高的\n" + str(video_info_response.json_data))
        # 获取视频地址
        for video_info in video_info_list:
            result_video_info["video_url_list"].append(crawler.get_json_value(video_info, "backup_url", 0, type_check=str))
        # 获取视频分P标题
        result_video_info["video_part_title"] = crawler.get_json_value(video_part_info, "part", type_check=str)
        result["video_part_info_list"].append(result_video_info)
    return result


# 获取指定id的相簿
def get_album_page(album_id):
    # https://api.vc.bilibili.com/link_draw/v1/doc/detail?doc_id=739722
    api_url = "https://api.vc.bilibili.com/link_draw/v1/doc/detail"
    query_data = {
        "doc_id": album_id,
    }
    api_response = net.Request(api_url, method="GET", fields=query_data, cookies=COOKIES).enable_json_decode()
    result = {
        "photo_url_list": [],  # 全部图片地址
    }
    if api_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(api_response.status))
    for photo_info in crawler.get_json_value(api_response.json_data, "data", "item", "pictures", type_check=list):
        result["photo_url_list"].append(crawler.get_json_value(photo_info, "img_src", type_check=str))
    return result


# 获取指定视频
def get_audio_info_page(audio_id):
    # https://www.bilibili.com/audio/music-service-c/web/url?sid=15737&privilege=2&quality=2
    api_url = "https://www.bilibili.com/audio/music-service-c/web/url"
    query_data = {
        "sid": audio_id,
    }
    api_response = net.Request(api_url, method="GET", fields=query_data).enable_json_decode()
    result = {
        "audio_url": "",  # 音频地址
    }
    if api_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(api_response.status))
    result["audio_url"] = crawler.get_json_value(api_response.json_data, "data", "cdns", 0, type_check=str)
    return result


class BiliBili(crawler.Crawler):
    def __init__(self, **kwargs):
        global COOKIES

        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            const.SysConfigKey.DOWNLOAD_PHOTO: True,
            const.SysConfigKey.DOWNLOAD_VIDEO: True,
            const.SysConfigKey.DOWNLOAD_AUDIO: True,
            const.SysConfigKey.GET_COOKIE: ("bilibili.com",),
            const.SysConfigKey.SAVE_DATA_FORMATE: (0, ["", "0", "0", "0"]),  # account_name  last_video_id  last_audio_id  last_album_id
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 设置全局变量，供子线程调用
        COOKIES = self.cookie_value

        # 下载线程
        self.set_crawler_thread(CrawlerThread)

    def init(self):
        net.set_default_user_agent()

        # 检测登录状态
        if self.is_download_video:
            if check_login():
                global IS_LOGIN
                IS_LOGIN = True
                return

            while True:
                input_str = input(tool.convert_timestamp_to_formatted_time() + " 没有检测到账号登录状态，可能无法解析相簿、需要登录才能查看的视频以及获取高分辨率，继续程序(C)ontinue？或者退出程序(E)xit？:")
                input_str = input_str.lower()
                if input_str in ["e", "exit"]:
                    tool.process_exit()
                elif input_str in ["c", "continue"]:
                    break


class CrawlerThread(crawler.CrawlerThread):
    def __init__(self, main_thread, single_save_data):
        self.index_key = single_save_data[0]  # account id
        if len(single_save_data) >= 5 and single_save_data[4]:
            self.display_name = single_save_data[4]
        else:
            self.display_name = single_save_data[0]
        crawler.CrawlerThread.__init__(self, main_thread, single_save_data)

    # 获取所有可下载视频
    def get_crawl_video_list(self):
        page_count = 1
        unique_list = []
        video_info_list = []
        is_over = False
        while not is_over:
            album_pagination_description = f"第{page_count}页视频"
            self.start_parse(album_pagination_description)
            try:
                album_pagination_response = get_one_page_video(self.index_key, page_count)
            except CrawlerException as e:
                self.error(e.http_error(album_pagination_description))
                raise
            self.parse_result(album_pagination_description, album_pagination_response["video_info_list"])

            # 寻找这一页符合条件的视频
            for video_info in album_pagination_response["video_info_list"]:
                # 检查是否达到存档记录
                if video_info["video_time"] > int(self.single_save_data[1]):
                    # 新增相簿导致的重复判断
                    if video_info["video_id"] in unique_list:
                        continue
                    else:
                        video_info_list.append(video_info)
                        unique_list.append(video_info["video_id"])
                else:
                    is_over = True
                    break

            if not is_over:
                # 获取的视频数量少于1页的上限，表示已经到结束了
                # 如果视频数量正好是页数上限的倍数，则由下一页获取是否为空判断
                if len(album_pagination_response["video_info_list"]) < EACH_PAGE_COUNT:
                    is_over = True
                else:
                    page_count += 1

        return video_info_list

    # 获取所有可下载音频
    def get_crawl_audio_list(self):
        page_count = 1
        unique_list = []
        audio_info_list = []
        is_over = False
        while not is_over:
            album_pagination_description = f"第{page_count}页音频"
            self.start_parse(album_pagination_description)
            try:
                album_pagination_response = get_one_page_audio(self.index_key, page_count)
            except CrawlerException as e:
                self.error(e.http_error(album_pagination_description))
                raise
            self.parse_result(album_pagination_description, album_pagination_response["audio_info_list"])

            # 寻找这一页符合条件的音频
            for audio_info in album_pagination_response["audio_info_list"]:
                # 检查是否达到存档记录
                if audio_info["audio_id"] > int(self.single_save_data[2]):
                    # 新增相簿导致的重复判断
                    if audio_info["audio_id"] in unique_list:
                        continue
                    else:
                        audio_info_list.append(audio_info)
                        unique_list.append(audio_info["audio_id"])
                else:
                    is_over = True
                    break

            if not is_over:
                # 获取的音频数量少于1页的上限，表示已经到结束了
                # 如果音频数量正好是页数上限的倍数，则由下一页获取是否为空判断
                if len(album_pagination_response["audio_info_list"]) < EACH_PAGE_COUNT:
                    is_over = True
                else:
                    page_count += 1

        return audio_info_list

    # 获取所有可下载相簿
    def get_crawl_photo_list(self):
        page_count = 1
        unique_list = []
        album_id_list = []
        is_over = False
        while not is_over:
            album_pagination_description = f"第{page_count}页相簿"
            self.start_parse(album_pagination_description)
            try:
                album_pagination_response = get_one_page_album(self.index_key, page_count)
            except CrawlerException as e:
                self.error(e.http_error(album_pagination_description))
                raise
            self.parse_result(album_pagination_description, album_pagination_response["album_id_list"])

            # 寻找这一页符合条件的相簿
            for album_id in album_pagination_response["album_id_list"]:
                # 检查是否达到存档记录
                if album_id > int(self.single_save_data[3]):
                    # 新增相簿导致的重复判断
                    if album_id in unique_list:
                        continue
                    else:
                        album_id_list.append(album_id)
                        unique_list.append(album_id)
                else:
                    is_over = True
                    break

            if not is_over:
                # 获取的相册数量少于1页的上限，表示已经到结束了
                # 如果相册数量正好是页数上限的倍数，则由下一页获取是否为空判断
                if len(album_pagination_response["album_id_list"]) < EACH_PAGE_COUNT:
                    is_over = True
                else:
                    page_count += 1

        return album_id_list

    # 解析单个视频
    def crawl_video(self, video_info):
        video_description = f"视频{video_info['video_id']}《{video_info['video_title']}》"
        self.start_parse(video_description)
        try:
            video_play_response = get_video_page(video_info["video_id"])
        except CrawlerException as e:
            self.error(e.http_error(video_description))
            raise
        if video_play_response["is_private"]:
            log.error(f"{video_description} 需要登录才能访问，跳过")
            return
        self.parse_result(video_description, video_play_response["video_part_info_list"])

        video_index = 1
        video_part_index = 1
        for video_part_info in video_play_response["video_part_info_list"]:
            video_split_index = 1
            for video_part_url in video_part_info["video_url_list"]:
                video_name = "%010d %s" % (video_info["video_id"], video_info["video_title"])
                if len(video_play_response["video_part_info_list"]) > 1:
                    if video_part_info["video_part_title"]:
                        video_name += "_" + video_part_info["video_part_title"]
                    else:
                        video_name += "_" + str(video_part_index)
                if len(video_part_info["video_url_list"]) > 1:
                    video_name += f" ({video_split_index})"
                video_name = f"{video_name}.{url.get_file_ext(video_part_url)}"
                video_path = os.path.join(self.main_thread.video_download_path, self.display_name, video_name)
                part_video_description = f"视频{video_info['video_id']}《{video_info['video_title']}》第{video_index}个视频"
                headers = {"Referer": f"https://www.bilibili.com/video/av{video_info['video_id']}"}
                if self.download(video_part_url, video_path, part_video_description, headers=headers, auto_multipart_download=True, is_failure_exit=False):
                    self.temp_path_list.append(video_path)  # 设置临时目录
                    self.total_video_count += 1  # 计数累加
                else:
                    return False
                video_split_index += 1
                video_index += 1
            video_part_index += 1

        # 视频内所有分P全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.single_save_data[1] = str(video_info["video_time"])  # 设置存档记录
        return True

    # 解析单个相簿
    def crawl_audio(self, audio_info):
        audio_description = f"音频{audio_info['audio_id']}《{audio_info['audio_title']}》"
        self.start_parse(audio_description)
        try:
            audio_info_response = get_audio_info_page(audio_info["audio_id"])
        except CrawlerException as e:
            self.error(e.http_error(audio_description))
            raise

        audio_type = url.get_file_ext(audio_info_response["audio_url"])
        audio_name = f"%06d %s.{audio_type}" % (audio_info["audio_id"], audio_info["audio_title"])
        audio_path = os.path.join(self.main_thread.audio_download_path, self.display_name, audio_name)
        if self.download(audio_info_response["audio_url"], audio_path, audio_description, is_failure_exit=False, headers={"Referer": "https://www.bilibili.com/"}):
            self.total_audio_count += 1  # 计数累加
        else:
            return False

        # 音频下载完毕
        self.single_save_data[2] = str(audio_info["audio_id"])  # 设置存档记录
        return True

    # 解析单个相簿
    def crawl_photo(self, album_id):
        album_description = f"相簿{album_id}"
        self.start_parse(album_description)
        try:
            album_response = get_album_page(album_id)
        except CrawlerException as e:
            self.error(e.http_error(album_description))
            raise
        self.parse_result(album_description, album_response["photo_url_list"])

        photo_index = 1
        for photo_url in album_response["photo_url_list"]:
            photo_name = f"%09d_%02d.{url.get_file_ext(photo_url)}" % (album_id, photo_index)
            photo_path = os.path.join(self.main_thread.photo_download_path, self.display_name, photo_name)
            photo_description = f"相簿{album_id}第{photo_index}张图片"
            if self.download(photo_url, photo_path, photo_description, failure_callback=self.photo_download_failure_callback, is_failure_exit=False):
                self.temp_path_list.append(photo_path)  # 设置临时目录
                self.total_photo_count += 1  # 计数累加
            else:
                return False
            photo_index += 1

        # 相簿内图片全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.single_save_data[3] = str(album_id)  # 设置存档记录
        return True

    def photo_download_failure_callback(self, photo_url, photo_path, photo_description, download_return: net.Download):
        # 源文件禁止访问，增加后缀生成新的图片
        if download_return.code == 404:
            photo_url = photo_url + "@100000w.jpg"
            self.main_thread_check()
            download_return.update(net.Download(photo_url, photo_path))
            if download_return:
                self.info(f"{photo_description} 下载成功")
                return False
        return True

    def _run(self):
        # 视频下载
        if self.main_thread.is_download_video:
            # 获取所有可下载视频
            video_info_list = self.get_crawl_video_list()
            self.info(f"需要下载的全部视频解析完毕，共{len(video_info_list)}个")

            # 从最早的视频开始下载
            while len(video_info_list) > 0:
                if not self.crawl_video(video_info_list.pop()):
                    break

        # 音频下载
        if self.main_thread.is_download_audio:
            # 获取所有可下载音频
            audio_info_list = self.get_crawl_audio_list()
            self.info(f"需要下载的全部音频解析完毕，共{len(audio_info_list)}个")

            # 从最早的相簿开始下载
            while len(audio_info_list) > 0:
                if not self.crawl_audio(audio_info_list.pop()):
                    break

        # 图片下载
        if self.main_thread.is_download_photo:
            # 获取所有可下载相簿
            album_id_list = self.get_crawl_photo_list()
            self.info(f"需要下载的全部相簿解析完毕，共{len(album_id_list)}个")

            # 从最早的相簿开始下载
            while len(album_id_list) > 0:
                if not self.crawl_photo(album_id_list.pop()):
                    break


if __name__ == "__main__":
    BiliBili().main()
