# -*- coding:UTF-8  -*-
"""
http://www.5442.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import json
import os
import re
import traceback
from pyquery import PyQuery as pq
from common import *


# 获取指定一页图集
def get_one_page_album(page_count):
    album_pagination_url = "http://www.5442.com/meinv/list_1_%s.html" % page_count
    album_pagination_response = net.http_request(album_pagination_url, method="GET")
    result = {
        "album_info_list": [],  # 全部图集地址
        "is_over": None,  # 是否最后页图集
    }
    if album_pagination_response.status == 514:
        return get_one_page_album(page_count)
    elif album_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_pagination_response.status))
    album_pagination_response_content = album_pagination_response.data.decode("GBK", errors="ignore")
    album_list_selector = pq(album_pagination_response_content).find(".imgList ul li")
    if album_list_selector.length == 0:
        raise crawler.CrawlerException("页面截取图集列表失败\n%s" % album_pagination_response_content)
    # 获取所有图集地址
    for album_index in range(0, album_list_selector.length):
        result_album_info = {
            "album_id": None,  # 图集id
            "album_url": None,  # 图集地址
        }
        album_selector = album_list_selector.eq(album_index)
        # 获取图集地址
        album_url = album_selector.find("a:first").attr("href")
        if not album_url:
            raise crawler.CrawlerException("图集信息截取图集地址失败\n%s" % album_selector.html())
        result_album_info["album_url"] = album_url
        # 获取图集id
        album_id = album_url.split("/")[-1].split(".")[0]
        if not crawler.is_integer(album_id):
            raise crawler.CrawlerException("图集地址截取图集id失败\n%s" % album_url)
        result_album_info["album_id"] = int(album_id)
        result["album_info_list"].append(result_album_info)
    # 判断是不是最后一页
    result["is_over"] = pq(album_pagination_response_content).find(".page ul li:last a").length == 0
    return result


# 获取指定图集
def get_album_page(album_url):
    page_count = max_page_count = 1
    result = {
        "album_title": "",  # 图集标题
        "is_delete": False,  # 是否已删除
        "photo_url_list": [],  # 全部图片地址
    }
    photo_url_list = []
    while page_count <= max_page_count:
        if page_count == 1:
            pagination_album_url = album_url
        else:
            pagination_album_url = album_url.replace(".html", "_%s.html" % page_count)
        album_response = net.http_request(pagination_album_url, method="GET")
        if album_response.status == 514:
            continue
        elif page_count == 1 and album_response.status == 404:
            result["is_delete"] = True
            return result
        elif album_response.status != net.HTTP_RETURN_CODE_SUCCEED:
            raise crawler.CrawlerException("第%s页" % page_count + crawler.request_failre(album_response.status))
        album_response_content = album_response.data.decode("GBK", errors="ignore")
        if page_count == 1:
            # 获取图集标题
            album_title = pq(album_response_content).find(".arcTitle h1 a").html()
            if not album_title:
                raise crawler.CrawlerException("页面截取图集标题失败\n%s" % album_response_content)
            result["album_title"] = album_title.strip()
            # 获取总页数
            max_page_count_html = pq(album_response_content).find("#aplist ul li:first a").html()
            if max_page_count_html:
                max_page_count_find = re.findall("共(\d*)页: ", max_page_count_html)
                if len(max_page_count_find) != 1:
                    raise crawler.CrawlerException("图集总页数信息截取图集总页数失败\n%s" % album_response_content)
                max_page_count = int(max_page_count_find[0])
            else:
                if pq(album_response_content).find("#aplist ul").length == 0:
                    raise crawler.CrawlerException("页面截取图集总页数信息失败\n%s" % album_response_content)
        # 获取图片地址
        photo_list_selector = pq(album_response_content).find(".arcBody #contents a img")
        if photo_list_selector.length == 0:
            if pq(album_response_content).find(".arcBody #contents").length != 1:
                raise crawler.CrawlerException("第%s页页面截取图片信息失败\n%s" % (page_count, album_response_content))
        for photo_index in range(0, photo_list_selector.length):
            # http://pic.ytqmx.com:82/2014/0621/07/02.jpg!960.jpg -> http://pic.ytqmx.com:82/2014/0621/07/02.jpg
            photo_url_list.append(photo_list_selector.eq(photo_index).attr("src").split("!")[0].replace(".com :", ".com:"))
        page_count += 1
    # 根据自增命名、尝试补上那些确实的图片
    # http://www.5442.com/meinv/20161026/36948.html
    photo_index_list = {}  # 数字命名的图片
    extra_photo_list = []  # 非数字命名的图片
    is_format = True  # 是不是使用0填充命名
    temp_list = photo_url_list[0].split("/")
    file_type = "jpg"
    for photo_url in photo_url_list:
        photo_name, file_type = photo_url.split("/")[-1].split(".")
        # 存在非自增数字命名的图片
        if not crawler.is_integer(photo_name) or int(photo_name) > 100 + len(photo_url_list):
            extra_photo_list.append(photo_url)
        else:
            # 自增的图片
            photo_index_list[int(photo_name)] = 1
            if is_format and len(photo_name) == 1:
                is_format = False
    if len(photo_index_list) > 0 and (max(photo_index_list) != len(photo_url_list) or len(photo_index_list) != len(photo_url_list)):
        result["is_reset"] = True
        for photo_index in range(1, max(photo_index_list) + 2):  # 多一张
            if is_format:
                temp_list[-1] = "%02d.%s" % (photo_index, file_type)
            else:
                temp_list[-1] = "%s.%s" % (photo_index, file_type)
            result["photo_url_list"].append("/".join(temp_list))
        result["photo_url_list"] += extra_photo_list
    else:
        result["photo_url_list"] = photo_url_list
    return result


class Album(crawler.Crawler):
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
            album_id_to_url_list = {}
            # 从缓存文件中读取
            cache_file_path = os.path.join(self.cache_data_path, "cache.json")
            cache_album_id_to_url_list = tool.json_decode(file.read_file(cache_file_path))
            if cache_album_id_to_url_list is None:
                page_count = 1
                is_over = False
                while not is_over:
                    if not self.is_running():
                        tool.process_exit(0)
                    log.step("开始解析第%s页图集" % page_count)

                    # 获取第一页图集
                    try:
                        album_pagination_response = get_one_page_album(page_count)
                    except crawler.CrawlerException as e:
                        log.error("第%s页图集解析失败，原因：%s" % (page_count, e.message))
                        raise

                    log.trace("第%s页解析的全部图集：%s" % (page_count, album_pagination_response["album_info_list"]))
                    log.step("第%s页解析获取%s个图集" % (page_count, len(album_pagination_response["album_info_list"])))

                    # 寻找这一页符合条件的图集
                    for album_info in album_pagination_response["album_info_list"]:
                        album_id_to_url_list[album_info["album_id"]] = album_info["album_url"]

                    if not is_over:
                        is_over = album_pagination_response["is_over"]
                        page_count += 1

                # 保存到缓存文件中
                file.write_file(json.dumps(album_id_to_url_list), cache_file_path, file.WRITE_FILE_TYPE_REPLACE)
            else:
                # 写入文件后key变成string类型了
                for temp in cache_album_id_to_url_list:
                    album_id_to_url_list[int(temp)] = cache_album_id_to_url_list[temp]

            while album_id <= max(album_id_to_url_list):
                if not self.is_running():
                    tool.process_exit(0)
                # 如果图集id在列表页存在的
                if album_id not in album_id_to_url_list:
                    album_id += 1
                    continue

                album_url = album_id_to_url_list[album_id]
                log.step("开始解析图集 %s" % album_url)

                try:
                    album_response = get_album_page(album_url)
                except crawler.CrawlerException as e:
                    log.error("图集 %s 解析失败，原因：%s" % (album_url, e.message))
                    raise

                if album_response["is_delete"]:
                    log.error("图集 %s 不存在，跳过" % album_url)
                    album_id += 1
                    continue

                log.trace("图集%s《%s》 %s 解析的全部图片：%s" % (album_id, album_response["album_title"], album_url, album_response["photo_url_list"]))
                log.step("图集%s《%s》 %s 解析获取%s张图片" % (album_id, album_response["album_title"], album_url, len(album_response["photo_url_list"])))

                photo_index = 1
                # 过滤标题中不支持的字符
                album_path = temp_path = os.path.join(self.photo_download_path, "%05d %s" % (album_id, path.filter_text(album_response["album_title"])))
                thread_list = []
                for photo_url in album_response["photo_url_list"]:
                    if not self.is_running():
                        break
                    log.step("图集%s《%s》开始下载第%s张图片 %s" % (album_id, album_response["album_title"], photo_index, photo_url))

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
                        log.error("图集%s《%s》 %s 第%s张图片 %s 下载失败，原因：%s" % (album_id, album_response["album_title"], album_url, thread.photo_index, thread.photo_url, crawler.download_failre(save_file_return["code"])))
                if self.is_running():
                    log.step("图集%s《%s》全部图片下载完毕" % (album_id, album_response["album_title"]))
                else:
                    tool.process_exit(0)

                # 图集内图片全部下载完毕
                temp_path = ""  # 临时目录设置清除
                self.total_photo_count += photo_index - 1  # 计数累加
                album_id += 1  # 设置存档记录
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
        if self.result["status"] == 0:
            if self.result["code"] == 404:
                temp_list = self.photo_url.split("/")
                photo_name, file_type = temp_list[-1].split(".")
                if crawler.is_integer(photo_name) and int(photo_name) < 10 and len(photo_name) == 2:
                    temp_list[-1] = "%s.%s" % (int(photo_name), file_type)
                    photo_url = "/".join(temp_list)
                    self.result = net.save_net_file(photo_url, self.file_path)
            elif self.result["code"] == 514:
                return self.run()
        self.notify_main_thread()

    def get_result(self):
        return self.result


if __name__ == "__main__":
    Album().main()
