# -*- coding:UTF-8  -*-
"""
ameblo图片爬虫
https://ameblo.jp/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import re
import urllib.parse
from PIL import Image
from pyquery import PyQuery as pq
from common import *

EACH_LOOP_MAX_PAGE_COUNT = 200
COOKIES = {}


# 检测登录状态
def check_login():
    global COOKIES
    if not COOKIES:
        return False
    account_index_url = "https://www.ameba.jp/home"
    index_response = net.Request(account_index_url, method="GET", cookies=COOKIES).disable_redirect()
    if index_response.status == const.ResponseCode.SUCCEED:
        return True
    COOKIES = {}
    return False


# 获取指定页数的全部日志
def get_one_page_blog(account_name, page_count):
    blog_pagination_url = f"https://ameblo.jp/{account_name}/page-{page_count}.html"
    blog_pagination_response = net.Request(blog_pagination_url, method="GET")
    result = {
        "blog_id_list": [],  # 全部日志id
        "is_over": False,  # 是否最后一页日志
    }
    if blog_pagination_response.status == 404:
        raise CrawlerException("账号不存在")
    elif blog_pagination_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(blog_pagination_response.status))
    # 获取日志id
    blog_id_list = re.findall(r'data-unique-entry-id="(\d*)"', blog_pagination_response.content)
    result["blog_id_list"] = list(map(int, blog_id_list))
    # 另一种页面格式
    if len(result["blog_id_list"]) == 0:
        # goto-risako
        blog_list_selector = pq(blog_pagination_response.content).find("#main li a.skin-titleLink")
        for blog_url_index in range(blog_list_selector.length):
            blog_url = blog_list_selector.eq(blog_url_index).attr("href")
            blog_id = tool.find_sub_string(blog_url, "entry-", ".html")
            if not tool.is_integer(blog_id):
                raise CrawlerException(f"日志地址 {blog_url} 截取日志id失败")
            result["blog_id_list"].append(int(blog_id))
    if len(result["blog_id_list"]) == 0:
        if page_count == 1:
            raise CrawlerException("页面匹配日志id失败\n" + blog_pagination_response.content)
        log.error(account_name + " 新的分页页面")
        result["is_over"] = True
        return result
    # 判断是不是最后一页
    # https://ameblo.jp/18prokonan/
    if pq(blog_pagination_response.content).find("div.pagingArea").length > 0:
        if pq(blog_pagination_response.content).find("div.pagingArea a.pagingNext").length == 0 and \
                pq(blog_pagination_response.content).find("div.pagingArea a.pagingPrev").length == 0:
            raise CrawlerException("页面截取分页信息div.pagingArea失败\n" + blog_pagination_response.content)
        result["is_over"] = pq(blog_pagination_response.content).find("div.pagingArea a.pagingNext").length == 0
    # https://ameblo.jp/1108ayanyan/
    elif pq(blog_pagination_response.content).find("ul.skin-paging").length > 0:
        if pq(blog_pagination_response.content).find("ul.skin-paging a.skin-pagingNext").length == 0 and \
                pq(blog_pagination_response.content).find("ul.skin-paging a.skin-pagingPrev").length == 0:
            raise CrawlerException("页面截取分页信息ul.skin-paging失败\n" + blog_pagination_response.content)
        result["is_over"] = pq(blog_pagination_response.content).find("ul.skin-paging a.skin-pagingNext").length == 0
    # https://ameblo.jp/48orii48/
    elif pq(blog_pagination_response.content).find("div.page").length > 0:
        pagination_selector = pq(blog_pagination_response.content).find("div.page").eq(0).find("a")
        find_page_count_list = []
        for pagination_index in range(pagination_selector.length):
            temp_page_count = tool.find_sub_string(pagination_selector.eq(pagination_index).attr("href"), "/page-", ".html")
            if tool.is_integer(temp_page_count):
                find_page_count_list.append(int(temp_page_count))
        if len(find_page_count_list) == 0:
            raise CrawlerException("页面截取分页信息失败\n" + blog_pagination_response.content)
        result["is_over"] = page_count >= max(find_page_count_list)
    return result


# 获取指定id的日志
def get_blog_page(account_name, blog_id):
    blog_url = f"https://ameblo.jp/{account_name}/entry-{blog_id}.html"
    blog_response = net.Request(blog_url, method="GET", cookies=COOKIES)
    result = {
        "photo_url_list": [],  # 全部图片地址
        "is_delete": False,  # 是否已删除
    }
    if blog_response.status == 404:
        result["is_delete"] = True
        return result
    elif blog_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(blog_response.status))
    if blog_response.content.find("この記事はアメンバーさん限定です。") >= 0:
        raise CrawlerException(f"需要关注后才能访问，请在 https://profile.ameba.jp/ameba/{account_name}，选择'アメンバー申請'")
    # 截取日志正文部分（有多种页面模板）
    article_class_list = ["subContentsInner", "articleText", "skin-entryInner"]
    article_html_selector = None
    for article_class in article_class_list:
        article_html_selector = pq(blog_response.content).find("." + article_class)
        if article_html_selector.length > 0:
            break
    if article_html_selector is None or article_html_selector.length == 0:
        raise CrawlerException("页面截取正文失败\n" + blog_response.content)
    # 获取图片地址
    photo_list_selector = article_html_selector.find("img")
    for photo_index in range(photo_list_selector.length):
        photo_selector = photo_list_selector.eq(photo_index)
        if photo_selector.has_class("accessLog"):
            continue
        photo_url = photo_selector.attr("src")
        if not photo_url:
            continue
        # 用户上传的图片
        if photo_url.find("//stat.ameba.jp/user_images/") > 0:
            result["photo_url_list"].append(photo_url)
        # 外部图片
        elif photo_url.find("//img-proxy.blog-video.jp/images?url=") > 0:
            pass
        # 表情
        elif photo_url.find("//emoji.ameba.jp/img/") > 0 or photo_url.find("//stat.ameba.jp/blog/ucs/img/") > 0 \
                or photo_url.find("//stat.ameba.jp/mb/") > 0 or photo_url.find("//stat.ameba.jp/common_style/") > 0 \
                or photo_url.find("//stat100.ameba.jp/blog/ucs/img/") > 0 or photo_url.find("//stat100.ameba.jp/candy/"):
            pass
        elif photo_url.startswith("data:image/gif;base64,") or photo_url.startswith("file://"):
            pass
        else:
            log.warning(f"未知图片地址：{photo_url} ({blog_url})")
    # todo 含有视频
    # https://ameblo.jp/kawasaki-nozomi/entry-12111279076.html
    return result


# 获取原始图片下载地址
# https://stat.ameba.jp/user_images/20110612/15/akihabara48/af/3e/j/t02200165_0800060011286009555.jpg
# ->
# https://stat.ameba.jp/user_images/20110612/15/akihabara48/af/3e/j/o0800060011286009555.jpg
# https://stat.ameba.jp/user_images/4b/90/10112135346_s.jpg
# ->
# https://stat.ameba.jp/user_images/4b/90/10112135346.jpg
def get_origin_photo_url(photo_url):
    if photo_url.find("//stat.ameba.jp/user_images/") != -1:
        # 最新的photo_url使用?caw=指定显示分辨率，去除
        # http://stat.ameba.jp/user_images/20161220/12/akihabara48/fd/1a/j/o0768032013825427476.jpg?caw=800
        photo_url = url.remove_query(photo_url)
        photo_name, photo_extension = url.get_file_name_ext(photo_url)
        if not photo_name.startswith("o"):
            # https://stat.ameba.jp/user_images/20110612/15/akihabara48/af/3e/j/t02200165_0800060011286009555.jpg
            if photo_name.startswith("t") and photo_name.find("_") > 0:
                new_photo_name = "o" + photo_name.split("_", 1)[1] + "." + photo_extension
                photo_url = urllib.parse.urljoin(photo_url, new_photo_name)
            # https://stat.ameba.jp/user_images/4b/90/10112135346_s.jpg
            elif photo_name.endswith("_s"):
                new_photo_name = tool.remove_string_suffix(photo_name, "_s") + "." + photo_extension
                photo_url = urllib.parse.urljoin(photo_url, new_photo_name)
            # https://stat.ameba.jp/user_images/2a/ce/10091204420.jpg
            elif tool.is_integer(photo_name.split(".")[0]):
                pass
            else:
                log.warning(f"无法解析的图片地址 {photo_url}")
    elif photo_url.find("//stat100.ameba.jp/blog/img/") > 0:
        pass
    return photo_url


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
    # 文件小于 5K 并且 长或宽任意小于100像素的
    if file_size < 5 * const.SIZE_KB and (image.height <= 100 or image.width <= 100):
        return True
    return False


class Ameblo(crawler.Crawler):
    def __init__(self, **kwargs):
        global COOKIES

        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            const.SysConfigKey.DOWNLOAD_PHOTO: True,
            const.SysConfigKey.GET_COOKIE: ("ameba.jp", "www.ameba.jp"),
            const.SysConfigKey.SAVE_DATA_FORMATE: (0, ["", "0"]),  # account_name  last_blog_id
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 设置全局变量，供子线程调用
        COOKIES = self.cookie_value

        # 下载线程
        self.set_crawler_thread(CrawlerThread)

    def init(self):
        # 检测登录状态
        if check_login():
            return

        while True:
            input_str = input(tool.convert_timestamp_to_formatted_time() + " 没有检测到账号登录状态，可能无法解析只对会员开放的日志，继续程序(C)ontinue？或者退出程序(E)xit？:")
            input_str = input_str.lower()
            if input_str in ["e", "exit"]:
                tool.process_exit()
            elif input_str in ["c", "continue"]:
                break


class CrawlerThread(crawler.CrawlerThread):
    def __init__(self, main_thread, single_save_data):
        self.index_key = single_save_data[0]  # account id
        if len(single_save_data) >= 3 and single_save_data[2]:
            self.display_name = single_save_data[2]
        else:
            self.display_name = single_save_data[0]
        crawler.CrawlerThread.__init__(self, main_thread, single_save_data)
        self.duplicate_list = {}

    # 获取偏移量，避免一次查询过多页数
    def get_offset_page_count(self):
        start_page_count = 1
        while EACH_LOOP_MAX_PAGE_COUNT > 0:
            start_page_count += EACH_LOOP_MAX_PAGE_COUNT
            blog_pagination_description = f"第{start_page_count}页日志"
            self.start_parse(blog_pagination_description)
            try:
                blog_pagination_response = get_one_page_blog(self.index_key, start_page_count)
            except CrawlerException as e:
                self.error(e.http_error(blog_pagination_description))
                raise
            # 这页没有任何内容，返回上一个检查节点
            if blog_pagination_response["is_over"]:
                start_page_count -= EACH_LOOP_MAX_PAGE_COUNT
                break
            # 这页已经匹配到存档点，返回上一个节点
            if blog_pagination_response["blog_id_list"][-1] < int(self.single_save_data[1]):
                start_page_count -= EACH_LOOP_MAX_PAGE_COUNT
                break
            self.info(f"前{start_page_count}页日志全部符合条件，跳过{EACH_LOOP_MAX_PAGE_COUNT}页后继续查询")
        return start_page_count

    # 获取所有可下载日志
    def get_crawl_list(self, page_count):
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

            for blog_id in blog_pagination_response["blog_id_list"]:
                # 检查是否达到存档记录
                if blog_id > int(self.single_save_data[1]):
                    # 新增日志导致的重复判断
                    if blog_id in blog_id_list:
                        continue
                    else:
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
        album_description = f"日志{blog_id}"
        self.start_parse(album_description)
        try:
            blog_response = get_blog_page(self.index_key, blog_id)
        except CrawlerException as e:
            self.error(e.http_error(album_description))
            raise
        # 日志只对关注者可见
        if blog_response["is_delete"]:
            self.error(f"{album_description} 已被删除，跳过")
            return
        self.parse_result(album_description, blog_response["photo_url_list"])

        photo_index = 1
        for photo_url in blog_response["photo_url_list"]:
            # 获取原始图片下载地址
            photo_url = get_origin_photo_url(photo_url)
            if photo_url in self.duplicate_list:
                self.info(f"{album_description}的图片 {photo_url} 已存在")
                continue
            self.duplicate_list[photo_url] = 1

            photo_name = f"%011d_%02d.{url.get_file_ext(photo_url, 'jpg')}" % (blog_id, photo_index)
            photo_path = os.path.join(self.main_thread.photo_download_path, self.index_key, photo_name)
            photo_description = f"日志{blog_id}第{photo_index}/{blog_response['photo_url_list']}张图片"
            download_return = self.download(photo_url, photo_path, photo_description, success_callback=self.download_success_callback)
            if download_return and not download_return["is_invalid_photo"]:
                self.temp_path_list.append(photo_path)  # 设置临时目录
                self.total_photo_count += 1  # 计数累加

            photo_index += 1

        # 日志内图片全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.single_save_data[1] = str(blog_id)  # 设置存档记录

    def download_success_callback(self, photo_url, photo_path, photo_description, download_return: net.Download):
        if check_photo_invalid(photo_path):
            path.delete_dir_or_file(photo_path)
            self.info(f"{photo_description} {photo_url} 不符合规则，删除")
            download_return["is_invalid_photo"] = True
            return False
        download_return["is_invalid_photo"] = False
        return True

    def _run(self):
        # 查询当前任务大致需要从多少页开始爬取
        start_page_count = self.get_offset_page_count()

        while start_page_count >= 1:
            # 获取所有可下载日志
            blog_id_list = self.get_crawl_list(start_page_count)
            self.info(f"需要下载的全部日志解析完毕，共{len(blog_id_list)}个")

            # 从最早的日志开始下载
            while len(blog_id_list) > 0:
                self.crawl_blog(blog_id_list.pop())

            start_page_count -= EACH_LOOP_MAX_PAGE_COUNT


if __name__ == "__main__":
    Ameblo().main()
