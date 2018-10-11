# -*- coding:UTF-8  -*-
"""
微博图片爬虫
https://www.weibo.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import re
import time
import traceback
import urllib.parse
from common import *
from project.meipai import meipai

EACH_PAGE_PHOTO_COUNT = 20  # 每次请求获取的图片数量
INIT_SINCE_ID = "9999999999999999"
COOKIE_INFO = {"SUB": ""}


# 检测登录状态
def check_login():
    if "SUB" not in COOKIE_INFO or not COOKIE_INFO["SUB"]:
        return False
    cookies_list = {"SUB": COOKIE_INFO["SUB"]}
    index_url = "https://weibo.com/"
    index_response = net.http_request(index_url, method="GET", cookies_list=cookies_list)
    if index_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        return index_response.data.decode(errors="ignore").find("$CONFIG['islogin']='1';") >= 0
    return False


# 使用浏览器保存的cookie模拟登录请求，获取一个session级别的访问cookie
def init_session():
    login_url = "https://login.sina.com.cn/sso/login.php"
    query_data = {"url": "https://weibo.com"}
    login_response = net.http_request(login_url, method="GET", fields=query_data, cookies_list=COOKIE_INFO)
    if login_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        COOKIE_INFO.update(net.get_cookies_from_response_header(login_response.headers))
        return True
    return False


# 获取账号首页
def get_account_index_page(account_id):
    account_index_url = "https://weibo.com/u/%s" % account_id
    cookies_list = {"SUB": tool.generate_random_string(30)}
    result = {
        "account_page_id": None,  # 账号page id
    }
    account_index_response = net.http_request(account_index_url, method="GET", cookies_list=cookies_list)
    if account_index_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        # 获取账号page id
        account_page_id = tool.find_sub_string(account_index_response.data.decode(errors="ignore"), "$CONFIG['page_id']='", "'")
        if not crawler.is_integer(account_page_id):
            raise crawler.CrawlerException("账号不存在")
        result["account_page_id"] = account_page_id
    else:
        raise crawler.CrawlerException(crawler.request_failre(account_index_response.status))
    return result


# 检测图片是不是被微博自动删除的文件
def check_photo_invalid(file_path):
    file_md5 = file.get_file_md5(file_path)
    if file_md5 in ["14f2559305a6c96608c474f4ca47e6b0", "37b9e6dec174b68a545c852c63d4645a", "7bd88df2b5be33e1a79ac91e7d0376b5", "82af4714a8b2a5eea3b44726cfc9920d"]:
        return True
    return False


# 获取一页的图片信息
def get_one_page_photo(account_id, page_count):
    photo_pagination_url = "http://photo.weibo.com/photos/get_all"
    query_data = {
        "uid": account_id,
        "count": EACH_PAGE_PHOTO_COUNT,
        "page": page_count,
        "type": "3",
    }
    cookies_list = {"SUB": COOKIE_INFO["SUB"]}
    result = {
        "photo_info_list": [],  # 全部图片信息
        "is_over": False,  # 是否最后一页图片
    }
    photo_pagination_response = net.http_request(photo_pagination_url, method="GET", fields=query_data, cookies_list=cookies_list, json_decode=True)
    if photo_pagination_response.status == net.HTTP_RETURN_CODE_JSON_DECODE_ERROR and photo_pagination_response.data.find('<p class="txt M_txtb">用户不存在或者获取用户信息失败</p>'.encode()) >= 0:
        raise crawler.CrawlerException("账号不存在")
    elif photo_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(photo_pagination_response.status))
    if not crawler.check_sub_key(("data",), photo_pagination_response.json_data):
        raise crawler.CrawlerException("返回数据'data'字段不存在\n%s" % photo_pagination_response.json_data)
    if not crawler.check_sub_key(("total", "photo_list"), photo_pagination_response.json_data["data"]):
        raise crawler.CrawlerException("返回数据'data'字段格式不正确\n%s" % photo_pagination_response.json_data)
    if not crawler.is_integer(photo_pagination_response.json_data["data"]["total"]):
        raise crawler.CrawlerException("返回数据'total'字段类型不正确\n%s" % photo_pagination_response.json_data)
    if not isinstance(photo_pagination_response.json_data["data"]["photo_list"], list):
        raise crawler.CrawlerException("返回数据'photo_list'字段类型不正确\n%s" % photo_pagination_response.json_data)
    for photo_info in photo_pagination_response.json_data["data"]["photo_list"]:
        result_photo_info = {
            "photo_time": None,  # 图片上传时间
            "photo_id": None,  # 图片上传时间
            "photo_url": None,  # 图片地址
        }
        # 获取图片上传时间
        if not crawler.check_sub_key(("timestamp",), photo_info):
            raise crawler.CrawlerException("图片信息'timestamp'字段不存在\n%s" % photo_info)
        if not crawler.is_integer(photo_info["timestamp"]):
            raise crawler.CrawlerException("图片信息'timestamp'字段类型不正确\n%s" % photo_info)
        result_photo_info["photo_time"] = int(photo_info["timestamp"])
        # 获取图片id
        if not crawler.check_sub_key(("photo_id",), photo_info):
            raise crawler.CrawlerException("图片信息'photo_id'字段不存在\n%s" % photo_info)
        if not crawler.is_integer(photo_info["photo_id"]):
            raise crawler.CrawlerException("图片信息'photo_id'字段类型不正确\n%s" % photo_info)
        result_photo_info["photo_id"] = int(photo_info["photo_id"])
        # 获取图片地址
        if not crawler.check_sub_key(("pic_host", "pic_name"), photo_info):
            raise crawler.CrawlerException("图片信息'pic_host'或者'pic_name'字段不存在\n%s" % photo_info)
        result_photo_info["photo_url"] = photo_info["pic_host"] + "/large/" + photo_info["pic_name"]
        result["photo_info_list"].append(result_photo_info)
    # 检测是不是还有下一页 总的图片数量 / 每页显示的图片数量 = 总的页数
    result["is_over"] = page_count >= (photo_pagination_response.json_data["data"]["total"] * 1.0 / EACH_PAGE_PHOTO_COUNT)
    return result


# 获取一页的视频信息
# page_id -> 1005052535836307
def get_one_page_video(account_page_id, since_id):
    # https://weibo.com/p/aj/album/loading?type=video&since_id=9999999999999999&page_id=1005052535836307&page=1&ajax_call=1
    video_pagination_url = "https://weibo.com/p/aj/album/loading"
    query_data = {
        "type": "video",
        "since_id": since_id,
        "page_id": account_page_id,
        "ajax_call": "1",
        "__rnd": int(time.time() * 1000),
    }
    cookies_list = {"SUB": COOKIE_INFO["SUB"]}
    result = {
        "next_page_since_id": None,  # 下一页视频指针
        "video_play_url_list": [],  # 全部视频地址
    }
    video_pagination_response = net.http_request(video_pagination_url, method="GET", fields=query_data, cookies_list=cookies_list, json_decode=True)
    if video_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_pagination_response.status))
    if not crawler.check_sub_key(("code", "data"), video_pagination_response.json_data):
        raise crawler.CrawlerException("返回信息'code'或'data'字段不存在\n%s" % video_pagination_response.json_data)
    if not crawler.is_integer(video_pagination_response.json_data["code"]):
        raise crawler.CrawlerException("返回信息'code'字段类型不正确\n%s" % video_pagination_response.json_data)
    if int(video_pagination_response.json_data["code"]) != 100000:
        raise crawler.CrawlerException("返回信息'code'字段取值不正确\n%s" % video_pagination_response.json_data)
    page_html = video_pagination_response.json_data["data"]
    # 获取视频播放地址
    result["video_play_url_list"] = re.findall('<a target="_blank" href="([^"]*)"><div ', page_html)
    if len(result["video_play_url_list"]) == 0:
        if since_id != INIT_SINCE_ID or page_html.find("还没有发布过视频") == -1:
            raise crawler.CrawlerException("返回信息匹配视频地址失败\n%s" % video_pagination_response.json_data)
    # 获取下一页视频的指针
    next_page_since_id = tool.find_sub_string(page_html, "type=video&owner_uid=&viewer_uid=&since_id=", '">')
    if next_page_since_id:
        if not crawler.is_integer(next_page_since_id):
            raise crawler.CrawlerException("返回信息截取下一页指针失败\n%s" % video_pagination_response.json_data)
        result["next_page_since_id"] = next_page_since_id
    return result


# 从视频播放页面中提取下载地址
def get_video_url(video_play_url):
    video_url = None
    # http://miaopai.com/show/Gmd7rwiNrc84z5h6S9DhjQ__.htm
    if video_play_url.find("miaopai.com/show/") >= 0:  # 秒拍
        video_id = tool.find_sub_string(video_play_url, "miaopai.com/show/", ".")
        video_info_url = "http://gslb.miaopai.com/stream/%s.json" % video_id
        query_data = {"token": ""}
        video_info_response = net.http_request(video_info_url, method="GET", fields=query_data, json_decode=True)
        if video_info_response.status != net.HTTP_RETURN_CODE_SUCCEED:
            raise crawler.CrawlerException(crawler.request_failre(video_info_response.status))
        if not crawler.check_sub_key(("status", "result"), video_info_response.json_data):
            raise crawler.CrawlerException("返回信息'status'或'result'字段不存在\n%s" % video_info_response.json_data)
        if not crawler.is_integer(video_info_response.json_data["status"]):
            raise crawler.CrawlerException("返回信息'status'字段类型不正确\n%s" % video_info_response.json_data)
        if int(video_info_response.json_data["status"]) != 200:
            raise crawler.CrawlerException("返回信息'status'字段取值不正确\n%s" % video_info_response.json_data)
        if len(video_info_response.json_data["result"]) == 0:
            raise crawler.CrawlerException("返回信息'result'字段长度不正确\n%s" % video_info_response.json_data)
        for video_info in video_info_response.json_data["result"]:
            if crawler.check_sub_key(("path", "host", "scheme"), video_info):
                video_url = video_info["scheme"] + video_info["host"] + video_info["path"]
                break
        if video_url is None:
            raise crawler.CrawlerException("返回信息匹配视频地址失败\n%s" % video_info_response.json_data)
    # https://video.weibo.com/show?fid=1034:e608e50d5fa95410748da61a7dfa2bff
    elif video_play_url.find("video.weibo.com/show?fid=") >= 0:  # 微博视频
        cookies_list = {"SUB": COOKIE_INFO["SUB"]}
        video_play_response = net.http_request(video_play_url, method="GET", cookies_list=cookies_list)
        if video_play_response.status == net.HTTP_RETURN_CODE_SUCCEED:
            video_play_response_content = video_play_response.data.decode(errors="ignore")
            video_url = tool.find_sub_string(video_play_response_content, "video_src=", "&")
            if not video_url:
                video_url = tool.find_sub_string(video_play_response_content, 'flashvars="list=', '"')
            if not video_url:
                raise crawler.CrawlerException("页面截取视频地址失败\n%s" % video_play_response_content)
            video_url = urllib.parse.unquote(video_url)
            if video_url.find("//") == 0:
                video_url = "https:" + video_url
        elif video_play_response.status == 404:
            video_url = ""
        else:
            raise crawler.CrawlerException(crawler.request_failre(video_play_response.status))
    # https://www.meipai.com/media/98089758
    elif video_play_url.find("www.meipai.com/media") >= 0:  # 美拍
        video_play_response = net.http_request(video_play_url, method="GET")
        if video_play_response.status != net.HTTP_RETURN_CODE_SUCCEED:
            raise crawler.CrawlerException(crawler.request_failre(video_play_response.status))
        video_play_response_content = video_play_response.data.decode(errors="ignore")
        if video_play_response_content.decode().find('<p class="error-p">为建设清朗网络空间，视频正在审核中，暂时无法播放。</p>') > 0:
            video_url = ""
        else:
            video_url_find = re.findall('<meta content="([^"]*)" property="og:video:url">', video_play_response_content)
            if len(video_url_find) != 1:
                raise crawler.CrawlerException("页面匹配加密视频信息失败\n%s" % video_play_response_content)
            video_url = meipai.decrypt_video_url(video_url_find[0])
            if video_url is None:
                raise crawler.CrawlerException("加密视频地址解密失败\n%s" % video_url_find[0])
    # https://v.xiaokaxiu.com/v/0YyG7I4092d~GayCAhwdJQ__.html
    elif video_play_url.find("v.xiaokaxiu.com/v/") >= 0:  # 小咖秀
        video_id = video_play_url.split("/")[-1].split(".")[0]
        video_url = "https://gslb.miaopai.com/stream/%s.mp4" % video_id
    else:  # 其他视频，暂时不支持，收集看看有没有
        raise crawler.CrawlerException("未知的第三方视频\n%s" % video_play_url)
    return video_url


class Weibo(crawler.Crawler):
    def __init__(self, extra_config=None):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_DOWNLOAD_VIDEO: True,
            crawler.SYS_GET_COOKIE: ("sina.com.cn", "login.sina.com.cn"),
        }
        crawler.Crawler.__init__(self, sys_config, extra_config)

        # 设置全局变量，供子线程调用
        COOKIE_INFO.update(self.cookie_value)

        # 解析存档文件
        # account_id  last_photo_id  video_count  last_video_url  (account_name)
        self.account_list = crawler.read_save_data(self.save_data_path, 0, ["", "0", "0", ""])

        # 检测登录状态
        if not check_login():
            # 如果没有获得登录相关的cookie，则模拟登录并更新cookie
            if init_session() and check_login():
                pass
            else:
                log.error("没有检测到登录信息")
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

        log.step("全部下载完毕，耗时%s秒，共计图片%s张" % (self.get_run_time(), self.total_photo_count))


class Download(crawler.DownloadThread):
    def __init__(self, account_info, main_thread):
        crawler.DownloadThread.__init__(self, account_info, main_thread)
        self.account_id = self.account_info[0]
        if len(self.account_info) >= 5 and self.account_info[4]:
            self.display_name = self.account_info[4]
        else:
            self.display_name = self.account_info[0]
        self.step("开始")

    # 获取所有可下载图片
    def get_crawl_photo_list(self):
        page_count = 1
        unique_list = []
        photo_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的图片
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析第%s页图片" % page_count)

            # 获取指定一页图片的信息
            try:
                photo_pagination_response = get_one_page_photo(self.account_id, page_count)
            except crawler.CrawlerException as e:
                self.error("第%s页图片解析失败，原因：%s" % (page_count, e.message))
                raise

            self.trace("第%s页解析的全部图片：%s" % (page_count, photo_pagination_response["photo_info_list"]))
            self.step("第%s页解析获取%s张图片" % (page_count, len(photo_pagination_response["photo_info_list"])))

            # 寻找这一页符合条件的图片
            for photo_info in photo_pagination_response["photo_info_list"]:
                # 检查是否达到存档记录
                if photo_info["photo_id"] > int(self.account_info[1]):
                    # 新增图片导致的重复判断
                    if photo_info["photo_id"] in unique_list:
                        continue
                    else:
                        photo_info_list.append(photo_info)
                        unique_list.append(photo_info["photo_id"])
                else:
                    is_over = True
                    break

            if not is_over:
                if photo_pagination_response["is_over"]:
                    is_over = True
                else:
                    page_count += 1

        return photo_info_list

    # 获取所有可下载视频
    def get_crawl_video_list(self):
        # 获取账号首页
        try:
            account_index_response = get_account_index_page(self.account_id)
        except crawler.CrawlerException as e:
            self.error("首页解析失败，原因：%s" % e.message)
            raise

        video_play_url_list = []
        since_id = INIT_SINCE_ID
        is_over = False
        # 获取全部还未下载过需要解析的视频
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析since_id：%s页视频" % since_id)

            # 获取指定时间点后的一页视频信息
            try:
                video_pagination_response = get_one_page_video(account_index_response["account_page_id"], since_id)
            except crawler.CrawlerException as e:
                self.error("since_id：%s页视频解析失败，原因：%s" % (since_id, e.message))
                raise

            self.trace("since_id：%s页解析的全部视频：%s" % (since_id, video_pagination_response["video_play_url_list"]))
            self.step("since_id：%s页解析获取%s个视频" % (since_id, len(video_pagination_response["video_play_url_list"])))

            # 寻找这一页符合条件的视频
            for video_play_url in video_pagination_response["video_play_url_list"]:
                # 检查是否达到存档记录
                if self.account_info[3] != video_play_url:
                    video_play_url_list.append(video_play_url)
                else:
                    is_over = True
                    break

            if not is_over:
                if video_pagination_response["next_page_since_id"] is None:
                    is_over = True
                    # todo 没有找到历史记录如何处理
                    # 有历史记录，但此次直接获取了全部视频
                    if self.account_info[3] != "":
                        self.error("没有找到上次下载的最后一个视频地址")
                else:
                    # 设置下一页指针
                    since_id = video_pagination_response["next_page_since_id"]

        return video_play_url_list

    # 下载图片
    def crawl_photo(self, photo_info):
        photo_file_path = os.path.join(self.main_thread.photo_download_path, self.display_name, "%16d.%s" % (photo_info["photo_id"], net.get_file_type(photo_info["photo_url"], "jpg")))
        save_file_return = net.save_net_file(photo_info["photo_url"], photo_file_path)
        if save_file_return["status"] == 1:
            if check_photo_invalid(photo_file_path):
                path.delete_dir_or_file(photo_file_path)
                self.error("图片%s %s 资源已被删除，跳过" % (photo_info["photo_id"], photo_info["photo_url"]))
            else:
                # 设置临时目录
                self.step("图片%s下载成功" % photo_info["photo_id"])
        else:
            self.error("图片%s %s 下载失败，原因：%s" % (photo_info["photo_id"], photo_info["photo_url"], crawler.download_failre(save_file_return["code"])))

        # 图片下载完毕
        self.total_photo_count += 1  # 计数累加
        self.account_info[1] = str(photo_info["photo_id"])  # 设置存档记录

    # 解析单个视频
    def crawl_video(self, video_play_url):
        video_index = int(self.account_info[2]) + 1
        # 获取这个视频的下载地址
        try:
            video_url = get_video_url(video_play_url)
        except crawler.CrawlerException as e:
            self.error("第%s个视频 %s 解析失败，原因：%s" % (video_index, video_play_url, e.message))
            raise

        if video_url is "":
            self.step("第%s个视频 %s 跳过" % (video_index, video_play_url))
            return

        self.main_thread_check()  # 检测主线程运行状态
        self.step("开始下载第%s个视频 %s" % (video_index, video_url))

        video_file_path = os.path.join(self.main_thread.video_download_path, self.display_name, "%04d.mp4" % video_index)
        save_file_return = net.save_net_file(video_url, video_file_path)
        if save_file_return["status"] == 1:
            self.step("第%s个视频下载成功" % video_index)
        else:
            self.error("第%s个视频 %s（%s) 下载失败，原因：%s" % (video_index, video_play_url, video_url, crawler.download_failre(save_file_return["code"])))
            return

        # 视频下载完毕
        self.total_video_count += 1  # 计数累加
        self.account_info[2] = str(video_index)  # 设置存档记录
        self.account_info[3] = video_play_url  # 设置存档记录

    def run(self):
        try:
            # 图片下载
            if self.main_thread.is_download_photo:
                # 获取所有可下载图片
                photo_info_list = self.get_crawl_photo_list()
                self.step("需要下载的全部图片解析完毕，共%s张" % len(photo_info_list))

                # 从最早的图片开始下载
                while len(photo_info_list) > 0:
                    photo_info = photo_info_list.pop()
                    self.step("开始下载图片%s %s" % (photo_info["photo_id"], photo_info["photo_url"]))
                    self.crawl_photo(photo_info)
                    self.main_thread_check()  # 检测主线程运行状态

            # 视频下载
            if self.main_thread.is_download_video:
                # 获取所有可下载视频
                video_play_url_list = self.get_crawl_video_list()
                self.step("需要下载的全部视频片解析完毕，共%s个" % len(video_play_url_list))

                # 从最早的图片开始下载
                while len(video_play_url_list) > 0:
                    video_play_url = video_play_url_list.pop()
                    self.step("开始解析第%s个视频 %s" % (int(self.account_info[2]) + 1, video_play_url))
                    self.crawl_video(video_play_url)
                    self.main_thread_check()  # 检测主线程运行状态
        except SystemExit as se:
            if se.code == 0:
                self.step("提前退出")
            else:
                self.error("异常退出")
            # 如果临时目录变量不为空，表示同一时间的图片正在下载中，需要把下载了部分的内容给清理掉
            self.clean_temp_path()
        except Exception as e:
            self.error("未知异常")
            self.error(str(e) + "\n" + traceback.format_exc(), False)

        # 保存最后的信息
        with self.thread_lock:
            file.write_file("\t".join(self.account_info), self.main_thread.temp_save_data_path)
            self.main_thread.total_photo_count += self.total_photo_count
            self.main_thread.account_list.pop(self.account_id)
        self.step("下载完毕，总共获得%s张图片" % self.total_photo_count)
        self.notify_main_thread()


if __name__ == "__main__":
    Weibo().main()
