# -*- coding:UTF-8  -*-
"""
喜马拉雅
https://www.ximalaya.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import execjs
import math
import os
import random
import time
from common import *
from common import browser
from selenium.webdriver.common.by import By

COOKIES = {}
EACH_PAGE_AUDIO_COUNT = 30  # 每次请求获取的视频数量
IS_LOGIN = False
IS_VIP = False
TEMPLATE_HTML_PATH = os.path.join(os.path.dirname(__file__), "html/template.html")


def get_sign():
    chrome_options_argument = ["user-agent=" + net.DEFAULT_USER_AGENT]
    with browser.Chrome("file:///" + os.path.realpath(TEMPLATE_HTML_PATH), add_argument=chrome_options_argument) as chrome:
        for i in range(30):
            session_id = chrome.find_element(by=By.ID, value="result_SessionId").text
            browser_id = chrome.find_element(by=By.ID, value="result_BrowserId").text
            if session_id and browser_id:
                break
            else:
                time.sleep(1)
    return f"{browser_id}&&{session_id}" if session_id and browser_id else None

# 判断是否已登录
def check_login():
    if not COOKIES:
        return False
    api_url = "https://www.ximalaya.com/revision/main/getCurrentUser"
    api_response = net.Request(api_url, method="GET", cookies=COOKIES).enable_json_decode()
    if api_response.status == const.ResponseCode.SUCCEED:
        global IS_VIP
        IS_VIP = crawler.get_json_value(api_response.json_data, "data", "isVip", type_check=bool)
        return crawler.get_json_value(api_response.json_data, "ret", type_check=int, default_value=0) == 200
    return False


# 获取指定页数的全部音频信息
def get_one_page_album(album_id, page_count):
    album_pagination_url = "https://www.ximalaya.com/revision/album/v1/getTracksList"
    query_data = {
        "albumId": album_id,
        "pageNum": page_count,
        "pageSize": 30,
        "sort": "1",
    }
    headers = {
        "Xm-sign": get_sign(),
        "Referer": f"https://www.ximalaya.com/youshengshu/{album_id}/p{page_count}",
        "Host": "www.ximalaya.com",
    }
    album_pagination_response = net.Request(album_pagination_url, method="GET", fields=query_data, cookies=COOKIES, headers=headers).enable_json_decode()
    result = {
        "audio_info_list": [],  # 全部音频信息
        "is_over": False,  # 是否最后一页音频
    }
    if album_pagination_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(album_pagination_response.status))
    if crawler.get_json_value(album_pagination_response.json_data, "data", "riskLevel", type_check=int, default_value=0) > 0:
        raise CrawlerException("加密参数丢失")
    # 获取音频信息
    try:
        audio_info_list = crawler.get_json_value(album_pagination_response.json_data, "data", "tracks", type_check=list)
    except CrawlerException:
        error_message = crawler.get_json_value(album_pagination_response.json_data, "msg", type_check=str, default_value="")
        if error_message == f"该专辑[id:{album_id}]已被删除~" or error_message == f"该专辑[id:{album_id}]已下架~":
            raise CrawlerException("专辑已被删除")
        elif error_message == "该专辑不存在~" and page_count > 1:
            time.sleep(3)
            return get_one_page_album(album_id, page_count)
        else:
            raise
    for audio_info in audio_info_list:
        result_audio_info = {
            "audio_id": 0,  # 音频id
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
    result["is_over"] = page_count >= math.ceil(total_audio_count / real_page_size) if real_page_size > 0 else True
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
    headers = {
        "xm-sign": get_sign(),
    }
    audit_pagination_response = net.Request(audio_pagination_url, method="GET", fields=query_data, headers=headers).enable_json_decode()
    result = {
        "audio_info_list": [],  # 全部音频信息
        "is_over": False,  # 是否最后一页音频
    }
    if audit_pagination_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(audit_pagination_response.status))
    # 获取音频信息
    for audio_info in crawler.get_json_value(audit_pagination_response.json_data, "data", "trackList", type_check=list):
        result_audio_info = {
            "audio_id": 0,  # 音频id
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
    global COOKIES
    result = {
        "audio_title": "",  # 音频标题
        "audio_url": "",  # 音频地址
        "is_delete": False,  # 是否已删除
        "is_video": False,  # 是否是视频
    }

    audio_info_url = f"https://www.ximalaya.com/mobile-playpage/track/v3/baseInfo/{int(time.time() * 1000)}"
    query_data = {
        "device": "www2",
        "trackId": audio_id,
        "trackQualityLevel": 1,
    }
    audio_info_response = net.Request(audio_info_url, method="GET", fields=query_data, cookies=COOKIES).enable_json_decode()
    if audio_info_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(audio_info_response.status))

    # 加密后的音频地址
    try:
        result["is_video"] = crawler.get_json_value(audio_info_response.json_data, "trackInfo", "isVideo", type_check=bool)
        if result["is_video"]:
            return result
        # 获取音频标题
        result["audio_title"] = crawler.get_json_value(audio_info_response.json_data, "trackInfo", "title", type_check=str)

        decrypt_url = crawler.get_json_value(audio_info_response.json_data, "trackInfo", "playUrlList", 0, "url", type_check=str)
    except CrawlerException:
        return_code = crawler.get_json_value(audio_info_response.json_data, "ret", type_check=int, default_value=0)
        error_message = crawler.get_json_value(audio_info_response.json_data, "msg", type_check=str, default_value="")
        # API请求限制
        if return_code == 1001 and error_message == "系统繁忙，请稍后再试!":
            log.info("达到请求限制，等待后重试")
            time.sleep(600)
            return get_audio_info_page(audio_id)

        is_free = crawler.get_json_value(audio_info_response.json_data, "trackInfo", "isFree", type_check=int)
        if not is_free and not IS_VIP:
            raise CrawlerException("非免费音频")
        raise

    # 使用喜马拉雅的加密JS方法解密url地址
    js_code = file.read_file(os.path.join(crawler.PROJECT_APP_PATH, "js", "aes.js"))
    js_code += file.read_file(os.path.join(crawler.PROJECT_APP_PATH, "js", "mode-ecb.js"))
    js_code += """
    function encrypt_url(encrypt_url) {
        return CryptoJS.AES.decrypt(
            {
                ciphertext: CryptoJS.enc.Base64.parse(encrypt_url)
            },
            CryptoJS.enc.Hex.parse("aaad3e4fd540b0f79dca95606e72bf93"),
            {
                mode: CryptoJS.mode.ECB,
                padding: CryptoJS.pad.Pkcs7
            }
        ).toString(CryptoJS.enc.Utf8);
    }
    """
    try:
        audio_url = execjs.compile(js_code).call("encrypt_url", decrypt_url)
    except execjs.ProgramError:
        raise CrawlerException(f"url {decrypt_url}解密失败")
    result["audio_url"] = audio_url

    return result


class XiMaLaYa(crawler.Crawler):
    def __init__(self, sys_config=None, **kwargs):
        if sys_config is None:
            sys_config = {}
        global COOKIES, USER_AGENT
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        default_sys_config = {
            const.SysConfigKey.NOT_CHECK_SAVE_DATA: True,
            const.SysConfigKey.DOWNLOAD_AUDIO: True,
            const.SysConfigKey.GET_COOKIE: ("ximalaya.com",),
            const.SysConfigKey.APP_CONFIG: (
                ("USER_AGENT", "", const.ConfigAnalysisMode.RAW),
            ),
        }
        default_sys_config.update(sys_config)
        crawler.Crawler.__init__(self, default_sys_config, **kwargs)

        # 设置全局变量，供子线程调用
        COOKIES = self.cookie_value
        net.DEFAULT_USER_AGENT = self.app_config["USER_AGENT"]

    def init(self):
        global COOKIES, IS_LOGIN

        # 检测登录状态
        if check_login():
            IS_LOGIN = True
            return

        while True:
            input_str = input(tool.convert_timestamp_to_formatted_time() + " 没有检测到账号登录状态，可能无法解析需要登录才能查看的音频，继续程序(C)ontinue？或者退出程序(E)xit？:")
            input_str = input_str.lower()
            if input_str in ["e", "exit"]:
                tool.process_exit()
            elif input_str in ["c", "continue"]:
                COOKIES = {}
                break
