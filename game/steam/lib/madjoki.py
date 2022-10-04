# -*- coding:UTF-8  -*-
"""
madjoki相关数据解析爬虫
https://steam.madjoki.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import time
from pyquery import PyQuery as pq
from common import *

COOKIE_INFO = {}


def get_banned_game_list():
    result = []
    is_over = False
    page_count = 1
    while not is_over:
        output.print_msg("开始解析第%s页删除游戏" % page_count)
        api_url = "https://ren.madjoki.com/SteamApps/Query"
        query_data = {
            "page": page_count,
            "sort": "BannedTime",
            "owned": "0",
            "apptype": "1",
            "list": "banned",
        }
        api_response = net.request(api_url, method="GET", fields=query_data, is_random_ip=False, json_decode=True)
        if api_response.status != net.HTTP_RETURN_CODE_SUCCEED:
            raise crawler.CrawlerException("第%s页，%s" % (page_count, crawler.request_failre(api_response.status)))
        # 获取游戏名字
        for game_info in crawler.get_json_value(api_response.json_data, "Items", type_check=list):
            result_game_info = {
                "game_id": None,  # 游戏ID
                "game_name": "",  # 游戏名字
                "game_banned_time": None,  # 游戏下线时间
            }
            # 获取游戏名字
            game_name = crawler.get_json_value(game_info, "Name", type_check=str)
            if not game_name:
                raise crawler.CrawlerException("游戏信息截取游戏名字失败\n" + game_info)
            result_game_info["game_name"] = game_name.strip()
            # 获取游戏ID
            game_id = crawler.get_json_value(game_info, "ID", type_check=int)
            result_game_info["game_id"] = game_id
            # 获取游戏下线时间
            game_banned_time_text = crawler.get_json_value(game_info, "BannedTime", type_check=str)
            game_banned_time = int(time.mktime(time.strptime(game_banned_time_text, "%Y-%m-%dT%H:%M:%S+00:00")))
            result_game_info["game_banned_time"] = game_banned_time
            result.append(result_game_info)
        # 获取总页数
        is_over = len(result) >= crawler.get_json_value(api_response.json_data, "TotalCount", type_check=int)
        page_count += 1
    return result
