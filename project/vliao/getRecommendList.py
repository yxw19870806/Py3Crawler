# -*- coding:UTF-8  -*-
"""
V聊app全推荐账号获取
http://www.vchat6.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import *
from project.vliao import vLiao

TAG_ID_LIST = [1]


# 从API获取所有推荐账号
def get_account_list_from_api():
    account_list = {}
    for tag_id in TAG_ID_LIST:
        try:
            tag_account_list = get_tag_account_list(tag_id)
        except crawler.CrawlerException as e:
            log.error("tag %s推荐账号解析失败，原因：%s" % (tag_id, e.message))
            raise
        log.trace("频道%s获取的全部推荐账号：%s" % (tag_id, tag_account_list))
        log.step("频道%s获取推荐账号%s个" % (tag_id, len(tag_account_list)))
        # 累加账号
        account_list.update(tag_account_list)
    return account_list


# 调用API获取tag内全部账号
def get_tag_account_list(tag_id):
    page_count = 1
    account_list = {}
    while True:
        log.step("开始解析tag %s第%s页推荐账号" % (tag_id, page_count))
        account_pagination_url = "http://v3.vliao3.xyz/v31/homepage"
        post_data = {
            "userId": vLiao.USER_ID,
            "userKey": vLiao.USER_KEY,
            "tagId": tag_id,
            "page": page_count,
        }
        account_pagination_response = net.http_request(account_pagination_url, method="POST", fields=post_data, json_decode=True)
        if account_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
            raise crawler.CrawlerException(crawler.request_failre(account_pagination_response.status))
        # 获取全部账号id
        if not crawler.check_sub_key(("data",), account_pagination_response.json_data):
            raise crawler.CrawlerException("返回信息'data'字段不存在\n%s" % account_pagination_response.json_data)
        for account_info in account_pagination_response.json_data["data"]:
            # 获取账号id
            if not crawler.check_sub_key(("id",), account_info):
                raise crawler.CrawlerException("账号信息'id'字段不存在\n%s" % account_info)
            if not crawler.is_integer(account_info["id"]):
                raise crawler.CrawlerException("账号信息'id'字段类型不正确\n%s" % account_info)
            account_id = str(account_info["id"])
            # 获取账号昵称
            if not crawler.check_sub_key(("nickname",), account_info):
                raise crawler.CrawlerException("账号信息'title'字段不存在\n%s" % account_info)
            account_name = account_info["nickname"]
            account_list[account_id] = account_name

        # 判断是不是最后一页
        if not crawler.check_sub_key(("maxPage",), account_pagination_response.json_data):
            raise crawler.CrawlerException("返回信息'maxPage'字段不存在\n%s" % account_pagination_response.json_data)
        if not crawler.is_integer(account_pagination_response.json_data["maxPage"]):
            raise crawler.CrawlerException("返回信息'maxPage'字段类型不正确\n%s" % account_pagination_response.json_data)
        if page_count >= int(account_pagination_response.json_data["maxPage"]):
            break
        else:
            page_count += 1
    return account_list


def main():
    # 初始化类
    vLiao_obj = vLiao.VLiao()

    account_list_from_api = get_account_list_from_api()
    if len(account_list_from_api) > 0:
        # 存档位置
        for account_id in account_list_from_api:
            if account_id not in vLiao_obj.account_list:
                vLiao_obj.account_list[account_id] = [account_id, "0", account_list_from_api[account_id]]
        temp_list = [vLiao_obj.account_list[key] for key in sorted(vLiao_obj.account_list.keys())]
        file.write_file(tool.list_to_string(temp_list), vLiao_obj.account_list, file.WRITE_FILE_TYPE_REPLACE)


if __name__ == "__main__":
    main()
