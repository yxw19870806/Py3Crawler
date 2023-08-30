# -*- coding:UTF-8  -*-
"""
根据所有打折游戏更新缓存信息
https://store.steampowered.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import console, const, CrawlerException
from game.steam.lib import steam


def main():
    # 获取登录状态
    steam_class = steam.Steam(need_login=True)

    # 所有打折游戏
    discount_cache = steam_class.new_cache("discount.txt", const.FileType.JSON)
    discount_game_list = discount_cache.read()
    if not isinstance(discount_game_list, list):
        discount_game_list = []
    game_id_list = []
    for game_info in discount_game_list:
        if game_info["type"] == "game":
            game_id_list.append(game_info["app_id"])
        else:
            game_id_list += game_info["app_id"]

    # 已检测过的游戏列表
    discount_checked_app_cache = steam_class.new_cache("discount_checked.txt", const.FileType.COMMA_DELIMITED)
    checked_apps_list = discount_checked_app_cache.read()
    # 已删除的游戏
    deleted_app_list = steam_class.deleted_app_list_cache.read()
    # 已资料受限制的游戏
    restricted_app_list = steam_class.restricted_app_list_cache.read()
    # 游戏的DLC列表
    game_dlc_list = steam_class.game_dlc_list_cache.read()

    while len(game_id_list) > 0:
        game_id = game_id_list.pop()
        game_id = str(game_id)
        if not game_id.endswith("0"):
            continue
        if game_id in deleted_app_list or game_id in restricted_app_list:
            continue
        if game_id in checked_apps_list:
            continue

        console.log(f"游戏{game_id}，剩余数量：{len(game_id_list)}")

        # 获取游戏信息
        try:
            game_data = steam.get_game_store_index(game_id)
        except CrawlerException as e:
            console.log(e.http_error(f"游戏{game_id}"))
            continue

        if len(game_data["dlc_list"]) > 0:
            console.log(f"游戏{game_id}全部DLC：{game_data['dlc_list']}")
            is_change = False
            for dlc_id in game_data["dlc_list"]:
                if dlc_id not in game_dlc_list:
                    is_change = True
                    game_dlc_list[dlc_id] = game_id
            # 保存数据
            if is_change:
                steam_class.game_dlc_list_cache.write(game_dlc_list)

        # 已资料受限制
        if game_data["restricted"]:
            console.log(f"游戏{game_id}已资料受限制")
            restricted_app_list.append(game_id)
            # 保存数据
            steam_class.restricted_app_list_cache.write(restricted_app_list)

        # 增加检测标记
        checked_apps_list.append(game_id)
        discount_checked_app_cache.write(checked_apps_list)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
