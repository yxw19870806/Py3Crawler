# -*- coding:UTF-8  -*-
"""
检测已被资料受限的游戏是否有恢复
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import console, CrawlerException
from game.steam.lib import steam


def main():
    # 获取登录状态
    steam_class = steam.Steam(need_login=False)

    # 已删除的游戏
    restricted_app_list = steam_class.restricted_app_list_cache.read()

    console.log("总共获取%s个已受限游戏" % len(restricted_app_list))

    result_game_ids = []
    while len(restricted_app_list) > 0:
        game_id = restricted_app_list.pop()

        console.log("游戏：%s，剩余数量：%s" % (game_id, len(restricted_app_list)))

        # 获取游戏信息
        try:
            game_data = steam.get_game_store_index(game_id)
        except CrawlerException as e:
            console.log(e.http_error("游戏%s" % game_id))
            continue
        if game_data["error"]:
            console.log("游戏 %s 访问错误，%s" % (game_id, game_data["error"]))
            result_game_ids.append(game_id)
        elif game_data["restricted"] is False:
            console.log("游戏 %s 不在已受限列表中" % game_id)
            result_game_ids.append(game_id)

    console.log(result_game_ids)
    restricted_app_list = steam_class.restricted_app_list_cache.read()
    for game_id in result_game_ids:
        restricted_app_list.remove(game_id)
    steam_class.restricted_app_list_cache.write(restricted_app_list)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
