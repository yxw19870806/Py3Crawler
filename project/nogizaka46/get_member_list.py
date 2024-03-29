# -*- coding:UTF-8  -*-
"""
乃木坂46 OFFICIAL BLOG成员id获取
https://blog.nogizaka46.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import *
from pyquery import PyQuery as pq
from project.nogizaka46 import nogizaka46_diary


# 从页面获取全部成员账号
def get_account_from_index():
    index_url = "https://www.nogizaka46.com/s/n46/diary/MEMBER"
    index_response = net.Request(index_url, method="GET")
    if index_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(index_response.status))
    member_selector_list = pq(index_response.content).find("div.ba--ml__list .ba--ml__one__a")
    if member_selector_list.length == 0:
        raise CrawlerException("页面截取成员类别失败\n" + index_response.content)
    account_list = {}
    for member_index in range(member_selector_list.length):
        member_selector = member_selector_list.eq(member_index)
        # 成员id
        member_index_url_path = member_selector.attr("href")
        member_id = tool.find_sub_string(member_index_url_path, "&ct=")
        # 成员名字
        member_name = member_selector.find(".ba--ml__one__name").text().replace(" ", "")
        account_list[member_id] = member_name
    return account_list


def main():
    # 初始化类
    nogizaka46diary_class = nogizaka46_diary.Nogizaka46Diary(extra_sys_config={const.SysConfigKey.NOT_CHECK_SAVE_DATA: True})

    # 存档位置
    account_list_from_api = get_account_from_index()
    if len(account_list_from_api) > 0:
        for account_id in account_list_from_api:
            if account_id not in nogizaka46diary_class.save_data:
                nogizaka46diary_class.save_data.save(account_id, [account_id, "0", account_list_from_api[account_id]])
        nogizaka46diary_class.save_data.done()


if __name__ == "__main__":
    main()
