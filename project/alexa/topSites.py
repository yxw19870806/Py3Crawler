# -*- coding:UTF-8  -*-
"""
Alexa top sites排名抓取爬虫
https://www.alexa.com/topsites/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import csv
import math
import os
from pyquery import PyQuery as pq
from common import *

COOKIE_INFO = {}
CATEGORIES_CACHE_FILE_PATH = os.path.join(os.path.dirname(__file__), "categories.csv")
COUNTRY_SITES_RESULT_FILE_PATH = os.path.join(os.path.dirname(__file__), "country_sites.csv")
CATEGORY_SITES_RESULT_FILE_PATH = os.path.join(os.path.dirname(__file__), "category_sites.csv")
DUPLICATE_RESULT_FILE_PATH = os.path.join(os.path.dirname(__file__), "sites.csv")


def get_countries():
    index_url = "https://www.alexa.com/topsites/countries"
    index_response = net.http_request(index_url, method="GET", cookies_list=COOKIE_INFO)
    if index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(index_response.status))
    result = []
    index_response_content = index_response.data.decode(errors="ignore")
    country_list_selector = pq(index_response_content).find("div.categories ul.countries li a")
    for country_index in range(0, country_list_selector.length):
        country_selector = country_list_selector.eq(country_index)
        country_code = tool.find_sub_string(country_selector.attr("href"), "/countries/")
        country_name = country_selector.text()
        result.append([country_code, country_name])
    return result


def get_categories(category_href, csv_writer):
    index_url = "https://www.alexa.com/%s" % category_href
    index_response = net.http_request(index_url, method="GET", cookies_list=COOKIE_INFO)
    if index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(index_response.status))
    index_response_content = index_response.data.decode(errors="ignore")
    category_list_selector = pq(index_response_content).find("div.categories ul.subcategories li")
    for category_index in range(0, category_list_selector.length):
        category_selector = category_list_selector.eq(category_index)
        category_name = category_selector.find("a").text()
        sub_category_href = category_selector.find("a").attr("href")
        sites_count_selector = category_selector.find("span")
        # 如果子网站数量大于500个，查看子category
        if sites_count_selector.length == 1:
            sites_count = sites_count_selector.eq(0).text().replace("( ", "").replace(" )", "").replace(",", "")
            sites_count = int(sites_count)
            if sites_count < 500:
                if sites_count > 0:
                    print(category_name, sub_category_href, sites_count)
                    csv_writer.writerow([category_name.lower(), sub_category_href, str(sites_count)])
                continue
        print("start get sub categories " + sub_category_href)
        get_categories(sub_category_href, csv_writer)
    print("end get sub categories " + category_href)


def get_top_sites_by_country(country_code):
    result = []
    for page_count in range(0, 20):
        pagination_url = "https://www.alexa.com/topsites/countries;%s/%s" % (page_count, country_code)
        pagination_response = net.http_request(pagination_url, method="GET", cookies_list=COOKIE_INFO)
        if pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
            raise crawler.CrawlerException("第%s页，" + crawler.request_failre(pagination_response.status))
        pagination_response_content = pagination_response.data.decode(errors="ignore")
        if page_count > 0 and pq(pagination_response_content).find(".profile").length == 0:
            raise crawler.CrawlerException("登录状态已丢失")
        site_list_selector = pq(pagination_response_content).find("div.site-listing")
        for site_index in range(0, site_list_selector.length):
            site_selector = site_list_selector.eq(site_index)
            ranking = site_selector.find(".number").text()
            site_name = site_selector.find(".DescriptionCell>p>a").text()
            print("country:%s, rank:%s, site:%s" % (country_code, ranking, site_name))
            result.append([ranking, site_name])
    return result


def get_top_sites_by_category(category_href, category_name, sites_count):
    result = []
    sub_category_href = tool.find_sub_string(category_href, "/topsites/category")
    max_page_count = 1
    if COOKIE_INFO:
        max_page_count = int(math.ceil(sites_count / 25))
    for page_count in range(0, max_page_count):
        if COOKIE_INFO:
            pagination_url = "https://www.alexa.com/topsites/category;%s%s" % (page_count, sub_category_href)
        else:
            pagination_url = "https://www.alexa.com/%s" % category_href
        pagination_response = net.http_request(pagination_url, method="GET", cookies_list=COOKIE_INFO)
        if pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
            raise crawler.CrawlerException("第%s页，" + crawler.request_failre(pagination_response.status))
        pagination_response_content = pagination_response.data.decode(errors="ignore")
        if page_count > 0 and pq(pagination_response_content).find(".profile").length == 0:
            raise crawler.CrawlerException("登录状态已丢失")
        site_list_selector = pq(pagination_response_content).find("div.site-listing")
        for site_index in range(0, site_list_selector.length):
            site_selector = site_list_selector.eq(site_index)
            ranking = site_selector.find(".number").text()
            site_name = site_selector.find(".DescriptionCell>p>a").text()
            print("category:%s, rank:%s, site:%s" % (category_name, ranking, site_name))
            result.append([ranking, site_name])
    return result


class TopSites(crawler.Crawler):
    def __init__(self):
        global COOKIE_INFO

        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_NOT_CHECK_SAVE_DATA: True,
            crawler.SYS_GET_COOKIE: ("alexa.com", "www.alexa.com"),
        }
        crawler.Crawler.__init__(self, sys_config)

        # 设置全局变量，供子线程调用
        COOKIE_INFO = self.cookie_value

    @staticmethod
    def country():
        try:
            country_list = get_countries()
        except crawler.CrawlerException as e:
            print("国家列表获取失败，原因：%s" % e.message)
            raise

        for country_code, country_name in country_list:
            print("start get: %s(%s)" % (country_name, country_code))
            try:
                site_list = get_top_sites_by_country(country_code)
            except crawler.CrawlerException as e:
                print("国家%s的site列表获取失败，原因：%s" % (country_name, e.message))
                raise
            with open(COUNTRY_SITES_RESULT_FILE_PATH, "a", newline="", encoding="UTF-8") as file_handle:
                csv_writer = csv.writer(file_handle)
                for ranking, site_name in site_list:
                    csv_writer.writerow([country_name.lower(), country_code.lower(), ranking, site_name.lower()])

    @staticmethod
    def category():
        if not os.path.exists(CATEGORIES_CACHE_FILE_PATH):
            default_category_href = "/topsites/category"
            with open(CATEGORIES_CACHE_FILE_PATH, "a", newline="", encoding="UTF-8") as file_handle:
                csv_writer = csv.writer(file_handle)
                try:
                    get_categories(default_category_href, csv_writer)
                except crawler.CrawlerException as e:
                    print("category列表获取失败，原因：%s" % e.message)
                    raise

        with open(CATEGORIES_CACHE_FILE_PATH, "r", encoding="UTF-8") as cache_file_handle:
            with open(CATEGORY_SITES_RESULT_FILE_PATH, "a", newline="", encoding="UTF-8") as result_file_handle:
                result_csv_writer = csv.writer(result_file_handle)
                for category_info in csv.reader(cache_file_handle):
                    print("start get: %s(%s)" % (category_info[1], category_info[2]))
                    site_count = int(category_info[2])
                    try:
                        site_list = get_top_sites_by_category(category_info[1], category_info[0], site_count)
                    except crawler.CrawlerException as e:
                        print("分类%s的site列表获取失败，原因：%s" % (category_info[0], e.message))
                        raise
                    for ranking, site_name in site_list:
                        result_csv_writer.writerow([category_info[0], ranking, site_name.lower()])

    @staticmethod
    def duplicate():
        result_list = {}
        if os.path.exists(COUNTRY_SITES_RESULT_FILE_PATH):
            for result in csv.reader(COUNTRY_SITES_RESULT_FILE_PATH):
                result_list[result[2]] = 1

        if os.path.exists(CATEGORY_SITES_RESULT_FILE_PATH):
            for result in csv.reader(CATEGORY_SITES_RESULT_FILE_PATH):
                result_list[result[2]] = 1

        file.write_file("\n".join(result_list.keys()), DUPLICATE_RESULT_FILE_PATH, file.WRITE_FILE_TYPE_REPLACE)


if __name__ == "__main__":
    ts = TopSites()
    ts.country()
    ts.category()
    ts.duplicate()
