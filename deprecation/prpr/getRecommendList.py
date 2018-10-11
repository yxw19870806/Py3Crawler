# -*- coding:UTF-8  -*-
"""
PR社APP全推荐账号获取
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import *
from deprecation.prpr import prpr

EACH_PAGE_ACCOUNT_COUNT = 50


# 从API获取所有推荐账号
def get_account_list_from_api():
    try:
        channel_list = get_channel_from_api()
    except crawler.CrawlerException as e:
        output.print_msg("频道列表解析失败，原因：%s" % e.message)
        raise

    account_list = {}
    for channel_id in channel_list:
        try:
            channel_account_list = get_channel_account_from_api(channel_id)
        except crawler.CrawlerException as e:
            output.print_msg("频道%s推荐账号解析失败，原因：%s" % (channel_id, e.message))
            raise
        output.print_msg("频道%s获取推荐账号%s个" % (channel_id, len(channel_account_list)))
        # 累加账号
        account_list.update(channel_account_list)
    return account_list


# 获取全部推荐频道
def get_channel_from_api():
    api_url = "https://api.prpr.tinydust.cn/v3/channels/user/channels"
    api_response = net.http_request(api_url, method="GET", json_decode=True)
    channel_list = []
    if api_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(api_response.status))
    if not crawler.check_sub_key(("code",), api_response.json_data):
        raise crawler.CrawlerException("返回信息'code'字段不存在\n%s" % api_response.json_data)
    if not crawler.is_integer(api_response.json_data["code"]):
        raise crawler.CrawlerException("返回信息'code'字段类型不正确\n%s" % api_response.json_data)
    if int(api_response.json_data["code"]) != 200:
        raise crawler.CrawlerException("返回信息'code'字段取值不正确\n%s" % api_response.json_data)
    if not crawler.check_sub_key(("result",), api_response.json_data):
        raise crawler.CrawlerException("返回信息'result'字段不存在\n%s" % api_response.json_data)
    for channel_info in api_response.json_data["result"]:
        if not crawler.check_sub_key(("_id",), channel_info):
            raise crawler.CrawlerException("频道信息'_id'字段不存在\n%s" % channel_info)
        channel_list.append(channel_info["_id"])
    return channel_list


# 调用推荐API获取全部推荐账号
def get_channel_account_from_api(channel_id):
    page_count = 1
    account_list = {}
    while True:
        api_url = "https://api.prpr.tinydust.cn/v3/channels/%s/girls" % channel_id
        query_data = {
            "page": page_count,
            "limit": EACH_PAGE_ACCOUNT_COUNT,
        }
        api_response = net.http_request(api_url, method="GET", fields=query_data, json_decode=True)
        if api_response.status != net.HTTP_RETURN_CODE_SUCCEED:
            raise crawler.CrawlerException(crawler.request_failre(api_response.status))
        if not crawler.check_sub_key(("code",), api_response.json_data):
            raise crawler.CrawlerException("返回信息'code'字段不存在\n%s" % api_response.json_data)
        if not crawler.is_integer(api_response.json_data["code"]):
            raise crawler.CrawlerException("返回信息'code'字段类型不正确\n%s" % api_response.json_data)
        if int(api_response.json_data["code"]) != 200:
            raise crawler.CrawlerException("返回信息'code'字段取值不正确\n%s" % api_response.json_data)
        if not crawler.check_sub_key(("result",), api_response.json_data):
            raise crawler.CrawlerException("返回信息'result'字段不存在\n%s" % api_response.json_data)
        if len(api_response.json_data["result"]) == 0:
            break
        for account_info in api_response.json_data["result"]:
            if not crawler.check_sub_key(("_id",), account_info):
                raise crawler.CrawlerException("返回信息'_id'字段不存在\n%s" % account_info)
            if not crawler.check_sub_key(("nickname",), account_info):
                raise crawler.CrawlerException("返回信息'result'字段不存在\n%s" % account_info)
            account_list[account_info["_id"]] = path.filter_text(account_info["nickname"])
        page_count += 1
    return account_list


def main():
    # 初始化类
    prpr_obj = prpr.PrPr()

    account_list_from_api = get_account_list_from_api()
    if len(account_list_from_api) > 0:
        # 存档位置
        for account_id in account_list_from_api:
            if account_id not in prpr_obj.account_list:
                prpr_obj.account_list[account_id] = [account_id, "", account_list_from_api[account_id]]
        temp_list = [prpr_obj.account_list[key] for key in sorted(prpr_obj.account_list.keys())]
        file.write_file(tool.list_to_string(temp_list), prpr_obj.save_data_path, file.WRITE_FILE_TYPE_REPLACE)


if __name__ == "__main__":
    main()
