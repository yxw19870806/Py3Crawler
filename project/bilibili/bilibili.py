# -*- coding:UTF-8  -*-
"""
bilibili用户投稿视频/音频/相册爬虫
https://www.bilibili.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import time
import traceback
from common import *

IS_DOWNLOAD_CONTRIBUTION_VIDEO = True
IS_DOWNLOAD_SHORT_VIDEO = True
EACH_PAGE_COUNT = 30


# 检测是否已登录
def check_login():
    api_url = "https://account.bilibili.com/home/userInfo"
    api_response = net.http_request(api_url, method="GET", json_decode=True)
    if api_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        return crawler.get_json_value(api_response.json_data, "status", default_value=False, type_check=bool) is True
    return False


# 获取指定页数的全部视频
def get_one_page_video(account_id, page_count):
    # https://space.bilibili.com/ajax/member/getSubmitVideos?mid=116683&pagesize=30&tid=0&page=3&keyword=&order=pubdate
    api_url = "https://space.bilibili.com/ajax/member/getSubmitVideos"
    query_data = {
        "keyword": "",
        "mid": account_id,
        "order": "pubdate",
        "page": page_count,
        "pagesize": EACH_PAGE_COUNT,
        "tid": "0",
    }
    api_response = net.http_request(api_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "video_info_list": [],  # 全部视频信息
    }
    if api_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(api_response.status))
    for video_info in crawler.get_json_value(api_response.json_data, "data", "vlist", type_check=list):
        result_video_info = {
            "video_id": None,  # 视频id
            "video_title": "",  # 视频标题
        }
        # 获取视频id
        result_video_info["video_id"] = crawler.get_json_value(video_info, "aid", type_check=int)
        # 获取视频标题
        result_video_info["video_title"] = crawler.get_json_value(video_info, "title", type_check=str)
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
    api_response = net.http_request(api_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "video_info_list": [],  # 全部视频信息
        "next_page_offset": None,  # 下一页指针
    }
    if api_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(api_response.status))
    if crawler.get_json_value(api_response.json_data, "msg", type_check=str) != "success":
        raise crawler.CrawlerException("返回信息'msg'字段取值不正确\n%s" % api_response.json_data)
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
    api_response = net.http_request(api_url, method="GET", fields=query_data, json_decode=True)
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
    api_response = net.http_request(api_url, method="GET", fields=query_data, json_decode=True)
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
        raise crawler.CrawlerException("'data'字段类型不正确\n%s" % api_response.json_data)
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
    video_play_response = net.http_request(video_play_url, method="GET")
    result = {
        "video_part_info_list": [],  # 全部视频地址
    }
    if video_play_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_play_response.status))
    video_play_response_content = video_play_response.data.decode(errors="ignore")
    script_json = tool.json_decode(tool.find_sub_string(video_play_response_content, "window.__INITIAL_STATE__=", ";(function()"))
    if script_json is None:
        raise crawler.CrawlerException("页面截取视频信息失败\n%s" % video_play_response_content)
    # 分P https://www.bilibili.com/video/av33131459
    for video_part_info in crawler.get_json_value(script_json, "videoData", "pages", type_check=list):
        result_video_info = {
            "video_url_list": [],  # 视频地址
            "video_part_title": "",  # 视频分P标题
        }
        # https://api.bilibili.com/x/player/playurl?avid=149236&cid=246864&qn=112&otype=json
        video_info_url = "https://api.bilibili.com/x/player/playurl"
        query_data = {
            "avid": video_id,
            "cid": crawler.get_json_value(video_part_info, "cid", type_check=int),
            "qn": "112",  # 高清 1080P+: 112, 高清 1080P: 80, 高清 720P: 64, 清晰 480P: 32, 流畅 360P: 16
            "otype": "json",
        }
        video_info_response = net.http_request(video_info_url, method="GET", fields=query_data, json_decode=True)
        if video_info_response.status != net.HTTP_RETURN_CODE_SUCCEED:
            raise crawler.CrawlerException("视频信息，" + crawler.request_failre(video_info_response.status))
        try:
            video_info_list = crawler.get_json_value(video_info_response.json_data, "data", "durl", type_check=list)
        except crawler.CrawlerException:
            # https://www.bilibili.com/video/av116528/?p=2
            if crawler.get_json_value(video_info_response.json_data, "data", "message", default_value="", type_check=str) == "Novideoinfo.":
                continue
            raise
        # 获取视频地址
        for video_info in video_info_list:
            result_video_info["video_url_list"].append(crawler.get_json_value(video_info, "url", type_check=str))
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
    api_response = net.http_request(api_url, method="GET", fields=query_data, json_decode=True)
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
    api_response = net.http_request(api_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "audio_url": None,  # 音频地址
    }
    if api_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(api_response.status))
    result["audio_url"] = crawler.get_json_value(api_response.json_data, "data", "cdns", 0, type_check=str)
    return result


class BiliBili(crawler.Crawler):
    def __init__(self, **kwargs):
        global IS_DOWNLOAD_CONTRIBUTION_VIDEO
        global IS_DOWNLOAD_SHORT_VIDEO
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_DOWNLOAD_VIDEO: True,
            crawler.SYS_DOWNLOAD_AUDIO: True,
            crawler.SYS_APP_CONFIG: (
                ("IS_DOWNLOAD_CONTRIBUTION_VIDEO", True, crawler.CONFIG_ANALYSIS_MODE_BOOLEAN),
                ("IS_DOWNLOAD_SHORT_VIDEO", True, crawler.CONFIG_ANALYSIS_MODE_BOOLEAN),
            ),
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 设置全局变量，供子线程调用
        IS_DOWNLOAD_CONTRIBUTION_VIDEO = self.app_config["IS_DOWNLOAD_CONTRIBUTION_VIDEO"]
        IS_DOWNLOAD_SHORT_VIDEO = self.app_config["IS_DOWNLOAD_SHORT_VIDEO"]

        # 解析存档文件
        # account_name  last_video_id  last_short_video_id  last_audio_id  last_album_id
        self.account_list = crawler.read_save_data(self.save_data_path, 0, ["", "0", "0", "0", "0"])

    def main(self):
        # 循环下载每个id
        thread_list = []
        for account_id in sorted(self.account_list.keys()):
            # 提前结束
            if not self.is_running():
                break

            # 开始下载
            thread = Download(self.account_list[account_id], self)
            thread.start()
            thread_list.append(thread)

            time.sleep(1)

        # 等待子线程全部完成
        while len(thread_list) > 0:
            thread_list.pop().join()

        # 未完成的数据保存
        if len(self.account_list) > 0:
            file.write_file(tool.list_to_string(list(self.account_list.values())), self.temp_save_data_path)

        # 重新排序保存存档文件
        crawler.rewrite_save_file(self.temp_save_data_path, self.save_data_path)

        log.step("全部下载完毕，耗时%s秒，共计图片%s张，%s个视频，%s个音频" % (self.get_run_time(), self.total_photo_count, self.total_video_count, self.total_audio_count))


class Download(crawler.DownloadThread):
    def __init__(self, account_info, main_thread):
        crawler.DownloadThread.__init__(self, account_info, main_thread)
        self.account_id = self.account_info[0]
        if len(self.account_info) >= 6 and self.account_info[5]:
            self.display_name = self.account_info[5]
        else:
            self.display_name = self.account_info[0]
        self.step("开始")

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
                album_pagination_response = get_one_page_video(self.account_id, page_count)
            except crawler.CrawlerException as e:
                self.error("第%s页视频解析失败，原因：%s" % (page_count, e.message))
                raise

            self.trace("第%s页解析的全部视频：%s" % (page_count, album_pagination_response["video_info_list"]))
            self.step("第%s页解析获取%s个视频" % (page_count, len(album_pagination_response["video_info_list"])))

            # 寻找这一页符合条件的视频
            for video_info in album_pagination_response["video_info_list"]:
                # 检查是否达到存档记录
                if video_info["video_id"] > int(self.account_info[1]):
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

    # 获取所有可下载短视频
    def get_crawl_short_video_list(self):
        page_offset = 0
        video_info_list = []
        is_over = False
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析offset %s后一页视频" % page_offset)

            # 获取一页相簿
            try:
                album_pagination_response = get_one_page_short_video(self.account_id, page_offset)
            except crawler.CrawlerException as e:
                self.error("offset %s后一页视频解析失败，原因：%s" % (page_offset, e.message))
                raise

            self.trace("offset %s后一页解析的全部视频：%s" % (page_offset, album_pagination_response["video_info_list"]))
            self.step("offset %s后一页解析获取%s个视频" % (page_offset, len(album_pagination_response["video_info_list"])))

            # 寻找这一页符合条件的视频
            for video_info in album_pagination_response["video_info_list"]:
                # 检查是否达到存档记录
                if video_info["video_id"] > int(self.account_info[2]):
                    video_info_list.append(video_info)
                else:
                    is_over = True
                    break

            if not is_over:
                # 获取的视频数量等于0，表示已经到结束了
                if len(album_pagination_response["video_info_list"]) == 0:
                    is_over = True
                else:
                    page_offset = album_pagination_response["next_page_offset"]

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
                album_pagination_response = get_one_page_audio(self.account_id, page_count)
            except crawler.CrawlerException as e:
                self.error("第%s页音频解析失败，原因：%s" % (page_count, e.message))
                raise

            self.trace("第%s页解析的全部音频：%s" % (page_count, album_pagination_response["audio_info_list"]))
            self.step("第%s页解析获取%s个音频" % (page_count, len(album_pagination_response["audio_info_list"])))

            # 寻找这一页符合条件的音频
            for audio_info in album_pagination_response["audio_info_list"]:
                # 检查是否达到存档记录
                if audio_info["audio_id"] > int(self.account_info[3]):
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
                album_pagination_response = get_one_page_album(self.account_id, page_count)
            except crawler.CrawlerException as e:
                self.error("第%s页相簿解析失败，原因：%s" % (page_count, e.message))
                raise

            self.trace("第%s页解析的全部相簿：%s" % (page_count, album_pagination_response["album_id_list"]))
            self.step("第%s页解析获取%s个相簿" % (page_count, len(album_pagination_response["album_id_list"])))

            # 寻找这一页符合条件的相簿
            for album_id in album_pagination_response["album_id_list"]:
                # 检查是否达到存档记录
                if album_id > int(self.account_info[4]):
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
            self.error("视频%s《%s》解析失败，原因：%s" % (video_info["video_id"], video_info["video_title"], e.message))
            raise

        self.trace("视频%s《%s》解析的全部视频：%s" % (video_info["video_id"], video_info["video_title"], video_play_response["video_part_info_list"]))
        self.step("视频%s《%s》解析获取%s段视频" % (video_info["video_id"], video_info["video_title"], len(video_play_response["video_part_info_list"])))

        video_index = 1
        part_index = 1
        for video_part_info in video_play_response["video_part_info_list"]:
            video_part_index = 1
            for video_part_url in video_part_info["video_url_list"]:
                self.main_thread_check()  # 检测主线程运行状态
                self.step("视频%s《%s》开始下载第%s个视频 %s" % (video_info["video_id"], video_info["video_title"], video_index, video_part_url))

                video_name = "%08d %s" % (video_info["video_id"], video_info["video_title"])
                if len(video_play_response["video_part_info_list"]) > 1:
                    if video_part_info["video_part_title"]:
                        video_name += "_" + video_part_info["video_part_title"]
                    else:
                        video_name += "_" + str(part_index)
                if len(video_part_info["video_url_list"]) > 1:
                    video_name += " (%s)" % video_part_index
                video_name = path.filter_text(video_name)
                video_name = "%s.%s" % (video_name, net.get_file_type(video_part_url))
                file_path = os.path.join(self.main_thread.video_download_path, self.display_name, video_name)
                save_file_return = net.save_net_file(video_part_url, file_path, header_list={"Referer": "https://www.bilibili.com/video/av%s" % video_info["video_id"]})
                if save_file_return["status"] == 1:
                    self.step("视频%s《%s》第%s个视频下载成功" % (video_info["video_id"], video_info["video_title"], video_index))
                    # 设置临时目录
                    self.temp_path_list.append(file_path)
                else:
                    self.error("视频%s《%s》第%s个视频 %s，下载失败，原因：%s" % (video_info["video_id"], video_info["video_title"], video_index, video_part_url, crawler.download_failre(save_file_return["code"])))
                video_part_index += 1
                video_index += 1

        # 视频内所有分P全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.total_photo_count += video_index - 1  # 计数累加
        self.account_info[1] = str(video_info["video_id"])  # 设置存档记录

    # 解析单个短视频
    def crawl_short_video(self, video_info):
        self.step("开始下载短视频%s %s" % (video_info["video_id"], video_info["video_url"]))

        file_path = os.path.join(self.main_thread.video_download_path, self.display_name, "%07d.%s" % (video_info["video_id"], net.get_file_type(video_info["video_url"])))
        save_file_return = net.save_net_file(video_info["video_url"], file_path)
        if save_file_return["status"] == 1:
            self.step("短视频%s下载成功" % video_info["video_id"])
        else:
            self.error("短视频%s  %s，下载失败，原因：%s" % (video_info["video_id"], video_info["video_url"], crawler.download_failre(save_file_return["code"])))

        # 短视频下载完毕
        self.total_photo_count += 1  # 计数累加
        self.account_info[2] = str(video_info["video_id"])  # 设置存档记录

    # 解析单个相簿
    def crawl_audio(self, audio_info):
        self.step("开始解析音频%s" % audio_info["audio_id"])

        # 获取音频信息
        try:
            audio_info_response = get_audio_info_page(audio_info["audio_id"])
        except crawler.CrawlerException as e:
            self.error("音频%s《%s》解析失败，原因：%s" % (audio_info["audio_id"], audio_info["audio_title"], e.message))
            raise

        self.step("开始下载音频%s《%s》 %s" % (audio_info["audio_id"], audio_info["audio_title"], audio_info_response["audio_url"]))

        file_path = os.path.join(self.main_thread.video_download_path, self.display_name, "%06d %s.%s" % (audio_info["audio_id"], path.filter_text(audio_info["audio_title"]), net.get_file_type(audio_info_response["audio_url"])))
        save_file_return = net.save_net_file(audio_info_response["audio_url"], file_path)
        if save_file_return["status"] == 1:
            self.step("音频%s《%s》下载成功" % (audio_info["audio_id"], audio_info["audio_title"]))
        else:
            self.error("音频%s《%s》 %s，下载失败，原因：%s" % (audio_info["audio_id"], audio_info["audio_title"], audio_info_response["audio_url"], crawler.download_failre(save_file_return["code"])))

        # 音频下载完毕
        self.total_audio_count += 1  # 计数累加
        self.account_info[3] = str(audio_info["audio_id"])  # 设置存档记录

    # 解析单个相簿
    def crawl_photo(self, album_id):
        self.step("开始解析相簿%s" % album_id)

        # 获取相簿
        try:
            album_response = get_album_page(album_id)
        except crawler.CrawlerException as e:
            self.error("相簿%s解析失败，原因：%s" % (album_id, e.message))
            raise

        self.trace("相簿%s解析的全部图片：%s" % (album_id, album_response["photo_url_list"]))
        self.step("相簿%s解析获取%s张图" % (album_id, len(album_response["photo_url_list"])))

        photo_index = 1
        for photo_url in album_response["photo_url_list"]:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("相簿%s开始下载第%s张图片 %s" % (album_id, photo_index, photo_url))

            file_path = os.path.join(self.main_thread.photo_download_path, self.display_name, "%07d_%02d.%s" % (album_id, photo_index, net.get_file_type(photo_url)))
            save_file_return = net.save_net_file(photo_url, file_path)
            if save_file_return["status"] == 1:
                self.step("相簿%s第%s张图片下载成功" % (album_id, photo_index))
                # 设置临时目录
                self.temp_path_list.append(file_path)
            else:
                self.error("相簿%s第%s张图片 %s，下载失败，原因：%s" % (album_id, photo_index, photo_url, crawler.download_failre(save_file_return["code"])))
            photo_index += 1

        # 相簿内图片全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.total_photo_count += photo_index - 1  # 计数累加
        self.account_info[4] = str(album_id)  # 设置存档记录

    def run(self):
        try:
            # 视频下载
            if self.main_thread.is_download_video:
                if IS_DOWNLOAD_CONTRIBUTION_VIDEO:
                    # 获取所有可下载视频
                    video_info_list = self.get_crawl_video_list()
                    self.step("需要下载的全部视频解析完毕，共%s个" % len(video_info_list))

                    # 从最早的视频开始下载
                    while len(video_info_list) > 0:
                        self.crawl_video(video_info_list.pop())
                        self.main_thread_check()  # 检测主线程运行状态

                if IS_DOWNLOAD_SHORT_VIDEO:
                    # 获取所有可下载短视频
                    video_info_list = self.get_crawl_short_video_list()
                    self.step("需要下载的全部短视频解析完毕，共%s个" % len(video_info_list))

                    # 从最早的视频开始下载
                    while len(video_info_list) > 0:
                        self.crawl_short_video(video_info_list.pop())
                        self.main_thread_check()  # 检测主线程运行状态

            # 音频下载
            if self.main_thread.is_download_audio:
                # 获取所有可下载音频
                audio_info_list = self.get_crawl_audio_list()
                self.step("需要下载的全部音频解析完毕，共%s个" % len(audio_info_list))

                # 从最早的相簿开始下载
                while len(audio_info_list) > 0:
                    self.crawl_audio(audio_info_list.pop())
                    self.main_thread_check()  # 检测主线程运行状态

            # 图片下载
            if self.main_thread.is_download_photo:
                # 获取所有可下载相簿
                album_id_list = self.get_crawl_photo_list()
                self.step("需要下载的全部相簿解析完毕，共%s个" % len(album_id_list))

                # 从最早的相簿开始下载
                while len(album_id_list) > 0:
                    self.crawl_photo(album_id_list.pop())
                    self.main_thread_check()  # 检测主线程运行状态
        except SystemExit as se:
            if se.code == 0:
                self.step("提前退出")
            else:
                self.error("异常退出")
            # 如果临时目录变量不为空，表示某个视频/相簿正在下载中，需要把下载了部分的内容给清理掉
            self.clean_temp_path()
        except Exception as e:
            self.error("未知异常")
            self.error(str(e) + "\n" + traceback.format_exc(), False)

        # 保存最后的信息
        with self.thread_lock:
            file.write_file("\t".join(self.account_info), self.main_thread.temp_save_data_path)
            self.main_thread.total_photo_count += self.total_photo_count
            self.main_thread.account_list.pop(self.account_id)
        self.step("下载完毕，总共获得%s张图片，%s个视频，%s个音频" % (self.total_photo_count, self.total_video_count, self.total_audio_count))
        self.notify_main_thread()


if __name__ == "__main__":
    BiliBili().main()
