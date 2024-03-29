# -*- coding:UTF-8  -*-
"""
根据所有拥有的游戏更新缓存信息
https://store.steampowered.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import *
from game.steam.lib import steam


def main():
    # 获取登录状态
    steam_class = steam.Steam(need_login=True)

    # 获取自己的全部游戏列表
    try:
        owned_game_list = steam.get_account_owned_app_list(steam_class.account_id)
    except CrawlerException as e:
        console.log(e.http_error("个人游戏主页"))
        raise

    # 已检测过的游戏列表
    app_checked_cache = steam_class.new_cache("checked.txt", const.FileType.COMMA_DELIMITED)
    checked_apps_list = app_checked_cache.read()
    # 已删除的游戏
    deleted_app_list = steam_class.deleted_app_list_cache.read()
    # 已资料受限制的游戏
    restricted_app_list = steam_class.restricted_app_list_cache.read()
    # 游戏的DLC列表
    game_dlc_list = steam_class.game_dlc_list_cache.read()

    while len(owned_game_list) > 0:
        game_id = owned_game_list.pop()
        if game_id in checked_apps_list:
            continue

        console.log(f"游戏{game_id}，剩余数量: {len(owned_game_list)}")
        # 获取游戏信息
        try:
            game_data = steam.get_game_store_index(game_id)
        except CrawlerException as e:
            console.log(e.http_error(f"游戏{game_id}"))
            raise

        # 已删除
        if game_data["deleted"]:
            console.log(f"游戏{game_id}已删除")
            if game_id not in deleted_app_list:
                deleted_app_list.append(game_id)
                # 保存数据
                steam_class.deleted_app_list_cache.write(deleted_app_list)
        else:
            # 受限制
            if game_data["restricted"]:
                console.log(f"游戏{game_id}已受限制")
                if game_id not in restricted_app_list:
                    restricted_app_list.append(game_id)
                    # 保存数据
                    steam_class.restricted_app_list_cache.write(restricted_app_list)
            # 所有的DLC
            if len(game_data["dlc_list"]) > 0:
                is_change = False
                for dlc_id in game_data["dlc_list"]:
                    console.log(f"游戏{game_id}，DLC {dlc_id}")
                    if dlc_id not in game_dlc_list:
                        game_dlc_list[dlc_id] = game_id
                # 保存数据
                if is_change:
                    steam_class.game_dlc_list_cache.write(game_dlc_list)

        checked_apps_list.append(game_id)
        app_checked_cache.write(",".join(checked_apps_list))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
