# -*- coding:UTF-8  -*-
"""
Instagram批量获取账号介绍
https://www.instagram.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from common import *
from project.instagram import instagram


# 获取账号首页
def get_account_index_page(account_name):
    account_index_url = f"https://www.instagram.com/{account_name}/"
    account_index_response = net.Request(account_index_url, method="GET")
    result = {
        "account_info": "",  # 自我介绍
        "external_url": "",  # 外部链接地址
    }
    if account_index_response.status == const.ResponseCode.SUCCEED:
        # 获取账号信息
        if account_index_response.content.find('"biography": null,') >= 0:
            result["account_info"] = ""
        else:
            account_info = tool.find_sub_string(account_index_response.content, '"biography": "', '"')
            if not account_info:
                raise CrawlerException("页面截取账号信息失败\n" + account_index_response.content)
            account_info = account_info.replace(r"\n", "").replace("'", chr(1))
            result["account_info"] = eval(f"u'{account_info}'").replace(chr(1), "'")
        # 获取外部链接地址
        if account_index_response.content.find('"external_url": null,') >= 0:
            result["external_url"] = ""
        else:
            result["external_url"] = tool.find_sub_string(account_index_response.content, '"external_url": "', '"')
    elif account_index_response.status == 404:
        raise CrawlerException("账号不存在")
    else:
        raise CrawlerException(crawler.request_failre(account_index_response.status))
    return result


def main():
    # 初始化类
    instagram_class = instagram.Instagram()

    result_file_path = os.path.join(os.path.dirname(__file__), "info/account_info.data")
    for account in sorted(instagram_class.save_data.keys()):
        try:
            account_index_response = get_account_index_page(account)
        except CrawlerException as e:
            console.log(e.http_error(f"账号{account}首页"))
            continue
        file.write_file("\t".join([account, account_index_response["account_info"], account_index_response["external_url"]]), result_file_path)


if __name__ == "__main__":
    main()
