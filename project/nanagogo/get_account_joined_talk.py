# -*- coding:UTF-8  -*-
"""
7gogo批量获取账号所参与的全部talk id
https://7gogo.jp/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from pyquery import PyQuery as pq
from common import *

# 存放账号的文件路径
ACCOUNT_ID_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "info/account.data"))
# 存放解析出的账号文件路径
TALK_ID_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "info/talk.data"))


# 获取account id文件
def get_account_from_file():
    account_list = {}
    for line in file.read_file(ACCOUNT_ID_FILE_PATH, const.ReadFileMode.LINE):
        split_temp = line.strip("\n\r").split("\t")
        account_list[split_temp[0]] = split_temp[1]
    return account_list


# 根据talk id获取全部参与者
def get_account_talks(account_id, account_name, talk_list):
    account_index = f"https://7gogo.jp/users/{account_id}"
    account_index_response = net.Request(account_index, method="GET")
    if account_index_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(account_index_response.status))
    talk_list_selector = pq(account_index_response.content).find(".UserTalkWrapper .UserTalk")
    for talk_index in range(talk_list_selector.length):
        talk_selector = talk_list_selector.eq(talk_index)
        # 获取talk地址
        talk_url_path = talk_selector.attr("href")
        if not talk_url_path:
            raise CrawlerException("talk信息截取talk地址失败\n" + talk_selector.html())
        talk_id = talk_url_path.replace("/", "")
        if not talk_id:
            raise CrawlerException(f"talk地址 {talk_url_path} 截取talk id失败")
        # 获取talk名字
        talk_name = talk_selector.find(".UserTalk__talkname").text()
        if not talk_name:
            raise CrawlerException("talk信息截取talk名字失败\n" + talk_selector.html())
        talk_name = tool.filter_emoji(talk_name.strip())
        # 获取talk描述
        talk_description = talk_selector.find(".UserTalk__description").text()
        if talk_description:
            talk_description = tool.filter_emoji(talk_description.strip())
        else:
            talk_description = ""
        if talk_id in talk_list:
            talk_list[talk_id]["account_list"].append(account_name)
        else:
            talk_list[talk_id] = {
                "account_list": [account_name],
                "talk_name": talk_name,
                "talk_description": talk_description,
            }
        console.log(account_id + ": " + talk_name + ", " + talk_description)


def main():
    account_list = get_account_from_file()
    talk_list = {}
    for account_id in account_list:
        try:
            get_account_talks(account_id, account_list[account_id], talk_list)
        except CrawlerException as e:
            console.log(e.http_error(f"账号{account_id}"))
    if len(talk_list) > 0:
        with open(TALK_ID_FILE_PATH, "w", encoding="UTF-8") as file_handle:
            for talk_id in talk_list:
                account_list = " & ".join(talk_list[talk_id]["account_list"])
                file_handle.write("\t".join([talk_id, talk_list[talk_id]["talk_name"], talk_list[talk_id]["talk_description"], account_list]))


if __name__ == "__main__":
    main()
