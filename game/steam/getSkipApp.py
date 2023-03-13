# -*- coding:UTF-8  -*-
"""
获取缓存文件中所有无效的steam游戏
https://store.steampowered.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import console
from game.steam.lib import steam


def main():
    # 获取登录状态
    steam_class = steam.Steam(need_login=False)
    steam_class.format_cache_app_info()

    # 已删除的游戏
    deleted_app_list = steam_class.load_deleted_app_list()
    # 已资料受限制的游戏
    restricted_app_list = steam_class.load_restricted_app_list()

    console.log(deleted_app_list + restricted_app_list)


if __name__ == "__main__":
    main()
