# -*- coding:UTF-8  -*-
"""
检测已被删除的游戏是否有恢复
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
    deleted_app_list = steam_class.deleted_app_list_cache.read()

    console.log(f"总共获取{len(deleted_app_list)}个已删除游戏")

    result_game_ids = []
    while len(deleted_app_list) > 0:
        game_id = deleted_app_list.pop()

        console.log(f"游戏{game_id}，剩余数量：{len(deleted_app_list)}")

        # 获取游戏信息
        try:
            game_data = steam.get_game_store_index(game_id)
        except CrawlerException as e:
            console.log(e.http_error(f"游戏{game_id}"))
            continue
        if game_data["deleted"] is False:
            console.log(f"游戏{game_id}不在已删除列表中")
            result_game_ids.append(game_id)

    console.log(result_game_ids)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
