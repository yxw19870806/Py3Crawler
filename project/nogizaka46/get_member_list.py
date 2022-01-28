# -*- coding:UTF-8  -*-
"""
乃木坂46 OFFICIAL BLOG成员id获取
https://blog.nogizaka46.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import re
from common import *
from project.nogizaka46 import nogizaka46_diary


# 从页面获取全部成员账号
def get_account_from_index():
    index_url = "https://blog.nogizaka46.com/"
    index_response = net.request(index_url, method="GET")
    account_list = {}
    if index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(index_response.status))
    index_response_content = index_response.data.decode(errors="ignore")
    member_list_find = re.findall('<div class="unit"><a href="./([^"]*)"><img src="[^>]*alt="([^"]*)" />', index_response_content)
    if len(member_list_find) == 0:
        raise crawler.CrawlerException("页面截取成员类别失败\n%s" % index_response_content)
    for member_info in member_list_find:
        account_list[member_info[0]] = member_info[1].replace(" ", "")
    return account_list


def main():
    # 初始化类
    nogizaka46Diary_class = nogizaka46_diary.Nogizaka46Diary(extra_sys_config={crawler.SYS_NOT_CHECK_SAVE_DATA: True})

    # 存档位置
    account_list_from_api = get_account_from_index()
    if len(account_list_from_api) > 0:
        for account_id in account_list_from_api:
            if account_id not in nogizaka46Diary_class.save_data:
                nogizaka46Diary_class.save_data[account_id] = [account_id, "", "0", account_list_from_api[account_id]]
        temp_list = [nogizaka46Diary_class.save_data[key] for key in sorted(nogizaka46Diary_class.save_data.keys())]
        file.write_file(tool.list_to_string(temp_list), nogizaka46Diary_class.save_data_path, file.WRITE_FILE_TYPE_REPLACE)


if __name__ == "__main__":
    main()
