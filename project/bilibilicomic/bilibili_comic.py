# -*- coding:UTF-8  -*-
"""
bilibili漫画爬虫
https://manga.bilibili.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import time
import traceback
from common import *

COOKIE_INFO = {}


# 检测是否已登录
def check_login():
    api_url = "https://api.bilibili.com/x/web-interface/nav"
    api_response = net.http_request(api_url, method="GET", cookies_list=COOKIE_INFO, json_decode=True)
    if api_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        return crawler.get_json_value(api_response.json_data, "data", "isLogin", type_check=bool)
    return False


def get_comic_index_page(comic_id):
    # https://manga.bilibili.com/detail/mc24742
    api_url = "https://manga.bilibili.com/twirp/comic.v1.Comic/ComicDetail?device=pc&platform=web"
    post_data = {
        "comic_id": comic_id
    }
    api_response = net.http_request(api_url, method="POST", fields=post_data, cookies_list=COOKIE_INFO, json_decode=True)
    result = {
        "comic_info_list": {},  # 漫画列表信息
    }
    if api_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(api_response.status))
    for ep_info in crawler.get_json_value(api_response.json_data, "data", "ep_list", type_check=list):
        result_comic_info = {
            "ep_id": None,  # 章节id
            "ep_name": "",  # 章节名字
        }
        # 获取页面id
        result_comic_info["ep_id"] = crawler.get_json_value(ep_info, "id", type_check=int)
        # 获取章节名字
        short_title = crawler.get_json_value(ep_info, "short_title", type_check=str).strip()
        title = crawler.get_json_value(ep_info, "title", type_check=str).strip()
        result_comic_info["ep_name"] = (short_title + " " + title) if title else short_title
        result["comic_info_list"][result_comic_info["ep_id"]] = result_comic_info
    return result


# 获取漫画指定章节
def get_chapter_page(ep_id):
    # https://m.dmzj.com/view/9949/19842.html
    api_url = "https://manga.bilibili.com/twirp/comic.v1.Comic/GetImageIndex?device=pc&platform=web"
    post_data = {
        "ep_id": ep_id
    }
    api_response = net.http_request(api_url, method="POST", fields=post_data, cookies_list=COOKIE_INFO, json_decode=True)
    result = {
        "need_buy": False,  # 是否需要购买
        "photo_url_list": [],  # 全部漫画图片地址
    }
    if api_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(api_response.status))
    result["need_buy"] = crawler.get_json_value(api_response.json_data, "code", type_check=int) == 1
    image_path_list = []
    for image_info in crawler.get_json_value(api_response.json_data, "data", "images", type_check=list):
        image_path_list.append(crawler.get_json_value(image_info, "path"))
    token_api_url = "https://manga.bilibili.com/twirp/comic.v1.Comic/ImageToken?device=pc&platform=web"
    post_data = {
        "urls": tool.json_encode(image_path_list)
    }
    token_api_response = net.http_request(token_api_url, method="POST", fields=post_data, json_decode=True)
    if api_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException("图片token获取，" + crawler.request_failre(api_response.status))
    for token_info in crawler.get_json_value(token_api_response.json_data, "data", type_check=list):
        result["photo_url_list"].append("%s?token=%s" % (crawler.get_json_value(token_info, "url", type_check=str), crawler.get_json_value(token_info, "token", type_check=str)))
    return result


class BiliBiliComic(crawler.Crawler):
    def __init__(self, **kwargs):
        global COOKIE_INFO

        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_GET_COOKIE: ("bilibili.com",),
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 设置全局变量，供子线程调用
        COOKIE_INFO = self.cookie_value

        # 解析存档文件
        # comic_id  last_comic_id (comic_name)
        self.account_list = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

        # 检测登录状态
        if not check_login():
            while True:
                input_str = input(crawler.get_time() + " 没有检测到账号登录状态，可能无法解析需要登录才能查看的漫画，继续程序(C)ontinue？或者退出程序(E)xit？:")
                input_str = input_str.lower()
                if input_str in ["e", "exit"]:
                    tool.process_exit()
                elif input_str in ["c", "continue"]:
                    break

    def main(self):
        try:
            # 循环下载每个id
            thread_list = []
            for account_id in sorted(self.account_list.keys()):
                # 提前结束
                if not self.is_running():
                    break

                # 开始下载
                thread = Download(self.account_list[account_id], self)
                thread.start()
                thread_list.append(thread)

                time.sleep(1)

            # 等待子线程全部完成
            while len(thread_list) > 0:
                thread_list.pop().join()
        except KeyboardInterrupt:
            self.stop_process()

        # 未完成的数据保存
        if len(self.account_list) > 0:
            file.write_file(tool.list_to_string(list(self.account_list.values())), self.temp_save_data_path)

        # 重新排序保存存档文件
        crawler.rewrite_save_file(self.temp_save_data_path, self.save_data_path)

        log.step("全部下载完毕，耗时%s秒，共计图片%s张，%s个视频，%s个音频" % (self.get_run_time(), self.total_photo_count, self.total_video_count, self.total_audio_count))


class Download(crawler.DownloadThread):
    def __init__(self, account_info, main_thread):
        crawler.DownloadThread.__init__(self, account_info, main_thread)
        self.comic_id = self.account_info[0]
        if len(self.account_info) >= 3 and self.account_info[2]:
            self.display_name = self.account_info[2]
        else:
            self.display_name = self.account_info[0]
        self.step("开始")

    # 获取所有可下载漫画
    def get_crawl_list(self):
        comic_info_list = []

        # 获取漫画首页
        self.step("开始解析漫画首页")
        try:
            blog_pagination_response = get_comic_index_page(self.comic_id)
        except crawler.CrawlerException as e:
            self.error("漫画首页解析失败，原因：%s" % e.message)
            raise

        self.trace("漫画首页解析的全部漫画：%s" % blog_pagination_response["comic_info_list"])
        self.step("漫画首页解析获取%s个漫画" % len(blog_pagination_response["comic_info_list"]))

        # 寻找符合条件的章节
        for ep_id in sorted(list(blog_pagination_response["comic_info_list"].keys()), reverse=True):
            comic_info = blog_pagination_response["comic_info_list"][ep_id]
            # 检查是否达到存档记录
            if ep_id > int(self.account_info[1]):
                comic_info_list.append(comic_info)
            else:
                break

        return comic_info_list

    def crawl_comic(self, comic_info):
        self.step("开始解析漫画%s 《%s》" % (comic_info["ep_id"], comic_info["ep_name"]))

        # 获取指定漫画章节
        try:
            chapter_response = get_chapter_page(comic_info["ep_id"])
        except crawler.CrawlerException as e:
            self.error("漫画%s 《%s》解析失败，原因：%s" % (comic_info["ep_id"], comic_info["ep_name"], e.message))
            raise

        if chapter_response["need_buy"]:
            self.error("漫画%s 《%s》需要购买" % (comic_info["ep_id"], comic_info["ep_name"]))
            tool.process_exit()

        # 图片下载
        photo_index = 1
        chapter_path = os.path.join(self.main_thread.photo_download_path, self.display_name, "%06d %s" % (comic_info["ep_id"], path.filter_text(comic_info["ep_name"])))
        # 设置临时目录
        self.temp_path_list.append(chapter_path)
        for photo_url in chapter_response["photo_url_list"]:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("漫画%s 《%s》开始下载第%s张图片 %s" % (comic_info["ep_id"], comic_info["ep_name"], photo_index, photo_url))

            photo_file_path = os.path.join(chapter_path, "%03d.%s" % (photo_index, net.get_file_type(photo_url)))
            save_file_return = net.save_net_file(photo_url, photo_file_path, header_list={"Referer": "https://m.dmzj.com/"})
            if save_file_return["status"] == 1:
                self.total_photo_count += 1  # 计数累加
                self.step("漫画%s 《%s》第%s张图片下载成功" % (comic_info["ep_id"], comic_info["ep_name"], photo_index))
            else:
                self.error("漫画%s 《%s》第%s张图片 %s 下载失败，原因：%s" % (comic_info["ep_id"], comic_info["ep_name"], photo_index, photo_url, crawler.download_failre(save_file_return["code"])))
                self.check_thread_exit_after_download_failure()
            photo_index += 1

        # 章节内图片全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.account_info[1] = str(comic_info["ep_id"])  # 设置存档记录

    def run(self):
        try:
            # 获取所有可下载章节
            comic_info_list = self.get_crawl_list()
            self.step("需要下载的全部漫画解析完毕，共%s个" % len(comic_info_list))

            # 从最早的章节开始下载
            while len(comic_info_list) > 0:
                self.crawl_comic(comic_info_list.pop())
                self.main_thread_check()  # 检测主线程运行状态
        except (SystemExit, KeyboardInterrupt) as e:
            if isinstance(e, SystemExit) and e.code == 1:
                self.error("异常退出")
            else:
                self.step("提前退出")
            # 如果临时目录变量不为空，表示某个章节正在下载中，需要把下载了部分的内容给清理掉
            self.clean_temp_path()
        except Exception as e:
            self.error("未知异常")
            self.error(str(e) + "\n" + traceback.format_exc(), False)

        # 保存最后的信息
        with self.thread_lock:
            file.write_file("\t".join(self.account_info), self.main_thread.temp_save_data_path)
            self.main_thread.total_photo_count += self.total_photo_count
            self.main_thread.account_list.pop(self.comic_id)
        self.step("下载完毕，总共获得%s张图片" % self.total_photo_count)
        self.notify_main_thread()


if __name__ == "__main__":
    BiliBiliComic().main()
