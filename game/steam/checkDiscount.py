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
from game.steam import steamCommon


def main():
    # 获取登录状态
    steam_class = steamCommon.Steam(need_login=True)

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

    # 历史记录
    apps_cache_data = steam_class.load_cache_apps_info()

    while len(game_id_list) > 0:
        game_id = game_id_list.pop()
        game_id = str(game_id)
        if game_id in apps_cache_data["deleted_list"] or game_id in apps_cache_data["learning_list"]:
            continue
        if game_id in checked_apps_list:
            continue

        output.print_msg("游戏: %s，剩余数量: %s" % (game_id, len(game_id_list)))

        # 获取游戏信息
        try:
            game_data = steamCommon.get_game_store_index(game_id)
        except crawler.CrawlerException as e:
            output.print_msg("游戏%s解析失败，原因：%s" % (game_id, e.message))
            raise

        if len(game_data["dlc_list"]) > 0:
            output.print_msg("游戏%s全部DLC: %s" % (game_id, game_data["dlc_list"]))
            for dlc_id in game_data["dlc_list"]:
                apps_cache_data["dlc_in_game"][dlc_id] = game_id

        # 需要了解
        if game_data["learning"]:
            output.print_msg("游戏%s需要了解" % game_id)
            apps_cache_data["learning_list"].append(game_id)

        # 增加检测标记
        steam_class.save_cache_apps_info(apps_cache_data)
        checked_apps_list.append(game_id)
        file.write_file(",".join(checked_apps_list), checked_apps_file_path, file.WRITE_FILE_TYPE_REPLACE)


if __name__ == "__main__":
    main()

