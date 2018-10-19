# -*- coding:UTF-8  -*-
"""
看了又看APP图片爬虫
http://share.yasaxi.com/share.html
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import json
import os
import time
import traceback
from common import *
from common import crypto

EACH_PAGE_PHOTO_COUNT = 20  # 每次请求获取的图片数量
ACCESS_TOKEN = ""
AUTH_TOKEN = ""
ZHEZHE_INFO = ""
SESSION_DATA_PATH = None


# 从文件中获取用户信息
def get_token_from_file():
    account_data = tool.json_decode(crypto.Crypto().decrypt(file.read_file(SESSION_DATA_PATH)))
    if account_data is None:
        return False
    if crawler.check_sub_key(("access_token", "auth_token", "zhezhe_info"), account_data):
        global ACCESS_TOKEN, AUTH_TOKEN, ZHEZHE_INFO
        ACCESS_TOKEN = account_data["access_token"]
        AUTH_TOKEN = account_data["auth_token"]
        ZHEZHE_INFO = account_data["zhezhe_info"]
        return True
    return False


# 输入token并加密保存到文件中
def set_token_to_file():
    access_token = input(crawler.get_time() + " 请输入access_token: ")
    auth_token = input(crawler.get_time() + " 请输入auth_token: ")
    zhezhe_info = input(crawler.get_time() + " 请输入zhezhe_info: ")
    account_data = {
        "access_token": access_token,
        "auth_token": auth_token,
        "zhezhe_info": zhezhe_info,
    }
    file.write_file(crypto.Crypto().encrypt(json.dumps(account_data)), SESSION_DATA_PATH, file.WRITE_FILE_TYPE_REPLACE)


# 获取指定页数的全部日志
def get_one_page_photo(account_id, cursor):
    photo_pagination_url = "https://api.yasaxi.com/statuses/user"
    query_data = {
        "userId": account_id,
        "cursor": cursor,
        "count": EACH_PAGE_PHOTO_COUNT,
    }
    header_list = {
        "x-access-token": ACCESS_TOKEN,
        "x-auth-token": AUTH_TOKEN,
        "x-zhezhe-info": ZHEZHE_INFO,
        "User-Agent": "User-Agent: Dalvik/1.6.0 (Linux; U; Android 4.4.2; Nexus 6 Build/KOT49H)",
    }
    result = {
        "is_over": False,  # 是否最后一页日志
        "next_page_cursor": None,  # 下一页图片指针
        "status_info_list": [],  # 全部状态信息
    }
    photo_pagination_response = net.http_request(photo_pagination_url, method="GET", fields=query_data, header_list=header_list, is_random_ip=False, json_decode=True)
    if photo_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(photo_pagination_response.status))
    # 异常返回
    if crawler.check_sub_key(("meta",), photo_pagination_response.json_data) and crawler.check_sub_key(("code",), photo_pagination_response.json_data["meta"]):
        if photo_pagination_response.json_data["meta"]["code"] == "NoMoreDataError":
            result["is_over"] = True
        elif photo_pagination_response.json_data["meta"]["code"] == "TooManyRequests":
            log.step("请求过于频繁，等待并重试")
            time.sleep(60)
            return get_one_page_photo(account_id, cursor)
        else:
            raise crawler.CrawlerException("返回信息'code'字段取值不正确\n%s" % photo_pagination_response.json_data)
    # 正常数据返回
    elif crawler.check_sub_key(("data",), photo_pagination_response.json_data):
        if not isinstance(photo_pagination_response.json_data["data"], list):
            raise crawler.CrawlerException("返回信息'data'字段类型不正确\n%s" % photo_pagination_response.json_data)
        if len(photo_pagination_response.json_data["data"]) == 0:
            raise crawler.CrawlerException("返回信息'data'字段长度不正确\n%s" % photo_pagination_response.json_data)
        for status_info in photo_pagination_response.json_data["data"]:
            result_status_info = {
                "id": None,  # 状态id
                "photo_url_list": [],  # 全部图片地址
            }
            # 获取状态id
            if not crawler.check_sub_key(("statusId",), status_info):
                raise crawler.CrawlerException("状态信息'statusId'字段不存在\n%s" % status_info)
            result_status_info["id"] = status_info["statusId"]
            # 获取图片、视频地址
            if not crawler.check_sub_key(("medias",), status_info):
                raise crawler.CrawlerException("状态信息'medias'字段不存在\n%s" % status_info)
            if not isinstance(status_info["medias"], list):
                raise crawler.CrawlerException("状态信息'medias'字段类型不正确\n%s" % status_info)
            if len(status_info["medias"]) == 0:
                raise crawler.CrawlerException("状态信息'medias'字段长度不正确\n%s" % status_info)
            for media_info in status_info["medias"]:
                # 带模糊效果的，XXXXX_b.webp
                # https://s3-us-west-2.amazonaws.com/ysx.status.2/1080/baf196caa043a88ecf35a4652fa6017648aa5a02_b.webp?AWSAccessKeyId=AKIAJGLBMFWYTNLTZTOA&Expires=1498737886&Signature=%2F5Gmp5HRNXkGnlwJ2aulGfEqhh8%3D
                # 原始图的，XXXXX.webp
                # https://s3-us-west-2.amazonaws.com/ysx.status.2/1080/7ec8bccbbf0d618d67170f77054e3931220e3c14.webp?AWSAccessKeyId=AKIAJGLBMFWYTNLTZTOA&Expires=1498737886&Signature=9hvWk62TmAAPq67Rn577WU8NyYI%3D
                if not crawler.check_sub_key(("origin", "downloadUrl", "thumb"), media_info):
                    raise crawler.CrawlerException("媒体信息'origin'、'downloadUrl'、'thumb'字段不存在\n%s" % media_info)
                if not crawler.check_sub_key(("mediaType",), media_info):
                    raise crawler.CrawlerException("媒体信息'mediaType'字段不存在\n%s" % media_info)
                if not crawler.is_integer(media_info["mediaType"]):
                    raise crawler.CrawlerException("媒体信息'mediaType'字段不存在\n%s" % media_info)
                if int(crawler.is_integer(media_info["mediaType"])) not in [1, 2]:
                    raise crawler.CrawlerException("媒体信息'mediaType'取值不正确\n%s" % media_info)
                # 优先使用downloadUrl
                if media_info["downloadUrl"]:
                    result_status_info["photo_url_list"].append(media_info["downloadUrl"])
                # 前次使用downloadUrl
                elif media_info["origin"]:
                    result_status_info["photo_url_list"].append(media_info["origin"])
                else:
                    # 视频，可能只有预览图
                    if int(media_info["mediaType"]) == 2:
                        if not media_info["thumb"]:
                            raise crawler.CrawlerException("媒体信息'downloadUrl'、'origin'、'thumb'字段都没有值\n%s" % media_info)
                        result_status_info["photo_url_list"].append(media_info["thumb"])
                    # 图片，不存在origin和downloadUrl，抛出异常
                    elif int(media_info["mediaType"]) == 1:
                        raise crawler.CrawlerException("媒体信息'origin'和'downloadUrl'字段都没有值\n%s" % media_info)
            result["status_info_list"].append(result_status_info)
        # 获取下一页指针
        if not crawler.check_sub_key(("next",), photo_pagination_response.json_data):
            raise crawler.CrawlerException("返回信息'next'字段不存在\n%s" % photo_pagination_response.json_data)
        if photo_pagination_response.json_data["next"] and crawler.is_integer(photo_pagination_response.json_data["next"]):
            result["next_page_cursor"] = int(photo_pagination_response.json_data["next"])
    else:
        raise crawler.CrawlerException("返回信息'code'或'data'字段不存在\n%s" % photo_pagination_response.json_data)
    return result


class Yasaxi(crawler.Crawler):
    def __init__(self, **kwargs):
        global SESSION_DATA_PATH

        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_NOT_CHECK_SAVE_DATA: True,
        }
        if "extra_app_config" not in kwargs:
            kwargs["extra_app_config"] = {}
        # 服务器有请求数量限制，所以取消多线程
        kwargs["extra_app_config"]["thread_count"] = 1
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 设置全局变量，供子线程调用
        SESSION_DATA_PATH = self.session_data_path

        # 解析存档文件
        # account_id  status_id
        self.account_list = crawler.read_save_data(self.save_data_path, 0, ["", ""])

        # 从文件中宏读取账号信息（访问token）
        if not get_token_from_file():
            while True:
                input_str = input(crawler.get_time() + " 未检测到api token，是否手动输入(y)es / (N)o：").lower()
                if input_str in ["y", "yes"]:
                    set_token_to_file()
                    break
                elif input_str in ["n", "no"]:
                    return

    def main(self):
        # 循环下载每个id
        thread_list = []
        for account_id in sorted(self.account_list.keys()):
            # 提前结束
            if not self.is_running():
                break

            # 开始下载
            thread = Download(self.account_list[account_id], self)
            thread.start()
            thread_list.append(thread)

            time.sleep(1)

        # 等待子线程全部完成
        while len(thread_list) > 0:
            thread_list.pop().join()

        # 未完成的数据保存
        if len(self.account_list) > 0:
            file.write_file(tool.list_to_string(list(self.account_list.values())), self.temp_save_data_path)

        # 重新排序保存存档文件
        crawler.rewrite_save_file(self.temp_save_data_path, self.save_data_path)

        log.step("全部下载完毕，耗时%s秒，共计图片%s张" % (self.get_run_time(), self.total_photo_count))


class Download(crawler.DownloadThread):
    def __init__(self, account_info, main_thread):
        crawler.DownloadThread.__init__(self, account_info, main_thread)

    def run(self):
        account_id = self.account_info[0]
        account_name = self.account_info[2]
        photo_count = 1

        try:
            log.step(account_name + " 开始")

            cursor = 0
            is_over = False
            first_status_id = None
            photo_path = os.path.join(self.main_thread.photo_download_path, account_name)
            while not is_over:
                self.main_thread_check()  # 检测主线程运行状态
                log.step(account_name + " 开始解析cursor '%s'的图片" % cursor)

                # 获取一页图片
                try:
                    photo_pagination_response = get_one_page_photo(account_id, cursor)
                except crawler.CrawlerException as e:
                    log.error(account_name + " cursor '%s'后的一页图片解析失败，原因：%s" % (cursor, e.message))
                    raise

                if photo_pagination_response["is_over"]:
                    break

                for status_info in photo_pagination_response["status_info_list"]:
                    # 检查是否达到存档记录
                    if status_info["id"] == self.account_info[1]:
                        is_over = True
                        break

                    # 新的存档记录
                    if first_status_id is None:
                        first_status_id = status_info["id"]

                    log.step(account_name + " 开始解析状态%s的图片" % status_info["id"])

                    for photo_url in status_info["photo_url_list"]:
                        self.main_thread_check()  # 检测主线程运行状态
                        file_name_and_type = photo_url.split("?")[0].split("/")[-1]
                        resolution = photo_url.split("?")[0].split("/")[-2]
                        file_name, file_type = file_name_and_type.split(".")
                        if file_name[-2:] != "_b" and resolution == "1080":
                            photo_file_path = os.path.join(photo_path, "origin/%s.%s" % (file_name, file_type))
                        else:
                            photo_file_path = os.path.join(photo_path, "other/%s.%s" % (file_name, file_type))
                        log.step(account_name + " 开始下载第%s张图片 %s" % (photo_count, photo_url))
                        save_file_return = net.save_net_file(photo_url, photo_file_path)
                        if save_file_return["status"] == 1:
                            log.step(account_name + " 第%s张图片下载成功" % photo_count)
                            photo_count += 1
                        else:
                            log.error(account_name + " 第%s张图片 %s 下载失败，原因：%s" % (photo_count, photo_url, crawler.download_failre(save_file_return["code"])))

                if not is_over:
                    if photo_pagination_response["next_page_cursor"] is not None:
                        cursor = photo_pagination_response["next_page_cursor"]
                    else:
                        is_over = True
            # 新的存档记录
            if first_status_id is not None:
                self.account_info[1] = first_status_id
        except SystemExit as se:
            if se.code == 0:
                log.step(account_name + " 提前退出")
            else:
                log.error(account_name + " 异常退出")
        except Exception as e:
            log.error(account_name + " 未知异常")
            log.error(str(e) + "\n" + traceback.format_exc())

        # 保存最后的信息
        with self.thread_lock:
            file.write_file("\t".join(self.account_info), self.main_thread.temp_save_data_path)
            self.main_thread.total_photo_count += photo_count - 1
            self.main_thread.account_list.pop(account_id)
        log.step(account_name + " 下载完毕，总共获得%s张图片" % (photo_count - 1))
        self.notify_main_thread()

if __name__ == "__main__":
    Yasaxi().main()
