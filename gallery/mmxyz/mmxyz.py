# -*- coding:UTF-8  -*-
"""
http://www.mmxyz.net/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import traceback
import urllib.parse
from pyquery import PyQuery as pq
from common import *


# 获取图集首页
def get_one_page_album(page_count):
    album_pagination_url = "http://www.mmxyz.net/"
    query_data = {
        "action": "ajax_post",
        "pag": page_count,
    }
    album_pagination_response = net.http_request(album_pagination_url, method="GET", fields=query_data)
    result = {
        "album_info_list": [],  # 所有图集信息
        "is_over": False,  # 是否最后一页图集
    }
    if album_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_pagination_response.status))
    if len(album_pagination_response.data) == 0:
        result["is_over"] = True
        return result
    album_pagination_response_content = album_pagination_response.data.decode(errors="ignore")
    album_list_selector = pq(album_pagination_response_content).find(".post-home")
    for album_index in range(0, album_list_selector.length):
        result_album_info = {
            "album_id": None,  # 图集id
            "album_title": "",  # 图集标题
            "album_url": "",  # 图集地址
        }
        album_info_selector = album_list_selector.eq(album_index)
        # 图集id
        album_id = album_info_selector.attr("id").replace("post-", "")
        if not crawler.is_integer(album_id):
            raise crawler.CrawlerException("图集信息截取图集id失败\n%s" % album_info_selector.html())
        result_album_info["album_id"] = int(album_id)
        # 图集地址
        album_url = album_info_selector.find(".inimg").attr("href")
        if not album_url:
            raise crawler.CrawlerException("图集信息截取图集地址失败\n%s" % album_info_selector.html())
        result_album_info["album_url"] = album_url
        # 图集标题
        album_title = album_info_selector.find(".inimg").attr("title")
        if not album_title:
            raise crawler.CrawlerException("图集信息截取图集标题失败\n%s" % album_info_selector.html())
        result_album_info["album_title"] = album_title.strip()
        result["album_info_list"].append(result_album_info)
    return result


# 获取指定图集
def get_album_page(album_url):
    album_response = net.http_request(album_url, method="GET")
    result = {
        "photo_url_list": [],  # 全部图片地址
    }
    if album_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_response.status))
    album_response_content = album_response.data.decode()
    # 获取图集图片地址
    photo_list_selector = pq(album_response_content).find("#gallery-1 a")
    if photo_list_selector.length == 0:
        if pq(album_response_content).find(".post-inner .widgets").empty().parents(".post-inner").find(".post-content a>img").length == 0:
            raise crawler.CrawlerException("页面截取图片地址失败\n%s" % album_response_content)
        else:
            result["photo_url_list"].append(pq(album_response_content).find(".post-inner .post-content a").attr("href"))
    else:
        for photo_index in range(0, photo_list_selector.length):
            photo_url = photo_list_selector.eq(photo_index).attr("href")
            # 非正常源地址
            if photo_url.find("//www.mmxyz.net/") > 0:
                photo_url = photo_list_selector.eq(photo_index).find("img").attr("data-lazy-src").replace("-150x150", "")
            result["photo_url_list"].append(photo_url)
    return result


class MMXYZ(crawler.Crawler):
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
        # 解析存档文件，获取上一次的album id
        album_id = 1
        if os.path.exists(self.save_data_path):
            file_save_info = file.read_file(self.save_data_path)
            if not crawler.is_integer(file_save_info):
                log.error("存档内数据格式不正确")
                tool.process_exit()
            album_id = int(file_save_info)
        temp_path = ""

        try:
            page_count = 1
            album_info_list = []
            unique_list = []
            is_over = False
            while not is_over:
                if not self.is_running():
                    tool.process_exit(0)
                log.step("开始解析第%s页图集" % page_count)

                # 获取一页图集
                try:
                    album_pagination_response = get_one_page_album(page_count)
                except crawler.CrawlerException as e:
                    log.error("第%s页图集解析失败，原因：%s" % (page_count, e.message))
                    raise

                if album_pagination_response["is_over"]:
                    break

                log.trace("第%s页解析的全部图集：%s" % (page_count, album_pagination_response["album_info_list"]))
                log.step("第%s页解析获取%s个图集" % (page_count, len(album_pagination_response["album_info_list"])))

                # 寻找这一页符合条件的图集
                for album_info in album_pagination_response["album_info_list"]:
                    # 检查是否达到存档记录
                    if album_info["album_id"] > album_id:
                        # 新增图片导致的重复判断
                        if album_info["album_id"] in unique_list:
                            continue
                        else:
                            album_info_list.append(album_info)
                            unique_list.append(album_info["album_id"])
                    else:
                        is_over = True
                        break
                page_count += 1

            log.step("需要下载的全部图集解析完毕，共%s个" % len(album_info_list))

            # 从最早的图片开始下载
            while len(album_info_list) > 0:
                if not self.is_running():
                    tool.process_exit(0)
                album_info = album_info_list.pop()
                log.step("开始解析图集%s《%s》 %s" % (album_info["album_id"], album_info["album_title"], album_info["album_url"]))

                try:
                    album_response = get_album_page(album_info["album_url"])
                except crawler.CrawlerException as e:
                    log.error("图集%s《%s》 %s解析失败，原因：%s" % (album_info["album_id"], album_info["album_title"], album_info["album_url"], e.message))
                    raise

                log.trace("图集%s《%s》 %s 解析的全部图片：%s" % (album_info["album_id"], album_response["album_title"], album_info["album_url"], album_response["photo_url_list"]))
                log.step("图集%s《%s》 %s 解析获取%s张图片" % (album_info["album_id"], album_response["album_title"], album_info["album_url"], len(album_response["photo_url_list"])))

                photo_index = 1
                # 过滤标题中不支持的字符
                temp_path = album_path = os.path.join(self.photo_download_path, "%06d %s" % (album_info["album_id"], path.filter_text(album_info["album_title"])))
                thread_list = []
                for photo_url in album_response["photo_url_list"]:
                    if not self.is_running():
                        break
                    photo_url_split = urllib.parse.urlsplit(photo_url)
                    photo_url = photo_url_split[0] + "://" + photo_url_split[1] + urllib.parse.quote(photo_url_split[2])
                    log.step("图集%s《%s》开始下载第%s张图片 %s" % (album_info["album_id"], album_info["album_title"], photo_index, photo_url))

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
                    if save_file_return["status"] != 1:
                        log.error("图集%s《%s》 %s 第%s张图片 %s 下载失败，原因：%s" % (album_id, album_info["album_title"], album_info["album_url"], thread.photo_index, thread.photo_url, crawler.download_failre(save_file_return["code"])))
                if self.is_running():
                    log.step("图集%s《%s》全部图片下载完毕" % (album_id, album_info["album_title"]))
                else:
                    tool.process_exit(0)

                # 图集内图片全部下载完毕
                temp_path = ""  # 临时目录设置清除
                self.total_photo_count += photo_index - 1  # 计数累加
                album_id = album_info["album_id"]  # 设置存档记录
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
        file.write_file(str(album_id), self.save_data_path, file.WRITE_FILE_TYPE_REPLACE)
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
    MMXYZ().main()
