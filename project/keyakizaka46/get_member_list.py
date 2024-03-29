# -*- coding:UTF-8  -*-
"""
欅坂46公式Blog成员id获取
https://www.keyakizaka46.com/s/k46o/diary/member/list
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import re
from common import *
from project.keyakizaka46 import keyakizaka46_diary


# 从页面获取全部成员账号
def get_account_from_index():
    index_url = "https://www.keyakizaka46.com/s/k46o/diary/member/list"
    query_data = {"cd": "member"}
    index_response = net.Request(index_url, method="GET", fields=query_data)
    account_list = {}
    if index_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(index_response.status))
    member_list_data = tool.find_sub_string(index_response.content, '<ul class="thumb">', "</ul>")
    if not member_list_data:
        raise CrawlerException("页面截取账号列表失败\n" + index_response.content)
    member_list_find = re.findall(r"<li ([\S|\s]*?)</li>", member_list_data)
    for member_info in member_list_find:
        # 获取账号id
        account_id = tool.find_sub_string(member_info, "&ct=", '">')
        if not account_id:
            raise CrawlerException(f"账号信息{member_info}中截取账号id失败")
        # 获取成员名字
        account_name = tool.find_sub_string(member_info, '<p class="name">', "</p>").strip().replace(" ", "")
        if not account_name:
            raise CrawlerException(f"账号信息{member_info}中截取成员名字失败")
        account_list[account_id] = account_name
    return account_list


def main():
    # 初始化类
    keyakizaka46diary_class = keyakizaka46_diary.Keyakizaka46Diary(extra_sys_config={const.SysConfigKey.NOT_CHECK_SAVE_DATA: True})

    # 存档位置
    account_list_from_api = get_account_from_index()
    if len(account_list_from_api) > 0:
        for account_id in account_list_from_api:
            if account_id not in keyakizaka46diary_class.save_data:
                keyakizaka46diary_class.save_data.save(account_id, [account_id, "0", account_list_from_api[account_id]])
        keyakizaka46diary_class.save_data.done()


if __name__ == "__main__":
    main()
