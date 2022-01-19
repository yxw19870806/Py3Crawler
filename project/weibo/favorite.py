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
from pyquery import PyQuery as pq
from common import *
from project.weibo import weibo


# 获取一页的收藏微博ge
def get_one_page_favorite(page_count):
    # https://www.weibo.com/fav?page=1
    favorite_pagination_url = "http://www.weibo.com/fav"
    query_data = {"page": page_count}
    cookies_list = {"SUB": weibo.COOKIE_INFO["SUB"]}
    favorite_pagination_response = net.request(favorite_pagination_url, method="GET", fields=query_data, cookies_list=cookies_list)
    result = {
        "blog_info_list": [],  # 所有微博信息
        "delete_blog_id_list": [],  # 全部已删除的微博ID
        "is_over": False,  # 是否最后一页收藏
    }
    if favorite_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(favorite_pagination_response.status))
    favorite_pagination_content = favorite_pagination_response.data.decode(errors="ignore")
    favorite_data_html = tool.find_sub_string(favorite_pagination_content, '"ns":"pl.content.favoriteFeed.index"', '"})</script>', 2)
    favorite_data_html = tool.find_sub_string(favorite_data_html, '"html":"', '"})')
    if not favorite_data_html:
        raise crawler.CrawlerException("页面截取收藏信息失败\n%s" % favorite_pagination_content)
    # 替换全部转义斜杠以及没有用的换行符等
    html_data = favorite_data_html.replace("\\\\", chr(1))
    for replace_string in ["\\n", "\\r", "\\t", "\\"]:
        html_data = html_data.replace(replace_string, "")
    html_data = html_data.replace(chr(1), "\\")
    # 解析页面
    children_selector = pq(html_data).find('div.WB_feed').children()
    if children_selector.length == 0:
        raise crawler.CrawlerException("匹配收藏信息失败\n%s" % favorite_data_html)
    if children_selector.length == 1:
        raise crawler.CrawlerException("没有收藏了")
    # 解析日志id和图片地址
    for i in range(0, children_selector.length - 1):
        feed_selector = children_selector.eq(i)
        # 已被删除的微博
        if not feed_selector.has_class("WB_feed_type"):
            if feed_selector.attr("mid") is not None:
                result["delete_blog_id_list"].append(feed_selector.attr("mid"))
            elif feed_selector.find(".WB_empty").length == 1:
                result["delete_blog_id_list"].append(feed_selector.find(".WB_empty").attr("mid"))
            continue
        result_blog_info = {
            "blog_id": None,  # 日志id（mid）
            "photo_url_list": [],  # 所有图片地址
        }
        # 解析日志id
        blog_id = feed_selector.attr("mid")
        if not crawler.is_integer(blog_id):
            raise crawler.CrawlerException("收藏信息解析微博id失败\n%s" % feed_selector.html())
        result_blog_info["blog_id"] = blog_id
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
            thumb_photo_url_list = re.findall('<img src="([^"]*)"/>', media_selector.html())
            if len(thumb_photo_url_list) > 0:
                photo_url_list = []
                for photo_url in thumb_photo_url_list:
                    temp_list = photo_url.split("/")
                    temp_list[3] = "large"
                    photo_url_list.append("http:" + str("/".join(temp_list)))
                result_blog_info["photo_url_list"] = photo_url_list
        if len(result_blog_info["photo_url_list"]) > 0:
            result["blog_info_list"].append(result_blog_info)
    # 最后一条feed是分页信息
    page_selector = children_selector.eq(children_selector.length - 1)
    # 判断是不是最后一页
    page_count_find = re.findall("第(\d*)页", page_selector.html())
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
    header_list = {
        "Origin": "https://weibo.com",
        "Referer": "https://weibo.com/fav",
    }
    cookies_list = {"SUB": weibo.COOKIE_INFO["SUB"]}
    api_response = net.request(api_url, method="POST", fields=post_data, cookies_list=cookies_list, header_list=header_list, json_decode=True)
    if api_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(api_response.status))
    crawler.get_json_value(api_response.json_data, "code", type_check=int, value_check=100000)


class Favorite(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_NOT_CHECK_SAVE_DATA: True,
            crawler.SYS_GET_COOKIE: ("sina.com.cn", "login.sina.com.cn"),
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 设置全局变量，供子线程调用
        weibo.COOKIE_INFO.update(self.cookie_value)

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
            if not self.is_running():
                tool.process_exit(0)
            log.step("开始解析第%s页收藏" % page_count)

            try:
                favorite_pagination_response = get_one_page_favorite(page_count)
            except crawler.CrawlerException as e:
                log.error("第%s页收藏解析失败，原因：%s" % (page_count, e.message))
                raise

            log.trace("第%s页解析的已删除微博：%s" % (page_count, favorite_pagination_response["delete_blog_id_list"]))
            log.step("第%s页解析获取%s个已删除微博" % (page_count, len(favorite_pagination_response["delete_blog_id_list"])))

            for blog_id in favorite_pagination_response["delete_blog_id_list"]:
                log.step("开始删除微博%s" % blog_id)
                try:
                    delete_favorite(blog_id)
                except crawler.CrawlerException as e:
                    log.error("微博%s删除失败，原因：%s" % (blog_id, e.message))
                    raise
                log.step("删除微博%s成功" % blog_id)

            log.trace("第%s页解析的全部微博：%s" % (page_count, favorite_pagination_response["blog_info_list"]))
            log.step("第%s页解析获取%s个微博" % (page_count, len(favorite_pagination_response["blog_info_list"])))

            for blog_info in favorite_pagination_response["blog_info_list"]:
                log.step("开始解析微博%s" % blog_info["blog_id"])

                log.trace("微博%s解析的全部图片：%s" % (blog_info["blog_id"], blog_info["photo_url_list"]))
                log.step("微博%s解析获取%s张图片" % (blog_info["blog_id"], len(blog_info["photo_url_list"])))

                photo_count = 1
                photo_path = os.path.join(self.photo_download_path, blog_info["blog_id"])
                for photo_url in blog_info["photo_url_list"]:
                    log.step("微博%s开始下载第%s张图片 %s" % (blog_info["blog_id"], photo_count, photo_url))

                    file_path = os.path.join(photo_path, "%s.%s" % (photo_count, net.get_file_type(photo_url)))
                    save_file_return = net.save_net_file(photo_url, file_path)
                    if save_file_return["status"] == 1:
                        if weibo.check_photo_invalid(file_path):
                            path.delete_dir_or_file(file_path)
                            log.error("微博%s的第%s张图片 %s 资源已被删除，跳过" % (blog_info["blog_id"], photo_count, photo_url))
                        else:
                            log.step("微博%s的第%s张图片下载成功" % (blog_info["blog_id"], photo_count))
                            photo_count += 1
                            self.total_photo_count += 1
                    else:
                        log.error("微博%s的第%s张图片 %s 下载失败，原因：%s" % (blog_info["blog_id"], photo_count, photo_url, crawler.download_failre(save_file_return["code"])))

            if favorite_pagination_response["is_over"]:
                is_over = True
            else:
                page_count += 1

        log.step("全部下载完毕，耗时%s秒，共计图片%s张" % (self.get_run_time(), self.total_photo_count))


if __name__ == "__main__":
    Favorite().main()
