# -*- coding:UTF-8  -*-
"""
半次元图片爬虫
https://bcy.net/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import base64
import os
import time
import traceback
import urllib.parse
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from common import *

EACH_PAGE_ALBUM_COUNT = 20


# 获取指定页数的全部作品
def get_one_page_album(account_id, since_id):
    # https://bcy.net/apiv3/user/selfPosts?uid=50220&since=6059553291006664462
    api_url = "https://bcy.net/apiv3/user/selfPosts"
    query_data = {
        "since": since_id,
        "uid": account_id,
    }
    api_response = net.http_request(api_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "album_id_list": [],  # 全部作品id
    }
    if api_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(api_response.status))
    for album_info in crawler.get_json_value(api_response.json_data, "data", "items", type_check=list):
        result["album_id_list"].append(crawler.get_json_value(album_info, "item_detail", "item_id", type_check=int))
    return result


# 获取指定id的作品
def get_album_page(album_id):
    # https://bcy.net/item/detail/6383727612803440398
    # https://bcy.net/item/detail/5969608017174355726 该作品已被作者设置为只有粉丝可见
    # https://bcy.net/item/detail/6363512825238806286 该作品已被作者设置为登录后可见
    album_url = "https://bcy.net/item/detail/%s" % album_id
    album_response = net.http_request(album_url, method="GET")
    result = {
        "photo_url_list": [],  # 全部图片地址
        "video_id": None,  # 视频id
    }
    if album_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_response.status))
    album_response_content = album_response.data.decode(errors="ignore")
    script_json_html = tool.find_sub_string(album_response_content, "JSON.parse(", ");\n")
    if not script_json_html:
        raise crawler.CrawlerException("页面截取作品信息失败\n%s" % album_response_content)
    script_json = tool.json_decode(tool.json_decode(script_json_html))
    if not script_json:
        raise crawler.CrawlerException("作品信息加载失败\n%s" % album_response_content)
    is_skip = False
    album_type = crawler.get_json_value(script_json, "detail", "post_data", "type", type_check=str)
    # 问答
    # https://bcy.net/item/detail/6115326868729126670
    if album_type == "ganswer":
        is_skip = True
    # 文章
    # https://bcy.net/item/detail/6162547130750754574
    elif album_type == "article":
        is_skip = True
    # 视频
    # https://bcy.net/item/detail/6610952986225017096
    elif album_type == "video":
        is_skip = True
        result["video_id"] = crawler.get_json_value(script_json, "detail", "post_data", "video_info", "vid", type_check=str)
    elif album_type == "note":
        pass
    else:
        raise crawler.CrawlerException("未知的作品类型：%s" % album_type)
    # 获取全部图片
    for photo_info in crawler.get_json_value(script_json, "detail", "post_data", "multi", type_check=list):
        result["photo_url_list"].append(urllib.parse.unquote(crawler.get_json_value(photo_info, "original_path", type_check=str)))
    if not is_skip and len(result["photo_url_list"]) == 0:
        raise crawler.CrawlerException("页面匹配图片地址失败\n%s" % album_response_content)
    return result


# 使用selenium获取指定id的作品
def get_album_page_by_selenium(album_id):
    result = {
        "video_url": None,  # 视频地址
        "video_type": None,  # 视频类型
    }
    caps = DesiredCapabilities.CHROME
    caps['loggingPrefs'] = {'performance': 'ALL'}  # 记录所有日志
    chrome_options = webdriver.chrome.options.Options()
    chrome_options.add_argument('--headless')  # 不打开浏览器
    chrome = webdriver.Chrome(executable_path=crawler.CHROME_WEBDRIVER_PATH, options=chrome_options, desired_capabilities=caps)
    album_url = "https://bcy.net/item/detail/%s" % album_id
    chrome.get(album_url)
    for log_info in chrome.get_log("performance"):
        log_message = tool.json_decode(crawler.get_json_value(log_info, "message", type_check=str))
        if crawler.get_json_value(log_message, "message", "method", default_value="", type_check=str) == "Network.requestWillBeSent":
            video_info_url = crawler.get_json_value(log_message, "message", "params", "request", "url", default_value="", type_check=str)
            if video_info_url.find("//ib.365yg.com/video/urls/") > 0:
                video_info_url = video_info_url.replace("&callback=axiosJsonpCallback1", "")
                break
    else:
        raise crawler.CrawlerException("访问日志匹配视频信息地址失败")
    chrome.quit()
    # 获取视频信息
    video_info_response = net.http_request(video_info_url, method="GET", json_decode=True)
    if video_info_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_info_response.status))
    video_info_list = crawler.get_json_value(video_info_response.json_data, "data", "video_list", type_check=dict)
    max_resolution = 0
    encryption_video_url = None
    for video_info in video_info_list.values():
        resolution = crawler.get_json_value(video_info, "vwidth", type_check=int) * crawler.get_json_value(video_info, "vheight", type_check=int)
        if resolution > max_resolution:
            encryption_video_url = crawler.get_json_value(video_info, "main_url", type_check=str)
            result["video_type"] = crawler.get_json_value(video_info, "vtype", type_check=str)
    if encryption_video_url is None:
        crawler.CrawlerException("视频信息截取加密视频地址失败\n%s" % video_info_response.json_data)
    try:
        result["video_url"] = base64.b64decode(encryption_video_url).decode(errors="ignore")
    except TypeError:
        raise crawler.CrawlerException("歌曲加密地址解密失败\n%s" % encryption_video_url)
    return result


class Bcy(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_DOWNLOAD_VIDEO: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 解析存档文件
        # account_id  last_album_id
        self.account_list = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

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

        log.step("全部下载完毕，耗时%s秒，共计图片%s张，视频%s个" % (self.get_run_time(), self.total_photo_count, self.total_video_count))


class Download(crawler.DownloadThread):
    def __init__(self, account_info, main_thread):
        crawler.DownloadThread.__init__(self, account_info, main_thread)
        self.account_id = self.account_info[0]
        if len(self.account_info) >= 3:
            self.display_name = self.account_info[2]
        else:
            self.display_name = self.account_info[0]
        self.step("开始")

    # 获取所有可下载作品
    def get_crawl_list(self):
        page_since_id = 0
        album_id_list = []
        is_over = False
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析since %s后一页作品" % page_since_id)

            # 获取一页作品
            try:
                album_pagination_response = get_one_page_album(self.account_id, page_since_id)
            except crawler.CrawlerException as e:
                self.error("since %s后一页作品解析失败，原因：%s" % (page_since_id, e.message))
                raise

            self.trace("since %s后一页解析的全部作品：%s" % (page_since_id, album_pagination_response["album_id_list"]))
            self.step("since %s后一页解析获取%s个作品" % (page_since_id, len(album_pagination_response["album_id_list"])))

            # 寻找这一页符合条件的作品
            for album_id in album_pagination_response["album_id_list"]:
                # 检查是否达到存档记录
                if album_id > int(self.account_info[1]):
                    album_id_list.append(album_id)
                    page_since_id = str(album_id)
                else:
                    is_over = True
                    break

            if not is_over:
                if len(album_pagination_response["album_id_list"]) < EACH_PAGE_ALBUM_COUNT:
                    is_over = True

        return album_id_list

    # 解析单个作品
    def crawl_album(self, album_id):
        self.step("开始解析作品%s" % album_id)

        # 获取作品
        try:
            album_response = get_album_page(album_id)
        except crawler.CrawlerException as e:
            self.error("作品%s解析失败，原因：%s" % (album_id, e.message))
            raise

        # 图片
        photo_index = 1
        if self.main_thread.is_download_photo:
            self.trace("作品%s解析的全部图片：%s" % (album_id, album_response["photo_url_list"]))
            self.step("作品%s解析获取%s张图片" % (album_id, len(album_response["photo_url_list"])))

            album_path = os.path.join(self.main_thread.photo_download_path, self.display_name, str(album_id))
            # 设置临时目录
            self.temp_path_list.append(album_path)
            for photo_url in album_response["photo_url_list"]:
                self.main_thread_check()  # 检测主线程运行状态
                # 禁用指定分辨率
                self.step("作品%s开始下载第%s张图片 %s" % (album_id, photo_index, photo_url))

                file_path = os.path.join(album_path, "%03d.%s" % (photo_index, net.get_file_type(photo_url, "jpg")))
                for retry_count in range(0, 10):
                    save_file_return = net.save_net_file(photo_url, file_path)
                    if save_file_return["status"] == 1:
                        self.step("作品%s第%s张图片下载成功" % (album_id, photo_index))
                    else:
                        # 560报错，重新下载
                        if save_file_return["code"] == 404 and retry_count < 4:
                            log.step("图片 %s 访问异常，重试" % photo_url)
                            time.sleep(5)
                            continue
                        self.error("作品%s第%s张图片 %s，下载失败，原因：%s" % (album_id, photo_index, photo_url, crawler.download_failre(save_file_return["code"])))
                    photo_index += 1
                    break

        # 视频
        video_index = 1
        if self.main_thread.is_download_video and album_response["video_id"] is not None:
            self.step("开始解析作品%s的视频" % album_response["video_id"])
            try:
                video_response = get_album_page_by_selenium(album_id)
            except crawler.CrawlerException as e:
                self.error("作品%s的视频解析失败，原因：%s" % (album_id, e.message))
                raise

            self.step("作品%s开始下载视频 %s" % (album_id, video_response["video_url"]))

            file_path = os.path.join(self.main_thread.photo_download_path, self.display_name, "%s.%s" % (album_id, video_response["video_type"]))
            save_file_return = net.save_net_file(video_response["video_url"], file_path)
            if save_file_return["status"] == 1:
                self.step("作品%s视频下载成功" % album_id)
            else:
                self.error("作品%s视频 %s，下载失败，原因：%s" % (album_id, video_response["video_url"], crawler.download_failre(save_file_return["code"])))

        # 作品内图片下全部载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.total_photo_count += photo_index - 1  # 计数累加
        self.total_video_count += video_index - 1  # 计数累加
        self.account_info[1] = str(album_id)  # 设置存档记录

    def run(self):
        try:
            # 获取所有可下载作品
            album_id_list = self.get_crawl_list()
            self.step("需要下载的全部作品解析完毕，共%s个" % len(album_id_list))

            # 从最早的作品开始下载
            while len(album_id_list) > 0:
                self.crawl_album(album_id_list.pop())
                self.main_thread_check()  # 检测主线程运行状态
        except (SystemExit, KeyboardInterrupt) as e:
            if isinstance(e, SystemExit) and e.code == 1:
                self.error("异常退出")
            else:
                self.step("提前退出")
            # 如果临时目录变量不为空，表示某个图集正在下载中，需要把下载了部分的内容给清理掉
            self.clean_temp_path()
        except Exception as e:
            self.error("未知异常")
            self.error(str(e) + "\n" + traceback.format_exc(), False)

        # 保存最后的信息
        with self.thread_lock:
            file.write_file("\t".join(self.account_info), self.main_thread.temp_save_data_path)
            self.main_thread.total_photo_count += self.total_photo_count
            self.main_thread.account_list.pop(self.account_id)
        self.step("下载完毕，总共获得%s张图片和%s个视频" % (self.total_photo_count, self.total_video_count))
        self.notify_main_thread()


if __name__ == "__main__":
    Bcy().main()
