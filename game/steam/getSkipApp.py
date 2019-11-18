# -*- coding:UTF-8  -*-
"""
获取缓存文件中所有无效的steam游戏
https://store.steampowered.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import output
from game.steam.lib import steam


def main():
    # 获取登录状态
    steam_class = steam.Steam(need_login=False)
    steam_class.format_cache_app_info()
    output.print_msg(steam_class.deleted_app_list + steam_class.restricted_app_list)


if __name__ == "__main__":
    main()
