# -*- coding:UTF-8  -*-
"""
乃木坂46 OFFICIAL BLOG图片爬虫
https://blog.nogizaka46.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from PIL import Image
from pyquery import PyQuery as pq
from common import *


# 获取成员指定页数的一页日志信息
# account_id -> 264
def get_one_page_blog(account_id, page_count):
    # https://www.nogizaka46.com/s/n46/diary/MEMBER/list?ima=4653&page=0&ct=264&cd=MEMBER
    blog_pagination_url = "https://www.nogizaka46.com/s/n46/diary/MEMBER/list"
    query_data = {"ct": account_id, "page": page_count - 1}
    blog_pagination_response = net.Request(blog_pagination_url, method="GET", fields=query_data)
    result = {
        "blog_id_list": [],  # 全部日志id
        "is_over": False,  # 是否最后一页日志
    }
    if blog_pagination_response.status == 404:
        raise CrawlerException("账号不存在")
    elif blog_pagination_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(blog_pagination_response.status))
    if page_count == 1 and blog_pagination_response.content.find('<p class="bl--card__ttl">該当するデータがございません</p>') > 0:
        raise CrawlerException("账号不存在")
    blog_info_select_list = pq(blog_pagination_response.content).find(".bl--card.js-pos")
    if blog_info_select_list.length == 0:
        raise CrawlerException("页面截取日志列表失败\n" + blog_pagination_response.content)
    for blog_info_index in range(blog_info_select_list.length):
        blog_info_select = blog_info_select_list.eq(blog_info_index)
        blog_url_path = blog_info_select.attr("href")
        blog_id = tool.find_sub_string(blog_url_path, "/s/n46/diary/detail/", "?ima=")
        if not tool.is_integer(blog_id):
            raise CrawlerException("日志预览截取日志id失败\n" + blog_info_select.html())
        result["blog_id_list"].append(int(blog_id))

    # 判断是不是最后一页
    paginate_selector = pq(blog_pagination_response.content).find(".bl--pg .tolast a")
    if paginate_selector.length == 1:
        latest_url = paginate_selector.attr("href")
        if not latest_url:
            raise CrawlerException("页面截取最后一页按钮失败\n" + paginate_selector.html())
        max_page_count = tool.find_sub_string(latest_url, "page=", "&")
        if not tool.is_integer(max_page_count):
            raise CrawlerException("页面截取最后一页失败\n" + paginate_selector.html())
        result["is_over"] = page_count >= int(max_page_count)
    else:
        if pq(blog_pagination_response.content).find(".bl--pg").length == 1:
            result["is_over"] = True
        else:
            raise CrawlerException("页面截取分页信息失败\n" + blog_pagination_response.content)
    return result


def get_blog_page(blog_id):
    blog_url = f"https://www.nogizaka46.com/s/n46/diary/detail/{blog_id}"
    blog_response = net.Request(blog_url, method="GET")
    result = {
        "photo_info_list": [],  # 全部图片地址
    }
    if blog_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(blog_response.status))
    blog_html_selector = pq(blog_response.content).find(".bd--edit")
    if blog_html_selector.length != 1:
        raise CrawlerException("页面截取正文失败\n" + blog_response.content)
    # 获取图片地址
    photo_list_selector = blog_html_selector.find("img")
    for photo_index in range(photo_list_selector.length):
        result_photo_info = {
            "real_photo_url": "",
            "photo_url": "",
        }
        # 图片动作
        photo_selector = photo_list_selector.eq(photo_index)
        photo_url = photo_selector.attr("src")
        if not photo_url:
            raise CrawlerException("图片地址截取失败\n" + photo_selector.html())
        if not (photo_url.startswith("https://") or photo_url.startswith("https://")):
            photo_url = f"https://www.nogizaka46.com/{photo_url}"
        result_photo_info["photo_url"] = photo_url
        # 判断是否是预览地址
        photo_parent_selector = photo_selector.parent()
        if photo_parent_selector.is_("a") and photo_parent_selector.attr("href"):
            result_photo_info["real_photo_url"] = photo_parent_selector.attr("href")
        result["photo_info_list"].append(result_photo_info)
    return result


# 检查旧版本的实际大图是否可以访问
def check_preview_photo(photo_url, real_photo_url):
    result = {
        "cookies": {},  # 页面返回的cookies
        "photo_url": photo_url,  # 大图地址
        "is_over": False,  # 是否已经没有有效的大图了
    }
    # 没有预览地址，直接返回图片原始地址
    if real_photo_url:
        real_photo_response = net.Request(real_photo_url, method="GET")
        if real_photo_response.status == const.ResponseCode.SUCCEED:
            # 检测是不是已经过期删除
            temp_photo_url = tool.find_sub_string(real_photo_response.content, '<img src="', '"')
            if temp_photo_url != "/img/expired.gif":
                if temp_photo_url.find("://") >= 0:
                    result["photo_url"] = temp_photo_url
                else:
                    result["photo_url"] = "http://dcimg.awalker.jp" + temp_photo_url
            else:
                result["is_over"] = True
            # 获取cookies
            result["cookies"] = net.get_cookies_from_response_header(real_photo_response.headers)
    return result


# 检测图片是否有效
def check_photo_invalid(photo_path):
    file_size = os.path.getsize(photo_path)
    # 文件小于1K
    if file_size < const.SIZE_KB:
        return True
    try:
        image = Image.open(photo_path)
    except IOError:  # 不是图片格式
        return True
    # 长或宽任意小于20像素的
    if image.height <= 20 or image.width <= 20:
        return True
    return False


class Nogizaka46Diary(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            const.SysConfigKey.DOWNLOAD_PHOTO: True,
            const.SysConfigKey.SAVE_DATA_FORMATE: (0, ["", "0"]),  # account_id  last_blog_id
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 下载线程
        self.set_crawler_thread(CrawlerThread)


class CrawlerThread(crawler.CrawlerThread):
    def __init__(self, main_thread, single_save_data):
        self.index_key = single_save_data[0]  # account id
        if len(single_save_data) >= 3 and single_save_data[2]:
            self.display_name = single_save_data[2]
        else:
            self.display_name = single_save_data[0]
        crawler.CrawlerThread.__init__(self, main_thread, single_save_data)

    # 获取所有可下载日志
    def get_crawl_list(self):
        page_count = 1
        blog_id_list = []
        is_over = False
        # 获取全部还未下载过需要解析的日志
        while not is_over:
            blog_pagination_description = f"第{page_count}页日志"
            self.start_parse(blog_pagination_description)
            try:
                blog_pagination_response = get_one_page_blog(self.index_key, page_count)
            except CrawlerException as e:
                self.error(e.http_error(blog_pagination_description))
                raise
            self.parse_result(blog_pagination_description, blog_pagination_response["blog_id_list"])

            # 寻找这一页符合条件的日志
            for blog_id in blog_pagination_response["blog_id_list"]:
                # 检查是否达到存档记录
                if blog_id > int(self.single_save_data[1]):
                    blog_id_list.append(blog_id)
                else:
                    is_over = True
                    break

            if not is_over:
                if blog_pagination_response["is_over"]:
                    is_over = True
                else:
                    page_count += 1
        return blog_id_list

    # 解析单个日志
    def crawl_blog(self, blog_id):
        blog_description = f"日志{blog_id}"
        self.start_parse(blog_description)
        try:
            blog_response = get_blog_page(blog_id)
        except CrawlerException as e:
            self.error(e.http_error(f"日志{blog_id}"))
            raise
        self.parse_result(blog_description, blog_response["photo_info_list"])

        photo_index = 1
        for photo_info in blog_response["photo_info_list"]:
            # 检查是否存在大图可以下载
            preview_photo_response = check_preview_photo(photo_info["photo_url"], photo_info["real_photo_url"])
            if preview_photo_response["cookies"]:
                photo_url = preview_photo_response["photo_url"]
            else:
                photo_url = photo_info["photo_url"]

            photo_name = f"%06d_%02d.{url.get_file_ext(photo_url, 'jpg')}" % (blog_id, photo_index)
            photo_path = os.path.join(self.main_thread.photo_download_path, self.display_name, photo_name)
            photo_description = f"日志{blog_id}第{photo_index}张图片"
            if self.download(photo_url, photo_path, photo_description, cookies=preview_photo_response["cookies"], success_callback=self.download_success_callback):
                self.temp_path_list.append(photo_path)  # 设置临时目录
                self.total_photo_count += 1  # 计数累加
            photo_index += 1

        # 日志内图片全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.single_save_data[1] = str(blog_id)  # 设置存档记录

    def download_success_callback(self, photo_url, photo_path, photo_description, download_return):
        if check_photo_invalid(photo_path):
            path.delete_dir_or_file(photo_path)
            self.info(f"{photo_description} {photo_url} 不符合规则，删除")
            return False
        return True

    def _run(self):
        # 获取所有可下载日志
        blog_id_list = self.get_crawl_list()
        self.info(f"需要下载的全部日志解析完毕，共{len(blog_id_list)}个")

        # 从最早的日志开始下载
        while len(blog_id_list) > 0:
            self.crawl_blog(blog_id_list.pop())


if __name__ == "__main__":
    Nogizaka46Diary().main()
