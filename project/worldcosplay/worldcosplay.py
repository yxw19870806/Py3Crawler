# -*- coding:UTF-8  -*-
"""
World Cosplay图片爬虫
https://worldcosplay.net/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import time
import traceback
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
            "photo_id": None,  # 图片id
            "photo_url": None,  # 图片地址
        }
        # 获取图片id
        result_photo_info["photo_id"] = crawler.get_json_value(photo_info, "photo", "id", type_check=int)
        # 获取图片地址
        for key_name in ["sq300_url", "sq150_url"]:
            photo_url = crawler.get_json_value(photo_info, "photo", key_name, default_value="", type_check=str)
            if photo_url:
                if photo_url.find("-350x600.") == -1:
                    raise crawler.CrawlerException(f"图片信息{photo_info}中截取图片地址失败")
                result_photo_info["photo_url"] = photo_url
                break
        else:
            raise crawler.CrawlerException(f"图片信息{photo_info}中匹配图片地址失败")
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

    def main(self):
        try:
            # 循环下载每个id
            thread_list = []
            for account_id in sorted(self.save_data.keys()):
                # 提前结束
                if not self.is_running():
                    break

                # 开始下载
                thread = Download(self.save_data[account_id], self)
                thread.start()
                thread_list.append(thread)

                time.sleep(1)

            # 等待子线程全部完成
            while len(thread_list) > 0:
                thread_list.pop().join()
        except KeyboardInterrupt:
            self.stop_process()

        # 未完成的数据保存
        self.write_remaining_save_data()

        # 重新排序保存存档文件
        self.rewrite_save_file()

        self.end_message()


class Download(crawler.DownloadThread):
    def __init__(self, single_save_data, main_thread):
        crawler.DownloadThread.__init__(self, single_save_data, main_thread)
        self.account_id = self.single_save_data[0]
        if len(self.single_save_data) >= 3:
            self.display_name = self.single_save_data[2]
        else:
            self.display_name = self.single_save_data[0]
        self.step("开始")

    # 获取所有可下载图片
    def get_crawl_list(self):
        page_count = 1
        unique_list = []
        photo_info_list = []
        is_over = False
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step(f"开始解析第{page_count}页图片")

            # 获取一页图片
            try:
                photo_pagination_response = get_one_page_photo(self.account_id, page_count)
            except crawler.CrawlerException as e:
                self.error(e.http_error(f"第{page_count}页图片"))
                raise

            self.trace(f"第{page_count}页解析的全部图片：{photo_pagination_response['photo_info_list']}")
            self.step(f"第{page_count}页解析获取{len(photo_pagination_response['photo_info_list'])}张图片")

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
        self.step(f"开始下载图片{photo_info['photo_id']} {photo_info['photo_url']}")

        photo_url = get_photo_url(photo_info["photo_url"])
        file_path = os.path.join(self.main_thread.photo_download_path, self.display_name, f"%08d.{net.get_file_type(photo_url)}" % photo_info["photo_id"])
        save_file_return = net.download(photo_url, file_path)
        if save_file_return["status"] == 1:
            self.total_photo_count += 1  # 计数累加
            self.step(f"图片{photo_info['photo_id']}下载成功")
        else:
            self.error(f"图片{photo_info['photo_id']} {photo_info['photo_url']}，下载失败，原因：{crawler.download_failre(save_file_return['code'])}")
            self.check_download_failure_exit()

        # 图片内图片下全部载完毕
        self.single_save_data[1] = str(photo_info["photo_id"])  # 设置存档记录

    def run(self):
        try:
            # 获取所有可下载图片
            photo_info_list = self.get_crawl_list()
            self.step(f"需要下载的全部图片解析完毕，共{len(photo_info_list)}个")

            # 从最早的图片开始下载
            while len(photo_info_list) > 0:
                self.crawl_photo(photo_info_list.pop())
                self.main_thread_check()  # 检测主线程运行状态
        except (SystemExit, KeyboardInterrupt) as e:
            if isinstance(e, SystemExit) and e.code == 1:
                self.error("异常退出")
            else:
                self.step("提前退出")
        except Exception as e:
            self.error("未知异常")
            self.error(str(e) + "\n" + traceback.format_exc(), False)

        self.main_thread.save_data.pop(self.account_id)
        self.done()


if __name__ == "__main__":
    WorldCosplay().main()
