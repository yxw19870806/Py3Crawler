# -*- coding:UTF-8  -*-
"""
7gogo批量获取参与talk的账号
https://7gogo.jp/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from common import *
from project.nanagogo import nanagogo

# 存放解析出的账号文件路径
ACCOUNT_ID_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "info/account.data"))


# 根据talk id获取全部参与者
def get_member_from_talk(talk_id):
    talk_index_url = "https://7gogo.jp/%s" % talk_id
    talk_index_response = net.Request(talk_index_url, method="GET")
    account_list = {}
    if talk_index_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(talk_index_response.status))
    script_json_html = tool.find_sub_string(talk_index_response.content, "window.__DEHYDRATED_STATES__ = ", "</script>")
    if not script_json_html:
        raise CrawlerException("页面截取talk信息失败\n" + talk_index_response.content)
    script_json = tool.json_decode(script_json_html)
    if script_json is None:
        raise CrawlerException("talk信息加载失败\n" + script_json_html)
    for member_info in crawler.get_json_value(script_json, "page:talk:service:entity:talkMembers", "members", type_check=list):
        account_id = crawler.get_json_value(member_info, "userId", type_check=str)
        account_name = crawler.get_json_value(member_info, "name", type_check=str).replace(" ", "")
        account_list[account_id] = account_name
    return account_list


def main():
    # 初始化类
    nanagogo_class = nanagogo.NanaGoGo()

    # 存档位置
    account_list = list(crawler.read_save_data(ACCOUNT_ID_FILE_PATH, 0, []).keys())
    for talk_id in nanagogo_class.save_data:
        try:
            member_list = get_member_from_talk(talk_id)
        except CrawlerException as e:
            log.info(e.http_error("talk %s" % talk_id))
            continue
        for account_id in member_list:
            if account_id not in account_list:
                log.info("%s %s" % (account_id, member_list[account_id]))
                file.write_file("%s\t%s" % (account_id, member_list[account_id]), ACCOUNT_ID_FILE_PATH)
                account_list.append(account_id)


if __name__ == "__main__":
    main()
