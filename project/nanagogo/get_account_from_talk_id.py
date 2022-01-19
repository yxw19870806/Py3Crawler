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
from project.nanaGoGo import nanagogo

# 存放解析出的账号文件路径
ACCOUNT_ID_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "info/account.data"))


# 根据talk id获取全部参与者
def get_member_from_talk(talk_id):
    talk_index_url = "https://7gogo.jp/%s" % talk_id
    talk_index_response = net.request(talk_index_url, method="GET")
    account_list = {}
    if talk_index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(talk_index_response.status))
    talk_index_response_content = talk_index_response.data.decode(errors="ignore")
    script_json_html = tool.find_sub_string(talk_index_response_content, "window.__DEHYDRATED_STATES__ = ", "</script>")
    if not script_json_html:
        raise crawler.CrawlerException("页面截取talk信息失败\n%s" % talk_index_response_content)
    script_json = tool.json_decode(script_json_html)
    if script_json is None:
        raise crawler.CrawlerException("talk信息加载失败\n%s" % script_json_html)
    for member_info in crawler.get_json_value(script_json, "page:talk:service:entity:talkMembers", "members", type_check=list):
        account_list[crawler.get_json_value(member_info, "userId", type_check=str)] = crawler.get_json_value(member_info, "name", type_check=str).replace(" ", "")
    return account_list


def main():
    # 初始化类
    nanaGoGo_class = nanagogo.NanaGoGo()

    # 存档位置
    account_list = list(crawler.read_save_data(ACCOUNT_ID_FILE_PATH, 0, []).keys())
    for talk_id in nanaGoGo_class.account_list:
        try:
            member_list = get_member_from_talk(talk_id)
        except crawler.CrawlerException as e:
            output.print_msg(talk_id + " 获取成员失败，原因：%s" % e.message)
            continue
        for account_id in member_list:
            if account_id not in account_list:
                output.print_msg("%s %s" % (account_id, member_list[account_id]))
                file.write_file("%s\t%s" % (account_id, member_list[account_id]), ACCOUNT_ID_FILE_PATH)
                account_list.append(account_id)


if __name__ == "__main__":
    main()
