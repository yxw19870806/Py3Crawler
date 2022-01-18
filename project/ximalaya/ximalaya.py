# -*- coding:UTF-8  -*-
"""
喜马拉雅
https://www.ximalaya.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import math
import os
import random
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from common import *

COOKIE_INFO = {}
EACH_PAGE_AUDIO_COUNT = 30  # 每次请求获取的视频数量
CACHE_FILE_PATH = os.path.join(os.path.dirname(__file__), "cache")
TEMPLATE_HTML_PATH = os.path.join(os.path.dirname(__file__), "template", "template.html")


# 判断是否已登录
def check_login():
    if not COOKIE_INFO:
        return False
    api_url = "https://www.ximalaya.com/revision/main/getCurrentUser"
    api_response = net.http_request(api_url, method="GET", cookies_list=COOKIE_INFO, json_decode=True)
    if api_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        return crawler.get_json_value(api_response.json_data, "ret", type_check=int, default_value=0) == 200
    return False


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
        "is_video": False,  # 是否是视频
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
    # 判断是否是视频
    result["is_video"] = crawler.get_json_value(audio_simple_info_response.json_data, "data", "trackInfo", "isVideo", type_check=bool)
    if result["is_video"]:
        return result

    audio_info_url = "https://www.ximalaya.com/revision/play/v1/audio"
    query_data = {
        "id": audio_id,
        "ptype": 1,
    }
    audio_info_response = net.http_request(audio_info_url, fields=query_data, method="GET", json_decode=True)
    if audio_info_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException("音频详细信息" + crawler.request_failre(audio_info_response.status))
    # 获取音频地址
    try:
        result["audio_url"] = crawler.get_json_value(audio_info_response.json_data, "data", "src", type_check=str)
        return result
    except:
        crawler.get_json_value(audio_info_response.json_data, "data", "hasBuy", type_check=bool, value_check=True)

    # 需要购买或者vip才能解锁的音频
    vip_audio_info_url = "https://mobile.ximalaya.com/mobile-playpage/track/v3/baseInfo/1642399208220"
    query_data = {
        "device": "web",
        "trackId": audio_id,
    }
    vip_audio_info_response = net.http_request(vip_audio_info_url, fields=query_data, method="GET", json_decode=True)
    if vip_audio_info_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException("vip音频详细信息" + crawler.request_failre(vip_audio_info_response.status))
    decrypt_url = crawler.get_json_value(vip_audio_info_response.json_data, "trackInfo", "playUrlList", 0, "url", type_check=str)
    # 读取模板并替换相关参数
    template_html = file.read_file(TEMPLATE_HTML_PATH)
    template_html = template_html.replace("%%URL%%", decrypt_url)
    cache_html_path = os.path.realpath(os.path.join(CACHE_FILE_PATH, "%s.html" % audio_id))
    file.write_file(template_html, cache_html_path, file.WRITE_FILE_TYPE_REPLACE)
    # 使用喜马拉雅的加密JS方法解密url地址
    chrome_options = webdriver.ChromeOptions()
    chrome_options.headless = True  # 不打开浏览器
    chrome = webdriver.Chrome(executable_path=crawler.CHROME_WEBDRIVER_PATH, options=chrome_options)
    chrome.get("file:///" + cache_html_path)
    audio_url = chrome.find_element(by=By.ID, value="result").get_attribute('value')
    chrome.quit()
    path.delete_dir_or_file(cache_html_path)
    if not audio_url:
        raise crawler.CrawlerException("url解密失败\n%s" % decrypt_url)
    result["audio_url"] = audio_url
    return result


class XiMaLaYa(crawler.Crawler):
    def __init__(self, sys_config, **kwargs):
        global COOKIE_INFO, IS_LOGIN
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        default_sys_config = {
            crawler.SYS_NOT_CHECK_SAVE_DATA: True,
            crawler.SYS_DOWNLOAD_AUDIO: True,
            crawler.SYS_GET_COOKIE: ("ximalaya.com",),
        }
        default_sys_config.update(sys_config)
        crawler.Crawler.__init__(self, default_sys_config, **kwargs)

        # 设置全局变量，供子线程调用
        COOKIE_INFO = self.cookie_value

        # 检测登录状态
        if check_login():
            IS_LOGIN = True
        else:
            while True:
                input_str = input(crawler.get_time() + " 没有检测到账号登录状态，可能无法解析需要登录才能查看的音频，继续程序(C)ontinue？或者退出程序(E)xit？:")
                input_str = input_str.lower()
                if input_str in ["e", "exit"]:
                    tool.process_exit()
                elif input_str in ["c", "continue"]:
                    break

    def main(self):
        pass
