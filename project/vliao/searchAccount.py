# -*- coding:UTF-8  -*-
"""
V聊账号搜索
http://www.vliaoapp.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import *
from project.vliao import vLiaoCommon

SEARCH_TYPE_MATCH = "1"
SEARCH_TYPE_LOOKUP = "2"


# 搜索账号接口
def _search_account(account_name):
    search_url = "http://sp41.vliao12.com/user/search"
    post_data = {
        "userId": vLiaoCommon.USER_ID,
        "userKey": vLiaoCommon.USER_KEY,
        "keyword": account_name,
    }
    search_response = net.http_request(search_url, method="POST", fields=post_data, json_decode=True)
    if search_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(search_response.status))
    if not crawler.check_sub_key(("result", "data"), search_response.json_data):
        raise crawler.CrawlerException("返回信息`result`或`data`字段不存在\n%s" % search_response.json_data)
    if search_response.json_data["result"] is not True:
        raise crawler.CrawlerException("返回信息`result`字段取值不正确\n%s" % search_response.json_data)
    account_name_to_id_list = {}
    for search_result in search_response.json_data["data"]:
        if crawler.check_sub_key(("id", "realName"), search_result):
            account_name_to_id_list[search_result["realName"]] = str(search_result["id"])
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
    # 设置日志路径
    crawler.quicky_set_log_path()
    
    # 检测登录状态
    try:
        vLiaoCommon.check_login()
    except crawler.CrawlerException as e:
        log.error("登录失败，原因：%s" % e.message)
        tool.process_exit()

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
