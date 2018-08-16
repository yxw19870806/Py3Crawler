# -*- coding:UTF-8  -*-
"""
7gogo批量关注
https://www.instagram.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import time
from common import *

COOKIE_INFO = {}


# 关注指定账号
def follow_account(account_id):
    follow_api_url = "https://api.7gogo.jp/web/v2/follow/users/%s" % account_id
    post_data = {
        "userId": account_id,
    }
    header_list = {
        "X-7gogo-WebAuth": "yTRBxlzKsGnYfln9VQCx9ZQTZFERgoELVRh82k_lwDy=",
    }
    follow_response = net.http_request(follow_api_url, method="POST", fields=post_data, header_list=header_list, cookies_list=COOKIE_INFO, json_decode=True)
    if follow_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        if crawler.check_sub_key(("data", "error"), follow_response.json_data) and follow_response.json_data["data"] is None:
            output.print_msg("关注%s成功" % account_id)
            return True
        else:
            output.print_msg("关注%s失败，请求返回：%s，退出程序！" % (account_id, follow_response.json_data))
            tool.process_exit()
    else:
        output.print_msg("关注%s失败，请求返回结果：%s，退出程序！" % (account_id, crawler.request_failre(follow_response.status)))
        tool.process_exit()
    return False


def main():
    # 获取cookies
    all_cookie_from_browser = crawler.quickly_get_all_cookies_from_browser()
    if "api.7gogo.jp" in all_cookie_from_browser and ".7gogo.jp" in all_cookie_from_browser:
        for cookie_key in all_cookie_from_browser["api.7gogo.jp"]:
            COOKIE_INFO[cookie_key] = all_cookie_from_browser["api.7gogo.jp"][cookie_key]
        for cookie_key in all_cookie_from_browser[".7gogo.jp"]:
            COOKIE_INFO[cookie_key] = all_cookie_from_browser[".7gogo.jp"][cookie_key]
    else:
        output.print_msg("没有检测到登录信息")
        tool.process_exit()

    # 读取存档文件
    account_list = crawler.read_save_data(crawler.quickly_get_save_data_path(), 0, [])

    count = 0
    for account_id in account_list:
        if follow_account(account_id):
            count += 1
        time.sleep(0.1)

    output.print_msg("关注完成，成功关注了%s个账号" % count)


if __name__ == "__main__":
    main()
