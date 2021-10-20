# -*- coding:UTF-8  -*-
"""
喜马拉雅
https://www.ximalaya.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import math
import random
import time
from common import *

EACH_PAGE_AUDIO_COUNT = 30  # 每次请求获取的视频数量


# 获取指定页数的全部音频信息
def get_one_page_album(album_id, page_count):
    album_pagination_url = "https://www.ximalaya.com/revision/album/v1/getTracksList"
    query_data = {
        "albumId": album_id,
        "pageNum": page_count,
        "sort": "1",
    }
    album_pagination_response = net.http_request(album_pagination_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "audio_info_list": [],  # 全部音频信息
        "is_over": False,  # 是否最后一页音频
    }
    if album_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_pagination_response.status))
    # 获取音频信息
    for audio_info in crawler.get_json_value(album_pagination_response.json_data, "data", "tracks", type_check=list):
        result_audio_info = {
            "audio_id": None,  # 音频id
            "audio_title": "",  # 音频标题
        }
        # 获取音频id
        result_audio_info["audio_id"] = crawler.get_json_value(audio_info, "trackId", type_check=int)
        # 获取音频标题
        result_audio_info["audio_title"] = crawler.get_json_value(audio_info, "title", type_check=str).strip()
        result["audio_info_list"].append(result_audio_info)
    # 判断是不是最后一页
    total_audio_count = crawler.get_json_value(album_pagination_response.json_data, "data", "trackTotalCount", type_check=int)
    real_page_size = crawler.get_json_value(album_pagination_response.json_data, "data", "pageSize", type_check=int)
    result["is_over"] = page_count >= math.ceil(total_audio_count / real_page_size)
    return result


# 获取指定页数的全部音频信息
def get_one_page_audio(account_id, page_count):
    # https://www.ximalaya.com/zhubo/1014267/sound/
    audio_pagination_url = "https://www.ximalaya.com/revision/user/track"
    query_data = {
        "page": page_count,
        "pageSize": EACH_PAGE_AUDIO_COUNT,
        "keyWord": "",
        "uid": account_id,
        "orderType": "2",  # 降序
    }
    now = int(time.time() * 1000)
    # 加密方法解析来自 https://s1.xmcdn.com/yx/ximalaya-web-static/last/dist/scripts/b20b549ee.js
    header_list = {
        "xm-sign": "%s(%s)%s(%s)%s" % (tool.string_md5("himalaya-" + str(now)), random.randint(1, 100), now, random.randint(1, 100), now + random.randint(1, 100 * 60))
    }
    audit_pagination_response = net.http_request(audio_pagination_url, method="GET", fields=query_data, header_list=header_list, json_decode=True)
    result = {
        "audio_info_list": [],  # 全部音频信息
        "is_over": False,  # 是否最后一页音频
    }
    if audit_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(audit_pagination_response.status))
    # 获取音频信息
    for audio_info in crawler.get_json_value(audit_pagination_response.json_data, "data", "trackList", type_check=list):
        result_audio_info = {
            "audio_id": None,  # 音频id
            "audio_title": "",  # 音频标题
        }
        # 获取音频id
        result_audio_info["audio_id"] = crawler.get_json_value(audio_info, "trackId", type_check=int)
        # 获取音频标题
        result_audio_info["audio_title"] = crawler.get_json_value(audio_info, "title", type_check=str).strip()
        result["audio_info_list"].append(result_audio_info)
    # 判断是不是最后一页
    total_audio_count = crawler.get_json_value(audit_pagination_response.json_data, "data", "maxCount", type_check=int)
    real_page_size = crawler.get_json_value(audit_pagination_response.json_data, "data", "pageSize", type_check=int)
    result["is_over"] = page_count >= math.ceil(total_audio_count / real_page_size)
    return result


# 获取指定id的音频播放页
# audio_id -> 16558983
def get_audio_info_page(audio_id):
    result = {
        "audio_title": "",  # 音频标题
        "audio_url": None,  # 音频地址
        "is_delete": False,  # 是否已删除
    }
    audio_simple_info_url = "https://www.ximalaya.com/revision/track/simple"
    query_data = {
        "trackId": audio_id,
    }
    audio_simple_info_response = net.http_request(audio_simple_info_url, fields=query_data, method="GET", json_decode=True)
    if audio_simple_info_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException("音频简易信息 " + crawler.request_failre(audio_simple_info_response.status))
    if crawler.get_json_value(audio_simple_info_response.json_data, "ret", type_check=int) == 200:
        pass
    elif crawler.get_json_value(audio_simple_info_response.json_data, "ret", type_check=int) == 404:
        result["is_delete"] = True
        return result
    else:
        raise crawler.CrawlerException("音频简易信息 ret返回值不正确\n%s" % audio_simple_info_response.json_data)
    # 获取音频标题
    result["audio_title"] = crawler.get_json_value(audio_simple_info_response.json_data, "data", "trackInfo", "title", type_check=str)

    audio_info_url = "https://www.ximalaya.com/revision/play/v1/audio"
    query_data = {
        "id": audio_id,
        "ptype": 1,
    }
    audio_info_response = net.http_request(audio_info_url, fields=query_data, method="GET", json_decode=True)
    if audio_info_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException("音频详细信息" + crawler.request_failre(audio_info_response.status))
    # 获取音频地址
    result["audio_url"] = crawler.get_json_value(audio_info_response.json_data, "data", "src", type_check=str)
    return result
