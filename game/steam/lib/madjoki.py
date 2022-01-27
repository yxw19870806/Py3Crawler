# -*- coding:UTF-8  -*-
"""
madjoki相关数据解析爬虫
https://steam.madjoki.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import time
from pyquery import PyQuery as pq
from common import *

COOKIE_INFO = {}


def get_banned_game_list():
    page_count = max_page_count = 1
    result = []
    while page_count <= max_page_count:
        output.print_msg("开始解析第%s页删除游戏" % page_count)
        index_url = "https://steam.madjoki.com/apps/banned"
        query_data = {
            "type": "1",
            "page": page_count,
            "desc": "0"
        }
        index_response = net.request(index_url, method="GET", fields=query_data, is_random_ip=False)
        if index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
            raise "第%s页，%s" % (page_count, crawler.CrawlerException(crawler.request_failre(index_response.status)))
        index_response_content = index_response.data.decode(errors="ignore")
        # 获取游戏名字
        game_info_selector_list = pq(index_response_content).find("table.table-data tr")
        for game_index in range(1, game_info_selector_list.length - 1):
            result_game_info = {
                "game_id": None,  # 游戏ID
                "game_name": "",  # 游戏名字
                "game_banned_time": None,  # 游戏下线时间
            }
            game_info_selector = game_info_selector_list.eq(game_index)
            # 获取游戏名字
            game_name = game_info_selector.find("td").eq(2).find("a:first").text()
            if not game_name:
                raise crawler.CrawlerException("游戏信息截取游戏名字失败\n%s" % game_info_selector.html())
            result_game_info["game_name"] = game_name.strip()
            # 获取游戏ID
            game_url = game_info_selector.find("td").eq(2).find("a:first").attr("href")
            game_id = game_url.split("/")[-1]
            if tool.is_integer(game_id):
                result_game_info["game_id"] = int(game_id)
            # 获取游戏下线时间
            game_banned_time_text = game_info_selector.find("td").eq(3).find("time").attr("datetime")
            game_banned_time_zone = game_banned_time_text[-6:]
            game_banned_time_text = game_banned_time_text[:-6]
            game_banned_time = int(time.mktime(time.strptime(game_banned_time_text.split("+")[0], "%Y-%m-%dT%H:%M:%S")))
            if game_banned_time_zone[0] == "+":
                game_banned_time -= int(game_banned_time_zone[1:].split(":")[0]) * 60 * 60
            elif game_banned_time_zone[0] == "-":
                game_banned_time += int(game_banned_time_zone[1:].split(":")[0]) * 60 * 60
            result_game_info["game_banned_time"] = game_banned_time
            result.append(result_game_info)
        # 获取总页数
        max_page_count = pq(index_response_content).find("nav[aria-label='Pages']:first li.page-item").eq(-2).text()
        if not tool.is_integer(max_page_count):
            raise crawler.CrawlerException("页面截取分页信息失败\n%s" % index_response_content.html())
        max_page_count = int(max_page_count)
        page_count += 1
    return result
