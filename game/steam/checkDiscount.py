# -*- coding:UTF-8  -*-
"""
根据所有打折游戏更新缓存信息
https://store.steampowered.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from common import crawler, file, output, tool
from game.steam.lib import steam


def main():
    # 获取登录状态
    steam_class = steam.Steam(need_login=True)

    # 所有打折游戏
    discount_game_file_path = os.path.abspath(os.path.join(steam_class.cache_data_path, "discount.txt"))
    discount_game_list = tool.json_decode(file.read_file(discount_game_file_path), [])
    game_id_list = []
    for game_info in discount_game_list:
        if game_info["type"] == "game":
            game_id_list.append(game_info["app_id"])
        else:
            game_id_list += game_info["app_id"]
    # 已检测过的游戏列表
    checked_apps_file_path = os.path.join(steam_class.cache_data_path, "discount_checked.txt")
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

    while len(game_id_list) > 0:
        game_id = game_id_list.pop()
        game_id = str(game_id)
        if game_id[-1:] != "0":
            continue
        if game_id in deleted_app_list or game_id in restricted_app_list:
            continue
        if game_id in checked_apps_list:
            continue

        output.print_msg("游戏：%s，剩余数量：%s" % (game_id, len(game_id_list)))

        # 获取游戏信息
        try:
            game_data = steam.get_game_store_index(game_id)
        except crawler.CrawlerException as e:
            output.print_msg(e.http_error("游戏%s" % game_id))
            continue

        if len(game_data["dlc_list"]) > 0:
            output.print_msg("游戏：%s全部DLC：%s" % (game_id, game_data["dlc_list"]))
            is_change = False
            for dlc_id in game_data["dlc_list"]:
                if dlc_id not in game_dlc_list:
                    is_change = True
                    game_dlc_list[dlc_id] = game_id
            # 保存数据
            if is_change:
                steam_class.save_game_dlc_list(game_dlc_list)

        # 已资料受限制
        if game_data["restricted"]:
            output.print_msg("游戏：%s已资料受限制" % game_id)
            restricted_app_list.append(game_id)
            # 保存数据
            steam_class.save_restricted_app_list(restricted_app_list)

        # 增加检测标记
        checked_apps_list.append(game_id)
        file.write_file(",".join(checked_apps_list), checked_apps_file_path, file.WriteFileMode.REPLACE)


if __name__ == "__main__":
    main()
