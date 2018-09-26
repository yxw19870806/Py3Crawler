# -*- coding:UTF-8  -*-
"""
http://www6.imgxr.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import traceback
from pyquery import PyQuery as pq
from common import *


# 获取指定一页图集
def get_one_page_album(page_count):
    album_pagination_url = "http://www6.imgxr.com/page-%s.html" % page_count
    album_pagination_response = net.http_request(album_pagination_url, method="GET")
    result = {
        "album_url_list": [],  # 全部图集地址
        "max_page_count": None,  # 图集总页数
    }
    if album_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_pagination_response.status))
    album_pagination_response_content = album_pagination_response.data.decode(errors="ignore")
    album_list_selector = pq(album_pagination_response_content).find("#main .loop")
    if album_list_selector.length == 0:
        raise crawler.CrawlerException("页面截取图集列表失败\n%s" % album_pagination_response_content)
    # 获取所有图集地址
    for album_index in range(0, album_list_selector.length):
        album_selector = album_list_selector.eq(album_index)
        # 获取图集地址
        album_url = album_selector.find("a").attr("href")
        if not album_url:
            raise crawler.CrawlerException("图集信息截取图集地址失败\n%s" % album_pagination_response_content)
        result["album_url_list"].append(album_url)
    # 获取总图集页数
    page_info = pq(album_pagination_response_content).find("#page span.info").html()
    if not page_info:
        raise crawler.CrawlerException("页面截取页数信息失败\n%s" % album_pagination_response_content)
    current_page_count, max_page_count = page_info.split("/")
    if crawler.is_integer(current_page_count) and int(current_page_count) == page_count and crawler.is_integer(max_page_count):
        result["max_page_count"] = int(max_page_count)
    else:
        raise crawler.CrawlerException("页数信息截取当前页数和总页数失败\n%s" % album_pagination_response_content)
    return result


# 获取指定图集
def get_album_page(album_url):
    album_response = net.http_request(album_url, method="GET")
    result = {
        "album_id": None,  # 图集id
        "album_title": "",  # 图集标题
        "is_video": False,  # 是否是视频
        "photo_url_list": [],  # 全部图片地址
    }
    if album_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_response.status))
    album_response_content = album_response.data.decode(errors="ignore")
    # 获取图集id
    album_id = pq(album_response_content).find("#title .date a").attr("data-pid")
    if not crawler.is_integer(album_id):
        raise crawler.CrawlerException("页面截取图集id失败\n%s" % album_response_content)
    result["album_id"] = int(album_id)
    # 获取图集标题
    album_title = pq(album_response_content).find("#title h1:first").html()
    if not album_title:
        raise crawler.CrawlerException("页面截取图集标题失败\n%s" % album_response_content)
    result["album_title"] = album_title.strip()
    # 获取图片地址
    photo_list_selector = pq(album_response_content).find(".post span.photoThum a")
    if photo_list_selector.length == 0:
        if pq(album_response_content).find(".post #jwplayer_1").length == 1:
            result["is_video"] = True
        else:
            raise crawler.CrawlerException("页面截取图片信息失败\n%s" % album_response_content)
    for photo_index in range(0, photo_list_selector.length):
        photo_url = photo_list_selector.eq(photo_index).attr("href")
        if not photo_url:
            raise crawler.CrawlerException("图片信息截取图片地址失败\n%s" % album_response_content)
        result["photo_url_list"].append(photo_url)
    return result


class ImgXr(crawler.Crawler):
    def __init__(self):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_NOT_CHECK_SAVE_DATA: True,
        }
        crawler.Crawler.__init__(self, sys_config)

    def main(self):
        # 解析存档文件
        # last_album_url  last_album_page_count
        save_info = ["", "0"]
        if os.path.exists(self.save_data_path):
            file_save_info = file.read_file(self.save_data_path).split("\t")
            if len(file_save_info) >= 2 and crawler.is_integer(file_save_info[1]):
                save_info = file_save_info
            else:
                log.error("存档内数据格式不正确")
                tool.process_exit()
        temp_path = ""

        try:
            page_count = int(save_info[1])
            if page_count == 0:
                log.step("开始解析图集首页")
                # 获取第一页图集
                try:
                    album_pagination_response = get_one_page_album(1)
                except crawler.CrawlerException as e:
                    log.error("图集首页解析失败，原因：%s" % e.message)
                    raise
                log.step("图集总页数：%s" % album_pagination_response["max_page_count"])
                page_count = album_pagination_response["max_page_count"]

            is_find = True if save_info[0] == "" else False
            while page_count > 0:
                if not self.is_running():
                    tool.process_exit(0)
                log.step("开始解析第%s页图集" % page_count)

                try:
                    album_pagination_response = get_one_page_album(page_count)
                except crawler.CrawlerException as e:
                    log.error("第%s页图集解析失败，原因：%s" % (page_count, e.message))
                    raise

                log.trace("第%s页解析的全部图集：%s" % (page_count, album_pagination_response["album_url_list"]))
                log.step("第%s页解析获取%s个图集" % (page_count, len(album_pagination_response["album_url_list"])))

                # 从最早的图集开始下载
                while len(album_pagination_response["album_url_list"]) > 0:
                    if not self.is_running():
                        tool.process_exit(0)
                    album_url = album_pagination_response["album_url_list"].pop()

                    # 如果没有找到之前的记录，首先跳过不匹配的图集
                    if not is_find:
                        if album_url.lower() == save_info[0].lower():
                            is_find = True
                        continue

                    log.step("开始解析图集 %s" % album_url)

                    try:
                        album_response = get_album_page(album_url)
                    except crawler.CrawlerException as e:
                        log.error("图集 %s 解析失败，原因：%s" % (album_url, e.message))
                        raise

                    if album_response["is_video"]:
                        log.error("图集 %s 是视频，跳过" % album_url)
                        continue

                    log.trace("图集《%s》 %s 解析的全部图片：%s" % (album_response["album_title"], album_url, album_response["photo_url_list"]))
                    log.step("图集《%s》 %s 解析获取%s张图片" % (album_response["album_title"], album_url, len(album_response["photo_url_list"])))

                    temp_path = album_path = os.path.join(self.photo_download_path, "%05d %s" % (album_response["album_id"], path.filter_text(album_response["album_title"])))
                    photo_index = 1
                    thread_list = []
                    for photo_url in album_response["photo_url_list"]:
                        if not self.is_running():
                            break
                        log.step("图集《%s》 %s 开始下载第%s张图片 %s" % (album_response["album_title"], album_url, photo_index, photo_url))

                        # 开始下载
                        file_path = os.path.join(album_path, "%03d.%s" % (photo_index, net.get_file_type(photo_url)))
                        thread = Download(self, file_path, photo_url, photo_index)
                        thread.start()
                        thread_list.append(thread)
                        photo_index += 1

                    # 等待所有线程下载完毕
                    for thread in thread_list:
                        thread.join()
                        save_file_return = thread.get_result()
                        if self.is_running() and save_file_return["status"] != 1:
                            log.error("图集《%s》 %s 第%s张图片 %s 下载失败，原因：%s" % (album_response["album_title"], album_url, thread.photo_index, thread.photo_url, crawler.download_failre(save_file_return["code"])))
                    if self.is_running():
                        log.step("图集《%s》 %s 全部图片下载完毕" % (album_response["album_title"], album_url))
                    else:
                        tool.process_exit(0)

                    # 图集内图片全部下载完毕
                    temp_path = ""  # 临时目录设置清除
                    self.total_photo_count += photo_index - 1  # 计数累加
                    save_info[0] = album_url  # 设置存档记录
                    save_info[1] = str(page_count)  # 设置存档记录
                # 如果已经找到了存档记录，继续往前下载
                if is_find:
                    page_count -= 1
                else:
                    # 一直到最后一页都没有找到
                    if page_count >= album_pagination_response["max_page_count"]:
                        log.error("存档记录未找到，全部重新下载")
                        is_find = True
                    # 如果这一页都没有找到存档记录，继续往后查找
                    else:
                        page_count += 1
        except SystemExit as se:
            if se.code == 0:
                log.step("提前退出")
            else:
                log.error("异常退出")
            # 如果临时目录变量不为空，表示某个图集正在下载中，需要把下载了部分的内容给清理掉
            if temp_path:
                path.delete_dir_or_file(temp_path)
        except Exception as e:
            log.error("未知异常")
            log.error(str(e) + "\n" + traceback.format_exc())

        # 重新保存存档文件
        file.write_file("\t".join(save_info), self.save_data_path, file.WRITE_FILE_TYPE_REPLACE)
        log.step("全部下载完毕，耗时%s秒，共计图片%s张" % (self.get_run_time(), self.total_photo_count))


class Download(crawler.DownloadThread):
    def __init__(self, main_thread, file_path, photo_url, photo_index):
        crawler.DownloadThread.__init__(self, [], main_thread)
        self.file_path = file_path
        self.photo_url = photo_url
        self.photo_index = photo_index
        self.result = None

    def run(self):
        self.result = net.save_net_file(self.photo_url, self.file_path)
        self.notify_main_thread()

    def get_result(self):
        return self.result


if __name__ == "__main__":
    ImgXr().main()
