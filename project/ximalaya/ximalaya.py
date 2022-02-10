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
from selenium.webdriver.common.by import By
from common import *
from common import browser

COOKIE_INFO = {}
MAX_DAILY_VIP_DOWNLOAD_COUNT = 550
DAILY_VIP_DOWNLOAD_COUNT_CACHE_FILE = ''
DAILY_VIP_DOWNLOAD_COUNT = {}
EACH_PAGE_AUDIO_COUNT = 30  # 每次请求获取的视频数量
CACHE_FILE_PATH = os.path.join(os.path.dirname(__file__), "cache")
TEMPLATE_HTML_PATH = os.path.join(os.path.dirname(__file__), "template", "template.html")


# 判断是否已登录
def check_login():
    if not COOKIE_INFO:
        return False
    api_url = "https://www.ximalaya.com/revision/main/getCurrentUser"
    api_response = net.request(api_url, method="GET", cookies_list=COOKIE_INFO, json_decode=True)
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
    album_pagination_response = net.request(album_pagination_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "audio_info_list": [],  # 全部音频信息
        "is_over": False,  # 是否最后一页音频
    }
    if album_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_pagination_response.status))
    # 获取音频信息
    try:
        audio_info_list = crawler.get_json_value(album_pagination_response.json_data, "data", "tracks", type_check=list)
    except crawler.CrawlerException:
        error_message = crawler.get_json_value(album_pagination_response.json_data, "msg", type_check=str, default_value="")
        if error_message == f"该专辑[id:{album_id}]已被删除~" or error_message == f"该专辑[id:{album_id}]已下架~":
            raise crawler.CrawlerException("专辑已被删除")
        else:
            raise
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
        "xm-sign": f"{tool.string_md5('himalaya-' + str(now))}({random.randint(1, 100)}){now}({random.randint(1, 100)}){now + random.randint(1, 100 * 60)}"
    }
    audit_pagination_response = net.request(audio_pagination_url, method="GET", fields=query_data, header_list=header_list, json_decode=True)
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
    global COOKIE_INFO
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
    audio_simple_info_response = net.request(audio_simple_info_url, method="GET", fields=query_data, json_decode=True)
    if audio_simple_info_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException("音频简易信息 " + crawler.request_failre(audio_simple_info_response.status))
    if crawler.get_json_value(audio_simple_info_response.json_data, "ret", type_check=int) == 200:
        pass
    elif crawler.get_json_value(audio_simple_info_response.json_data, "ret", type_check=int) == 404:
        result["is_delete"] = True
        return result
    else:
        raise crawler.CrawlerException(f"音频简易信息{audio_simple_info_response.json_data}中'ret'返回值不正确")
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
    audio_info_response = net.request(audio_info_url, method="GET", fields=query_data, json_decode=True)
    if audio_info_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException("音频详细信息" + crawler.request_failre(audio_info_response.status))
    # 获取音频地址
    try:
        result["audio_url"] = crawler.get_json_value(audio_info_response.json_data, "data", "src", type_check=str)
        return result
    except:
        crawler.get_json_value(audio_info_response.json_data, "data", "hasBuy", type_check=bool)

    if not COOKIE_INFO:
        raise crawler.CrawlerException("非免费音频")

    day = crawler.get_time("%Y-%m-%d")
    if day not in DAILY_VIP_DOWNLOAD_COUNT:
        DAILY_VIP_DOWNLOAD_COUNT[day] = 0
    if DAILY_VIP_DOWNLOAD_COUNT[day] >= MAX_DAILY_VIP_DOWNLOAD_COUNT:
        raise crawler.CrawlerException("当日免费下载次数已达到限制")

    # 需要购买或者vip才能解锁的音频
    vip_audio_info_url = f"https://mobile.ximalaya.com/mobile-playpage/track/v3/baseInfo/{int(time.time() * 1000)}"
    query_data = {
        "device": "web",
        "trackId": audio_id,
    }
    vip_audio_info_response = net.request(vip_audio_info_url, method="GET", fields=query_data, cookies_list=COOKIE_INFO, json_decode=True)
    if vip_audio_info_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException("vip音频详细信息" + crawler.request_failre(vip_audio_info_response.status))
    try:
        decrypt_url = crawler.get_json_value(vip_audio_info_response.json_data, "trackInfo", "playUrlList", 0, "url", type_check=str)
    except crawler.CrawlerException:
        # 达到每日限制
        if crawler.get_json_value(vip_audio_info_response.json_data, "ret", type_check=int, value_check=999, default_value=0) and \
                crawler.get_json_value(vip_audio_info_response.json_data, "msg", type_check=str, value_check="今天操作太频繁啦，可以明天再试试哦~", default_value=""):
            # 清除cookies
            COOKIE_INFO = {}
            raise crawler.CrawlerException("达到vip每日限制")
        raise

    # 保存每日vip下载计数
    DAILY_VIP_DOWNLOAD_COUNT[day] += 1
    file.write_file(tool.json_encode(DAILY_VIP_DOWNLOAD_COUNT), DAILY_VIP_DOWNLOAD_COUNT_CACHE_FILE, file.WRITE_FILE_TYPE_REPLACE)

    # # 读取模板并替换相关参数
    # template_html = file.read_file(TEMPLATE_HTML_PATH)
    # template_html = template_html.replace("%%URL%%", decrypt_url)
    # cache_html_path = os.path.join(CACHE_FILE_PATH, f"{audio_id}.html")
    # file.write_file(template_html, cache_html_path, file.WRITE_FILE_TYPE_REPLACE)
    # # 使用喜马拉雅的加密JS方法解密url地址
    # with browser.Chrome("file:///" + os.path.realpath(cache_html_path)) as chrome:
    #     audio_url = chrome.find_element(by=By.ID, value="result").get_attribute('value')
    # # 删除临时模板文件
    # path.delete_dir_or_file(cache_html_path)
    # if not audio_url:
    #     raise crawler.CrawlerException(f"url{decrypt_url}解密失败")

    # 使用喜马拉雅的加密JS方法解密url地址
    js_code = file.read_file(os.path.join("template", "aes.js")) + "\n" + file.read_file(os.path.join("template", "mode-ecb.js")) + "\n"
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
    except execjs._exceptions.ProgramError:
        raise crawler.CrawlerException(f"url{decrypt_url}解密失败")
    result["audio_url"] = audio_url

    return result


class XiMaLaYa(crawler.Crawler):
    def __init__(self, sys_config=None, **kwargs):
        if sys_config is None:
            sys_config = {}
        global COOKIE_INFO, DAILY_VIP_DOWNLOAD_COUNT, DAILY_VIP_DOWNLOAD_COUNT_CACHE_FILE, CACHE_FILE_PATH, IS_LOGIN
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

        DAILY_VIP_DOWNLOAD_COUNT_CACHE_FILE = os.path.join(self.cache_data_path, "daily_vip_count.data")
        DAILY_VIP_DOWNLOAD_COUNT = tool.json_decode(file.read_file(DAILY_VIP_DOWNLOAD_COUNT_CACHE_FILE))
        if not isinstance(DAILY_VIP_DOWNLOAD_COUNT, dict):
            DAILY_VIP_DOWNLOAD_COUNT = {}

        # 临时文件目录
        CACHE_FILE_PATH = self.cache_data_path

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
                    COOKIE_INFO = {}
                    break

    def main(self):
        pass
