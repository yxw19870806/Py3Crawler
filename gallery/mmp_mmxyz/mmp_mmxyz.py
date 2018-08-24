# -*- coding:UTF-8  -*-
"""
http://mmp.mmxyz.net/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import re
import traceback
import urllib.parse
from pyquery import PyQuery as pq
from common import *


# 获取图集首页
def get_one_page_album(page_count):
    album_pagination_url = "http://mmp.mmxyz.net/index/%s.html" % page_count
    album_pagination_response = net.http_request(album_pagination_url, method="GET")
    result = {
        "album_info_list": [],  # 所有图集信息
        "is_over": False,  # 是否最后一页图集
    }
    if album_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_pagination_response.status))
    album_pagination_response_content = album_pagination_response.data.decode(errors="ignore")
    album_list_selector = pq(album_pagination_response_content).find("#container .post-home .post-thumbnail a")
    for album_index in range(0, album_list_selector.length):
        result_album_info = {
            "album_id": None,  # 图集id
            "album_title": "",  # 图集标题
            "album_url": "",  # 图集地址
        }
        album_info_selector = album_list_selector.eq(album_index)
        # 图集地址
        album_url = album_info_selector.attr("href")
        if not album_url:
            raise crawler.CrawlerException("图集信息截取图集地址失败\n%s" % album_info_selector.html())
        result_album_info["album_url"] = album_url
        # 图集id
        album_id = tool.find_sub_string(album_url, "rosi-", ".html")
        if not crawler.is_integer(album_id):
            raise crawler.CrawlerException("图集地址截取图集id失败\n%s" % album_info_selector.html())
        result_album_info["album_id"] = int(album_id)
        # 图集标题
        album_title = album_info_selector.attr("title")
        if not album_title:
            raise crawler.CrawlerException("图集信息截取图集标题失败\n%s" % album_info_selector.html())
        result_album_info["album_title"] = re.sub(re.compile("(\[\d*P\])"), "", album_title.strip()).strip()
        result["album_info_list"].append(result_album_info)
    max_page_count = pq(album_pagination_response_content).find("#pagenavi ol li").eq(-2).find("a").html()
    if not crawler.is_integer(max_page_count):
        raise crawler.CrawlerException("页面截取总页数失败\n%s" % album_pagination_response_content)
    result["is_over"] = page_count >= int(max_page_count)
    return result


# 获取指定图集
def get_album_page(album_url):
    album_response = net.http_request(album_url, method="GET")
    result = {
        "image_url_list": [],  # 全部图片地址
    }
    if album_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_response.status))
    album_response_content = album_response.data.decode()
    # 获取图集图片地址
    image_list_selector = pq(album_response_content).find(".post-content .photoThum a")
    if image_list_selector.length == 0:
        raise crawler.CrawlerException("页面截取图片地址失败\n%s" % album_response_content)
    for image_index in range(1, image_list_selector.length):
        result["image_url_list"].append(image_list_selector.eq(image_index).attr("href"))
    return result


class MMP_MMXYZ(crawler.Crawler):
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

                image_index = 1
                # 过滤标题中不支持的字符
                album_title = path.filter_text(album_info["album_title"])
                if album_title:
                    album_path = os.path.join(self.image_download_path, "%04d %s" % (album_info["album_id"], album_title))
                else:
                    album_path = os.path.join(self.image_download_path, "%04d" % album_info["album_id"])
                temp_path = album_path
                for image_url in album_response["image_url_list"]:
                    if not self.is_running():
                        tool.process_exit(0)
                    log.step("图集%s《%s》 开始下载第%s张图片 %s" % (album_info["album_id"], album_info["album_title"], image_index, image_url))

                    image_url_split = urllib.parse.urlsplit(image_url)
                    image_url = image_url_split[0] + "://" + image_url_split[1] + urllib.parse.quote(image_url_split[2])
                    file_path = os.path.join(album_path, "%03d.%s" % (image_index, net.get_file_type(image_url)))
                    save_file_return = net.save_net_file(image_url, file_path)
                    if save_file_return["status"] == 1:
                        log.step("图集%s《%s》 第%s张图片下载成功" % (album_info["album_id"], album_info["album_title"], image_index))
                    else:
                        log.error("图集%s《%s》 %s 第%s张图片 %s 下载失败，原因：%s" % (album_info["album_id"], album_info["album_title"], album_info["album_url"], image_index, image_url, crawler.download_failre(save_file_return["code"])))
                    image_index += 1
                # 图集内图片全部下载完毕
                temp_path = ""  # 临时目录设置清除
                self.total_image_count += image_index - 1  # 计数累加
                album_id = str(album_info["album_id"])  # 设置存档记录
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
    MMP_MMXYZ().main()
