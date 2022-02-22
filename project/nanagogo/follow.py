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
from common import quicky
from project.nanagogo import nanagogo


# 关注指定账号
def follow_account(account_id):
    follow_api_url = f"https://api.7gogo.jp/web/v2/follow/users/{account_id}"
    post_data = {
        "userId": account_id,
    }
    header_list = {
        "X-7gogo-WebAuth": "yTRBxlzKsGnYfln9VQCx9ZQTZFERgoELVRh82k_lwDy=",
    }
    follow_response = net.request(follow_api_url, method="POST", fields=post_data, header_list=header_list, cookies_list=nanagogo.COOKIE_INFO, json_decode=True)
    if follow_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        output.print_msg(f"关注{account_id}失败，请求返回结果：{crawler.request_failre(follow_response.status)}，退出程序！")
        tool.process_exit()
    try:
        crawler.get_json_value(follow_response.json_data, "data", value_check=None)
        output.print_msg(f"关注{account_id}成功")
        return True
    except crawler.CrawlerException:
        output.print_msg(f"关注{account_id}失败，请求返回：{follow_response.json_data}，退出程序！")
        tool.process_exit()
    return False


class NanaGoGoFollow(nanagogo.NanaGoGo):
    def __init__(self, **kwargs):
        nanagogo.NanaGoGo.__init__(self, **kwargs)

    def main(self):
        count = 0
        for account_id in self.save_data:
            if follow_account(account_id):
                count += 1
            time.sleep(0.1)

        output.print_msg(f"关注完成，成功关注了{count}个账号")


if __name__ == "__main__":
    NanaGoGoFollow().main()
