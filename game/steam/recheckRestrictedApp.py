# -*- coding:UTF-8  -*-
"""
检测已被资料受限的游戏是否有恢复
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import crawler, output
from game.steam.lib import steam


def main():
    # 获取登录状态
    steam_class = steam.Steam(need_login=False)

    # 已删除的游戏
    restricted_app_list = steam_class.load_restricted_app_list()

    output.print_msg("总共获取%s个已受限游戏" % len(restricted_app_list))

    result_game_ids = []
    while len(restricted_app_list) > 0:
        game_id = restricted_app_list.pop()

        output.print_msg("游戏：%s，剩余数量：%s" % (game_id, len(restricted_app_list)))

        # 获取游戏信息
        try:
            game_data = steam.get_game_store_index(game_id)
        except crawler.CrawlerException as e:
            output.print_msg("游戏：%s解析失败，原因：%s" % (game_id, e.message))
            continue
        if game_data["error"]:
            output.print_msg("游戏 %s 访问错误，%s" % (game_id, game_data["error"]))
            result_game_ids.append(game_id)
        elif game_data["restricted"] is False:
            output.print_msg("游戏 %s 不在已受限列表中" % game_id)
            result_game_ids.append(game_id)

    output.print_msg(result_game_ids)
    restricted_app_list = steam_class.load_restricted_app_list()
    for game_id in result_game_ids:
        restricted_app_list.remove(game_id)
    steam_class.save_restricted_app_list(restricted_app_list)


if __name__ == "__main__":
    main()
