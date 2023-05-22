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

COOKIES = {}
USER_AGENT = None


def get_game_store_index(game_id):
    game_index_url = "https://steamdb.info/app/%s/" % game_id
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": "https://steamdb.info/",
    }
    if "User-Agent" not in headers:
        raise CrawlerException("header没有携带User-Agent")
    game_index_response = net.Request(game_index_url, method="GET", headers=headers, cookies=COOKIES).disable_auto_retry()
    result = {
        "game_name": None,  # 游戏名字
        "develop_name": None,  # Developer
        "publisher_name": None,  # Publisher
    }
    if game_index_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(game_index_response.status))
    # 获取游戏名字
    game_name = pq(game_index_response.content).find("[itemprop='name']").text()
    if not game_name:
        raise CrawlerException("页面截取游戏名字失败\n" + game_index_response.content)
    result["game_name"] = game_name
    # 获取开发者名字
    develop_name = pq(game_index_response.content).find("span[itemprop=author]").text()
    if not develop_name:
        develop_name = pq(game_index_response.content).find("a[itemprop=author]").text()
    if develop_name:
        result["develop_name"] = develop_name
    # 获取发行商名字
    publisher_name = pq(game_index_response.content).find("span[itemprop=publisher]").text()
    if not publisher_name:
        publisher_name = pq(game_index_response.content).find("a[itemprop=publisher]").text()
    if publisher_name:
        result["publisher_name"] = publisher_name
    if not result["develop_name"] or not result["publisher_name"]:
        history_api_url = "https://steamdb.info/api/GetAppHistory/"
        query_data = {
            "lastentry": "0",
            "appid": game_id,
        }
        headers["X-Requested-With"] = "XMLHttpRequest"
        history_api_response = net.Request(history_api_url, method="GET", fields=query_data, headers=headers, cookies=COOKIES)
        if history_api_response.status != const.ResponseCode.SUCCEED:
            raise CrawlerException("历史记录，%s" % crawler.request_failre(history_api_response.status))
        if not result["develop_name"]:
            history_info_selector_list = pq(history_api_response.content).find(".app-history i:contains('developer')")
            for history_index in range(history_info_selector_list.length):
                history_info_selector = history_info_selector_list.eq(history_index)
                history_type = history_info_selector.closest("li").text()
                if history_type:
                    history_type = history_type.strip()
                    check_text = "Removed developer –"
                    if history_type.startswith(check_text):
                        develop_name = history_type[len(check_text):].strip()
                        if develop_name:
                            result["develop_name"] = develop_name
                            break
        if not result["publisher_name"]:
            history_info_selector_list = pq(history_api_response.content).find(".app-history i:contains('publisher')")
            for history_index in range(history_info_selector_list.length):
                history_info_selector = history_info_selector_list.eq(history_index)
                history_type = history_info_selector.closest("li").text()
                if history_type:
                    history_type = history_type.strip()
                    check_text = "Removed publisher –"
                    if history_type.startswith(check_text):
                        publisher_name = history_type[len(check_text):].strip()
                        if publisher_name:
                            result["publisher_name"] = publisher_name
                            break
    return result


class SteamDb(crawler.Crawler):
    account_id = None

    def __init__(self, **kwargs):
        global COOKIES, USER_AGENT

        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

        # 初始化参数
        sys_config = {
            const.SysConfigKey.SET_PROXY: True,
            const.SysConfigKey.NOT_DOWNLOAD: True,
            const.SysConfigKey.NOT_CHECK_SAVE_DATA: True,
            const.SysConfigKey.GET_COOKIE: ("steamdb.info",),
            const.SysConfigKey.APP_CONFIG_PATH: os.path.join(crawler.PROJECT_APP_PATH, "lib", "steamdb.ini"),
            const.SysConfigKey.APP_CONFIG: (
                ("USER_AGENT", "", const.ConfigAnalysisMode.RAW),
            ),
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        COOKIES = self.cookie_value
        USER_AGENT = self.app_config["USER_AGENT"]

        net.disable_fake_proxy_ip()
