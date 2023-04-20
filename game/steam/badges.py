# -*- coding:UTF-8  -*-
"""
获取指定账号的全部未收集完成徽章对应的集换卡价格
https://store.steampowered.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import urllib.parse
from common import *
from game.steam.lib import steam

MIN_CARD_PRICE = 0  # 最低卡牌价格
MAX_CARD_PRICE = 0.5  # 最高卡牌价格
MAX_TOTAL_PRICE = 1.5  # 所有卡牌总价
IS_TOTAL_CARD = False  # 是不是一个game id下的所有卡牌都要符合条件
EXTRA_CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), "lib", "badges.ini")


# 获取当前account正在收集的徽章进度
def main():
    global MIN_CARD_PRICE, MAX_CARD_PRICE, MAX_TOTAL_PRICE, IS_TOTAL_CARD
    config = crawler.read_config(EXTRA_CONFIG_FILE_PATH)

    MIN_CARD_PRICE = crawler.analysis_config(config, "MIN_CARD_PRICE", 0, const.ConfigAnalysisMode.BOOLEAN)
    MAX_CARD_PRICE = crawler.analysis_config(config, "MAX_CARD_PRICE", 0.5, const.ConfigAnalysisMode.BOOLEAN)
    MAX_TOTAL_PRICE = crawler.analysis_config(config, "MAX_TOTAL_PRICE", 1.5, const.ConfigAnalysisMode.BOOLEAN)
    IS_TOTAL_CARD = crawler.analysis_config(config, "IS_TOTAL_CARD", False, const.ConfigAnalysisMode.BOOLEAN)

    # 获取登录状态
    steam_class = steam.Steam(need_login=True)
    skip_list_file_path = os.path.join(steam_class.cache_data_path, "badges_skip.txt")

    # 已删除的游戏
    deleted_app_list = steam_class.load_deleted_app_list()
    # 已设置跳过的游戏
    skip_list = []
    if os.path.exists(skip_list_file_path):
        skip_list = tool.json_decode(file.read_file(skip_list_file_path), [])

    # 获取全部没有收到恒宇卡牌掉落且还可以升级的徽章
    try:
        badges_detail_url_list = steam.get_self_uncompleted_account_badges(steam_class.account_id)
    except crawler.CrawlerException as e:
        console.log(e.http_error("个人徽章首页"))
        raise

    for badges_detail_url in badges_detail_url_list:
        game_id = badges_detail_url.split("/")[-2]
        # 跳过列表
        if game_id in skip_list:
            continue

        # 查询徽章剩余的卡牌以及数量
        try:
            wanted_card_list = steam.get_self_account_badge_card(badges_detail_url)
        except crawler.CrawlerException as e:
            console.log(e.http_error("徽章" % badges_detail_url))
            continue
        if len(wanted_card_list) == 0:
            # 已实际完成
            skip_list.append(game_id)
            file.write_file(tool.json_encode(skip_list), skip_list_file_path, const.WriteFileMode.REPLACE)
            continue
        if game_id in deleted_app_list:
            continue
        console.log("game id: %s" % game_id, False)
        # 获取全部卡牌的市场售价
        try:
            market_card_list = steam.get_market_game_trade_card_price(game_id)
        except crawler.CrawlerException as e:
            console.log(e.http_error("游戏%s的市场" % game_id))
            continue

        card_hash_name_dict = {}
        for card_hash_name in market_card_list:
            card_name = card_hash_name.replace(" (Trading Card)", "")
            card_hash_name_dict[card_name] = card_hash_name

        print_message_list = []
        is_total = True
        total_price = 0
        for card_name in wanted_card_list:
            if card_name in card_hash_name_dict:
                card_hash_name = card_hash_name_dict[card_name]
            else:
                card_hash_name = card_name

            if card_hash_name in market_card_list:
                card_price = float(market_card_list[card_hash_name])
                total_price += card_price
                if MIN_CARD_PRICE < card_price <= MAX_CARD_PRICE:
                    market_link = "https://steamcommunity.com/market/listings/753/%s-%s" % (game_id, urllib.parse.quote(card_hash_name))
                    message = "card: %s, wanted %s, min price: %s, link: %s" % (card_name, wanted_card_list[card_name], card_price, market_link)
                    print_message_list.append(message)
                else:
                    is_total = False
            else:
                market_link = "https://steamcommunity.com/market/listings/753/%s-%s" % (game_id, urllib.parse.quote(card_hash_name))
                message = "card: %s, wanted %s, not found price in market, link: %s" % (card_name, wanted_card_list[card_hash_name], market_link)
                print_message_list.append(message)

        if not IS_TOTAL_CARD or (IS_TOTAL_CARD and is_total):
            if MAX_TOTAL_PRICE <= 0 or (MAX_TOTAL_PRICE > 0 and total_price <= MAX_TOTAL_PRICE):
                for print_message in print_message_list:
                    console.log(print_message, False)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
