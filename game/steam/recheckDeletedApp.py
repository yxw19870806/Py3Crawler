# -*- coding:UTF-8  -*-
"""
检测已被删除的游戏是否有恢复
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
    deleted_app_list = steam_class.load_deleted_app_list()

    output.print_msg(f"总共获取{len(deleted_app_list)}个已删除游戏")

    result_game_ids = []
    while len(deleted_app_list) > 0:
        game_id = deleted_app_list.pop()

        output.print_msg(f"游戏：{game_id}，剩余数量：{len(deleted_app_list)}")

        # 获取游戏信息
        try:
            game_data = steam.get_game_store_index(game_id)
        except crawler.CrawlerException as e:
            output.print_msg(f"游戏 {game_id} 解析失败，原因：{e.message}")
            continue
        if game_data["deleted"] is False:
            output.print_msg(f"游戏 {game_id} 不在已删除列表中")
            result_game_ids.append(game_id)

    output.print_msg(result_game_ids)


if __name__ == "__main__":
    main()
