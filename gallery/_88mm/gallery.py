# -*- coding:UTF-8  -*-
"""
http://www.88mmw.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import re
import traceback
from pyquery import PyQuery as pq
from common import *

SUB_PATH_LIST = ["Dgxz", "GaoQing", "JiePai", "Pansi", "RiBen", "Rosi", "Sibao", "Sityle", "Tpimage"]


# 获取图集首页
def get_index_page():
    index_url = "http://www.88mmw.com/"
    index_response = net.http_request(index_url, method="GET", is_auto_redirect=False)
    result = {
        "max_album_id": None,  # 最新图集id
    }
    if index_response.status == 302:
        return get_index_page()
    elif index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(index_response.status))
    index_response_content = index_response.data.decode("GBK", errors="ignore")
    last_album_url = pq(index_response_content).find(".tboxa:first ul li:first a").attr("href")
    if not last_album_url:
        raise last_album_url.CrawlerException("页面截取最新图集地址失败\n%s" % index_response_content)
    album_id_find = re.findall("/(\d*)/", last_album_url)
    if len(album_id_find) != 1:
        raise crawler.CrawlerException("最新图集地址截取图集id失败\n%s" % index_response_content)
    result["max_album_id"] = int(album_id_find[0])
    return result


# 获取指定一页的图集
def get_album_page(album_id):
    page_count = max_page_count = 1
    sub_path = ""
    album_pagination_response = None
    result = {
        "album_title": "",  # 图集标题
        "album_url": None,  # 图集首页地址
        "image_url_list": [],  # 全部图片地址
        "is_delete": False,  # 是否已删除
    }
    while page_count <= max_page_count:
        if page_count == 1:
            for sub_path in SUB_PATH_LIST:
                album_pagination_url = "http://www.88mmw.com/%s/%s/" % (sub_path, album_id)
                album_pagination_response = net.http_request(album_pagination_url, method="GET", is_auto_redirect=False)
                if album_pagination_response.status == 404:
                    continue
                result["album_url"] = album_pagination_url
                break
        else:
            album_pagination_url = "http://www.88mmw.com/%s/%s/index_%s.html" % (sub_path, album_id, page_count)
            album_pagination_response = net.http_request(album_pagination_url, method="GET", is_auto_redirect=False)
        if album_pagination_response.status == 302:
            continue
        elif page_count == 1 and album_pagination_response.status == 404:
            result["is_delete"] = True
            return result
        elif album_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
            raise crawler.CrawlerException(crawler.request_failre(album_pagination_response.status))
        album_pagination_response_content = album_pagination_response.data.decode("GBK", errors="ignore")
        if page_count == 1:
            # 获取图集标题
            album_title = pq(album_pagination_response_content).find(".currentpath span a").eq(1).html()
            if not album_title:
                raise crawler.CrawlerException("页面截取标题失败\n%s" % album_pagination_response_content)
            result["album_title"] = album_title[:album_title.rfind("全部图片")].strip()
            # 获取图集总页数
            pagination_selector = pq(album_pagination_response_content).find("div.page span")
            if pagination_selector.length > 0:
                max_page_count = pagination_selector.eq(0).find("strong").html()
                if not crawler.is_integer(max_page_count):
                    raise crawler.CrawlerException("页面截取总页数失败\n%s" % album_pagination_response_content)
                max_page_count = int(max_page_count)
        # 获取图集图片地址
        image_list_selector = pq(album_pagination_response_content).find("div.zzz li img")
        if image_list_selector.length == 0:
            raise crawler.CrawlerException("第%s页页面匹配图片地址失败\n%s" % (page_count, album_pagination_response_content))
        for image_index in range(0, image_list_selector.length):
            result["image_url_list"].append("http://www.88mmw.com" + image_list_selector.eq(image_index).attr("src").replace("-lp", ""))
        page_count += 1
    return result


class Gallery(crawler.Crawler):
    def __init__(self):
        # 设置APP目录
        tool.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_IMAGE: True,
            crawler.SYS_NOT_CHECK_SAVE_DATA: True,
        }
        crawler.Crawler.__init__(self, sys_config)

    def main(self):
        # 解析存档文件，获取上一次的album id
        album_id = 1
        if os.path.exists(self.save_data_path):
            file_save_info = tool.read_file(self.save_data_path)
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

                if album_response["is_delete"]:
                    log.step("图集%s不存在，跳过" % album_id)
                    album_id += 1
                    continue

                log.trace("图集%s《%s》 %s 解析的全部图片：%s" % (album_id, album_response["album_title"], album_response["album_url"], album_response["image_url_list"]))
                log.step("图集%s《%s》 %s 解析获取%s张图片" % (album_id, album_response["album_title"], album_response["album_url"], len(album_response["image_url_list"])))

                image_index = 1
                # 过滤标题中不支持的字符
                album_title = path.filter_text(album_response["album_title"])
                if album_title:
                    album_path = os.path.join(self.image_download_path, "%04d %s" % (album_id, album_title))
                else:
                    album_path = os.path.join(self.image_download_path, "%04d" % album_id)
                temp_path = album_path
                for image_url in album_response["image_url_list"]:
                    if not self.is_running():
                        tool.process_exit(0)
                    log.step("图集%s《%s》开始下载第%s张图片 %s" % (album_id, album_response["album_title"], image_index, image_url))

                    file_path = os.path.join(album_path, "%03d.%s" % (image_index, net.get_file_type(image_url)))
                    save_file_return = net.save_net_file(image_url, file_path)
                    if save_file_return["status"] == 1:
                        log.step("图集%s《%s》第%s张图片下载成功" % (album_id, album_response["album_title"], image_index))
                    else:
                        log.error("图集%s《%s》 %s 第%s张图片 %s 下载失败，原因：%s" % (album_id, album_response["album_title"], album_response["album_url"], image_index, image_url, crawler.download_failre(save_file_return["code"])))
                    image_index += 1
                # 图集内图片全部下载完毕
                temp_path = ""  # 临时目录设置清除
                self.total_image_count += image_index - 1  # 计数累加
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
        tool.write_file(str(album_id), self.save_data_path, tool.WRITE_FILE_TYPE_REPLACE)
        log.step("全部下载完毕，耗时%s秒，共计图片%s张" % (self.get_run_time(), self.total_image_count))


if __name__ == "__main__":
    Gallery().main()
