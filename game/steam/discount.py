# -*- coding:UTF-8  -*-
"""
获取steam全部打折游戏信息
https://store.steampowered.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from common import *
from game.steam.lib import steam

INCLUDE_GAME = True  # 是否包含游戏
INCLUDE_PACKAGE = True  # 是否包含礼包(sub)
INCLUDE_BUNDLE = True  # 是否包含捆绑包(bundle)
SKIP_RESTRICTED_GAME = True  # 是否跳过Steam正在了解的游戏
MIN_DISCOUNT_PERCENT = 75  # 显示折扣大等于这个数字的游戏
MAX_DISCOUNT_PERCENT = 100  # 显示折扣大等于这个数字的游戏
MAX_SELLING_PERCENT = 1  # 显示价格小等于这个数字的游戏
EXTRA_CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), "lib", "discount.ini")


# 获取文件中的打折列表
def load_discount_list(discount_cache: crawler.CrawlerCache):
    default_discount_game_list = []
    if not os.path.exists(discount_cache.cache_path):
        return default_discount_game_list
    cache_time = tool.convert_timestamp_to_formatted_time("%Y-%m-%d %H:%M", os.path.getmtime(discount_cache.cache_path))
    while True:
        input_str = input(f"{tool.convert_timestamp_to_formatted_time()} 缓存文件时间：{cache_time}，是否使用？使用缓存数据(Y)es，删除缓存数据并重新获取(N)o，退出程序(E)xit：")
        input_str = input_str.lower()
        if input_str in ["y", "yes"]:
            break
        elif input_str in ["n", "no"]:
            return default_discount_game_list
        elif input_str in ["e", "exit"]:
            tool.process_exit()
    discount_game_list = discount_cache.read()
    return discount_game_list if isinstance(discount_game_list, list) else default_discount_game_list


# 给出给定大等于最低折扣或者小等于最低价格的还没有的打折游戏
def main():
    global INCLUDE_GAME, INCLUDE_PACKAGE, INCLUDE_BUNDLE, SKIP_RESTRICTED_GAME
    global MIN_DISCOUNT_PERCENT, MAX_DISCOUNT_PERCENT, MAX_SELLING_PERCENT
    config = crawler.read_config(EXTRA_CONFIG_FILE_PATH)

    INCLUDE_GAME = crawler.analysis_config(config, "INCLUDE_GAME", True, const.ConfigAnalysisMode.BOOLEAN)
    INCLUDE_PACKAGE = crawler.analysis_config(config, "INCLUDE_PACKAGE", True, const.ConfigAnalysisMode.BOOLEAN)
    INCLUDE_BUNDLE = crawler.analysis_config(config, "INCLUDE_BUNDLE", True, const.ConfigAnalysisMode.BOOLEAN)
    SKIP_RESTRICTED_GAME = crawler.analysis_config(config, "SKIP_RESTRICTED_GAME", True, const.ConfigAnalysisMode.BOOLEAN)
    MIN_DISCOUNT_PERCENT = crawler.analysis_config(config, "MIN_DISCOUNT_PERCENT", 75, const.ConfigAnalysisMode.INTEGER)
    MAX_DISCOUNT_PERCENT = crawler.analysis_config(config, "MAX_DISCOUNT_PERCENT", 100, const.ConfigAnalysisMode.INTEGER)
    MAX_SELLING_PERCENT = crawler.analysis_config(config, "MAX_SELLING_PERCENT", 1, const.ConfigAnalysisMode.INTEGER)
    MIN_DISCOUNT_PERCENT = min(max(MIN_DISCOUNT_PERCENT, 1), 100)
    MAX_DISCOUNT_PERCENT = min(max(MAX_DISCOUNT_PERCENT, 1), 100)
    MAX_SELLING_PERCENT = max(MAX_SELLING_PERCENT, 1)

    # 获取登录状态
    steam_class = steam.Steam(need_login=True)
    # 缓存的打折信息
    discount_cache = steam_class.new_cache("discount.txt", const.FileType.JSON)
    # 已资料受限制的游戏
    restricted_app_list = steam_class.restricted_app_list_cache.read()
    # 游戏的DLC列表
    game_dlc_list = steam_class.game_dlc_list_cache.read()

    # 从文件里获取打折列表
    discount_game_list = load_discount_list(discount_cache)
    if not discount_game_list:
        # 调用API获取打折列表
        try:
            discount_game_list = steam.get_discount_game_list()
        except CrawlerException as e:
            console.log(e.http_error("打折游戏"))
            raise
        # 将打折列表写入文件
        discount_cache.write(discount_game_list)
        console.log("get discount game list from website")
    else:
        console.log("get discount game list from cache file")
    # 获取自己的全部游戏列表
    try:
        owned_game_list = steam.get_account_owned_app_list(steam_class.account_id)
    except CrawlerException as e:
        console.log(e.http_error("个人游戏主页"))
        raise
    for discount_info in discount_game_list:
        # 获取到的价格不大于0的跳过
        if discount_info["now_price"] <= 0 or discount_info["old_price"] <= 0:
            continue
        app_discount = discount_info["discount"]
        # 只显示当前价格或折扣小等于限制的那些游戏
        if discount_info["now_price"] <= MAX_SELLING_PERCENT or MAX_DISCOUNT_PERCENT >= app_discount >= MIN_DISCOUNT_PERCENT:
            discount_info_string = f"discount {app_discount}%%, old price: {discount_info['old_price']}, discount price: {discount_info['now_price']}"

            # bundle 或者 package，都包含多个游戏
            if discount_info["type"] == "bundle" or discount_info["type"] == "package":
                # 是否不显示package
                if discount_info["type"] == "package" and not INCLUDE_PACKAGE:
                    continue
                # 是否不显示bundle
                if discount_info["type"] == "bundle" and not INCLUDE_BUNDLE:
                    continue
                is_all = True
                # 遍历包含的全部游戏，如果都有了，则跳过
                for app_id in discount_info["app_id"]:
                    if SKIP_RESTRICTED_GAME and app_id in restricted_app_list:
                        is_all = True
                        break
                    if app_id not in owned_game_list and app_id not in game_dlc_list:
                        is_all = False
                        # break
                if not is_all:
                    if discount_info["type"] == "bundle":
                        console.log(f"https://store.steampowered.com/bundle/{discount_info['id']}/ , {discount_info_string}", False)
                    else:
                        console.log(f"https://store.steampowered.com/sub/{discount_info['id']}/ , {discount_info_string}", False)
            else:
                if not INCLUDE_GAME:
                    continue
                if SKIP_RESTRICTED_GAME and discount_info["app_id"] in restricted_app_list:
                    continue
                if discount_info["app_id"] not in owned_game_list and discount_info["app_id"] not in game_dlc_list:
                    console.log(f"https://store.steampowered.com/app/{discount_info['id']}/ , {discount_info_string}", False)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
