# -*- coding:UTF-8  -*-
"""
乃木坂46 OFFICIAL BLOG图片爬虫
https://blog.nogizaka46.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import re
import time
import traceback
from PIL import Image
from pyquery import PyQuery as pq
from common import *


# 获取成员指定页数的一页日志信息
# account_id -> asuka.saito
def get_one_page_blog(account_id, page_count):
    # https://blog.nogizaka46.com/asuka.saito
    blog_pagination_url = "https://blog.nogizaka46.com/%s/" % account_id
    query_data = {"p": page_count}
    blog_pagination_response = net.request(blog_pagination_url, method="GET", fields=query_data)
    result = {
        "blog_info_list": [],  # 全部图片信息
        "is_over": False,  # 是否最后一页日志
    }
    if blog_pagination_response.status == 404:
        raise crawler.CrawlerException("账号不存在")
    elif blog_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(blog_pagination_response.status))
    blog_pagination_response_content = blog_pagination_response.data
    blog_body_selector = pq(blog_pagination_response_content).find("div#sheet div.entrybody")
    blog_bottom_selector = pq(blog_pagination_response_content).find("div#sheet div.entrybottom")
    if blog_body_selector.length == 0 or blog_bottom_selector.length == 0:
        raise crawler.CrawlerException("页面截取正文失败\n%s" % blog_pagination_response_content)
    if blog_body_selector.length != blog_bottom_selector.length:
        raise crawler.CrawlerException("页面截取正文数量不匹配\n%s" % blog_pagination_response_content)
    for blog_body_index in range(0, blog_body_selector.length):
        result_photo_info = {
            "big_2_small_photo_list": {},  # 全部含有大图的图片
            "blog_id": None,  # 日志id
            "photo_url_list": [],  # 全部图片地址
        }
        blog_body_html = blog_body_selector.eq(blog_body_index).html()
        # 获取日志id
        blog_url = blog_bottom_selector.eq(blog_body_index).find("a").eq(0).attr("href")
        if blog_url is None:
            raise crawler.CrawlerException("日志内容截取日志地址失败\n%s" % blog_bottom_selector.eq(blog_body_index).html())
        blog_id = blog_url.split("/")[-1].split(".")[0]
        if not tool.is_integer(blog_id):
            raise crawler.CrawlerException("日志内容截取日志id失败\n%s" % blog_bottom_selector.eq(blog_body_index).html())
        result_photo_info["blog_id"] = int(blog_id)
        # 获取图片地址列表
        result_photo_info["photo_url_list"] = re.findall('src="(http[^"]*)"', blog_body_html)
        # 获取全部大图对应的小图
        big_photo_list_find = re.findall('<a href="([^"]*)"><img[\S|\s]*? src="([^"]*)"', blog_body_html)
        big_2_small_photo_lust = {}
        for big_photo_url, small_photo_url in big_photo_list_find:
            big_2_small_photo_lust[small_photo_url] = big_photo_url
        result_photo_info["big_2_small_photo_lust"] = big_2_small_photo_lust
        result["blog_info_list"].append(result_photo_info)
    # 判断是不是最后一页
    paginate_selector = pq(blog_pagination_response_content).find("div#sheet div.paginate")
    if paginate_selector.length > 0:
        paginate_url = paginate_selector.eq(0).find("a:last").attr("href")
        if paginate_url is None:
            raise crawler.CrawlerException("页面截取分页信息失败\n%s" % paginate_selector.html())
        max_page_count = paginate_url.split("?p=")[-1]
        if not tool.is_integer(max_page_count):
            raise crawler.CrawlerException("分页信息解析失败\n%s" % blog_bottom_selector.html())
        result["is_over"] = page_count >= int(max_page_count)
    else:
        result["is_over"] = True
    return result


# 检查图片是否存在对应的大图，以及判断大图是否仍然有效，如果存在可下载的大图则返回大图地址，否则返回原图片地址
def check_big_photo(photo_url, big_2_small_list):
    result = {
        "cookies": None,  # 页面返回的cookies
        "photo_url": None,  # 大图地址
        "is_over": False,  # 是否已经没有有效的大图了
    }
    if photo_url in big_2_small_list:
        if big_2_small_list[photo_url].find("//dcimg.awalker.jp") > 0:
            big_photo_response = net.request(big_2_small_list[photo_url], method="GET")
            if big_photo_response.status == net.HTTP_RETURN_CODE_SUCCEED:
                # 检测是不是已经过期删除
                temp_photo_url = tool.find_sub_string(big_photo_response.data, '<img src="', '"')
                if temp_photo_url != "/img/expired.gif":
                    if temp_photo_url.find("://") >= 0:
                        result["photo_url"] = temp_photo_url
                    else:
                        result["photo_url"] = "http://dcimg.awalker.jp" + temp_photo_url
                else:
                    result["is_over"] = True
                # 获取cookies
                result["cookies"] = net.get_cookies_from_response_header(big_photo_response.headers)
        else:
            result["photo_url"] = big_2_small_list[photo_url]
    return result


# 检测图片是否有效
def check_photo_invalid(file_path):
    file_size = os.path.getsize(file_path)
    # 文件小于5K
    if file_size < 5120:
        try:
            image = Image.open(file_path)
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
            crawler.SYS_DOWNLOAD_PHOTO: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 解析存档文件
        # account_id  last_blog_id
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

        log.step("全部下载完毕，耗时%s秒，共计图片%s张" % (self.get_run_time(), self.total_photo_count))


class Download(crawler.DownloadThread):
    def __init__(self, single_save_data, main_thread):
        crawler.DownloadThread.__init__(self, single_save_data, main_thread)
        self.account_id = self.single_save_data[0]
        if len(self.single_save_data) >= 3 and self.single_save_data[2]:
            self.display_name = self.single_save_data[2]
        else:
            self.display_name = self.single_save_data[0]
        self.step("开始")

    # 获取所有可下载日志
    def get_crawl_list(self):
        page_count = 1
        blog_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的日志
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析第%s页日志" % page_count)

            # 获取一页图片
            try:
                blog_pagination_response = get_one_page_blog(self.account_id, page_count)
            except crawler.CrawlerException as e:
                self.error("第%s页日志解析失败，原因：%s" % (page_count, e.message))
                raise

            self.trace("第%s页解析的全部日志：%s" % (page_count, blog_pagination_response["blog_info_list"]))
            self.step("第%s页解析获取%s个日志" % (page_count, len(blog_pagination_response["blog_info_list"])))

            # 寻找这一页符合条件的日志
            for blog_info in blog_pagination_response["blog_info_list"]:
                # 检查是否达到存档记录
                if blog_info["blog_id"] > int(self.single_save_data[1]):
                    blog_info_list.append(blog_info)
                else:
                    is_over = True
                    break

            if not is_over:
                if blog_pagination_response["is_over"]:
                    is_over = True
                else:
                    page_count += 1

        return blog_info_list

    # 解析单个日志
    def crawl_blog(self, blog_info):
        self.step("开始解析日志%s" % blog_info["blog_id"])

        self.trace("日志%s解析的全部图片：%s" % (blog_info["blog_id"], blog_info["photo_url_list"]))
        self.step("日志%s解析获取%s张图片" % (blog_info["blog_id"], len(blog_info["photo_url_list"])))

        photo_index = 1
        for photo_url in blog_info["photo_url_list"]:
            self.main_thread_check()  # 检测主线程运行状态
            # 检查是否存在大图可以下载
            big_photo_response = check_big_photo(photo_url, blog_info["big_2_small_photo_lust"])
            if big_photo_response["photo_url"] is not None:
                photo_url = big_photo_response["photo_url"]
            self.step("开始下载日志%s的第%s张图片 %s" % (blog_info["blog_id"], photo_index, photo_url))

            file_path = os.path.join(self.main_thread.photo_download_path, self.display_name, "%06d_%02d.%s" % (blog_info["blog_id"], photo_index, net.get_file_type(photo_url, "jpg")))
            save_file_return = net.download(photo_url, file_path, cookies_list=big_photo_response["cookies"])
            if save_file_return["status"] == 1:
                if check_photo_invalid(file_path):
                    path.delete_dir_or_file(file_path)
                    self.step("日志%s的第%s张图片 %s 不符合规则，删除" % (blog_info["blog_id"], photo_index, photo_url))
                    continue
                else:
                    self.temp_path_list.append(file_path)  # 设置临时目录
                    self.total_photo_count += 1  # 计数累加
                    self.step("日志%s的第%s张图片下载成功" % (blog_info["blog_id"], photo_index))
            else:
                self.error("日志%s的第%s张图片 %s 下载失败，原因：%s" % (blog_info["blog_id"], photo_index, photo_url, crawler.download_failre(save_file_return["code"])))
                self.check_thread_exit_after_download_failure()
            photo_index += 1

        # 日志内图片全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.single_save_data[1] = str(blog_info["blog_id"])  # 设置存档记录

    def run(self):
        try:
            # 获取所有可下载日志
            blog_info_list = self.get_crawl_list()
            self.step("需要下载的全部日志解析完毕，共%s个" % len(blog_info_list))

            # 从最早的日志开始下载
            while len(blog_info_list) > 0:
                self.crawl_blog(blog_info_list.pop())
                self.main_thread_check()  # 检测主线程运行状态
        except (SystemExit, KeyboardInterrupt) as e:
            if isinstance(e, SystemExit) and e.code == 1:
                self.error("异常退出")
            else:
                self.step("提前退出")
            # 如果临时目录变量不为空，表示某个日志正在下载中，需要把下载了部分的内容给清理掉
            self.clean_temp_path()
        except Exception as e:
            self.error("未知异常")
            self.error(str(e) + "\n" + traceback.format_exc(), False)

        # 保存最后的信息
        with self.thread_lock:
            self.write_single_save_data()
            self.main_thread.total_photo_count += self.total_photo_count
            self.main_thread.save_data.pop(self.account_id)
        self.step("下载完毕，总共获得%s张图片" % self.total_photo_count)
        self.notify_main_thread()


if __name__ == "__main__":
    Nogizaka46Diary().main()
