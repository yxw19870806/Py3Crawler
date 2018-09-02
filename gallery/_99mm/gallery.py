# -*- coding:UTF-8  -*-
"""
http://www.99mm.me/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import re
import traceback
from pyquery import PyQuery as pq
from common import *

SUB_PATH_LIST = ["meitui", "qingchun", "xinggan"]


# 获取图集首页
def get_index_page():
    index_url = "http://www.99mm.me/"
    index_response = net.http_request(index_url, method="GET")
    result = {
        "max_album_id": None,  # 最新图集id
    }
    if index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(index_response.status))
    index_response_content = index_response.data.decode(errors="ignore")
    last_album_url = pq(index_response_content).find("#piclist li:first dt a").attr("href")
    if not last_album_url:
        raise crawler.CrawlerException("页面截取最新图集地址失败\n%s" % index_response_content)
    album_id_find = re.findall("/(\d*).html", last_album_url)
    if len(album_id_find) != 1:
        raise crawler.CrawlerException("最新图集地址截取图集id失败\n%s" % index_response_content)
    result["max_album_id"] = int(album_id_find[0])
    return result


# 获取指定id的图集
def get_album_page(album_id):
    result = {
        "album_title": "",  # 图集标题
        "album_url": None,  # 图集首页地址
        "photo_url_list": [],  # 全部图片地址
    }
    album_pagination_url = ""
    album_pagination_response = None
    for sub_path in SUB_PATH_LIST:
        album_pagination_url = "http://www.99mm.me/%s/%s.html" % (sub_path, album_id)
        album_pagination_response = net.http_request(album_pagination_url, method="GET", is_auto_redirect=False)
        if album_pagination_response.status == 404:
            continue
        result["album_url"] = album_pagination_url
        break
    if album_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_pagination_response.status))
    album_pagination_response_content = album_pagination_response.data.decode(errors="ignore")
    # 获取图集标题
    album_title = pq(album_pagination_response_content).find(".title span h2").html()
    if not album_title:
        raise crawler.CrawlerException(" %s 页面截取标题失败\n%s" % (album_pagination_url, album_pagination_response_content))
    result["album_title"] = album_title.strip()
    # 获取图集图片地址（逻辑解析来自页面JS文件http://www.99mm.me/css/content.js）
    js_string = tool.find_sub_string(album_pagination_response_content, "var iaStr = '", "'")
    if not js_string:
        raise crawler.CrawlerException(" %s 页面截取页面参数'iaStr'失败\n%s" % (album_pagination_url, album_pagination_response_content))
    var_list = js_string.split(",")
    if len(var_list) < 8:
        raise crawler.CrawlerException(" %s 'iaStr'参数长度不正确\n%s" % (album_pagination_url, album_pagination_response_content))
    if not crawler.is_integer(var_list[2]):
        raise crawler.CrawlerException(" %s 图片数量类型不正确\n%s" % (album_pagination_url, album_pagination_response_content))
    photo_count = int(var_list[2])
    if len(var_list) != photo_count + 8:
        log.error(" %s 'iaStr'参数长度不正确\n%s" % (album_pagination_url, var_list))
    path_list = []
    path_string = tool.find_sub_string(album_pagination_response_content, "var iaOther = '", "'")
    if path_string:
        path_list = path_string.split(",")
        if len(path_list) != photo_count:
            raise crawler.CrawlerException(" %s iaOther参数长度不正确\n%s" % (album_pagination_url, album_pagination_response_content))
    for photo_index in range(1, int(photo_count) + 1):
        if photo_index >= len(var_list) - 7:
            log.error(" %s 第%s张图片已被跳过" % (album_pagination_url, photo_index))
            continue
        host_name = "file" if len(path_list) == photo_count and path_list[photo_index - 1] == "1" else "fj"
        result["photo_url_list"].append("http://%s.kanmengmei.com/%s/%s/%s-%s.jpg" % (host_name, var_list[4], album_id, photo_index, var_list[photo_index + 7]))
    return result


class Gallery(crawler.Crawler):
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
            # 获取图集首页
            try:
                index_response = get_index_page()
            except crawler.CrawlerException as e:
                log.error("图集首页解析失败，原因：%s" % e.message)
                raise

            log.step("最新图集id：%s" % index_response["max_album_id"])

            while album_id <= index_response["max_album_id"]:
                if not self.is_running():
                    tool.process_exit(0)
                log.step("开始解析图集%s" % album_id)

                # 获取图集
                try:
                    album_response = get_album_page(album_id)
                except crawler.CrawlerException as e:
                    log.error("图集%s解析失败，原因：%s" % (album_id, e.message))
                    raise

                log.trace("图集%s《%s》 %s 解析的全部图片：%s" % (album_id, album_response["album_title"], album_response["album_url"], album_response["photo_url_list"]))
                log.step("图集%s《%s》 %s 解析获取%s张图片" % (album_id, album_response["album_title"], album_response["album_url"], len(album_response["photo_url_list"])))

                photo_index = 1
                # 过滤标题中不支持的字符
                album_title = path.filter_text(album_response["album_title"])
                if album_title:
                    album_path = os.path.join(self.photo_download_path, "%04d %s" % (album_id, album_title))
                else:
                    album_path = os.path.join(self.photo_download_path, "%04d" % album_id)
                temp_path = album_path
                for photo_url in album_response["photo_url_list"]:
                    if not self.is_running():
                        tool.process_exit(0)
                    log.step("图集%s《%s》开始下载第%s张图片 %s" % (album_id, album_response["album_title"], photo_index, photo_url))

                    file_path = os.path.join(album_path, "%03d.%s" % (photo_index, net.get_file_type(photo_url)))
                    save_file_return = net.save_net_file(photo_url, file_path, header_list={"Referer": "http://www.99mm.me/"})
                    if save_file_return["status"] == 1:
                        log.step("图集%s《%s》第%s张图片下载成功" % (album_id, album_response["album_title"], photo_index))
                    else:
                        log.error("图集%s《%s》 %s 第%s张图片 %s 下载失败，原因：%s" % (album_id, album_response["album_title"], album_response["album_url"], photo_index, photo_url, crawler.download_failre(save_file_return["code"])))
                    photo_index += 1
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


if __name__ == "__main__":
    Gallery().main()
