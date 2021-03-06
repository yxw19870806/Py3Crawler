# -*- coding:UTF-8  -*-
"""
Flickr图片爬虫
https://www.flickr.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import time
import traceback
from pyquery import PyQuery as pq
from common import *

EACH_PAGE_PHOTO_COUNT = 50  # 每次请求获取的图片数量
IS_LOGIN = False
COOKIE_INFO = {}


# 检测登录状态
def check_login():
    if not COOKIE_INFO:
        return False
    index_url = "https://www.flickr.com/"
    index_response = net.http_request(index_url, method="GET", cookies_list=COOKIE_INFO)
    if index_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        return index_response.data.decode(errors="ignore").find('data-track="gnYouMainClick"') >= 0
    return False


# 检测安全搜索设置
def check_safe_search():
    if not COOKIE_INFO:
        return False
    setting_url = "https://www.flickr.com/account/prefs/safesearch/"
    query_data = {
        "from": "privacy"
    }
    setting_response = net.http_request(setting_url, method="GET", fields=query_data, cookies_list=COOKIE_INFO, is_auto_redirect=False)
    if setting_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        if pq(setting_response.data.decode(errors="ignore")).find("input[name='safe_search']:checked").val() == "2":
            return True
    return False


# 获取账号相册首页
def get_account_index_page(account_name):
    account_index_url = "https://www.flickr.com/photos/%s" % account_name
    account_index_response = net.http_request(account_index_url, method="GET", cookies_list=COOKIE_INFO)
    result = {
        "site_key": None,  # site key
        "user_id": None,  # user id
        "csrf": None,  # csrf
    }
    if account_index_response.status == 404:
        raise crawler.CrawlerException("账号不存在")
    elif account_index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(account_index_response.status))
    account_index_response_content = account_index_response.data.decode(errors="ignore")
    # 获取user id
    user_id = tool.find_sub_string(tool.find_sub_string(account_index_response_content, "Y.ClientApp.init(", "},\n"), '"nsid":"', '"')
    if not user_id:
        raise crawler.CrawlerException("页面截取nsid失败\n%s" % account_index_response_content)
    if user_id.find("@N") == -1:
        raise crawler.CrawlerException("页面截取的nsid格式不正确\n%s" % account_index_response_content)
    result["user_id"] = user_id
    # 获取site key
    site_key = tool.find_sub_string(account_index_response_content, 'root.YUI_config.flickr.api.site_key = "', '"')
    if not site_key:
        raise crawler.CrawlerException("页面截取site key失败\n%s" % account_index_response_content)
    result["site_key"] = site_key
    # 获取CSRF
    root_auth = tool.find_sub_string(account_index_response_content, "root.auth = ", "};")
    if not site_key:
        raise crawler.CrawlerException("页面截取root.auth失败\n%s" % account_index_response_content)
    csrf = tool.find_sub_string(root_auth, '"csrf":"', '",')
    if IS_LOGIN and not csrf:
        raise crawler.CrawlerException("页面截取csrf失败\n%s" % account_index_response_content)
    result["csrf"] = csrf
    # 获取cookie_session
    if IS_LOGIN and "cookie_session" not in COOKIE_INFO:
        set_cookies = net.get_cookies_from_response_header(account_index_response.headers)
        if not crawler.check_sub_key(("cookie_session",), set_cookies):
            raise crawler.CrawlerException("请求返回cookie匹配cookie_session失败\n%s" % account_index_response.headers)
        COOKIE_INFO.update({"cookie_session": set_cookies["cookie_session"]})
    return result


# 获取指定页数的全部图片
# user_id -> 36587311@N08
def get_one_page_photo(user_id, page_count, api_key, csrf, request_id):
    api_url = "https://api.flickr.com/services/rest"
    # API文档：https://www.flickr.com/services/api/flickr.people.getPhotos.html
    # 全部可支持的参数
    # extras = [
    #     "can_addmeta", "can_comment", "can_download", "can_share", "contact", "count_comments", "count_faves",
    #     "count_views", "date_taken", "date_upload", "description", "icon_urls_deep", "isfavorite", "ispro", "license",
    #     "media", "needs_interstitial", "owner_name", "owner_datecreate", "path_alias", "realname", "rotation",
    #     "safety_level", "secret_k", "secret_h", "url_c", "url_f", "url_h", "url_k", "url_l", "url_m", "url_n",
    #     "url_o", "url_q", "url_s", "url_sq", "url_t", "url_z", "visibility", "visibility_source", "o_dims",
    #     "is_marketplace_printable", "is_marketplace_licensable", "publiceditability"
    # ]
    # content_type
    #   1 for photos only.
    #   2 for screenshots only.
    #   3 for 'other' only.
    #   4 for photos and screenshots.
    #   5 for screenshots and 'other'.
    #   6 for photos and 'other'.
    #   7 for photos, screenshots, and 'other' (all).
    # privacy_filter
    #   1 public photos
    #   2 private photos visible to friends
    #   3 private photos visible to family
    #   4 private photos visible to friends & family
    #   5 completely private photos
    # safe_search
    #   1 for safe.
    #   2 for moderate.
    #   3 for restricted.
    query_data = {
        "method": "flickr.people.getPhotos",
        "view_as": "use_pref",
        "sort": "use_pref",
        "format": "json",
        "nojsoncallback": 1,
        "privacy_filter ": 1,
        "safe_search": 3,
        "content_type": 7,
        "get_user_info": 0,
        "per_page": EACH_PAGE_PHOTO_COUNT,
        "page": page_count,
        "user_id": user_id,
        "api_key": api_key,
        "reqId": request_id,
        "csrf": csrf,
        "extras": "date_upload,url_c,url_f,url_h,url_k,url_l,url_m,url_n,url_o,url_q,url_s,url_sq,url_t,url_z",
    }
    # COOKIE_INFO = {}
    photo_pagination_response = net.http_request(api_url, method="GET", fields=query_data, cookies_list=COOKIE_INFO, json_decode=True)
    result = {
        "photo_info_list": [],  # 全部图片信息
        "is_over": False,  # 是否最后一页图片
    }
    if photo_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(photo_pagination_response.status))
    # 获取图片信息
    for photo_info in crawler.get_json_value(photo_pagination_response.json_data, "photos", "photo", type_check=list):
        result_photo_info = {
            "photo_id": None,  # 图片id
            "photo_time": None,  # 图片上传时间
            "photo_url": None,  # 图片地址
        }
        # 获取图片id
        result_photo_info["photo_id"] = crawler.get_json_value(photo_info, "id", type_check=int)
        # 获取图片上传时间
        result_photo_info["photo_time"] = crawler.get_json_value(photo_info, "dateupload", type_check=int)
        # 获取图片地址
        max_resolution = 0
        max_resolution_photo_type = ""
        # 可获取图片尺寸中最大的那张
        for photo_type in ["c", "f", "h", "k", "l", "m", "n", "o", "q", "s", "sq", "t", "z"]:
            if crawler.check_sub_key(("width_" + photo_type, "height_" + photo_type), photo_info):
                resolution = int(photo_info["width_" + photo_type]) * int(photo_info["height_" + photo_type])
                if resolution > max_resolution:
                    max_resolution = resolution
                    max_resolution_photo_type = photo_type
        if not max_resolution_photo_type:
            raise crawler.CrawlerException("图片信息匹配最高分辨率的图片尺寸失败\n%s" % photo_info)
        if crawler.check_sub_key(("url_" + max_resolution_photo_type + "_cdn",), photo_info):
            result_photo_info["photo_url"] = photo_info["url_" + max_resolution_photo_type + "_cdn"]
        elif crawler.check_sub_key(("url_" + max_resolution_photo_type,), photo_info):
            result_photo_info["photo_url"] = photo_info["url_" + max_resolution_photo_type]
        else:
            raise crawler.CrawlerException("图片信息'url_%s_cdn'或者'url_%s_cdn'字段不存在\n%s" % (max_resolution_photo_type, max_resolution_photo_type, photo_info))
        result["photo_info_list"].append(result_photo_info)
    if len(result["photo_info_list"]) == 0:
        raise crawler.CrawlerException("页面截取图片信息失败\n%s" % photo_pagination_response.json_data)
    # 判断是不是最后一页
    if page_count >= int(photo_pagination_response.json_data["photos"]["pages"]):
        result["is_over"] = True
    return result


class Flickr(crawler.Crawler):
    def __init__(self, **kwargs):
        global COOKIE_INFO, IS_LOGIN

        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_SET_PROXY: True,
            crawler.SYS_GET_COOKIE: ("flickr.com",),
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 设置全局变量，供子线程调用
        COOKIE_INFO = self.cookie_value

        # 解析存档文件
        # account_id  last_photo_time
        self.account_list = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

        # 检测登录状态
        console_string = ""
        if check_login():
            IS_LOGIN = True
            # 检测safe search开启状态
            if not check_safe_search():
                console_string = "账号安全搜尋已开启"
        else:
            console_string = "没有检测到账号登录状态"
        while console_string:
            input_str = input(crawler.get_time() + " %s，可能无法解析受限制的图片，继续程序(C)ontinue？或者退出程序(E)xit？:" % console_string)
            input_str = input_str.lower()
            if input_str in ["e", "exit"]:
                tool.process_exit()
            elif input_str in ["c", "continue"]:
                COOKIE_INFO = {}
                break

    def main(self):
        try:
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
        except KeyboardInterrupt:
            self.stop_process()

        # 未完成的数据保存
        if len(self.account_list) > 0:
            file.write_file(tool.list_to_string(list(self.account_list.values())), self.temp_save_data_path)

        # 重新排序保存存档文件
        crawler.rewrite_save_file(self.temp_save_data_path, self.save_data_path)

        log.step("全部下载完毕，耗时%s秒，共计图片%s张" % (self.get_run_time(), self.total_photo_count))


class Download(crawler.DownloadThread):
    request_id = tool.generate_random_string(8)  # 生成一个随机的request id用作访问（模拟页面传入）

    def __init__(self, account_info, main_thread):
        crawler.DownloadThread.__init__(self, account_info, main_thread)
        self.account_name = self.account_info[0]
        self.display_name = self.account_name
        self.step("开始")

    # 获取所有可下载图片
    def get_crawl_list(self, user_id, site_key, csrf):
        page_count = 1
        photo_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的图片
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析第%s页图片" % page_count)

            # 获取一页图片
            try:
                photo_pagination_response = get_one_page_photo(user_id, page_count, site_key, csrf, self.request_id)
            except crawler.CrawlerException as e:
                self.error("第%s页图片解析失败，原因：%s" % (page_count, e.message))
                raise

            self.trace("第%s页解析的全部图片：%s" % (page_count, photo_pagination_response["photo_info_list"]))
            self.step("第%s页解析获取%s张图片" % (page_count, len(photo_pagination_response["photo_info_list"])))

            # 寻找这一页符合条件的图片
            for photo_info in photo_pagination_response["photo_info_list"]:
                # 检查是否达到存档记录
                # photo_id是唯一的，但并不是递增的（分表主键），无法作为存档的判断依据
                if photo_info["photo_time"] > int(self.account_info[1]):
                    photo_info_list.append(photo_info)
                else:
                    is_over = True
                    break

            if not is_over:
                if photo_pagination_response["is_over"]:
                    is_over = True
                else:
                    page_count += 1

        return photo_info_list

    # 下载同一上传时间的所有图片
    def crawl_photo(self, photo_info_list):
        for photo_info in photo_info_list:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始下载图片%s %s" % (photo_info["photo_id"], photo_info["photo_url"]))
            file_path = os.path.join(self.main_thread.photo_download_path, self.account_name, "%011d.%s" % (photo_info["photo_id"], net.get_file_type(photo_info["photo_url"])))
            save_file_return = net.save_net_file(photo_info["photo_url"], file_path)
            if save_file_return["status"] == 1:
                # 设置临时目录
                self.temp_path_list.append(file_path)
                self.step("图片%s下载成功" % photo_info["photo_id"])
            else:
                self.error("图片%s %s 下载失败，原因：%s" % (photo_info["photo_id"], photo_info["photo_url"], crawler.download_failre(save_file_return["code"])))

        # 图片下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.total_photo_count += len(photo_info_list)  # 计数累加
        self.account_info[1] = str(photo_info_list[0]["photo_time"])  # 设置存档记

    def run(self):
        try:
            # 获取相册首页页面
            try:
                account_index_response = get_account_index_page(self.account_name)
            except crawler.CrawlerException as e:
                self.error("相册首页解析失败，原因：%s" % e.message)
                raise

            # 获取所有可下载图片
            photo_info_list = self.get_crawl_list(account_index_response["user_id"], account_index_response["site_key"], account_index_response["csrf"])
            self.step("需要下载的全部图片解析完毕，共%s张" % len(photo_info_list))

            # 从最早的图片开始下载
            deal_photo_info_list = []
            while len(photo_info_list) > 0:
                photo_info = photo_info_list.pop()
                # 下一张图片的上传时间一致，合并下载
                deal_photo_info_list.append(photo_info)
                if len(photo_info_list) > 0 and photo_info_list[-1]["photo_time"] == photo_info["photo_time"]:
                    continue

                # 下载同一上传时间的所有图片
                self.crawl_photo(deal_photo_info_list)
                deal_photo_info_list = []  # 累加图片地址清除
                self.main_thread_check()  # 检测主线程运行状态
        except (SystemExit, KeyboardInterrupt) as e:
            if isinstance(e, SystemExit) and e.code == 1:
                self.error("异常退出")
            else:
                self.step("提前退出")
            # 如果临时目录变量不为空，表示同一时间的图片正在下载中，需要把下载了部分的内容给清理掉
            self.clean_temp_path()
        except Exception as e:
            self.error("未知异常")
            self.error(str(e) + "\n" + traceback.format_exc(), False)

        # 保存最后的信息
        with self.thread_lock:
            file.write_file("\t".join(self.account_info), self.main_thread.temp_save_data_path)
            self.main_thread.total_photo_count += self.total_photo_count
            self.main_thread.account_list.pop(self.account_name)
        self.step("下载完毕，总共获得%s张图片" % self.total_photo_count)
        self.notify_main_thread()


if __name__ == "__main__":
    Flickr().main()
