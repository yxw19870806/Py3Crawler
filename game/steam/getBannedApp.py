# -*- coding:UTF-8  -*-
"""
获取缓存文件中不存在的已下线steam游戏
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import crawler, output
from game.steam.lib import madjoki, steam


def main():
    # 获取登录状态
    steam_class = steam.Steam(need_login=False)
    steam_class.format_cache_app_info()

    # 历史记录
    apps_cache_data = steam_class.load_cache_apps_info()

    try:
        banned_game_list = madjoki.get_banned_game_list()
    except crawler.CrawlerException as e:
        output.print_msg("已下线游戏列表获取失败，原因：%s" % e.message)
    else:
        for game_info in banned_game_list:
            if str(game_info["game_id"]) not in apps_cache_data["deleted_list"]:
                output.print_msg("\t".join(list(map(str, game_info.values()))), False)


if __name__ == "__main__":
    main()
