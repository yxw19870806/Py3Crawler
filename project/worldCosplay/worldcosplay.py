# -*- coding:UTF-8  -*-
"""
World Cosplay图片爬虫
https://worldcosplay.net/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import threading
import time
import traceback
from common import *

PHOTO_COUNT_PER_PAGE = 16


# 获取指定页数的全部图片
def get_one_page_photo(account_id, page_count):
    # https://worldcosplay.net/zh-hans/api/member/photos.json?limit=16&member_id=502191&p3_photo_list=true&page=1
    photo_pagination_url = "https://worldcosplay.net/zh-hans/api/member/photos.json"
    query_data = {
        "limit": PHOTO_COUNT_PER_PAGE,
        "member_id": account_id,
        "p3_photo_list": "true",
        "page": page_count,
    }
    photo_pagination_response = net.http_request(photo_pagination_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "photo_info_list": [],  # 全部图片信息
        "is_over": False,  # 是否最后一页图片
    }
    if photo_pagination_response.status == 404 and page_count == 1:
        raise crawler.CrawlerException("账号不存在")
    elif photo_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(photo_pagination_response.status))
    # 获取图片信息
    if not crawler.check_sub_key(("list",), photo_pagination_response.json_data):
        raise crawler.CrawlerException("返回信息'list'字段不存在\n%s" % photo_pagination_response.json_data)
    if not isinstance(photo_pagination_response.json_data["list"], list):
        raise crawler.CrawlerException("返回信息'list'字段类型不正确\n%s" % photo_pagination_response.json_data)
    for photo_info in photo_pagination_response.json_data["list"]:
        result_photo_info = {
            "photo_id": None,  # 图片id
            "photo_url": None,  # 图片地址
        }
        if not crawler.check_sub_key(("photo",), photo_info):
            raise crawler.CrawlerException("图片信息'photo'字段不存在\n%s" % photo_info)
        # 获取图片id
        if not crawler.check_sub_key(("id",), photo_info["photo"]):
            raise crawler.CrawlerException("图片信息'id'字段不存在\n%s" % photo_info)
        if not crawler.is_integer(photo_info["photo"]["id"]):
            raise crawler.CrawlerException("图片信息'id'字段类型不正确\n%s" % photo_info)
        result_photo_info["photo_id"] = int(photo_info["photo"]["id"])
        # 获取图片地址
        if crawler.check_sub_key(("sq300_url",), photo_info["photo"]):
            photo_url = photo_info["photo"]["sq300_url"]
        elif crawler.check_sub_key(("sq150_url",), photo_info["photo"]):
            photo_url = photo_info["photo"]["sq150_url"]
        else:
            raise crawler.CrawlerException("图片信息'sq300_url'和'sq150_url'字段不存在\n%s" % photo_info)
        if photo_url.find("-350x600.") == -1:
            raise crawler.CrawlerException("图片预览地址 %s 格式不正确\n" % photo_url)
        result_photo_info["photo_url"] = photo_url
        result["photo_info_list"].append(result_photo_info)
    # 判断是不是最后一页
    if not crawler.check_sub_key(("pager",), photo_pagination_response.json_data):
        raise crawler.CrawlerException("返回信息'pager'字段不存在\n%s" % photo_pagination_response.json_data)
    if not crawler.check_sub_key(("next_page",), photo_pagination_response.json_data["pager"]):
        raise crawler.CrawlerException("返回信息'next_page'字段不存在\n%s" % photo_pagination_response.json_data)
    if photo_pagination_response.json_data["pager"]["next_page"] is None:
        result["is_over"] = True
    return result


# 使用高分辨率的图片地址
def get_photo_url(photo_url):
    return photo_url.replace("-350x600.", "-740.")


class WorldCosplay(crawler.Crawler):
    def __init__(self):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
        }
        crawler.Crawler.__init__(self, sys_config)

        # 解析存档文件
        # account_id  last_photo_id
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
        self.account_id = self.account_info[0]
        if len(self.account_info) >= 3:
            self.display_name = self.account_info[2]
        else:
            self.display_name = self.account_info[0]
        self.step("开始")

    # 获取所有可下载图片
    def get_crawl_list(self):
        page_count = 1
        unique_list = []
        photo_info_list = []
        is_over = False
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析第%s页图片" % page_count)

            # 获取一页图片
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

    # 解析单个图片
    def crawl_photo(self, photo_info):
        # 禁用指定分辨率
        self.step("开始下载图片%s %s" % (photo_info["photo_id"], photo_info["photo_url"]))

        photo_url = get_photo_url(photo_info["photo_url"])
        file_path = os.path.join(self.main_thread.photo_download_path, self.display_name, "%08d.%s" % (photo_info["photo_id"], net.get_file_type(photo_url)))
        save_file_return = net.save_net_file(photo_url, file_path)
        if save_file_return["status"] == 1:
            self.step("图片%s下载成功" % photo_info["photo_id"])
        else:
            self.error("图片%s %s，下载失败，原因：%s" % (photo_info["photo_id"], photo_info["photo_url"], crawler.download_failre(save_file_return["code"])))

        # 图片内图片下全部载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.total_photo_count += 1  # 计数累加
        self.account_info[1] = str(photo_info["photo_id"])  # 设置存档记录

    def run(self):
        try:
            # 获取所有可下载图片
            photo_info_list = self.get_crawl_list()
            self.step("需要下载的全部图片解析完毕，共%s个" % len(photo_info_list))

            # 从最早的图片开始下载
            while len(photo_info_list) > 0:
                photo_info = photo_info_list.pop()
                self.crawl_photo(photo_info)
                self.main_thread_check()  # 检测主线程运行状态
        except SystemExit as se:
            if se.code == 0:
                self.step("提前退出")
            else:
                self.error("异常退出")
            # 如果临时目录变量不为空，表示某个图集正在下载中，需要把下载了部分的内容给清理掉
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
    WorldCosplay().main()
