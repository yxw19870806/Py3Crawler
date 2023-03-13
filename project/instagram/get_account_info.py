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
    account_index_url = "https://www.instagram.com/%s/" % account_name
    account_index_response = net.request(account_index_url, method="GET")
    result = {
        "account_info": "",  # 自我介绍
        "external_url": "",  # 外部链接地址
    }
    if account_index_response.status == const.ResponseCode.SUCCEED:
        account_index_response_content = account_index_response.data.decode(errors="ignore")
        # 获取账号信息
        if account_index_response_content.find('"biography": null,') >= 0:
            result["account_info"] = ""
        else:
            account_info = tool.find_sub_string(account_index_response_content, '"biography": "', '"')
            if not account_info:
                raise crawler.CrawlerException("页面截取账号信息失败\n" + account_index_response_content)
            account_info = account_info.replace(r"\n", "").replace("'", chr(1))
            result["account_info"] = eval("u'%s'" % account_info).replace(chr(1), "'")
        # 获取外部链接地址
        if account_index_response_content.find('"external_url": null,') >= 0:
            result["external_url"] = ""
        else:
            result["external_url"] = tool.find_sub_string(account_index_response_content, '"external_url": "', '"')
    elif account_index_response.status == 404:
        raise crawler.CrawlerException("账号不存在")
    else:
        raise crawler.CrawlerException(crawler.request_failre(account_index_response.status))
    return result


def main():
    # 初始化类
    instagram_class = instagram.Instagram()

    result_file_path = os.path.join(os.path.dirname(__file__), "info/account_info.data")
    for account in sorted(instagram_class.save_data.keys()):
        try:
            account_index_response = get_account_index_page(account)
        except crawler.CrawlerException as e:
            output.print_msg(e.http_error("账号%s首页" % account))
            continue
        file.write_file("%s\t%s\t%s" % (account, account_index_response["account_info"], account_index_response["external_url"]), result_file_path)


if __name__ == "__main__":
    main()
