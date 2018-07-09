# -*- coding:UTF-8  -*-
"""
获取指定账号的全部重复库存内个人资料背景和表情
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import output, crawler
from game.steam import steamCommon

CHECK_EXTRA_CARD = True  # 是否检测额外的交换卡（徽章等级大于5，并且还有卡牌）
CHECK_DUPLICATE_BACKGROUND = True  # 是否检测重复的个人背景图
CHECK_DUPLICATE_EMOTICON = True  # 是否检测重复的表情


# 获取当前account正在收集的徽章进度
def main(account_id):
    try:
        inventory_item_list = steamCommon.get_account_inventory(account_id)
    except crawler.CrawlerException as e:
        output.print_msg("库存解析失败，原因：%s" % e.message)
        raise
    badges_list = {}
    if CHECK_EXTRA_CARD:
        # 获取徽章等级
        try:
            badges_list = steamCommon.get_account_badges(account_id)
        except crawler.CrawlerException as e:
            output.print_msg("获取徽章等级失败，原因：%s" % e.message)
            raise
    for item_id, item_info in inventory_item_list.items():
        if item_info["type"] == steamCommon.INVENTORY_ITEM_TYPE_PROFILE_BACKGROUND:
            if CHECK_DUPLICATE_BACKGROUND and item_info["count"] > 1:
                output.print_msg(item_info)
        elif item_info["type"] == steamCommon.INVENTORY_ITEM_TYPE_EMOTICON:
            if CHECK_DUPLICATE_EMOTICON and item_info["count"] > 1:
                output.print_msg(item_info)
        elif item_info["type"] == steamCommon.INVENTORY_ITEM_TYPE_TRADE_CARD:
            # 有这个徽章并且徽章等级大等于5
            if CHECK_EXTRA_CARD and item_info["game_id"] in badges_list and badges_list[item_info["game_id"]] == 5:
                output.print_msg(item_info)


if __name__ == "__main__":
    main(steamCommon.get_account_id_from_file())
