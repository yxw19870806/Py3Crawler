# -*- coding:UTF-8  -*-
"""
V聊账号搜索
http://www.vchat6.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import *
from project.vliao import vLiao

SEARCH_TYPE_MATCH = "1"
SEARCH_TYPE_LOOKUP = "2"


# 搜索账号接口
def _search_account(account_name):
    search_url = "http://sp41.vliao12.com/user/search"
    post_data = {
        "userId": vLiao.USER_ID,
        "userKey": vLiao.USER_KEY,
        "keyword": account_name,
    }
    search_response = net.http_request(search_url, method="POST", fields=post_data, json_decode=True)
    if search_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(search_response.status))
    crawler.get_json_value(search_response.json_data, "result", type_check=True)
    account_name_to_id_list = {}
    for search_result in crawler.get_json_value(search_response.json_data, "data", type_check=list):
        account_name_to_id_list[crawler.get_json_value(search_result, "realName", type_check=str)] = crawler.get_json_value(search_result, "id", type_check=str)
    return account_name_to_id_list


# 搜索指定账号或模糊搜索某个关键词
def search_account(account_name, search_type):
    try:
        account_name_to_id_list = _search_account(account_name)
    except crawler.CrawlerException as e:
        log.error("搜索账号失败，原因：%s" % e.message)
        raise
    if search_type == SEARCH_TYPE_MATCH:
        if account_name in account_name_to_id_list:
            return {account_name: account_name_to_id_list[account_name]}
    elif search_type == SEARCH_TYPE_LOOKUP:
        return account_name_to_id_list
    return {}


def main():
    # 初始化类
    vLiao.VLiao()

    while True:
        search_type = input(crawler.get_time() + " 查找方式：完全匹配(1) / 模糊查找(2)：").lower()
        if search_type not in [SEARCH_TYPE_MATCH, SEARCH_TYPE_LOOKUP]:
            continue
        account_name = input(crawler.get_time() + " 查找内容：").lower()
        account_list = search_account(account_name, search_type)
        if len(account_list) == 0:
            log.step("没有找到账号")
        else:
            for account_name in account_list:
                output.print_msg("账号ID：%-10s, 昵称：%s" % (account_list[account_name], account_name), False)


if __name__ == "__main__":
    main()
