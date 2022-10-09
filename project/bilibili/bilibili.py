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
from common import *

COOKIE_INFO = {}
IS_LOGIN = False
EACH_PAGE_COUNT = 30

string_table = "fZodR9XQDSUm21yCkr6zBqiveYah8bt4xsWpHnJE7jL5VG3guMTKNPAwcF"
id_index = [11, 10, 3, 8, 4, 6]
xor = 177451812
add = 8728348608


# av id转bv id
def av_id_2_bv_id(av_id):
    if isinstance(av_id, str) and av_id[:2].lower() == "av":
        av_id = av_id[2:]
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


# 检测是否已登录
def check_login():
    if not COOKIE_INFO:
        return False
    api_url = "https://api.bilibili.com/x/member/web/account"
    api_response = net.request(api_url, method="GET", cookies_list=COOKIE_INFO, json_decode=True)
    if api_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        return crawler.get_json_value(api_response.json_data, "data", "mid", type_check=int, default_value=0) != 0
    return False


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
        api_response = net.request(api_url, method="GET", fields=query_data, cookies_list=COOKIE_INFO, json_decode=True)
        try:
            video_info_list = crawler.get_json_value(api_response.json_data, "data", "media_list", type_check=list)
        except crawler.CrawlerException:
            if crawler.get_json_value(api_response.json_data, "data", "media_list", value_check=None) is None:
                video_info_list = []
            else:
                raise
        for video_info in video_info_list:
            result_video_info = {
                "video_id": None,  # 视频id
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
    # https://space.bilibili.com/ajax/member/getSubmitVideos?mid=116683&pagesize=30&tid=0&page=3&keyword=&order=pubdate
    api_url = "https://api.bilibili.com/x/space/arc/search"
    query_data = {
        "keyword": "",
        "mid": account_id,
        "order": "pubdate",
        "pn": page_count,
        "ps": EACH_PAGE_COUNT,
        "tid": "0",
    }
    api_response = net.request(api_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "video_info_list": [],  # 全部视频信息
    }
    if api_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(api_response.status))
    for video_info in crawler.get_json_value(api_response.json_data, "data", "list", "vlist", type_check=list):
        result_video_info = {
            "video_id": None,  # 视频id
            "video_title": "",  # 视频标题
            "video_time": "",  # 视频上传时间
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
    api_response = net.request(api_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "video_info_list": [],  # 全部视频信息
        "next_page_offset": None,  # 下一页指针
    }
    if api_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(api_response.status))
    if crawler.get_json_value(api_response.json_data, "msg", type_check=str) != "success":
        raise crawler.CrawlerException("返回信息'msg'字段取值不正确\n" + str(api_response.json_data))
    # 获取下一页指针
    result["next_page_offset"] = crawler.get_json_value(api_response.json_data, "data", "next_offset", type_check=str)
    for video_info in crawler.get_json_value(api_response.json_data, "data", "items", type_check=list):
        result_video_info = {
            "video_id": None,  # 视频id
            "video_url": None,  # 视频标题
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
    # https://api.vc.bilibili.com/link_draw/v1/doc/doc_list?uid=116683&page_num=1&page_size=30&biz=all
    api_url = "https://api.vc.bilibili.com/link_draw/v1/doc/doc_list"
    query_data = {
        "uid": account_id,
        "page_num": page_count - 1,
        "page_size": EACH_PAGE_COUNT,
        "biz": "all",
    }
    api_response = net.request(api_url, method="GET", fields=query_data, cookies_list=COOKIE_INFO, json_decode=True)
    result = {
        "album_id_list": [],  # 全部相簿id
    }
    if api_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(api_response.status))
    for album_info in crawler.get_json_value(api_response.json_data, "data", "items", type_check=list):
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
    api_response = net.request(api_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "audio_info_list": [],  # 全部视频信息
    }
    if api_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(api_response.status))
    # 没有任何音频
    audio_info_list = crawler.get_json_value(api_response.json_data, "data", "data")
    if audio_info_list is None:
        return result
    elif not isinstance(audio_info_list, list):
        raise crawler.CrawlerException("'data'字段类型不正确\n" + str(api_response.json_data))
    for audio_info in audio_info_list:
        result_audio_info = {
            "audio_id": None,  # 音频id
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
    video_play_url = "https://www.bilibili.com/video/av%s" % video_id
    video_play_response = net.request(video_play_url, method="GET", cookies_list=COOKIE_INFO)
    result = {
        "is_private": False,  # 是否需要登录
        "video_part_info_list": [],  # 全部视频地址
        "video_title": "",  # 视频标题
    }
    if video_play_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_play_response.status))
    video_play_response_content = video_play_response.data.decode(errors="ignore")
    script_json = tool.json_decode(tool.find_sub_string(video_play_response_content, "window.__INITIAL_STATE__=", ";(function()"))
    if script_json is None:
        raise crawler.CrawlerException("页面截取视频信息失败\n" + video_play_response_content)
    try:
        video_part_info_list = crawler.get_json_value(script_json, "videoData", "pages", type_check=list)
        # 获取视频标题
        result["video_title"] = crawler.get_json_value(script_json, "videoData", "title", type_check=str).strip()
    except crawler.CrawlerException:
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
            except crawler.CrawlerException:
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
        video_info_response = net.request(video_info_url, method="GET", fields=query_data, cookies_list=COOKIE_INFO, header_list={"Referer": "https://www.bilibili.com/video/av%s" % video_id}, json_decode=True)
        if video_info_response.status != net.HTTP_RETURN_CODE_SUCCEED:
            raise crawler.CrawlerException("视频信息，" + crawler.request_failre(video_info_response.status))
        try:
            video_info_list = crawler.get_json_value(video_info_response.json_data, "data", "durl", type_check=list)
        except crawler.CrawlerException:
            # https://www.bilibili.com/video/av116528/?p=2
            if crawler.get_json_value(video_info_response.json_data, "data", "message", default_value="", type_check=str) == "No video info.":
                continue
            # https://www.bilibili.com/video/av44067
            elif crawler.get_json_value(video_info_response.json_data, "message", default_value="", type_check=str) == "啥都木有":
                continue
            raise
        if IS_LOGIN:
            if max(crawler.get_json_value(video_info_response.json_data, "data", "accept_quality", type_check=list)) != crawler.get_json_value(video_info_response.json_data, "data", "quality", type_check=int):
                raise crawler.CrawlerException("返回的视频分辨率不是最高的\n" + str(video_info_response.json_data))
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
    api_response = net.request(api_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "photo_url_list": [],  # 全部图片地址
    }
    if api_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(api_response.status))
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
    api_response = net.request(api_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "audio_url": None,  # 音频地址
    }
    if api_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(api_response.status))
    result["audio_url"] = crawler.get_json_value(api_response.json_data, "data", "cdns", 0, type_check=str)
    return result


