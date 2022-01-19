# -*- coding:UTF-8  -*-
"""
欅坂46公式Blog成员id获取
https://www.keyakizaka46.com/s/k46o/diary/member/list
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import re
from common import *
from project.keyakizaka46 import keyakizaka46_diary


# 从页面获取全部成员账号
def get_account_from_index():
    index_url = "https://www.keyakizaka46.com/s/k46o/diary/member/list"
    query_data = {"cd": "member"}
    index_response = net.request(index_url, method="GET", fields=query_data)
    account_list = {}
    if index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(index_response.status))
    index_response_content = index_response.data.decode(errors="ignore")
    member_list_data = tool.find_sub_string(index_response_content, '<ul class="thumb">', "</ul>")
    if not member_list_data:
        raise crawler.CrawlerException("页面截取账号列表失败\n%s" % index_response_content)
    member_list_find = re.findall("<li ([\S|\s]*?)</li>", member_list_data)
    for member_info in member_list_find:
        # 获取账号id
        account_id = tool.find_sub_string(member_info, "&ct=", '">')
        if not account_id:
            raise crawler.CrawlerException("账号信息截取账号id失败\n%s" % member_info)
        # 获取成员名字
        account_name = tool.find_sub_string(member_info, '<p class="name">', "</p>").strip().replace(" ", "")
        if not account_name:
            raise crawler.CrawlerException("账号信息截取成员名字失败\n%s" % member_info)
        account_list[account_id] = account_name
    return account_list


def main():
    # 初始化类
    keyakizaka46Diary_class = keyakizaka46_diary.Keyakizaka46Diary(extra_sys_config={crawler.SYS_NOT_CHECK_SAVE_DATA: True})

    # 存档位置
    account_list_from_api = get_account_from_index()
    if len(account_list_from_api) > 0:
        for account_id in account_list_from_api:
            if account_id not in keyakizaka46Diary_class.account_list:
                keyakizaka46Diary_class.account_list[account_id] = [account_id, "0", account_list_from_api[account_id]]
        temp_list = [keyakizaka46Diary_class.account_list[key] for key in sorted(keyakizaka46Diary_class.account_list.keys())]
        file.write_file(tool.list_to_string(temp_list), keyakizaka46Diary_class.save_data_path, file.WRITE_FILE_TYPE_REPLACE)


if __name__ == "__main__":
    main()
