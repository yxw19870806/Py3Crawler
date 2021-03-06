# -*- coding:UTF-8  -*-
"""
Google Play指定包名的app信息
https://play.google.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import copy
import csv
import os
import time
from pyquery import PyQuery as pq
from common import *

COOKIE_INFO = {}
# 旧版本app信息
SOURCE_FILE_PATH = os.path.join(os.path.dirname(__file__), "old_apps.csv")
# app信息
RESULT_FILE_PATH = os.path.join(os.path.dirname(__file__), "apps.csv")
# 异常包
ERROR_FILE_PATH = os.path.join(os.path.dirname(__file__), "error.csv")
# 去重后的开发者邮箱
DEVELOPER_MAIL_FILE_PATH = os.path.join(os.path.dirname(__file__), "mail.csv")

DEFAULT_APP_INFO = {
    "category": None,  # 分类
    "update_time": None,  # 最后更新时间
    "file_size": None,  # 安装包大小
    "install_count": None,  # 安装数
    "score_count": None,  # 打分人数
    "developer_id": "",  # 开发者id
    "developer_name": None,  # 开发者
    "developer_email": "",  # 开发者邮箱
}


def get_app_info(package_name):
    app_info_url = "https://play.google.com/store/apps/details"
    query_data = {
        "id": package_name,
    }
    app_info_response = net.http_request(app_info_url, method="GET", fields=query_data)
    result = copy.copy(DEFAULT_APP_INFO)
    if app_info_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(app_info_response.status))
    app_info_response_content = app_info_response.data.decode(errors="ignore")
    label_list_selector = pq(app_info_response_content).find(".xyOfqd .hAyfc")
    for label_index in range(0, label_list_selector.length):
        label_selector = label_list_selector.eq(label_index)
        label_text = label_selector.find(".BgcNfc").text()
        label_value = label_selector.find("span.htlgb>div>span.htlgb").text()
        if label_text == "Updated":
            result["update_time"] = time.strftime("%Y%m%d", time.strptime(label_value, "%B %d, %Y"))
        elif label_text == "Size":
            result["file_size"] = label_value
        elif label_text == "Installs":
            result["install_count"] = label_value.replace(",", "").replace("+", "")
        elif label_text == "Developer":
            for sub_label_value in label_value.split("\n"):
                if sub_label_value.find("@") > 0:
                    result["developer_email"] = sub_label_value
                    break
    # 获取分类
    label_list_selector = pq(app_info_response_content).find(".jdjqLd .ZVWMWc .hrTbp.R8zArc")
    for label_index in range(0, label_list_selector.length):
        label_selector = label_list_selector.eq(label_index)
        label_href = label_selector.attr("href")
        if label_href is not None:
            if label_href.find("store/apps/dev?id=") > 0:
                result["developer_id"] = tool.find_sub_string(label_href, "store/apps/dev?id=")
                result["developer_name"] = label_selector.text()
            elif label_href.find("store/apps/developer?id=") > 0:
                result["developer_name"] = label_selector.text()
            elif label_href.find("store/apps/category/") > 0:
                result["category"] = tool.find_sub_string(label_href, "store/apps/category/")
            else:
                log.notice(package_name + " 非开发者信息和应用分类地址: %s" % label_href)
    # 获取评价人数
    score_count_text = pq(app_info_response_content).find(".jdjqLd .dNLKff").text()
    if score_count_text:
        score_count = score_count_text.replace(",", "")
        if not crawler.is_integer(score_count):
            log.notice(package_name + " 打分人数转换失败%s" % score_count_text)
        result["score_count"] = score_count
    return result


class GooglePlayApps(crawler.Crawler):
    def __init__(self, **kwargs):
        global COOKIE_INFO

        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_NOT_CHECK_SAVE_DATA: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

    def main(self):
        # 需要查找的包所在文件不存在
        if not os.path.exists(SOURCE_FILE_PATH):
            return

        # 之前的记录
        done_list = {}
        if os.path.exists(RESULT_FILE_PATH):
            with open(RESULT_FILE_PATH, "r", encoding="UTF-8") as file_handle:
                for temp_list in csv.reader(file_handle):
                    if len(temp_list) == 0:
                        continue
                    done_list[temp_list[0]] = 1
        if os.path.exists(ERROR_FILE_PATH):
            with open(ERROR_FILE_PATH, "r", encoding="UTF-8") as file_handle:
                for temp_list in csv.reader(file_handle):
                    if len(temp_list) == 0:
                        continue
                    done_list[temp_list[0]] = 1

        with open(SOURCE_FILE_PATH, "r", encoding="UTF-8") as source_file_handle, \
                open(RESULT_FILE_PATH, "a", newline="", encoding="UTF-8") as destination_file_handle, \
                open(ERROR_FILE_PATH, "a", newline="", encoding="UTF-8") as error_file_handle:
            csv_writer = csv.writer(destination_file_handle)
            error_csv_writer = csv.writer(error_file_handle)
            thread_list = []
            for app_info in csv.reader(source_file_handle):
                # 提前结束
                if not self.is_running():
                    break
                if len(app_info) == 0:
                    continue
                # 已经查过了，跳过
                package_name = app_info[0]
                if package_name in done_list:
                    continue
                # 开始下载
                thread = AppsInfo(self, package_name, app_info, csv_writer, error_csv_writer)
                thread.start()
                thread_list.append(thread)

            # 等待子线程全部完成
            while len(thread_list) > 0:
                thread_list.pop().join()


class AppsInfo(crawler.DownloadThread):
    def __init__(self, main_thread, package_name, old_app_data, csv_writer, error_csv_writer):
        crawler.DownloadThread.__init__(self, [], main_thread)
        self.display_name = self.package_name = package_name
        self.old_app_data = old_app_data
        self.csv_writer = csv_writer
        self.error_csv_writer = error_csv_writer
        self.step("开始")

    def run(self):
        try:
            app_info = get_app_info(self.package_name)
        except crawler.CrawlerException as e:
            log.step("%s获取应用信息失败，原因：%s" % (self.package_name, e.message))
            self.error_csv_writer.writerow([self.package_name])
        except SystemExit:
            pass
        else:
            log.step("%s done" % self.package_name)
            if app_info["category"] is not None and app_info["install_count"] is not None and app_info["score_count"] is not None and \
                    app_info["file_size"] is not None and app_info["developer_name"] is not None and app_info["update_time"]is not None:
                # 写入排名结果
                with self.thread_lock:
                    # 包名, 分类, 最小安装数, 应用文件大小, 开发者id, 开发者名, 开发者邮箱, 应用最后更新时间, 爬虫更新时间
                    self.csv_writer.writerow([
                        self.package_name,
                        app_info["category"],
                        app_info["install_count"],
                        app_info["score_count"],
                        app_info["file_size"],
                        app_info["developer_id"],
                        app_info["developer_name"],
                        app_info["developer_email"],
                        app_info["update_time"],
                        int(time.time())
                    ])
            else:
                log.error("%s抓取数据不完整" % self.package_name)
                with self.thread_lock:
                    self.csv_writer.writerow(self.old_app_data)
        self.notify_main_thread()


if __name__ == "__main__":
    GooglePlayApps().main()
