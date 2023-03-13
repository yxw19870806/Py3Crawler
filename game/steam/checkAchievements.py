# -*- coding:UTF-8  -*-
"""
获取指定账号的全部含有异常成就的游戏
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import console
from game.steam.lib import astats, steam


def main():
    steam_class = steam.Steam(need_login=False)
    owned_game_list = steam.get_account_owned_app_list(steam_class.account_id)
    for game_id in owned_game_list:
        console.log("开始解析游戏 %s" % game_id)
        astats.get_game_invalid_achievements(game_id)


if __name__ == "__main__":
    main()
