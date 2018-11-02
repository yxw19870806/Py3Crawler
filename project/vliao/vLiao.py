# -*- coding:UTF-8  -*-
"""
V聊视频爬虫
http://www.vchat6.com/
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

USER_ID = ""
USER_KEY = ""
SESSION_DATA_PATH = None


# 检查登录信息
def check_login():
    global USER_ID, USER_KEY
    # 文件存在，检查格式是否正确
    if SESSION_DATA_PATH is not None:
        api_info = tool.json_decode(crypto.Crypto().decrypt(file.read_file(SESSION_DATA_PATH)))
        if crawler.check_sub_key(("user_id", "user_key"), api_info):
            # 验证token是否有效
            if check_token(api_info["user_id"], api_info["user_key"]):
                # 设置全局变量
                USER_ID = api_info["user_id"]
                USER_KEY = api_info["user_key"]
                return True
            log.step("登录信息已过期")
        # token已经无效了，删除掉
        path.delete_dir_or_file(SESSION_DATA_PATH)
    while True:
        input_str = input(crawler.get_time() + " 未检测到api信息，是否手动输入手机号码+密码登录(1)、或者直接输入api信息进行验证(2)、或者退出程序(E)xit？").lower()
        if input_str in ["e", "exit"]:
            tool.process_exit()
        elif input_str not in ["1", "2"]:
            continue
        elif input_str == "1":
            phone_number = input(crawler.get_time() + " 请输入手机号：")
            password = input(crawler.get_time() + " 请输入密码：")
            # 模拟登录
            login_status, error_message = login(phone_number, password)
            if login_status is False:
                log.step("登录失败，原因：%s" % error_message)
                continue
        elif input_str == "2":
            user_id = input(crawler.get_time() + " 请输入USER ID: ")
            user_key = input(crawler.get_time() + " 请输入USER KEY; ")
            # 验证token是否有效
            if not check_token(user_id, user_key):
                log.step("无效的登录信息，请重新输入")
                continue
            # 设置全局变量
            USER_ID = user_id
            USER_KEY = user_key
        # 加密保存到文件中
        file.write_file(crypto.Crypto().encrypt(json.dumps({"user_id": USER_ID, "user_key": USER_KEY})), SESSION_DATA_PATH, file.WRITE_FILE_TYPE_REPLACE)
        return True
    return False


# 模拟使用手机号码+密码登录
def login(phone_number, password):
    global USER_ID, USER_KEY
    login_url = "http://sp40.vliao12.com/auth/phone-number-login"
    post_data = {
        "phoneNumber": phone_number,
        "password": password,
        "appVersion": "4.0",
    }
    login_response = net.http_request(login_url, method="POST", fields=post_data, json_decode=True)
    if login_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(login_response.status))
    # 判断是否登录成功
    if crawler.get_json_value(login_response.json_data, "result", type_check=bool) is False:
        return False, crawler.get_json_value(login_response.json_data, "errorMsg", type_check=str)
    # 获取token
    USER_ID = crawler.get_json_value(login_response.json_data, "user", "id", type_check=str)
    USER_KEY = crawler.get_json_value(login_response.json_data, "user", "userKey", type_check=str)
    return True, ""


# 验证user_id和user_key是否匹配
def check_token(user_id, user_key):
    index_url = "http://v3.vliao3.xyz/v31/user/mydata"
    post_data = {
        "userId": user_id,
        "userKey": user_key,
    }
    index_response = net.http_request(index_url, method="POST", fields=post_data, json_decode=True)
    if index_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        return crawler.get_json_value(index_response.json_data, "result", default_value=False, is_raise_exception=False, type_check=bool)
    return False


# 获取一页视频
def get_one_page_video(account_id, page_count):
    video_pagination_url = "http://v3.vliao3.xyz/v31/smallvideo/list"
    post_data = {
        "userId": USER_ID,
        "userKey": USER_KEY,
        "page": page_count,
        "vid": account_id,
    }
    video_pagination_response = net.http_request(video_pagination_url, method="POST", fields=post_data, json_decode=True)
    result = {
        "video_info_list": [],  # 全部视频信息
    }
    if video_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_pagination_response.status))
    if crawler.get_json_value(video_pagination_response.json_data, "result", type_check=bool) is False:
        if crawler.get_json_value(video_pagination_response.json_data, "errorCode", type_check=int) == 3:
            raise crawler.CrawlerException("账号不存在")
        else:
            raise crawler.CrawlerException("未知返回状态\n%s" % video_pagination_response.json_data)
    # 判断是不是最后一页
    result["is_over"] = crawler.get_json_value(video_pagination_response.json_data, "maxPage", type_check=int) <= page_count
    # 获取全部视频id
    for video_info in crawler.get_json_value(video_pagination_response.json_data, "data", type_check=list):
        result_video_info = {
            "video_id": None,  # 视频id
            "video_title": None,  # 视频id
        }
        # 获取视频id
        result_video_info["video_id"] = crawler.get_json_value(video_info, "id", type_check=int)
        # 获取视频标题
        result_video_info["video_title"] = crawler.get_json_value(video_info, "title", type_check=str)
        result["video_info_list"].append(result_video_info)
    return result


# 获取指定视频
def get_video_info_page(account_id, video_id):
    video_info_url = "http://v3.vliao3.xyz/v31/smallvideo/one"
    post_data = {
        "userId": USER_ID,
        "userKey": USER_KEY,
        "videoId": video_id,
        "vid": account_id,
    }
    video_info_response = net.http_request(video_info_url, method="POST", fields=post_data, json_decode=True)
    result = {
        "video_url": None,  # 视频地址
    }
    if video_info_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_info_response.status))
    result["video_url"] = crawler.get_json_value(video_info_response.json_data, "data", "url", type_check=str)
    return result


class VLiao(crawler.Crawler):
    def __init__(self, **kwargs):
        global SESSION_DATA_PATH

        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_VIDEO: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 设置全局变量，供子线程调用
        SESSION_DATA_PATH = self.session_data_path

        # 解析存档文件
        # account_id  video_id
        self.account_list = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

        # 检测登录状态
        try:
            check_login()
        except crawler.CrawlerException as e:
            log.error("登录失败，原因：%s" % e.message)
            tool.process_exit()

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

        log.step("全部下载完毕，耗时%s秒，共计视频%s个" % (self.get_run_time(), self.total_video_count))


class Download(crawler.DownloadThread):
    def __init__(self, account_info, main_thread):
        crawler.DownloadThread.__init__(self, account_info, main_thread)
        self.account_id = self.account_info[0]
        if len(self.account_info) >= 3 and self.account_info[2]:
            self.display_name = self.account_info[2]
        else:
            self.display_name = self.account_info[0]
        self.step("开始")

    # 获取所有可下载视频
    def get_crawl_list(self):
        page_count = 1
        video_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的视频
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析第%s页视频" % page_count)

            # 获取指定一页视频
            try:
                video_pagination_response = get_one_page_video(self.account_id, page_count)
            except crawler.CrawlerException as e:
                self.error("第%s页视频解析失败，原因：%s" % (page_count, e.message))
                raise

            self.trace("第%s页解析的全部视频：%s" % (page_count, video_pagination_response["video_info_list"]))
            self.step("第%s页解析获取%s个视频" % (page_count, len(video_pagination_response["video_info_list"])))

            # 寻找这一页符合条件的视频
            for video_info in video_pagination_response["video_info_list"]:
                # 检查是否达到存档记录
                if video_info["video_id"] > int(self.account_info[1]):
                    video_info_list.append(video_info)
                else:
                    is_over = True
                    break

            # 没有视频了
            if video_pagination_response["is_over"]:
                is_over = True
            else:
                page_count += 1

        return video_info_list

    # 解析单个视频
    def crawl_video(self, video_info):
        # 获取指定视频
        try:
            video_info_response = get_video_info_page(self.account_id, video_info["video_id"])
        except crawler.CrawlerException as e:
            self.error("视频%s 《%s》解析失败，原因：%s" % (video_info["video_id"], video_info["video_title"], e.message))
            raise

        # 视频下载
        self.main_thread_check()  # 检测主线程运行状态
        self.step("开始下载视频 %s 《%s》 %s" % (video_info["video_id"], video_info["video_title"], video_info_response["video_url"]))

        video_file_path = os.path.join(self.main_thread.video_download_path, self.display_name, "%06d %s.mp4" % (video_info["video_id"], path.filter_text(video_info["video_title"])))
        save_file_return = net.save_net_file(video_info_response["video_url"], video_file_path)
        if save_file_return["status"] == 1:
            self.step("视频 %s 《%s》下载成功" % (video_info["video_id"], video_info["video_title"]))
        else:
            self.error("视频 %s 《%s》 %s 下载失败，原因：%s" % (video_info["video_id"], video_info["video_title"], video_info_response["video_url"], crawler.download_failre(save_file_return["code"])))
            return

        # 媒体内图片和视频全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.total_video_count += 1  # 计数累加
        self.account_info[1] = str(video_info["video_id"])  # 设置存档记录

    def run(self):
        try:
            # 获取所有可下载视频
            video_info_list = self.get_crawl_list()
            self.step("需要下载的全部视频解析完毕，共%s个" % len(video_info_list))

            # 从最早的视频开始下载
            while len(video_info_list) > 0:
                video_info = video_info_list.pop()
                self.step("开始解析视频%s 《%s》" % (video_info["video_id"], video_info["video_title"]))
                self.crawl_video(video_info)
                self.main_thread_check()  # 检测主线程运行状态
        except SystemExit as se:
            if se.code == 0:
                self.step("提前退出")
            else:
                self.error("异常退出")
        except Exception as e:
            self.error("未知异常")
            self.error(str(e) + "\n" + traceback.format_exc(), False)

        # 保存最后的信息
        with self.thread_lock:
            file.write_file("\t".join(self.account_info), self.main_thread.temp_save_data_path)
            self.main_thread.total_video_count += self.total_video_count
            self.main_thread.account_list.pop(self.account_id)
        self.step("下载完毕，总共获得%s个视频" % self.total_video_count)
        self.notify_main_thread()


if __name__ == "__main__":
    VLiao().main()
