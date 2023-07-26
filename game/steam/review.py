# -*- coding:UTF-8  -*-
"""
获取steam可以发布评测的游戏
https://store.steampowered.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from common import *
from game.steam.lib import steam


# 打印列表
# print_type  0 全部游戏
# print_type  1 只要本体
# print_type  2 只要DLC
# print_type  3 只要本体已评测的DLC
def print_list(user_review_cache_data, game_dlc_list, print_type=0):
    for game_id in user_review_cache_data["can_review_lists"]:
        # 是DLC
        if game_id in game_dlc_list:
            if print_type == 1:
                continue
            # 本体没有评测过
            if game_dlc_list[game_id] in user_review_cache_data["can_review_lists"]:
                if print_type == 3:
                    continue
        else:
            if print_type == 2 or print_type == 3:
                continue
        console.log("https://store.steampowered.com/app/%s" % game_id)


def main(check_game=True):
    # 获取登录状态
    steam_class = steam.Steam(need_login=True)

    # 历史记录
    user_review_cache_data = steam_class.load_user_review_data()
    # 已检测过的游戏列表
    review_checked_app_cache = steam_class.new_cache("review_checked.txt", const.FileType.Text)
    checked_apps_string = review_checked_app_cache.read().strip()
    if checked_apps_string:
        checked_apps_list = checked_apps_string.split(",")
    else:
        checked_apps_list = []
    # 已删除的游戏
    deleted_app_list = steam_class.load_deleted_app_list()
    # 已资料受限制的游戏
    restricted_app_list = steam_class.load_restricted_app_list()
    # 游戏的DLC列表
    game_dlc_list = steam_class.load_game_dlc_list()

    # 获取自己的全部玩过的游戏列表
    try:
        played_game_list = steam.get_account_owned_app_list(steam_class.account_id, True)
    except CrawlerException as e:
        console.log(e.http_error("个人游戏主页"))
        raise

    if check_game:
        while len(played_game_list) > 0:
            game_id = played_game_list.pop()
            if game_id in deleted_app_list:
                continue
            if game_id in checked_apps_list:
                continue

            console.log("开始解析游戏 %s，剩余数量：%s" % (game_id, len(played_game_list)))

            # 获取游戏信息
            try:
                game_data = steam.get_game_store_index(game_id)
            except CrawlerException as e:
                console.log("游戏 %s 解析失败，原因：%s" % (game_id, e.message))
                console.log(e.http_error("游戏%s" % game_id))
                continue

            is_change = False
            # 已删除
            if game_data["deleted"]:
                deleted_app_list.append(game_id)
                # 保存数据
                steam_class.save_deleted_app_list(deleted_app_list)
            else:
                # 有DLC的话，遍历每个DLC
                for dlc_id in game_data["dlc_list"]:
                    # 已经评测过了，跳过检查
                    if dlc_id in user_review_cache_data["review_list"]:
                        continue

                    # DLC和游戏本体关系字典
                    if dlc_id not in game_dlc_list:
                        game_dlc_list[dlc_id] = game_id
                        is_change = True

                    # 获取DLC信息
                    try:
                        dlc_data = steam.get_game_store_index(dlc_id)
                    except CrawlerException as e:
                        console.log(e.http_error("游戏%s" % dlc_id))
                        continue

                    if dlc_data["owned"]:
                        # 已经评测过了
                        if dlc_data["reviewed"]:
                            # 从待评测列表中删除
                            if dlc_id in user_review_cache_data["can_review_lists"]:
                                user_review_cache_data["can_review_lists"].remove(dlc_id)
                            # 增加已评测记录
                            if dlc_id not in user_review_cache_data["review_list"]:
                                user_review_cache_data["review_list"].append(dlc_id)
                        # 新的可以评测游戏
                        else:
                            if dlc_id not in user_review_cache_data["can_review_lists"]:
                                user_review_cache_data["can_review_lists"].append(dlc_id)

                # 已经评测过了
                if game_data["reviewed"]:
                    # 从待评测列表中删除
                    if game_id in user_review_cache_data["can_review_lists"]:
                        user_review_cache_data["can_review_lists"].remove(game_id)
                    # 增加已评测记录
                    if game_id not in user_review_cache_data["review_list"]:
                        user_review_cache_data["review_list"].append(game_id)
                # 新的可以评测游戏
                else:
                    if game_id not in user_review_cache_data["can_review_lists"]:
                        user_review_cache_data["can_review_lists"].append(game_id)

                if is_change:
                    steam_class.save_game_dlc_list(game_dlc_list)

                # 已资料受限制
                if game_data["restricted"]:
                    if game_id not in restricted_app_list:
                        restricted_app_list.append(game_id)
                        # 保存数据
                        steam_class.save_restricted_app_list(restricted_app_list)

            # 增加检测标记
            steam_class.user_review_cache.write(user_review_cache_data)
            # 保存数据
            checked_apps_list.append(game_id)
            review_checked_app_cache.write(",".join(checked_apps_list))

    # 输出
    print_list(user_review_cache_data, game_dlc_list)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
