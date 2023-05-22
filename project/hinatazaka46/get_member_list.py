# -*- coding:UTF-8  -*-
"""
欅坂46公式Blog成员id获取
https://www.hinatazaka46.com/s/official/diary/member
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from pyquery import PyQuery as pq
from common import *
from project.hinatazaka46 import hinatazaka46_diary


# 从页面获取全部成员账号
def get_account_from_index():
    index_url = "https://www.hinatazaka46.com/s/official/diary/member"
    index_response = net.Request(index_url, method="GET")
    account_list = {}
    if index_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(index_response.status))
    member_info_list_selector = pq(index_response.content).find(".p-blog-face__group .p-blog-face__list")
    if member_info_list_selector.length == 0:
        raise CrawlerException("页面截取账号信息列表失败\n" + index_response.content)
    for member_index in range(member_info_list_selector.length):
        member_info_selector = member_info_list_selector.eq(member_index)
        # 获取账号id
        blog_url_path = member_info_selector.attr("href")
        if not blog_url_path:
            raise CrawlerException("账号信息截取blog地址失败\n" + member_info_selector.html())
        account_id = tool.find_sub_string(blog_url_path, "&ct=")
        if not tool.is_integer(account_id):
            raise CrawlerException("blog地址%s截取account id失败" % blog_url_path)
        # 获取成员名字
        account_name = member_info_selector.find(".c-blog-face__name").html()
        if not account_name:
            raise CrawlerException("账号信息截取成员名字失败\n" + member_info_selector.html())
        account_list[account_id] = account_name.strip().replace(" ", "")
    return account_list


def main():
    # 初始化类
    hinatazaka46diary_class = hinatazaka46_diary.Hinatazaka46Diary(extra_sys_config={const.SysConfigKey.NOT_CHECK_SAVE_DATA: True})

    # 存档位置
    account_list_from_api = get_account_from_index()
    if len(account_list_from_api) > 0:
        for account_id in account_list_from_api:
            if account_id not in hinatazaka46diary_class.save_data:
                hinatazaka46diary_class.save_data[account_id] = [account_id, "0", account_list_from_api[account_id]]
        temp_list = [hinatazaka46diary_class.save_data[key] for key in sorted(hinatazaka46diary_class.save_data.keys())]
        file.write_file(tool.dyadic_list_to_string(temp_list), hinatazaka46diary_class.save_data_path, const.WriteFileMode.REPLACE)


if __name__ == "__main__":
    main()
