# -*- coding:UTF-8  -*-
"""
站酷图片爬虫
https://hodakwo.zcool.com.cn/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import time
from pyquery import PyQuery as pq
from common import *


# 获取指定页数的全部作品
def get_one_page_album(account_name, page_count):
    # https://www.zcool.com.cn/u/17050872?myCate=0&sort=8&p=2
    if tool.is_integer(account_name):
        album_pagination_url = f"https://www.zcool.com.cn/u/{account_name}"
    else:
        album_pagination_url = f"https://{account_name}.zcool.com.cn/"
    query_data = {
        "myCate": "0",
        "sort": "8",  # 按时间倒叙
        "p": page_count,
    }
    album_pagination_response = net.request(album_pagination_url, method="GET", fields=query_data)
    result = {
        "album_info_list": [],  # 全部作品信息
        "is_over": False,  # 是否最后页
    }
    if page_count == 1 and album_pagination_response.status == 404:
        raise crawler.CrawlerException("账号不存在")
    elif album_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_pagination_response.status))
    album_pagination_response_content = album_pagination_response.data.decode(errors="ignore")
    album_list_selector = pq(album_pagination_response_content).find(".work-list-box .card-box")
    for album_index in range(0, album_list_selector.length):
        result_album_info = {
            "album_id": None,  # 作品id
            "album_title": None,  # 作品标题
            "album_time": None,  # 作品创建时间
        }
        album_selector = album_list_selector.eq(album_index)
        # 获取作品id
        album_url = album_selector.find(".card-img>a").attr("href")
        if not album_url:
            raise crawler.CrawlerException("作品信息截取作品地址失败\n" + album_selector.html())
        # 文章
        if album_url.find("www.zcool.com.cn/article/") > 0:
            continue
        album_id = tool.find_sub_string(album_url, "/work/", ".html")
        if not album_id:
            raise crawler.CrawlerException("作品地址截取作品id失败\n" + album_selector.html())
        result_album_info["album_id"] = album_id
        # 获取作品标题
        album_title = album_selector.find(".card-img>a").attr("title")
        if not album_title:
            raise crawler.CrawlerException("作品信息截取作品标题失败\n" + album_selector.html())
        result_album_info["album_title"] = album_title
        # 获取作品创建日期
        album_time_text = album_selector.find(".card-item>span").attr("title")
        if not album_time_text:
            raise crawler.CrawlerException("作品信息截取作品日期信息失败\n" + album_selector.html())
        album_time_string = tool.find_sub_string(album_time_text, "创建时间：")
        if not album_time_string:
            raise crawler.CrawlerException(f"作品日期信息{album_time_text}截取作品发布日期失败")
        try:
            album_time = time.strptime(album_time_string, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise crawler.CrawlerException(f"作品发布日期{album_time_string}的格式不正确")
        result_album_info["album_time"] = int(time.mktime(album_time))
        result["album_info_list"].append(result_album_info)
    result["is_over"] = album_list_selector.length == 0
    return result


# 获取作品
def get_album_page(album_id):
    album_url = f"https://www.zcool.com.cn/work/{album_id}.html"
    album_response = net.request(album_url, method="GET")
    result = {
        "photo_url_list": [],  # 全部图片地址
    }
    if album_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_response.status))
    album_response_content = album_response.data.decode(errors="ignore")
    photo_list_selector = pq(album_response_content).find(".work-show-box .reveal-work-wrap img")
    if photo_list_selector.length == 0:
        raise crawler.CrawlerException("页面截取图片列表失败\n" + album_response_content)
    for photo_index in range(0, photo_list_selector.length):
        result["photo_url_list"].append(photo_list_selector.eq(photo_index).attr("src"))
    return result


# 去除指定分辨率
# https://img.zcool.cn/community/011d1d592bae06b5b3086ed41bf15f.jpg@1280w_1l_2o_100sh.jpg
# ->
# https://img.zcool.cn/community/011d1d592bae06b5b3086ed41bf15f.jpg
def get_photo_url(photo_url):
    return photo_url.split("@")[0]


class ZCool(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 解析存档文件
        # account_name  last_album_time
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

    def _main(self):
        # 循环下载每个id
        thread_list = []
        for account_name in sorted(self.save_data.keys()):
            # 提前结束
            if not self.is_running():
                break

            # 开始下载
            thread = Download(self.save_data[account_name], self)
            thread.start()
            thread_list.append(thread)

            time.sleep(1)

        # 等待子线程全部完成
        while len(thread_list) > 0:
            thread_list.pop().join()


class Download(crawler.DownloadThread):
    def __init__(self, single_save_data, main_thread):
        crawler.DownloadThread.__init__(self, single_save_data, main_thread)
        self.index_key = self.single_save_data[0]  # account name
        if len(self.single_save_data) >= 3 and self.single_save_data[2]:
            self.display_name = self.single_save_data[2]
        else:
            self.display_name = self.single_save_data[0]
        self.step("开始")

    def _run(self):
        # 获取所有可下载作品
        album_info_list = self.get_crawl_list()
        self.step(f"需要下载的全部作品解析完毕，共{len(album_info_list)}个")

        # 从最早的作品开始下载
        while len(album_info_list) > 0:
            self.crawl_album(album_info_list.pop())
            self.main_thread_check()  # 检测主线程运行状态

    # 获取所有可下载作品
    def get_crawl_list(self):
        page_count = 1
        unique_list = []
        album_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的作品
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step(f"开始解析第{page_count}页作品")

            try:
                album_pagination_response = get_one_page_album(self.index_key, page_count)
            except crawler.CrawlerException as e:
                self.error(e.http_error(f"第{page_count}页作品"))
                raise

            self.trace(f"第{page_count}页解析的全部作品：{album_pagination_response['album_info_list']}")
            self.step(f"第{page_count}页解析获取{len(album_pagination_response['album_info_list'])}个作品")

            # 寻找这一页符合条件的作品
            for album_info in album_pagination_response["album_info_list"]:
                # 检查是否达到存档记录
                if album_info["album_time"] > int(self.single_save_data[1]):
                    # 新增作品导致的重复判断
                    if album_info["album_id"] in unique_list:
                        continue
                    else:
                        album_info_list.append(album_info)
                        unique_list.append(album_info["album_id"])
                else:
                    is_over = True
                    break

            if not is_over:
                if album_pagination_response["is_over"]:
                    is_over = True
                else:
                    page_count += 1

        return album_info_list

    # 解析单个作品
    def crawl_album(self, album_info):
        self.step(f"开始解析作品 {album_info['album_id']}")

        # 获取作品
        try:
            album_response = get_album_page(album_info["album_id"])
        except crawler.CrawlerException as e:
            self.error(e.http_error(f"作品{album_info['album_id']}《{album_info['album_title']}》"))
            raise

        self.trace(f"作品{album_info['album_id']}解析的全部图片：{album_response['photo_url_list']}")
        self.step(f"作品{album_info['album_id']}解析获取{len(album_response['photo_url_list'])}张图片")

        photo_index = 1
        album_path = os.path.join(self.main_thread.photo_download_path, self.index_key, f"{album_info['album_id']} {path.filter_text(album_info['album_title'])}")
        self.temp_path_list.append(album_path)
        for photo_url in album_response["photo_url_list"]:
            self.main_thread_check()  # 检测主线程运行状态
            photo_url = get_photo_url(photo_url)
            self.step(f"开始下载作品{album_info['album_id']}《{album_info['album_title']}》的第{photo_index}张图片 {photo_url}")

            file_path = os.path.join(album_path, f"%02d.{net.get_file_extension(photo_url)}" % photo_index)
            save_file_return = net.download(photo_url, file_path)
            if save_file_return["status"] == 1:
                self.total_photo_count += 1  # 计数累加
                self.step(f"作品{album_info['album_id']}《{album_info['album_title']}》的第{photo_index}张图片下载成功")
            else:
                self.error(f"作品{album_info['album_id']}《{album_info['album_title']}》的第{photo_index}张图片 {photo_url} 下载失败，原因：{crawler.download_failre(save_file_return['code'])}")
                self.check_download_failure_exit()
            photo_index += 1

        # 作品内图片全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.single_save_data[1] = str(album_info["album_time"])  # 设置存档记录


if __name__ == "__main__":
    ZCool().main()
