# -*- coding:UTF-8  -*-
"""
Alexa指定domian全球排名抓取
https://www.alexa.com/topsites/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import csv
import os
from pyquery import PyQuery as pq
from common import *
from project.alexa import topSites

SITES_RESULT_FILE_PATH = os.path.join(os.path.dirname(__file__), "global_rank.csv")


def get_site_global_rank(domain):
    site_info_url = "https://www.alexa.com/siteinfo/%s" % domain
    site_info_response = net.http_request(site_info_url, method="GET")
    if site_info_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(site_info_response.status))
    site_info_response_content = site_info_response.data.decode(errors="ignore")
    global_rank = 0
    global_rank_text = pq(site_info_response_content).find("span.globleRank div strong").text()
    if global_rank_text:
        global_rank_text = global_rank_text.strip().replace(",", "")
        if global_rank_text != "-":
            global_rank = global_rank_text
    return global_rank


class SiteInfo(crawler.Crawler):
    def __init__(self):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_NOT_CHECK_SAVE_DATA: True,
        }
        crawler.Crawler.__init__(self, sys_config)

        self.thread_count = 1

    def main(self):
        # 之前的记录
        done_list = {}
        if os.path.exists(SITES_RESULT_FILE_PATH):
            with open(SITES_RESULT_FILE_PATH, "r", encoding="UTF-8") as file_handle:
                for temp_list in csv.reader(file_handle):
                    done_list[temp_list[0]] = 1

        with open(topSites.DUPLICATE_RESULT_FILE_PATH, "r", encoding="UTF-8") as source_file_handle, \
                open(SITES_RESULT_FILE_PATH, "a", newline="", encoding="UTF-8") as destination_file_handle:
            csv_writer = csv.writer(destination_file_handle)
            thread_list = []
            for site_rank_info in csv.reader(source_file_handle):
                # 提前结束
                if not self.is_running():
                    break
                # 已经查过了，跳过
                domain = site_rank_info[0]
                if domain in done_list:
                    continue
                # 开始下载
                thread = GlobalRank(self, domain, csv_writer)
                thread.start()
                thread_list.append(thread)

            # 等待子线程全部完成
            while len(thread_list) > 0:
                thread_list.pop().join()


class GlobalRank(crawler.DownloadThread):
    def __init__(self, main_thread, domain, csv_writer):
        crawler.DownloadThread.__init__(self, [], main_thread)
        self.display_name = self.domain = domain
        self.csv_writer = csv_writer
        self.step("开始")

    def run(self):
        try:
            global_rank = get_site_global_rank(self.domain)
        except crawler.CrawlerException as e:
            print("%s获取全球排名失败，原因：%s" % (self.domain, e.message))
        except SystemExit:
            pass
        else:
            log.step("domain: %s, global rank: %s" % (self.domain, global_rank))
            # 写入排名结果
            with self.thread_lock:
                self.csv_writer.writerow([self.domain, global_rank])
        self.notify_main_thread()


if __name__ == "__main__":
    SiteInfo().main()
