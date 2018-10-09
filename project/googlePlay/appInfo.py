# -*- coding:UTF-8  -*-
"""
Google Play指定包名的app信息
https://play.google.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import csv
import os
from pyquery import PyQuery as pq
from common import *

COOKIE_INFO = {}
# 包名
SOURCE_FILE_PATH = os.path.join(os.path.dirname(__file__), "packages_names.csv")
# app信息
RESULT_FILE_PATH = os.path.join(os.path.dirname(__file__), "apps.csv")


def get_app_info(package_name):
    app_info_url = "https://play.google.com/store/apps/details"
    query_data = {
        "id": package_name,
    }
    app_info_response = net.http_request(app_info_url, method="GET", fields=query_data)
    result = {
        "score_count": 0,  # 打分人数
        "install_count": 0,  # 安装人数
    }
    if app_info_response.status == 404:
        result["install_count"] = -1
        result["score_count"] = -1
        return result
    if app_info_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(app_info_response.status))
    app_info_response_content = app_info_response.data.decode(errors="ignore")
    # 获取评价人数
    score_count_text = pq(app_info_response_content).find(".AYi5wd.TBRnV span:first").text()
    if not score_count_text:
        raise crawler.CrawlerException("页面截取打分人数失败")
    score_count = score_count_text.replace(",", "")
    if not crawler.is_integer(score_count):
        raise crawler.CrawlerException("打分人数转换失败%s" % score_count_text)
    result["score_count"] = score_count
    # 获取安装人数
    install_label_index = 2
    install_label_text = pq(app_info_response_content).find(".xyOfqd .hAyfc").eq(install_label_index).find(".BgcNfc").text()
    if install_label_text == "Size":
        install_label_index = 3
        install_label_text = pq(app_info_response_content).find(".xyOfqd .hAyfc").eq(install_label_index).find(".BgcNfc").text()
    if install_label_text != "Installs":
        raise crawler.CrawlerException("安装人数标签查找失败")
    install_count_text = pq(app_info_response_content).find(".xyOfqd .hAyfc").eq(install_label_index).find("span.htlgb>div>span.htlgb").text()
    if not install_count_text:
        raise crawler.CrawlerException("页面截取安装人数失败")
    install_count = install_count_text.replace(",", "").replace("+", "")
    if not crawler.is_integer(install_count):
        raise crawler.CrawlerException("安装人数转换失败%s" % install_count_text)
    result["install_count"] = install_count
    return result


class GooglePlayApps(crawler.Crawler):
    def __init__(self):
        global COOKIE_INFO

        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_NOT_CHECK_SAVE_DATA: True,
        }
        crawler.Crawler.__init__(self, sys_config)

    def main(self):
        # 之前的记录
        done_list = {}
        if os.path.exists(RESULT_FILE_PATH):
            with open(RESULT_FILE_PATH, "r", encoding="UTF-8") as file_handle:
                for temp_list in csv.reader(file_handle):
                    done_list[temp_list[0]] = 1

        with open(SOURCE_FILE_PATH, "r", encoding="UTF-8") as source_file_handle, \
                open(RESULT_FILE_PATH, "a", newline="", encoding="UTF-8") as destination_file_handle:
            csv_writer = csv.writer(destination_file_handle)
            thread_list = []
            for app_info in csv.reader(source_file_handle):
                # 提前结束
                if not self.is_running():
                    break
                # 已经查过了，跳过
                package_name = app_info[0]
                if package_name in done_list:
                    continue
                # 开始下载
                thread = AppsInfo(self, package_name, csv_writer)
                thread.start()
                thread_list.append(thread)

            # 等待子线程全部完成
            while len(thread_list) > 0:
                thread_list.pop().join()


class AppsInfo(crawler.DownloadThread):
    def __init__(self, main_thread, package_name, csv_writer):
        crawler.DownloadThread.__init__(self, [], main_thread)
        self.display_name = self.package_name = package_name
        self.csv_writer = csv_writer
        self.step("开始")

    def run(self):
        try:
            app_info = get_app_info(self.package_name)
        except crawler.CrawlerException as e:
            print("%s获取安装数失败，原因：%s" % (self.package_name, e.message))
        except SystemExit:
            pass
        else:
            log.step("package: %s, install number: %s" % (self.package_name, app_info["install_count"]))
            # 写入排名结果
            with self.thread_lock:
                self.csv_writer.writerow([self.package_name, app_info["install_count"], app_info["score_count"]])
        self.notify_main_thread()

if __name__ == "__main__":
    GooglePlayApps().main()
