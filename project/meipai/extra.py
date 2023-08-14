# -*- coding:UTF-8  -*-
"""
https://www.meipai.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import re
from common import *


# 获取指定账号的全部关注列表
def get_follow_list(account_id):
    max_page_count = 1
    page_count = 1
    follow_list = {}
    while page_count <= max_page_count:
        follow_pagination_url = f"https://www.meipai.com/user/{account_id}/friends"
        query_data = {"p": page_count}
        follow_pagination_response = net.Request(follow_pagination_url, method="GET", fields=query_data)
        if follow_pagination_response.status != const.ResponseCode.SUCCEED:
            return None
        follow_list_find = re.findall(r'<div class="ucard-info">([\s|\S]*?)</div>', follow_pagination_response.content)
        for follow_info in follow_list_find:
            follow_account_id = tool.find_sub_string(follow_info, '<a hidefocus href="/user/', '"').strip()
            follow_account_name = tool.find_sub_string(follow_info, 'title="', '"')
            follow_list[follow_account_id] = follow_account_name
        if max_page_count == 1:
            page_info = tool.find_sub_string(follow_pagination_response.content, '<div class="paging-wrap">', "</div>")
            if page_info:
                page_count_find = re.findall(r"friends\?p=(\d*)", page_info)
                max_page_count = max(list(map(int, page_count_find)))
        page_count += 1
    return follow_list
