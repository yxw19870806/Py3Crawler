# -*- coding:UTF-8  -*-
"""
图虫图片爬虫
https://tuchong.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import time
import traceback
from common import *

PHOTO_COUNT_PER_PAGE = 20  # 每次请求获取的图片数量


# 获取账号首页
def get_account_index_page(account_name):
    if crawler.is_integer(account_name):
        account_index_url = "https://tuchong.com/%s" % account_name
    else:
        account_index_url = "https://%s.tuchong.com" % account_name
    account_index_response = net.http_request(account_index_url, method="GET", is_auto_redirect=False)
    result = {
        "account_id": None,  # 账号id（字母账号->数字账号)
    }
    if account_index_response.status == 301 and account_index_response.getheader("Location") == "https://tuchong.com/":
        raise crawler.CrawlerException("账号不存在")
    elif account_index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(account_index_response.status))
    account_index_response_content = account_index_response.data.decode(errors="ignore")
    account_id = tool.find_sub_string(account_index_response_content, 'site_id":"', '",')
    if not account_id:
        raise crawler.CrawlerException("页面截取site id失败\n%s" % account_index_response_content)
    if not crawler.is_integer(account_id):
        raise crawler.CrawlerException("site id类型不正确\n%s" % account_index_response_content)
    result["account_id"] = account_id
    return result


# 获取指定时间点起的一页相册信息列表
# account_name -> deer-vision
# account_id -> 1186455
# post_time -> 2016-11-11 11:11:11
def get_one_page_album(account_id, post_time):
    # https://deer-vision.tuchong.com/rest/sites/1186455/posts/2016-11-11%2011:11:11?limit=20
    album_pagination_url = "https://www.tuchong.com/rest/sites/%s/posts/%s" % (account_id, post_time)
    query_data = {"limit": PHOTO_COUNT_PER_PAGE}
    album_pagination_response = net.http_request(album_pagination_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "album_info_list": [],  # 全部图片信息
    }
    if album_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_pagination_response.status))
    if not crawler.check_sub_key(("posts", "result"), album_pagination_response.json_data):
        raise crawler.CrawlerException("返回数据'posts'或者'result'字段不存在\n%s" % album_pagination_response.json_data)
    if album_pagination_response.json_data["result"] != "SUCCESS":
        raise crawler.CrawlerException("返回数据'result'字段取值不正确\n%s" % album_pagination_response.json_data)
    for album_info in album_pagination_response.json_data["posts"]:
        result_photo_info = {
            "album_id": None,  # 相册id
            "album_time": None,  # 相册创建时间
            "album_title": "",  # 相册标题
            "photo_url_list": [],  # 全部图片地址
        }
        # 获取相册id
        if not crawler.check_sub_key(("post_id",), album_info):
            raise crawler.CrawlerException("相册信息'post_id'字段不存在\n%s" % album_info)
        if not crawler.is_integer(album_info["post_id"]):
            raise crawler.CrawlerException("相册信息'post_id'字段类型不正确\n%s" % album_info)
        result_photo_info["album_id"] = int(album_info["post_id"])
        # 获取相册标题
        if not crawler.check_sub_key(("title",), album_info):
            raise crawler.CrawlerException("相册信息'title'字段不存在\n%s" % album_info)
        result_photo_info["album_title"] = album_info["title"]
        # 获取图片地址
        if not crawler.check_sub_key(("image_count", "images"), album_info):
            raise crawler.CrawlerException("相册信息'photo_count'或'images'字段不存在\n%s" % album_info)
        if not crawler.check_sub_key(("image_count",), album_info):
            raise crawler.CrawlerException("相册信息'image_count'字段类型不正确\n%s" % album_info)
        if not isinstance(album_info["images"], list):
            raise crawler.CrawlerException("相册信息'images'字段类型不正确\n%s" % album_info)
        if len(album_info["images"]) != int(album_info["image_count"]):
            raise crawler.CrawlerException("相册信息'images'长度和'photo_count'数值不匹配\n%s" % album_info)
        for photo_info in album_info["images"]:
            if not crawler.check_sub_key(("img_id",), photo_info):
                raise crawler.CrawlerException("相册信息'img_id'字段不存在\n%s" % album_info)
            result_photo_info["photo_url_list"].append("https://photo.tuchong.com/%s/f/%s.jpg" % (account_id, photo_info["img_id"]))
        if int(album_info["image_count"]) > 0 and len(result_photo_info["photo_url_list"]) == 0:
            raise crawler.CrawlerException("相册信息匹配图片地址失败\n%s" % album_info)
        # 获取相册创建时间
        if not crawler.check_sub_key(("published_at",), album_info):
            raise crawler.CrawlerException("相册信息'published_at'字段不存在\n%s" % album_info)
        result_photo_info["album_time"] = album_info["published_at"]
        result["album_info_list"].append(result_photo_info)
    return result


class TuChong(crawler.Crawler):
    def __init__(self):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
        }
        crawler.Crawler.__init__(self, sys_config)

        # 解析存档文件
        # account_id  last_post_id
        self.account_list = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

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
        self.account_name = self.account_info[0]
        self.display_name = self.account_name
        self.step("开始")

    # 获取所有可下载相册
    def get_crawl_list(self, account_id):
        post_time = time.strftime('%Y-%m-%d %H:%M:%S')
        album_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的相册
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析%s后一页相册" % post_time)

            # 获取一页相册
            try:
                album_pagination_response = get_one_page_album(account_id, post_time)
            except crawler.CrawlerException as e:
                self.error("%s后一页相册解析失败，原因：%s" % (post_time, e.message))
                raise

            # 如果为空，表示已经取完了
            if len(album_pagination_response["album_info_list"]) == 0:
                break

            self.trace("%s后一页解析的全部相册：%s" % (post_time, album_pagination_response["album_info_list"]))
            self.step("%s后一页解析获取%s个相册" % (post_time, len(album_pagination_response["album_info_list"])))

            # 寻找这一页符合条件的相册
            for album_info in album_pagination_response["album_info_list"]:
                # 检查是否达到存档记录
                if album_info["album_id"] > int(self.account_info[1]):
                    album_info_list.append(album_info)
                    post_time = album_info["album_time"]
                else:
                    is_over = True
                    break

        return album_info_list

    # 解析单个相册
    def crawl_album(self, album_info):
        photo_index = 1
        # 过滤标题中不支持的字符
        album_title = path.filter_text(album_info["album_title"])
        if album_title:
            post_path = os.path.join(self.main_thread.photo_download_path, self.account_name, "%08d %s" % (album_info["album_id"], album_title))
        else:
            post_path = os.path.join(self.main_thread.photo_download_path, self.account_name, "%08d" % album_info["album_id"])
        self.temp_path_list.append(post_path)
        for photo_url in album_info["photo_url_list"]:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("相册%s《%s》开始下载第%s张图片 %s" % (album_info["album_id"], album_info["album_title"], photo_index, photo_url))

            file_path = os.path.join(post_path, "%s.jpg" % photo_index)
            save_file_return = net.save_net_file(photo_url, file_path)
            if save_file_return["status"] == 1:
                self.step("相册%s《%s》第%s张图片下载成功" % (album_info["album_id"], album_info["album_title"], photo_index))
                photo_index += 1
            else:
                self.error("相册%s《%s》第%s张图片 %s 下载失败，原因：%s" % (album_info["album_id"], album_info["album_title"], photo_index, photo_url, crawler.download_failre(save_file_return["code"])))

        # 相册内图片全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.total_photo_count += photo_index - 1  # 计数累加
        self.account_info[1] = str(album_info["album_id"])  # 设置存档记录

    def run(self):
        try:
            try:
                account_index_response = get_account_index_page(self.account_name)
            except crawler.CrawlerException as e:
                self.error("主页解析失败，原因：%s" % e.message)
                raise

            # 获取所有可下载相册
            album_info_list = self.get_crawl_list(account_index_response["account_id"])
            self.step("需要下载的全部相册解析完毕，共%s个" % len(album_info_list))

            # 从最早的相册开始下载
            while len(album_info_list) > 0:
                self.main_thread_check()  # 检测主线程运行状态
                album_info = album_info_list.pop()
                self.step("开始解析相册%s" % album_info["album_id"])
                self.crawl_album(album_info)
                self.main_thread_check()  # 检测主线程运行状态
        except SystemExit as se:
            if se.code == 0:
                self.step("提前退出")
            else:
                self.error("异常退出")
            # 如果临时目录变量不为空，表示某个相册正在下载中，需要把下载了部分的内容给清理掉
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
    TuChong().main()
