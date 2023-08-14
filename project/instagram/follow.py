# -*- coding:UTF-8  -*-
"""
Instagram批量关注
https://www.instagram.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import time
from common import *
from project.instagram import instagram

IS_FOLLOW_PRIVATE_ACCOUNT = False  # 是否对私密账号发出关注请求


# 获取账号首页
def get_account_index_page(account_name):
    account_index_url = f"https://www.instagram.com/{account_name}"
    account_index_response = net.Request(account_index_url, method="GET", cookies=instagram.COOKIES)
    result = {
        "is_follow": False,  # 是否已经关注
        "is_private": False,  # 是否私密账号
        "account_id": 0,  # 账号id
    }
    if account_index_response.status == const.ResponseCode.SUCCEED:
        # 获取账号id
        account_id = tool.find_sub_string(account_index_response.content, '"profilePage_', '"')
        if not tool.is_integer(account_id):
            raise CrawlerException("页面截取账号id失败\n" + account_index_response.content)
        result["account_id"] = int(account_id)
        # 判断是不是已经关注
        result["is_follow"] = tool.find_sub_string(account_index_response.content, '"followed_by_viewer": ', ",") == "true"
        # 判断是不是私密账号
        result["is_private"] = tool.find_sub_string(account_index_response.content, '"is_private": ', ",") == "true"
    elif account_index_response.status == 404:
        raise CrawlerException("账号不存在")
    else:
        raise CrawlerException(crawler.request_failre(account_index_response.status))
    return result


# 关注指定账号
def follow_account(account_name, account_id):
    follow_api_url = f"https://www.instagram.com/web/friendships/{account_id}/follow/"
    headers = {"Referer": "https://www.instagram.com/", "x-csrftoken": instagram.COOKIES["csrftoken"], "X-Instagram-AJAX": 1}
    follow_response = net.Request(follow_api_url, method="POST", headers=headers, cookies=instagram.COOKIES).enable_json_decode()
    if follow_response.status == const.ResponseCode.SUCCEED:
        follow_result = crawler.get_json_value(follow_response.json_data, "result", default_value="", type_check=str)
        if follow_result == "following":
            console.log(f"关注{account_name}成功")
            return True
        elif follow_result == "requested":
            console.log(f"私密账号{account_name}，已发送关注请求")
            return True
        elif not follow_result:
            console.log(f"关注{account_name}失败，返回内容不匹配\n{follow_response.json_data}")
            tool.process_exit()
        else:
            return False
    elif follow_response.status == 403 and follow_response.data == "Please wait a few minutes before you try again.":
        console.log(CrawlerException(f"关注{account_name}失败，连续关注太多等待一会儿继续尝试"))
        tool.process_exit()
    else:
        console.log(CrawlerException(f"关注{account_name}失败，请求返回结果：{crawler.request_failre(follow_response.status)}"))
        tool.process_exit()


class InstagramFollow(instagram.Instagram):
    def __init__(self, **kwargs):
        instagram.Instagram.__init__(self, **kwargs)

    def main(self):
        # 初始化类
        count = 0
        for account_name in sorted(self.save_data.keys()):
            try:
                account_index_response = get_account_index_page(account_name)
            except CrawlerException as e:
                log.error(e.http_error(f"账号{account_name}首页"))
                continue

            if account_index_response["is_follow"]:
                console.log(f"{account_name}已经关注，跳过")
            elif account_index_response["is_private"] and not IS_FOLLOW_PRIVATE_ACCOUNT:
                console.log(f"{account_name}是私密账号，跳过")
            else:
                if follow_account(account_name, account_index_response["account_id"]):
                    count += 1
                time.sleep(0.1)

        console.log(f"关注完成，成功关注了{count}个账号")


if __name__ == "__main__":
    InstagramFollow().main()
