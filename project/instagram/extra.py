# -*- coding:UTF-8  -*-
"""
Instagram公共方法
https://www.instagram.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import *

EACH_PAGE_ACCOUNT_COUNT = 50  # 每次请求获取的账号数量
COOKIE_INFO = {}


# 获取指定账号的全部粉丝列表（需要cookies）
# account_id -> 490060609
def get_follow_by_list(account_id):
    cursor = None
    follow_by_list = []
    while True:
        api_url = "https://www.instagram.com/query/"
        # node支持的字段：id,is_verified,followed_by_viewer,requested_by_viewer,full_name,profile_pic_url,username
        if cursor is None:
            post_data = {"q": "ig_user(%s){followed_by.first(%s){nodes{username},page_info}}" % (account_id, EACH_PAGE_ACCOUNT_COUNT)}
        else:
            post_data = {"q": "ig_user(%s){followed_by.after(%s,%s){nodes{username},page_info}}" % (account_id, cursor, EACH_PAGE_ACCOUNT_COUNT)}
        header_list = {"Referer": "https://www.instagram.com/", "X-CSRFToken": COOKIE_INFO["csrftoken"]}
        follow_by_pagination_response = net.request(api_url, method="POST", fields=post_data, header_list=header_list, cookies_list=COOKIE_INFO, json_decode=True)
        if follow_by_pagination_response.status == net.HTTP_RETURN_CODE_SUCCEED:
            for account_info in crawler.get_json_value(follow_by_pagination_response.json_data, "followed_by", "nodes", type_check=list):
                follow_by_list.append(crawler.get_json_value(account_info, "username", type_check=str))
            if crawler.get_json_value(follow_by_pagination_response.json_data, "followed_by", "page_info", "has_next_page", type_check=bool):
                cursor = crawler.get_json_value(follow_by_pagination_response.json_data, "followed_by", "page_info", "end_cursor", type_check=str)
                continue
        break
    return follow_by_list


# 获取指定账号的全部关注列表（需要cookies）
# account_id -> 490060609
def get_follow_list(account_id):
    cursor = None
    follow_list = []
    while True:
        api_url = "https://www.instagram.com/query/"
        # node支持的字段：id,is_verified,followed_by_viewer,requested_by_viewer,full_name,profile_pic_url,username
        if cursor is None:
            post_data = {"q": "ig_user(%s){follows.first(%s){nodes{username},page_info}}" % (account_id, EACH_PAGE_ACCOUNT_COUNT)}
        else:
            post_data = {"q": "ig_user(%s){follows.after(%s,%s){nodes{username},page_info}}" % (account_id, cursor, EACH_PAGE_ACCOUNT_COUNT)}
        header_list = {"Referer": "https://www.instagram.com/", "X-CSRFToken": COOKIE_INFO["csrftoken"]}
        follow_pagination_response = net.request(api_url, method="POST", fields=post_data, header_list=header_list, cookies_list=COOKIE_INFO, json_decode=True)
        if follow_pagination_response.status == net.HTTP_RETURN_CODE_SUCCEED:
            for account_info in crawler.get_json_value(follow_pagination_response.json_data, "follows", "nodes", type_check=list):
                follow_list.append(crawler.get_json_value(account_info, "username", type_check=str))
            if crawler.get_json_value(follow_pagination_response.json_data, "follows", "page_info", "has_next_page", type_check=bool):
                cursor = crawler.get_json_value(follow_pagination_response.json_data, "follows", "page_info", "end_cursor", type_check=str)
                continue
        break
    return follow_list
