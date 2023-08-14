# -*- coding:UTF-8  -*-
"""
7gogo批量关注
https://7gogo.jp/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import time
from common import *
from project.nanagogo import nanagogo


# 关注指定账号
def follow_account(account_id):
    follow_api_url = f"https://api.7gogo.jp/web/v2/follow/users/{account_id}"
    post_data = {
        "userId": account_id,
    }
    headers = {
        "X-7gogo-WebAuth": "yTRBxlzKsGnYfln9VQCx9ZQTZFERgoELVRh82k_lwDy=",
    }
    follow_response = net.Request(follow_api_url, method="POST", fields=post_data, headers=headers, cookies=nanagogo.COOKIES).enable_json_decode()
    if follow_response.status != const.ResponseCode.SUCCEED:
        console.log(f"关注{account_id}失败，请求返回结果：{crawler.request_failre(follow_response.status)}，退出程序！")
        tool.process_exit()
    try:
        crawler.get_json_value(follow_response.json_data, "data", value_check=None)
        console.log(f"关注{account_id}成功")
        return True
    except CrawlerException:
        console.log(f"关注{account_id}失败，请求返回：{follow_response.json_data}，退出程序！")
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

        console.log(f"关注完成，成功关注了{count}个账号")


if __name__ == "__main__":
    NanaGoGoFollow().main()
