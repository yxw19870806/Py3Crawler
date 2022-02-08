# -*- coding:UTF-8  -*-
"""
获取指定账号的全部重复库存内个人资料背景和表情
https://store.steampowered.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import output, crawler
from game.steam.lib import steam

CHECK_EXTRA_CARD = True  # 是否检测额外的交换卡（徽章等级大于5，并且还有卡牌）
CHECK_DUPLICATE_BACKGROUND = True  # 是否检测重复的个人背景图
CHECK_DUPLICATE_EMOTICON = False  # 是否检测重复的表情


# 获取当前account正在收集的徽章进度
def main():
    # 获取登录状态
    steam_class = steam.Steam(need_login=True)

    # 获取所有库存
    try:
        inventory_item_list = steam.get_account_inventory(steam_class.account_id)
    except crawler.CrawlerException as e:
        output.print_msg(f"库存解析失败，原因：{e.message}")
        raise
    badges_list = {}
    if CHECK_EXTRA_CARD:
        # 获取徽章等级
        try:
            badges_list = steam.get_account_badges(steam_class.account_id)
        except crawler.CrawlerException as e:
            output.print_msg(f"获取徽章等级失败，原因：{e.message}")
            raise
    for item_id, item_info in inventory_item_list.items():
        if item_info["type"] == steam.INVENTORY_ITEM_TYPE_PROFILE_BACKGROUND:
            if CHECK_DUPLICATE_BACKGROUND and item_info["count"] > 1:
                output.print_msg(item_info)
        elif item_info["type"] == steam.INVENTORY_ITEM_TYPE_EMOTICON:
            if CHECK_DUPLICATE_EMOTICON and item_info["count"] > 1:
                output.print_msg(item_info)
        elif item_info["type"] == steam.INVENTORY_ITEM_TYPE_TRADE_CARD:
            if CHECK_EXTRA_CARD:
                # 闪卡，跳过
                if item_info['name'].find("(Foil)") >= 0 or item_info['name'].find("(Foil Trading Card)") >= 0:
                    continue
                if item_info["game_id"] in badges_list:
                    badge_level = badges_list[item_info["game_id"]]
                else:
                    badge_level = 0
                # 如果剩余卡牌数量 + 当前徽章等级 > 5
                if item_info["count"] + badge_level > steam.MAX_BADGE_LEVEL:
                    output.print_msg(item_info)


if __name__ == "__main__":
    main()
