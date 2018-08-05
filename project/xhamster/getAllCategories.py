# -*- coding:UTF-8  -*-
"""
xhamster全部category下载
https://xhamster.com
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import string
from pyquery import PyQuery as pq
from common import *


# 获取指定orientation下的一页category
def get_one_page_categories(orientation, category_index):
    category_list = []
    if orientation == "straight":
        category_index_url = "https://xhamster.com/categories-%s" % category_index
    elif orientation in ["gay", "shemale"]:
        category_index_url = "https://xhamster.com/%s/categories-%s" % (orientation, category_index)
    else:
        return category_list
    category_index_response = net.http_request(category_index_url, method="GET")
    if category_index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        log.error(category_index_url + " " + crawler.request_failre(category_index_response.status))
    category_index_response_content = category_index_response.data.decode()
    category_list_selector = pq(category_index_response_content).find(".items .item")
    for index in range(0, category_list_selector.length):
        category_name = category_list_selector.eq(index).find("a").html()
        if category_name:
            category_list.append(category_name)
    return category_list


def main():
    crawler.quickly_set_proxy()

    for orientation in ["straight", "gay", "shemale"]:
        category_list = []
        for category_index in "0" + string.ascii_lowercase:
            category_list += get_one_page_categories(orientation, category_index)
        if len(category_list) > 0:
            category_file_path = os.path.join(os.path.dirname(__file__), "category\\%s.data" % orientation)
            tool.write_file("\n".join(category_list), category_file_path, tool.WRITE_FILE_TYPE_REPLACE)


if __name__ == "__main__":
    main()
