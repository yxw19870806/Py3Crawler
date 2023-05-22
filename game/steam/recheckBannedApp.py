# -*- coding:UTF-8  -*-
"""
检测已被ban的游戏是否有恢复
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import console, CrawlerException
from game.steam.lib import madjoki, steam


def main():
    # 获取登录状态
    steam_class = steam.Steam(need_login=False)

    # 已删除的游戏
    deleted_app_list = steam_class.load_deleted_app_list()

    try:
        banned_game_list = madjoki.get_banned_game_list()
    except CrawlerException as e:
        console.log(e.http_error("已下线游戏列表"))
    else:
        console.log("总共获取%s个已删除游戏" % len(banned_game_list))

        banned_game_id_list = {}
        for game_info in banned_game_list:
            banned_game_id_list[str(game_info["game_id"])] = 1
        for game_id in deleted_app_list:
            if game_id not in banned_game_id_list:
                # 获取游戏信息
                try:
                    game_data = steam.get_game_store_index(game_id)
                except CrawlerException as e:
                    console.log(e.http_error("游戏%s" % game_id))
                    continue
                if game_data["deleted"] is False:
                    console.log("游戏 %s 不在已删除列表中" % game_id)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
