# -*- coding:UTF-8  -*-
"""
微博收藏夹图片爬虫
https://www.weibo.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import re
import urllib.parse
from pyquery import PyQuery as pq
from common import *
from project.weibo import weibo


# 获取一页的收藏微博ge
def get_one_page_favorite(page_count):
    # https://www.weibo.com/fav?page=1
    favorite_pagination_url = "https://www.weibo.com/fav"
    query_data = {"page": page_count}
    cookies = {"SUB": weibo.COOKIES["SUB"]}
    favorite_pagination_response = net.Request(favorite_pagination_url, method="GET", fields=query_data, cookies=cookies)
    result = {
        "blog_info_list": [],  # 所有微博信息
        "delete_blog_id_list": [],  # 全部已删除的微博ID
        "is_over": False,  # 是否最后一页收藏
    }
    if favorite_pagination_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(favorite_pagination_response.status))
    favorite_data_html = tool.find_sub_string(favorite_pagination_response.content, '"ns":"pl.content.favoriteFeed.index"', '"})</script>', const.IncludeStringMode.END)
    favorite_data_html = tool.find_sub_string(favorite_data_html, '"html":"', '"})')
    if not favorite_data_html:
        raise CrawlerException("页面截取收藏信息失败\n" + favorite_pagination_response.content)
    # 替换全部转义斜杠以及没有用的换行符等
    html_data = favorite_data_html.replace(r"\\", chr(1))
    for replace_string in [r"\n", r"\r", r"\t", "\\"]:
        html_data = html_data.replace(replace_string, "")
    html_data = html_data.replace(chr(1), "\\")
    # 解析页面
    children_selector = pq(html_data).find("div.WB_feed").children()
    if children_selector.length == 0:
        raise CrawlerException("匹配收藏信息失败\n" + favorite_data_html)
    if children_selector.length == 1:
        raise CrawlerException("没有收藏了")
    # 解析日志id和图片地址
    for i in range(children_selector.length - 1):
        result_blog_info = {
            "blog_id": 0,  # 日志id（mid）
            "photo_url_list": [],  # 所有图片地址
        }
        feed_selector = children_selector.eq(i)
        # 已被删除的微博
        if not feed_selector.has_class("WB_feed_type"):
            if feed_selector.attr("mid"):
                result["delete_blog_id_list"].append(feed_selector.attr("mid"))
            elif feed_selector.find(".WB_empty").length == 1:
                result["delete_blog_id_list"].append(feed_selector.find(".WB_empty").attr("mid"))
            continue
        # 解析日志id
        blog_id = feed_selector.attr("mid")
        if not tool.is_integer(blog_id):
            raise CrawlerException("收藏信息解析微博id失败\n" + feed_selector.html())
        result_blog_info["blog_id"] = int(blog_id)
        # WB_text       微博文本
        # WB_media_wrap 微博媒体（图片）
        # .WB_feed_expand .WB_expand     转发的微博，下面同样包含WB_text、WB_media_wrap这些结构
        # 包含转发微博
        if feed_selector.find(".WB_feed_expand .WB_expand").length == 0:
            media_selector = feed_selector.find(".WB_media_wrap")
        else:
            media_selector = feed_selector.find(".WB_feed_expand .WB_expand .WB_media_wrap")
        # 如果存在媒体
        if media_selector.length == 1:
            thumb_photo_url_list = re.findall(r'<img src="([^"]*)"/>', media_selector.html())
            if len(thumb_photo_url_list) > 0:
                photo_url_list = []
                for photo_url in thumb_photo_url_list:
                    # https://wx3.sinaimg.cn/mw2000/e212e359gy1hdzbgobbpvj20lc0sgtce.jpg
                    # ->
                    # https://wx3.sinaimg.cn/large/e212e359gy1hdzbgobbpvj20lc0sgtce.jpg
                    url_split_result = url.split_path(photo_url)
                    url_split_result[0] = "large"
                    url_split_result.insert(0, "")
                    photo_url_list.append(urllib.parse.urljoin(photo_url, "/".join(url_split_result)))
                result_blog_info["photo_url_list"] = photo_url_list
        if len(result_blog_info["photo_url_list"]) > 0:
            result["blog_info_list"].append(result_blog_info)
    # 最后一条feed是分页信息
    page_selector = children_selector.eq(children_selector.length - 1)
    # 判断是不是最后一页
    page_count_find = re.findall(r"第(\d*)页", page_selector.html())
    if len(page_count_find) > 0:
        page_count_find = list(map(int, page_count_find))
        result["is_over"] = page_count >= max(page_count_find)
    else:
        result["is_over"] = True
    return result


def delete_favorite(blog_id):
    api_url = " https://weibo.com/aj/fav/mblog/del?ajwvr=6"
    post_data = {
        "mid": blog_id,
        "location": "v6_fav"
    }
    headers = {
        "Origin": "https://weibo.com",
        "Referer": "https://weibo.com/fav",
    }
    cookies = {"SUB": weibo.COOKIES["SUB"]}
    api_response = net.Request(api_url, method="POST", fields=post_data, cookies=cookies, headers=headers).enable_json_decode()
    if api_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(api_response.status))
    crawler.get_json_value(api_response.json_data, "code", type_check=int, value_check=100000)


class Favorite(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            const.SysConfigKey.DOWNLOAD_PHOTO: True,
            const.SysConfigKey.NOT_CHECK_SAVE_DATA: True,
            const.SysConfigKey.GET_COOKIE: ("sina.com.cn", "login.sina.com.cn"),
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 设置全局变量，供子线程调用
        weibo.COOKIES.update(self.cookie_value)

        # 检测登录状态
        if not weibo.check_login():
            # 如果没有获得登录相关的cookie，则模拟登录并更新cookie
            if weibo.init_session() and weibo.check_login():
                pass
            else:
                log.error("没有检测到登录信息")
                tool.process_exit()

    def main(self):
        page_count = 1
        is_over = False
        while not is_over:
            favorite_pagination_description = f"第{page_count}页收藏"
            self.start_parse(favorite_pagination_description)
            try:
                favorite_pagination_response = get_one_page_favorite(page_count)
            except CrawlerException as e:
                log.error(e.http_error(favorite_pagination_description))
                raise
            self.parse_result(favorite_pagination_description + "已删除微博", favorite_pagination_response["delete_blog_id_list"])

            for blog_id in favorite_pagination_response["delete_blog_id_list"]:
                blog_description = f"微博{blog_id}"
                log.info(f"开始删除 {blog_description}")
                try:
                    delete_favorite(blog_id)
                except CrawlerException as e:
                    log.error(e.http_error(blog_description))
                    raise
                log.info(f"{blog_description} 删除成功")

            self.parse_result(favorite_pagination_description, favorite_pagination_response["blog_info_list"])

            for blog_info in favorite_pagination_response["blog_info_list"]:
                blog_description = f"微博{blog_info['blog_id']}"
                self.start_parse(blog_description)
                self.parse_result(blog_description, blog_info["photo_url_list"])

                photo_count = 1
                photo_path = os.path.join(self.photo_download_path, blog_info["blog_id"])
                for photo_url in blog_info["photo_url_list"]:
                    photo_path = os.path.join(photo_path, f"%02d.{url.get_file_ext(photo_url)}" % photo_count)
                    photo_description = f"微博{blog_info['blog_id']}第{photo_count}张图片"
                    if self.download(photo_url, photo_path, photo_description, success_callback=self.download_success_callback):
                        self.total_photo_count += 1
                        photo_count += 1

            if favorite_pagination_response["is_over"]:
                is_over = True
            else:
                page_count += 1

        self.end_message()

    def download_success_callback(self, photo_url, photo_path, photo_description, download_return):
        if weibo.check_photo_invalid(photo_path):
            path.delete_dir_or_file(photo_path)
            log.error(f"{photo_description} {photo_url} 已被屏蔽，删除")
            return False
        return True


if __name__ == "__main__":
    Favorite().main()
