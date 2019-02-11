# -*- coding:UTF-8  -*-
"""
获取steam全部打折游戏信息
https://store.steampowered.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import json
import os
import time
from common import *
from game.steam import steamCommon

INCLUDE_GAME = True
INCLUDE_PACKAGE = True
INCLUDE_BUNDLE = True
SKIP_LEARNING_GAME = True
MIN_DISCOUNT_PERCENT = 75  # 显示折扣大等于这个数字的游戏
MAX_DISCOUNT_PERCENT = 100  # 显示折扣大等于这个数字的游戏
MAX_SELLING_PERCENT = 1  # 显示价格小等于这个数字的游戏


# 打折游戏列表保存到文件
def save_discount_list(cache_file_path, discount_game_list):
    file.write_file(json.dumps(discount_game_list), cache_file_path, file.WRITE_FILE_TYPE_REPLACE)


# 获取文件中的打折列表
def load_discount_list(cache_file_path):
    discount_game_list = []
    if not os.path.exists(cache_file_path):
        return discount_game_list
    cache_time = time.strftime("%Y-%m-%d %H:%M", time.gmtime(os.path.getmtime(cache_file_path)))
    while True:
        input_str = input(crawler.get_time() + " 缓存文件时间：%s，是否使用？使用缓存数据(Y)es，删除缓存数据并重新获取(N)o，退出程序(E)xit：" % cache_time)
        input_str = input_str.lower()
        if input_str in ["y", "yes"]:
            break
        elif input_str in ["n", "no"]:
            return discount_game_list
        elif input_str in ["e", "exit"]:
            tool.process_exit()
    discount_game_list = tool.json_decode(file.read_file(cache_file_path), discount_game_list)
    return discount_game_list


# 给出给定大等于最低折扣或者小等于最低价格的还没有的打折游戏
def main():
    # 获取登录状态
    steam_class = steamCommon.Steam(need_login=True)
    cache_file_path = os.path.abspath(os.path.join(steam_class.cache_data_path, "discount.txt"))
    apps_cache_data = steam_class.load_cache_apps_info()

    # 从文件里获取打折列表
    discount_game_list = load_discount_list(cache_file_path)
    if not discount_game_list:
        # 调用API获取打折列表
        try:
            discount_game_list = steamCommon.get_discount_game_list()
        except crawler.CrawlerException as e:
            output.print_msg("打折游戏解析失败，原因：%s" % e.message)
            raise
        # 将打折列表写入文件
        save_discount_list(cache_file_path, discount_game_list)
        output.print_msg("get discount game list from website")
    else:
        output.print_msg("get discount game list from cache file")
    # 获取自己的全部游戏列表
    try:
        owned_game_list = steamCommon.get_account_owned_app_list(steam_class.account_id)
    except crawler.CrawlerException as e:
        output.print_msg("个人游戏主页解析失败，原因：%s" % e.message)
        raise
    dlc_ids = apps_cache_data["dlc_in_game"]
    for discount_info in discount_game_list:
        # 获取到的价格不大于0的跳过
        if discount_info["now_price"] <= 0 or discount_info["old_price"] <= 0:
            continue
        # 只显示当前价格或折扣小等于限制的那些游戏
        if discount_info["now_price"] <= MAX_SELLING_PERCENT or (discount_info["discount"] >= MIN_DISCOUNT_PERCENT and discount_info["discount"] <= MAX_DISCOUNT_PERCENT):
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
                    if SKIP_LEARNING_GAME and app_id in apps_cache_data["learning_list"]:
                        is_all = True
                        break
                    if app_id not in owned_game_list and app_id not in dlc_ids:
                        is_all = False
                        # break
                if not is_all:
                    if discount_info["type"] == "bundle":
                        output.print_msg("http://store.steampowered.com/bundle/%s/ ,discount %s%%, old price: %s, discount price: %s" % (discount_info["id"], discount_info["discount"], discount_info["old_price"], discount_info["now_price"]), False)
                    else:
                        output.print_msg("http://store.steampowered.com/sub/%s ,discount %s%%, old price: %s, discount price: %s" % (discount_info["id"], discount_info["discount"], discount_info["old_price"], discount_info["now_price"]), False)
            else:
                if not INCLUDE_GAME:
                    continue
                if SKIP_LEARNING_GAME and discount_info["app_id"] in apps_cache_data["learning_list"]:
                    continue
                if discount_info["app_id"] not in owned_game_list and discount_info["app_id"] not in dlc_ids:
                    output.print_msg("http://store.steampowered.com/app/%s/ ,discount %s%%, old price: %s, discount price: %s" % (discount_info["id"], discount_info["discount"], discount_info["old_price"], discount_info["now_price"]), False)


if __name__ == "__main__":
    main()
