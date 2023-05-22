# -*- coding:UTF-8  -*-
"""
获取缓存文件中不存在的已下线steam游戏
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import console, CrawlerException
from game.steam.lib import madjoki, steam, steamdb


def main():
    # 获取登录状态
    steam_class = steam.Steam(need_login=False)

    steamdb.SteamDb()

    # 已删除的游戏
    deleted_app_list = steam_class.load_deleted_app_list()

    try:
        banned_game_list = madjoki.get_banned_game_list()
    except CrawlerException as e:
        console.log(e.http_error("已下线游戏列表"))
        return
    console.log("总共获取%s个已删除游戏" % len(banned_game_list))

    for game_info in banned_game_list:
        if str(game_info["game_id"]) not in deleted_app_list:
            if str(game_info["game_id"]) in ["533120"]:
                continue
            try:
                steamdb_info = steamdb.get_game_store_index(game_info["game_id"])
            except CrawlerException as e:
                console.log(e.http_error("游戏%s" % game_info["game_id"]))
            else:
                deleted_app_list.append(str(game_info["game_id"]))
                console.log("\t".join(list(map(str, [game_info["game_id"], game_info["game_name"], steamdb_info["develop_name"]]))), False)

    steam_class.save_deleted_app_list(deleted_app_list)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
