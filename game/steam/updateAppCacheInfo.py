# -*- coding:UTF-8  -*-
"""
根据所有拥有的游戏更新缓存信息
https://store.steampowered.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from common import crawler, file, output
from game.steam.lib import steam


def main():
    # 获取登录状态
    steam_class = steam.Steam(need_login=True)

    # 获取自己的全部游戏列表
    try:
        owned_game_list = steam.get_account_owned_app_list(steam_class.account_id)
    except crawler.CrawlerException as e:
        output.print_msg("个人游戏主页解析失败，原因：%s" % e.message)
        raise

    # 已检测过的游戏列表
    checked_apps_file_path = os.path.join(steam_class.cache_data_path, "checked.txt")
    checked_apps_string = file.read_file(checked_apps_file_path)
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

    while len(owned_game_list) > 0:
        game_id = owned_game_list.pop()
        if game_id in checked_apps_list:
            continue

        output.print_msg("游戏: %s，剩余数量: %s" % (game_id, len(owned_game_list)))
        # 获取游戏信息
        try:
            game_data = steam.get_game_store_index(game_id)
        except crawler.CrawlerException as e:
            output.print_msg("游戏%s解析失败，原因：%s" % (game_id, e.message))
            raise

        # 已删除
        if game_data["deleted"]:
            output.print_msg("游戏: %s，已删除" % game_id)
            if game_id not in deleted_app_list:
                deleted_app_list.append(game_id)
                # 保存数据
                steam_class.save_deleted_app_list(deleted_app_list)
        else:
            # 受限制
            if game_data["learning"]:
                output.print_msg("游戏: %s，已受限制" % game_id)
                if game_id not in restricted_app_list:
                    restricted_app_list.append(game_id)
                    # 保存数据
                    steam_class.save_restricted_app_list(restricted_app_list)
            # 所有的DLC
            if len(game_data["dlc_list"]) > 0:
                is_change = False
                for dlc_id in game_data["dlc_list"]:
                    output.print_msg("游戏: %s，DLC: %s" % (game_id, dlc_id))
                    if dlc_id not in game_dlc_list:
                        game_dlc_list[dlc_id] = game_id
                # 保存数据
                if is_change:
                    steam_class.save_game_dlc_list(game_dlc_list)

        checked_apps_list.append(game_id)
        file.write_file(",".join(checked_apps_list), checked_apps_file_path, file.WRITE_FILE_TYPE_REPLACE)


if __name__ == "__main__":
    main()