class BiliBili(crawler.Crawler):
    def __init__(self, **kwargs):
        global COOKIE_INFO

        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_DOWNLOAD_VIDEO: True,
            crawler.SYS_DOWNLOAD_AUDIO: True,
            crawler.SYS_GET_COOKIE: ("bilibili.com",),
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 设置全局变量，供子线程调用
        COOKIE_INFO = self.cookie_value

        # 解析存档文件
        # account_name  last_video_id  last_audio_id  last_album_id
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "0", "0", "0"])

        # 检测登录状态
        if self.is_download_video:
            global IS_LOGIN
            if check_login():
                IS_LOGIN = True
            else:
                while True:
                    input_str = input(tool.get_time() + " 没有检测到账号登录状态，可能无法解析需要登录才能查看的视频以及获取高分辨率，继续程序(C)ontinue？或者退出程序(E)xit？:")
                    input_str = input_str.lower()
                    if input_str in ["e", "exit"]:
                        tool.process_exit()
                    elif input_str in ["c", "continue"]:
                        break

        # 下载线程
        self.download_thread = Download


class Download(crawler.DownloadThread):
    def __init__(self, single_save_data, main_thread):
        self.index_key = single_save_data[0]  # account id
        if len(single_save_data) >= 5 and single_save_data[4]:
            self.display_name = single_save_data[4]
        else:
            self.display_name = single_save_data[0]
        crawler.DownloadThread.__init__(self, single_save_data, main_thread)

    def _run(self):
        # 视频下载
        if self.main_thread.is_download_video:
            # 获取所有可下载视频
            video_info_list = self.get_crawl_video_list()
            self.step("需要下载的全部视频解析完毕，共%s个" % len(video_info_list))

            # 从最早的视频开始下载
            while len(video_info_list) > 0:
                if not self.crawl_video(video_info_list.pop()):
                    break
                self.main_thread_check()  # 检测主线程运行状态

        # 音频下载
        if self.main_thread.is_download_audio:
            # 获取所有可下载音频
            audio_info_list = self.get_crawl_audio_list()
            self.step("需要下载的全部音频解析完毕，共%s个" % len(audio_info_list))

            # 从最早的相簿开始下载
            while len(audio_info_list) > 0:
                if not self.crawl_audio(audio_info_list.pop()):
                    break
                self.main_thread_check()  # 检测主线程运行状态

        # 图片下载
        if self.main_thread.is_download_photo:
            # 获取所有可下载相簿
            album_id_list = self.get_crawl_photo_list()
            self.step("需要下载的全部相簿解析完毕，共%s个" % len(album_id_list))

            # 从最早的相簿开始下载
            while len(album_id_list) > 0:
                if not self.crawl_photo(album_id_list.pop()):
                    break
                self.main_thread_check()  # 检测主线程运行状态

    # 获取所有可下载视频
    def get_crawl_video_list(self):
        page_count = 1
        unique_list = []
        video_info_list = []
        is_over = False
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析第%s页视频" % page_count)

            # 获取一页相簿
            try:
                album_pagination_response = get_one_page_video(self.index_key, page_count)
            except crawler.CrawlerException as e:
                self.error(e.http_error("第%s页视频" % page_count))
                raise

            self.trace("第%s页解析的全部视频：%s" % (page_count, album_pagination_response["video_info_list"]))
            self.step("第%s页解析获取%s个视频" % (page_count, len(album_pagination_response["video_info_list"])))

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
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析第%s页音频" % page_count)

            # 获取一页相簿
            try:
                album_pagination_response = get_one_page_audio(self.index_key, page_count)
            except crawler.CrawlerException as e:
                self.error(e.http_error("第%s页音频" % page_count))
                raise

            self.trace("第%s页解析的全部音频：%s" % (page_count, album_pagination_response["audio_info_list"]))
            self.step("第%s页解析获取%s个音频" % (page_count, len(album_pagination_response["audio_info_list"])))

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
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析第%s页相簿" % page_count)

            # 获取一页相簿
            try:
                album_pagination_response = get_one_page_album(self.index_key, page_count)
            except crawler.CrawlerException as e:
                self.error(e.http_error("第%s页相簿" % page_count))
                raise

            self.trace("第%s页解析的全部相簿：%s" % (page_count, album_pagination_response["album_id_list"]))
            self.step("第%s页解析获取%s个相簿" % (page_count, len(album_pagination_response["album_id_list"])))

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
        self.step("开始解析视频%s" % video_info["video_id"])

        # 获取相簿
        try:
            video_play_response = get_video_page(video_info["video_id"])
        except crawler.CrawlerException as e:
            self.error(e.http_error("视频%s《%s》" % (video_info["video_id"], video_info["video_title"])))
            raise

        if video_play_response["is_private"]:
            log.error("视频%s《%s》需要登录才能访问，跳过" % (video_info["video_id"], video_info["video_title"]))
            return

        self.trace("视频%s《%s》解析的全部视频：%s" % (video_info["video_id"], video_info["video_title"], video_play_response["video_part_info_list"]))
        self.step("视频%s《%s》解析获取%s段视频" % (video_info["video_id"], video_info["video_title"], len(video_play_response["video_part_info_list"])))

        video_index = 1
        video_part_index = 1
        for video_part_info in video_play_response["video_part_info_list"]:
            video_split_index = 1
            for video_part_url in video_part_info["video_url_list"]:
                self.main_thread_check()  # 检测主线程运行状态
                self.step("视频%s《%s》开始下载第%s个视频 %s" % (video_info["video_id"], video_info["video_title"], video_index, video_part_url))

                video_name = "%010d %s" % (video_info[""], video_info["video_title"])
                if len(video_play_response["video_part_info_list"]) > 1:
                    if video_part_info["video_part_title"]:
                        video_name += "_" + video_part_info["video_part_title"]
                    else:
                        video_name += "_" + str(video_part_index)
                if len(video_part_info["video_url_list"]) > 1:
                    video_name += " (%s)" % video_split_index
                video_name = "%s.%s" % (path.filter_text(video_name), net.get_file_extension(video_part_url))
                file_path = os.path.join(self.main_thread.video_download_path, self.display_name, video_name)
                download_return = net.Download(video_part_url, file_path, auto_multipart_download=True, header_list={"Referer": "https://www.bilibili.com/video/av%s" % video_info["video_id"]})
                if download_return.status == net.Download.DOWNLOAD_SUCCEED:
                    self.temp_path_list.append(file_path)  # 设置临时目录
                    self.total_video_count += 1  # 计数累加
                    self.step("视频%s《%s》第%s个视频下载成功" % (video_info["video_id"], video_info["video_title"], video_index))
                else:
                    self.error("视频%s《%s》第%s个视频 %s，下载失败，原因：%s" % (video_info["video_id"], video_info["video_title"], video_index, video_part_url, crawler.download_failre(download_return.code)))
                    if self.check_download_failure_exit(False):
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
        self.step("开始解析音频%s" % audio_info["audio_id"])

        # 获取音频信息
        try:
            audio_info_response = get_audio_info_page(audio_info["audio_id"])
        except crawler.CrawlerException as e:
            self.error(e.http_error("音频%s《%s》" % (audio_info["audio_id"], audio_info["audio_title"])))
            raise

        self.step("开始下载音频%s《%s》 %s" % (audio_info["audio_id"], audio_info["audio_title"], audio_info_response["audio_url"]))

        file_path = os.path.join(self.main_thread.audio_download_path, self.display_name, "%06d %s.%s" % (audio_info["audio_id"], path.filter_text(audio_info["audio_title"]), net.get_file_extension(audio_info_response["audio_url"])))
        download_return = net.Download(audio_info_response["audio_url"], file_path, header_list={"Referer": "https://www.bilibili.com/"})
        if download_return.status == net.Download.DOWNLOAD_SUCCEED:
            self.total_audio_count += 1  # 计数累加
            self.step("音频%s《%s》下载成功" % (audio_info["audio_id"], audio_info["audio_title"]))
        else:
            self.error("音频%s《%s》 %s，下载失败，原因：%s" % (audio_info["audio_id"], audio_info["audio_title"], audio_info_response["audio_url"], crawler.download_failre(download_return.code)))
            if self.check_download_failure_exit(False):
                return False

        # 音频下载完毕
        self.single_save_data[2] = str(audio_info["audio_id"])  # 设置存档记录
        return True

    # 解析单个相簿
    def crawl_photo(self, album_id):
        self.step("开始解析相簿%s" % album_id)

        # 获取相簿
        try:
            album_response = get_album_page(album_id)
        except crawler.CrawlerException as e:
            self.error(e.http_error("相簿%s" % album_id))
            raise

        self.trace("相簿%s解析的全部图片：%s" % (album_id, album_response["photo_url_list"]))
        self.step("相簿%s解析获取%s张图" % (album_id, len(album_response["photo_url_list"])))

        photo_index = 1
        for photo_url in album_response["photo_url_list"]:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("相簿%s开始下载第%s张图片 %s" % (album_id, photo_index, photo_url))

            file_path = os.path.join(self.main_thread.photo_download_path, self.display_name, "%09d_%02d.%s" % (album_id, photo_index, net.get_file_extension(photo_url)))
            download_return = net.Download(photo_url, file_path)
            if download_return.status == net.Download.DOWNLOAD_SUCCEED:
                self.temp_path_list.append(file_path)  # 设置临时目录
                self.total_photo_count += 1  # 计数累加
                self.step("相簿%s第%s张图片下载成功" % (album_id, photo_index))
            else:
                self.error("相簿%s第%s张图片 %s，下载失败，原因：%s" % (album_id, photo_index, photo_url, crawler.download_failre(download_return.code)))
                if self.check_download_failure_exit(False):
                    return False
            photo_index += 1

        # 相簿内图片全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.single_save_data[3] = str(album_id)  # 设置存档记录
        return True


if __name__ == "__main__":
    BiliBili().main()
