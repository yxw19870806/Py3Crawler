# -*- coding:UTF-8  -*-
"""
美拍视频爬虫
https://www.meipai.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import base64
import os
from functools import reduce
from pyquery import PyQuery as pq
from common import *

EACH_PAGE_VIDEO_COUNT = 20  # 每次请求获取的视频数量


# 获取指定页数的全部视频
def get_one_page_video(account_id, page_count):
    # https://www.meipai.com/users/user_timeline?uid=22744352&page=1&count=20&single_column=1
    video_pagination_url = "https://www.meipai.com/users/user_timeline"
    query_data = {
        "uid": account_id,
        "page": page_count,
        "count": EACH_PAGE_VIDEO_COUNT,
        "single_column": 1,
    }
    video_pagination_response = net.request(video_pagination_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "video_info_list": [],  # 全部视频信息
    }
    if video_pagination_response.status != const.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_pagination_response.status))
    for media_info in crawler.get_json_value(video_pagination_response.json_data, "medias", type_check=list):
        # 历史直播，跳过
        if crawler.check_sub_key(("lives",), media_info):
            continue
        result_video_info = {
            "video_id": 0,  # 视频id
            "video_url": "",  # 视频地址
        }
        # 获取视频id
        result_video_info["video_id"] = crawler.get_json_value(media_info, "id", type_check=int)
        # 获取视频下载地址
        encrypted_video_url = crawler.get_json_value(media_info, "video", type_check=str)
        video_url = decrypt_video_url(encrypted_video_url)
        if video_url is None:
            raise crawler.CrawlerException("加密视频地址 %s 解密失败" % encrypted_video_url)
        result_video_info["video_url"] = video_url
        result["video_info_list"].append(result_video_info)
    return result


# 获取指定视频播放页
def get_video_play_page(video_id):
    video_play_url = "https://www.meipai.com/media/%s" % video_id
    video_play_response = net.request(video_play_url, method="GET")
    result = {
        "is_delete": False,  # 是否已删除
        "video_url": "",  # 视频地址
    }
    if video_play_response.status == 404:
        result["is_delete"] = True
        return result
    elif video_play_response.status != const.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_play_response.status))
    video_play_response_content = video_play_response.data.decode(errors="ignore")
    video_url_crypt_string = pq(video_play_response_content).find("meta[property='og:video:url']").attr("content")
    if not video_url_crypt_string:
        if pq(video_play_response_content).find(".error-p").length == 1:
            error_message = pq(video_play_response_content).find(".error-p").text()
            if error_message == "为建设清朗网络空间，视频正在审核中，暂时无法播放。" or error_message == "可能已被删除或网址输入错误,请再核对下吧~":
                result["is_delete"] = True
                return result
        raise crawler.CrawlerException("页面截取加密视频地址失败\n" + video_play_response_content)
    video_url = decrypt_video_url(video_url_crypt_string)
    if not video_url:
        raise crawler.CrawlerException("加密视频地址 %s 解密失败" % video_url_crypt_string)
    result["video_url"] = video_url
    return result


# 视频地址解谜
# 破解于播放器swf文件中com.meitu.cryptography.meipai.Default.decode
def decrypt_video_url(encrypted_string):
    loc1 = _get_hex(encrypted_string)
    loc2 = _get_dec(loc1["hex"])
    loc3 = _sub_str(loc1["str"], loc2["pre"])
    encryption_video_url = _sub_str(loc3, _get_pos(loc3, loc2["tail"]))
    try:
        video_url = base64.b64decode(encryption_video_url).decode(errors="ignore")
    except TypeError:
        return None
    if video_url.find("http") != 0:
        return None
    return video_url


def _get_hex(arg1):
    return {"str": arg1[4:], "hex": reduce(lambda x, y: y + x, arg1[0:4])}


def _get_dec(arg1):
    loc1 = str(int(arg1, 16))
    return {"pre": [int(loc1[0]), int(loc1[1])], "tail": [int(loc1[2]), int(loc1[3])]}


def _sub_str(arg1, arg2):
    loc1 = arg1[:arg2[0]]
    loc2 = arg1[arg2[0]: arg2[0] + arg2[1]]
    return loc1 + arg1[arg2[0]:].replace(loc2, "", 1)


def _get_pos(arg1, arg2):
    arg2[0] = len(arg1) - arg2[0] - arg2[1]
    return arg2


class MeiPai(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            const.SysConfigKey.DOWNLOAD_VIDEO: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 解析存档文件
        # account_id  last_video_id
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

        # 下载线程
        self.crawler_thread = CrawlerThread


class CrawlerThread(crawler.CrawlerThread):
    def __init__(self, main_thread, single_save_data):
        self.index_key = single_save_data[0]  # account id
        if len(single_save_data) >= 3 and single_save_data[2]:
            self.display_name = single_save_data[2]
        else:
            self.display_name = single_save_data[0]
        crawler.CrawlerThread.__init__(self, main_thread, single_save_data)

    # 获取所有可下载视频
    def get_crawl_list(self):
        page_count = 1
        unique_list = []
        video_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的视频
        while not is_over:
            video_pagination_description = "第%s页视频" % page_count
            self.start_parse(video_pagination_description)
            try:
                video_pagination_response = get_one_page_video(self.index_key, page_count)
            except crawler.CrawlerException as e:
                self.error(e.http_error(video_pagination_description))
                raise
            self.parse_result(video_pagination_description, video_pagination_response["video_info_list"])

            # 寻找这一页符合条件的视频
            for video_info in video_pagination_response["video_info_list"]:
                # 检查是否达到存档记录
                if video_info["video_id"] > int(self.single_save_data[1]):
                    # 新增视频导致的重复判断
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
                if len(video_pagination_response["video_info_list"]) < EACH_PAGE_VIDEO_COUNT:
                    is_over = True
                else:
                    page_count += 1

        return video_info_list

    # 下载单个视频
    def crawl_video(self, video_info):
        video_path = os.path.join(self.main_thread.video_download_path, self.display_name, "%010d.mp4" % video_info["video_id"])
        video_description = "视频%s" % video_info["video_id"]
        if self.download(video_info["video_url"], video_path, video_description):
            self.total_video_count += 1  # 计数累加

        # 视频下载完毕
        self.single_save_data[1] = str(video_info["video_id"])  # 设置存档记录

    def _run(self):
        # 获取所有可下载视频
        video_info_list = self.get_crawl_list()
        self.info("需要下载的全部视频解析完毕，共%s个" % len(video_info_list))

        # 从最早的视频开始下载
        while len(video_info_list) > 0:
            self.crawl_video(video_info_list.pop())


if __name__ == "__main__":
    MeiPai().main()
