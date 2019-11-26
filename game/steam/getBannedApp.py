# -*- coding:UTF-8  -*-
"""
获取缓存文件中不存在的已下线steam游戏
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import crawler, output
from game.steam.lib import madjoki, steam, steamdb


def main():
    # 获取登录状态
    steam_class = steam.Steam(need_login=False)
    steam_class.format_cache_app_info()

    steamdb.SteamDb()

    # 已删除的游戏
    deleted_app_list = steam_class.load_deleted_app_list()

    try:
        banned_game_list = madjoki.get_banned_game_list()
    except crawler.CrawlerException as e:
        output.print_msg("已下线游戏列表获取失败，原因：%s" % e.message)
    else:
        output.print_msg("总共获取%s个已删除游戏" % len(banned_game_list))

        for game_info in banned_game_list:
            if str(game_info["game_id"]) not in deleted_app_list:
                try:
                    steamdb_info = steamdb.get_game_store_index(game_info["game_id"])
                except crawler.CrawlerException as e:
                    output.print_msg("游戏%s获取SteamDb信息失败，原因：%s" % (game_info["game_id"], e.message))
                else:
                    output.print_msg("\t".join(list(map(str, [game_info["game_id"], game_info["game_name"], steamdb_info["develop_name"]]))), False)


if __name__ == "__main__":
    main()
