# -*- coding:UTF-8  -*-
"""
Twitter REST API
https://dev.twitter.com/rest/reference
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import base64
import os
from common import *
from common import crypto, quicky

API_HOST = "https://api.twitter.com"
API_VERSION = "1.1"
ACCESS_TOKEN = None
token_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), r"info\session"))


def init():
    # 设置代理
    quicky.quickly_set_proxy()

    if ACCESS_TOKEN is not None:
        return True

    # 文件存在，检查格式是否正确
    if os.path.exists(token_file_path):
        api_info = tool.json_decode(crypto.Crypto().decrypt(file.read_file(token_file_path)), [])
        if tool.check_dict_sub_key(["api_key", "api_secret"], api_info):
            # 验证token是否有效
            if get_access_token(api_info["api_key"], api_info["api_secret"]):
                console.log("access token get succeed!")
                return True
            else:
                console.log("api info has expired")
        else:
            console.log("decrypt api info failure")
        # token已经无效了，删除掉
        path.delete_dir_or_file(token_file_path)
    console.log("Please input api info")
    while True:
        api_key = input("API KEY: ")
        api_secret = input("API SECRET; ")
        # 验证token是否有效
        if get_access_token(api_key, api_secret):
            # 加密保存到文件中
            if not os.path.exists(token_file_path):
                file.write_file(crypto.Crypto().encrypt(tool.json_encode({"api_key": api_key, "api_secret": api_secret})), token_file_path, const.WriteFileMode.REPLACE)
            console.log("access token get succeed!")
            return True
        console.log("incorrect api info, please type again!")


def get_access_token(api_key, api_secret):
    auth_url = API_HOST + "/oauth2/token"
    token = base64.b64encode(f"{api_key}:{api_secret}".encode()).decode()
    headers = {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
    }
    post_data = {
        "grant_type": "client_credentials"
    }
    response = net.Request(auth_url, method="POST", headers=headers, fields=post_data).enable_json_decode()
    if response.status == const.ResponseCode.SUCCEED:
        try:
            crawler.get_json_value(response.json_data, "token_type", type_check=str, value_check="bearer")
            global ACCESS_TOKEN
            ACCESS_TOKEN = crawler.get_json_value(response.json_data, "access_token", type_check=str)
        except CrawlerException:
            pass
        else:
            return True
    return False


def _get_api_url(end_point):
    return f"{API_HOST}/{API_VERSION}/{end_point}"


# 根据user_id获取用户信息
def get_user_info_by_user_id(user_id):
    api_url = _get_api_url("users/show.json")
    query_data = {"user_id": user_id}
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    response = net.Request(api_url, method="GET", fields=query_data, headers=headers).enable_json_decode()
    if response.status == const.ResponseCode.SUCCEED:
        return response.json_data
    return {}


# 关注指定用户
def follow_account(user_id):
    api_url = _get_api_url("friendships/create.json")
    api_url += f"?user_id={user_id}"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
    }
    response = net.Request(api_url, method="POST", headers=headers).enable_json_decode()
    if response.status == const.ResponseCode.SUCCEED:
        pass
    return False


if __name__ == "__main__":
    init()
