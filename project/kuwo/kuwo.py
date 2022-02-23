# -*- coding:UTF-8  -*-
"""
酷我音频爬虫
http://www.kuwo.cn/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import math
import os
from common import *

REQ_ID = "ed7a0d50-6889-11ec-a46a-3555ffbdcc91"
CSRF_TOKEN = "PYHB4QVEMDP"
EACH_PAGE_AUDIO_COUNT = 30


# 获取指定页数歌单的全部音频信息
def get_one_page_playlist(playlist_id, page_count):
    playlist_pagination_url = "http://www.kuwo.cn/api/www/playlist/playListInfo"
    query_data = {
        "pid": playlist_id,
        "pn": page_count,
        "rn": EACH_PAGE_AUDIO_COUNT,
        "httpsStatus": "1",
        "reqId": REQ_ID,
    }
    playlist_pagination_response = net.request(playlist_pagination_url, method="GET", fields=query_data, cookies_list={"kw_token": CSRF_TOKEN}, header_list={"csrf": CSRF_TOKEN}, json_decode=True)
    result = {
        "audio_info_list": [],  # 全部音频信息
        "is_over": False,  # 是否最后一页音频
    }
    if playlist_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(playlist_pagination_response.status))
    for audio_info in crawler.get_json_value(playlist_pagination_response.json_data, "data", "musicList", type_check=list):
        result_audio_info = {
            "audio_id": None,  # 音频id
            "audio_title": None,  # 音频标题
        }
        # 获取音频id
        result_audio_info["audio_id"] = crawler.get_json_value(audio_info, "rid")
        if not tool.is_integer(result_audio_info["audio_id"]):
            raise crawler.CrawlerException("获音频id失败\n" + audio_info)
        # 获取音频标题
        result_audio_info["audio_title"] = crawler.get_json_value(audio_info, "name")
        result["audio_info_list"].append(result_audio_info)
    # 判断是不是最后一页
    total_audio_count = crawler.get_json_value(playlist_pagination_response.json_data, "data", "total", type_check=int)
    result["is_over"] = page_count >= math.ceil(total_audio_count / EACH_PAGE_AUDIO_COUNT)
    return result


def get_audio_info_page(audio_id):
    audio_info_url = "https://www.kuwo.cn/api/v1/www/music/playUrl"
    query_data = {
        "mid": audio_id,
        "type": "music",
        "httpsStatus": "1",
        "reqId": REQ_ID,
    }
    audio_info_response = net.request(audio_info_url, method="GET", fields=query_data, cookies_list={"kw_token": CSRF_TOKEN}, header_list={"csrf": CSRF_TOKEN}, json_decode=True)
    result = {
        "audio_url": None,  # 音频地址
    }
    if audio_info_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(audio_info_response.status))
    # 获取音频地址
    try:
        result["audio_url"] = crawler.get_json_value(audio_info_response.json_data, "data", "url")
    except crawler.CrawlerException:
        if crawler.get_json_value(audio_info_response.json_data, "code", type_check=int, default_value=0) == -1:
            if error_message := crawler.get_json_value(audio_info_response.json_data, "msg", type_check=str, default_value=""):
                raise crawler.CrawlerException(error_message)
        raise
    return result


class KuWo(crawler.Crawler):
    def __init__(self, sys_config=None, **kwargs):
        if sys_config is None:
            sys_config = {}
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        default_sys_config = {
            crawler.SYS_NOT_CHECK_SAVE_DATA: True,
            crawler.SYS_DOWNLOAD_AUDIO: True,
        }
        default_sys_config.update(sys_config)
        crawler.Crawler.__init__(self, sys_config, **kwargs)

    def main(self):
        pass
