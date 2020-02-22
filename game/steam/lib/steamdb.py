# -*- coding:UTF-8  -*-
"""
steamdb相关数据解析爬虫
https://steamdb.info/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from pyquery import PyQuery as pq
from common import *

COOKIE_INFO = {}


def get_game_store_index(game_id):
    game_index_url = "https://steamdb.info/app/%s/" % game_id
    header_list = {
        # "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36",
        "Referer": "https://steamdb.info/",
    }
    if "User-Agent" not in header_list:
        raise crawler.CrawlerException("header没有携带User-Agent")
    game_index_response = net.http_request(game_index_url, method="GET", header_list=header_list, cookies_list=COOKIE_INFO, is_random_ip=False, is_auto_retry=False)
    result = {
        "game_name": None,  # 游戏名字
        "develop_name": None,  # Developer
        "publisher_name": None,  # Publisher
    }
    if game_index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(game_index_response.status))
    game_index_response_content = game_index_response.data.decode(errors="ignore")
    # 获取游戏名字
    game_name = pq(game_index_response_content).find(".css-truncate").text()
    if not game_name:
        raise crawler.CrawlerException("页面截取游戏名字失败\n%s" % game_index_response_content)
    result["game_name"] = game_name
    # 获取开发者名字
    develop_name = pq(game_index_response_content).find("span[itemprop=author]").text()
    if not develop_name:
        develop_name = pq(game_index_response_content).find("a[itemprop=author]").text()
    if develop_name:
        result["develop_name"] = develop_name
    # 获取发行商名字
    publisher_name = pq(game_index_response_content).find("span[itemprop=publisher]").text()
    if not publisher_name:
        pq(game_index_response_content).find("a[itemprop=publisher]").text()
    if publisher_name:
        result["publisher_name"] = publisher_name
    if not result["develop_name"] or not result["publisher_name"]:
        history_api_url = "https://steamdb.info/api/GetAppHistory/?lastentry=0&appid=999170"
        query_data = {
            "lastentry": "0",
            "appid": game_id,
        }
        history_api_response = net.http_request(history_api_url, method="GET", fields=query_data, header_list=header_list, cookies_list=COOKIE_INFO, is_random_ip=False, json_decode=True)
        if history_api_response.status != net.HTTP_RETURN_CODE_SUCCEED:
            raise crawler.CrawlerException("历史记录，%s" % crawler.request_failre(game_index_response.status))
        history_response_content = crawler.get_json_value(history_api_response.json_data, "data", "Rendered", type_check=str)
        if not result["develop_name"]:
            history_info_selector_list = pq(history_response_content).find(".app-history i:contains('developer')")
            for history_index in range(0, history_info_selector_list.length):
                history_info_selector = history_info_selector_list.eq(history_index)
                history_type = history_info_selector.closest("li").text()
                if history_type:
                    history_type = history_type.strip()
                    check_text = "Removed developer –"
                    if history_type[:len(check_text)] == check_text:
                        develop_name = history_type[len(check_text):].strip()
                        if develop_name:
                            result["develop_name"] = develop_name
                            break
        if not result["publisher_name"]:
            history_info_selector_list = pq(history_response_content).find(".app-history i:contains('publisher')")
            for history_index in range(0, history_info_selector_list.length):
                history_info_selector = history_info_selector_list.eq(history_index)
                history_type = history_info_selector.closest("li").text()
                if history_type:
                    history_type = history_type.strip()
                    check_text = "Removed publisher –"
                    if history_type[:len(check_text)] == check_text:
                        publisher_name = history_type[len(check_text):].strip()
                        if publisher_name:
                            result["publisher_name"] = publisher_name
                            break
    return result


class SteamDb(crawler.Crawler):
    account_id = None

    def __init__(self, need_login=True, **kwargs):
        global COOKIE_INFO

        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_SET_PROXY: True,
            crawler.SYS_NOT_DOWNLOAD: True,
            crawler.SYS_NOT_CHECK_SAVE_DATA: True,
            crawler.SYS_GET_COOKIE: ("steamdb.info",),
            crawler.SYS_APP_CONFIG_PATH: os.path.join(crawler.PROJECT_APP_PATH, "steamdb.ini"),
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        COOKIE_INFO = self.cookie_value
