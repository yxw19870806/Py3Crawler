# -*- coding:UTF-8  -*-
"""
World Cosplay图片爬虫
https://worldcosplay.net/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from common import *

EACH_PAGE_PHOTO_COUNT = 16  # 每次请求获取的图片数量


# 获取指定页数的全部图片
def get_one_page_photo(account_id, page_count):
    # https://worldcosplay.net/zh-hans/api/member/photos.json?limit=16&member_id=502191&p3_photo_list=true&page=1
    photo_pagination_url = "https://worldcosplay.net/zh-hans/api/member/photos.json"
    query_data = {
        "limit": EACH_PAGE_PHOTO_COUNT,
        "member_id": account_id,
        "p3_photo_list": "true",
        "page": page_count,
    }
    photo_pagination_response = net.request(photo_pagination_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "photo_info_list": [],  # 全部图片信息
        "is_over": False,  # 是否最后一页图片
    }
    if photo_pagination_response.status == 404 and page_count == 1:
        raise crawler.CrawlerException("账号不存在")
    elif photo_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(photo_pagination_response.status))
    # 获取图片信息
    for photo_info in crawler.get_json_value(photo_pagination_response.json_data, "list", type_check=list):
        result_photo_info = {
            "photo_id": 0,  # 图片id
            "photo_url": "",  # 图片地址
        }
        # 获取图片id
        result_photo_info["photo_id"] = crawler.get_json_value(photo_info, "id", type_check=int)
        # 获取图片地址
        result_photo_info["photo_url"] = crawler.get_json_value(photo_info, "img_url", type_check=str)
        result["photo_info_list"].append(result_photo_info)
    # 判断是不是最后一页
    if crawler.get_json_value(photo_pagination_response.json_data, "pager", "next_page") is None:
        result["is_over"] = True
    return result


# 使用高分辨率的图片地址
def get_photo_url(photo_url):
    return photo_url.replace("-350x600.", "-740.")


class WorldCosplay(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 解析存档文件
        # account_id  last_photo_id
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

        # 下载线程
        self.download_thread = Download


class Download(crawler.DownloadThread):
    def __init__(self, single_save_data, main_thread):
        self.index_key = single_save_data[0]  # account id
        if len(single_save_data) >= 3 and single_save_data[2]:
            self.display_name = single_save_data[2]
        else:
            self.display_name = single_save_data[0]
        crawler.DownloadThread.__init__(self, single_save_data, main_thread)

    def _run(self):
        # 获取所有可下载图片
        photo_info_list = self.get_crawl_list()
        self.step("需要下载的全部图片解析完毕，共%s个" % len(photo_info_list))

        # 从最早的图片开始下载
        while len(photo_info_list) > 0:
            self.crawl_photo(photo_info_list.pop())
            self.main_thread_check()  # 检测主线程运行状态

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
                photo_pagination_response = get_one_page_photo(self.index_key, page_count)
            except crawler.CrawlerException as e:
                self.error(e.http_error("第%s页图片" % page_count))
                raise

            self.trace("第%s页解析的全部图片：%s" % (page_count, photo_pagination_response["photo_info_list"]))
            self.step("第%s页解析获取%s张图片" % (page_count, len(photo_pagination_response["photo_info_list"])))

            # 寻找这一页符合条件的图片
            for photo_info in photo_pagination_response["photo_info_list"]:
                # 检查是否达到存档记录
                if photo_info["photo_id"] > int(self.single_save_data[1]):
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
        file_name = "%08d.%s" % (photo_info["photo_id"], net.get_file_extension(photo_url))
        file_path = os.path.join(self.main_thread.photo_download_path, self.display_name, file_name)
        download_return = net.Download(photo_url, file_path)
        if download_return.status == net.Download.DOWNLOAD_SUCCEED:
            self.total_photo_count += 1  # 计数累加
            self.step("图片%s下载成功" % photo_info["photo_id"])
        else:
            self.error("图片%s %s，下载失败，原因：%s" % (photo_info["photo_id"], photo_info["photo_url"], crawler.download_failre(download_return.code)))
            self.check_download_failure_exit()

        # 图片内图片下全部载完毕
        self.single_save_data[1] = str(photo_info["photo_id"])  # 设置存档记录


if __name__ == "__main__":
    WorldCosplay().main()
