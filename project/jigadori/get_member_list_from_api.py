# -*- coding:UTF-8  -*-
"""
グラドル自画撮り部 成员tweet账号获取
http://jigadori.fkoji.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import tkinter
from pyquery import PyQuery as pq
from tkinter import filedialog
from common import *
from project.jigadori import jigadori


# 从页面获取全部账号
def get_account_from_index():
    page_count = 1
    account_list = {}
    while True:
        try:
            pagination_account_list = get_one_page_account(page_count)
        except crawler.CrawlerException as e:
            output.print_msg(e.http_error(f"第{page_count}页账号"))
            break
        if pagination_account_list:
            account_list.update(pagination_account_list)
            page_count += 1
        else:
            break
    return account_list


# 获取一页账号
def get_one_page_account(page_count):
    account_pagination_url = "http://jigadori.fkoji.com/users"
    query_data = {"p": page_count}
    account_pagination_response = net.request(account_pagination_url, method="GET", fields=query_data)
    pagination_account_list = {}
    if account_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        crawler.CrawlerException(crawler.request_failre(account_pagination_response.status))
    account_list_selector = pq(account_pagination_response.data.decode(errors="ignore")).find(".users-list li")
    for account_index in range(0, account_list_selector.length):
        account_selector = account_list_selector.eq(account_index)
        # 获取成员名字
        account_name = account_selector.find(".profile-name").eq(0).text()
        if not account_name:
            account_name = ""
            # raise robot.CrawlerException("成员信息截取成员名字失败\n" + account_selector.html())
        else:
            account_name = account_name.strip()
        # 获取twitter账号
        account_id = account_selector.find(".screen-name a").text()
        if not account_id:
            raise crawler.CrawlerException("成员信息截取twitter账号失败\n" + account_selector.html())
        account_id = account_id.strip().replace("@", "")
        pagination_account_list[account_id] = account_name
    return pagination_account_list


def main():
    jigadori.Jigadori(extra_sys_config={crawler.SYS_NOT_CHECK_SAVE_DATA: True})
    # GUI窗口
    gui = tkinter.Tk()
    gui.withdraw()

    options = {
        "initialdir": os.path.abspath(os.path.join(crawler.PROJECT_ROOT_PATH, "project/twitter/info")),
        "initialfile": "save.data",
        "filetypes": [("data file", "*.data"), ("all files", "*")],
        "parent": gui,
    }
    save_data_path = tkinter.filedialog.asksaveasfilename(**options)
    if not save_data_path:
        tool.process_exit()

    account_list_from_api = get_account_from_index()
    if len(account_list_from_api) > 0:
        account_list_from_save_data = crawler.read_save_data(save_data_path, 0, [])
        for account_id in account_list_from_save_data:
            if account_id not in account_list_from_api:
                output.print_msg(f"{account_id} ({account_list_from_save_data[account_id]}) not found from API result")
        for account_id in account_list_from_api:
            if account_id not in account_list_from_save_data:
                account_list_from_save_data[account_id] = [account_id, "", "", "", "", account_list_from_api[account_id]]
            else:
                if len(account_list_from_save_data[account_id]) >= 6 and account_list_from_save_data[account_id][5] != account_list_from_api[account_id]:
                    output.print_msg(f"{account_id} name changed")
                    account_list_from_save_data[account_id][5] = account_list_from_api[account_id]
        temp_list = [account_list_from_save_data[key] for key in sorted(account_list_from_save_data.keys())]
        file.write_file(tool.list_to_string(temp_list), save_data_path, file.WRITE_FILE_TYPE_REPLACE)


if __name__ == "__main__":
    main()
