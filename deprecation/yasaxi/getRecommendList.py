# -*- coding:UTF-8  -*-
"""
看了又看APP全推荐账号获取
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import *
from deprecation.yasaxi import yasaxi


# 调用推荐API获取全部推荐账号
def get_account_from_api():
    api_url = "https://api.yasaxi.com/users/recommend"
    query_data = {"tag": ""}
    header_list = {
        "x-auth-token": yasaxi.AUTH_TOKEN,
        "x-zhezhe-info": yasaxi.ZHEZHE_INFO
    }
    account_list = {}
    api_response = net.http_request(api_url, method="GET", fields=query_data, header_list=header_list, json_decode=True)
    if api_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(api_response.status))
    if not crawler.check_sub_key(("data",), api_response.json_data):
        raise crawler.CrawlerException("返回信息'data'字段不存在\n%s" % api_response.json_data)
    for account_info in api_response.json_data["data"]:
        if not crawler.check_sub_key(("userId",), account_info):
            raise crawler.CrawlerException("账号信息'userId'字段不存在\n%s" % account_info)
        if not crawler.check_sub_key(("nick",), account_info):
            raise crawler.CrawlerException("账号信息'nick'字段不存在\n%s" % account_info)
        account_list[account_info["userId"]] = crawler.filter_emoji(account_info["nick"]).strip()
    return account_list


def main():
    # 初始化类
    yasaxi_obj = yasaxi.Yasaxi(extra_sys_config={crawler.SYS_NOT_CHECK_SAVE_DATA: True})

    # 存档位置
    try:
        account_list_from_api = get_account_from_api()
    except crawler.CrawlerException as e:
        output.print_msg("推荐账号解析失败，原因：%s" % e.message)
        raise
    if len(account_list_from_api) > 0:
        for account_id in account_list_from_api:
            if account_id not in yasaxi_obj.account_list:
                yasaxi_obj.account_list[account_id] = [account_id, "", account_list_from_api[account_id]]
        temp_list = [yasaxi_obj.account_list[key] for key in sorted(yasaxi_obj.account_list.keys())]
        file.write_file(tool.list_to_string(temp_list), yasaxi_obj.save_data_path, file.WRITE_FILE_TYPE_REPLACE)


if __name__ == "__main__":
    main()
