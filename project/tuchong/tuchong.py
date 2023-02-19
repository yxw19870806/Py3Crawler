# -*- coding:UTF-8  -*-
"""
图虫图片爬虫
https://tuchong.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from common import *

EACH_PAGE_PHOTO_COUNT = 20  # 每次请求获取的图片数量


# 获取账号首页
def get_account_index_page(account_name):
    if tool.is_integer(account_name):
        account_index_url = "https://tuchong.com/%s" % account_name
    else:
        account_index_url = "https://%s.tuchong.com" % account_name
    account_index_response = net.request(account_index_url, method="GET", is_auto_redirect=False)
    result = {
        "account_id": 0,  # 账号id（字母账号->数字账号)
    }
    if account_index_response.status == 302 and account_index_response.getheader("Location").find("https://tuchong.com/") == 0 and account_index_response.getheader("Location")[-5:] == "/work":
        account_index_url += "/work"
        account_index_response = net.request(account_index_url, method="GET", is_auto_redirect=False)
    if account_index_response.status == 301 and account_index_response.getheader("Location") == "https://tuchong.com/":
        raise crawler.CrawlerException("账号不存在")
    elif account_index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(account_index_response.status))
    account_index_response_content = account_index_response.data.decode(errors="ignore")
    account_id = tool.find_sub_string(account_index_response_content, 'site_id":"', '",')
    if not account_id:
        raise crawler.CrawlerException("页面截取site id失败\n" + account_index_response_content)
    if not tool.is_integer(account_id):
        raise crawler.CrawlerException("site id类型不正确\n" + account_index_response_content)
    result["account_id"] = int(account_id)
    return result


# 获取指定时间点起的一页相册信息列表
# account_name -> deer-vision
# account_id -> 1186455
# post_time -> 2016-11-11 11:11:11
def get_one_page_album(account_id, post_time):
    # https://deer-vision.tuchong.com/rest/sites/1186455/posts/2016-11-11%2011:11:11?limit=20
    album_pagination_url = "https://www.tuchong.com/rest/sites/%s/posts/%s" % (account_id, post_time)
    query_data = {"limit": EACH_PAGE_PHOTO_COUNT}
    album_pagination_response = net.request(album_pagination_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "album_info_list": [],  # 全部图片信息
    }
    if album_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_pagination_response.status))
    if crawler.get_json_value(album_pagination_response.json_data, "result", type_check=str) != "SUCCESS":
        raise crawler.CrawlerException("返回信息%s中'result'字段取值不正确" % album_pagination_response.json_data)
    for album_info in crawler.get_json_value(album_pagination_response.json_data, "posts", type_check=list):
        result_photo_info = {
            "album_id": 0,  # 相册id
            "album_time": "",  # 相册创建时间
            "album_title": "",  # 相册标题
            "photo_url_list": [],  # 全部图片地址
        }
        # 获取相册id
        result_photo_info["album_id"] = crawler.get_json_value(album_info, "post_id", type_check=int)
        # 获取相册标题
        result_photo_info["album_title"] = crawler.get_json_value(album_info, "title", type_check=str)
        # 获取图片地址
        for photo_info in crawler.get_json_value(album_info, "images", type_check=list):
            photo_id = crawler.get_json_value(photo_info, "img_id", type_check=str)
            result_photo_info["photo_url_list"].append("https://photo.tuchong.com/%s/f/%s.jpg" % (account_id, photo_id))
        # 获取相册创建时间
        result_photo_info["album_time"] = crawler.get_json_value(album_info, "published_at", type_check=str)
        result["album_info_list"].append(result_photo_info)
    return result


class TuChong(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SysConfigKey.DOWNLOAD_PHOTO: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 解析存档文件
        # account_id  last_post_id
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

        # 下载线程
        self.crawler_thread = CrawlerThread


class CrawlerThread(crawler.CrawlerThread):
    def __init__(self, main_thread, single_save_data):
        self.index_key = self.display_name = single_save_data[0]  # account name
        crawler.CrawlerThread.__init__(self, main_thread, single_save_data)

    # 获取所有可下载相册
    def get_crawl_list(self, account_id):
        post_time = tool.get_time("%Y-%m-%d %H:%M:%S")
        album_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的相册
        while not is_over:
            pagination_description = "%s后一页相册" % post_time
            self.start_parse(pagination_description)
            try:
                album_pagination_response = get_one_page_album(account_id, post_time)
            except crawler.CrawlerException as e:
                self.error(e.http_error("%s后一页相册" % post_time))
                raise
            self.parse_result(pagination_description, album_pagination_response["album_info_list"])

            # 已经没有相册了
            if len(album_pagination_response["album_info_list"]) == 0:
                break

            # 寻找这一页符合条件的相册
            for album_info in album_pagination_response["album_info_list"]:
                # 检查是否达到存档记录
                if album_info["album_id"] > int(self.single_save_data[1]):
                    album_info_list.append(album_info)
                    post_time = album_info["album_time"]
                else:
                    is_over = True
                    break

        return album_info_list

    # 解析单个相册
    def crawl_album(self, album_info):
        album_description = "相册%s" % album_info["album_id"]
        self.start_parse(album_description)

        photo_index = 1
        # 过滤标题中不支持的字符
        album_title = path.filter_text(album_info["album_title"])
        if album_title:
            post_path = os.path.join(self.main_thread.photo_download_path, self.index_key, "%08d %s" % (album_info["album_id"], album_title))
        else:
            post_path = os.path.join(self.main_thread.photo_download_path, self.index_key, "%08d" % album_info["album_id"])
        self.temp_path_list.append(post_path)
        for photo_url in album_info["photo_url_list"]:
            photo_path = os.path.join(post_path, "%s.jpg" % photo_index)
            photo_description = "相册%s《%s》第%s张图片" % (album_info["album_id"], album_info["album_title"], photo_index)
            if self.download(photo_url, photo_path, photo_description):
                self.total_photo_count += 1  # 计数累加
            photo_index += 1

        # 相册内图片全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.single_save_data[1] = str(album_info["album_id"])  # 设置存档记录

    def _run(self):
        try:
            account_index_response = get_account_index_page(self.index_key)
        except crawler.CrawlerException as e:
            self.error(e.http_error("主页"))
            raise

            # 获取所有可下载相册
        album_info_list = self.get_crawl_list(account_index_response["account_id"])
        self.step("需要下载的全部相册解析完毕，共%s个" % len(album_info_list))

        # 从最早的相册开始下载
        while len(album_info_list) > 0:
            self.crawl_album(album_info_list.pop())


if __name__ == "__main__":
    TuChong().main()
