# -*- coding:UTF-8  -*-
"""
https://www.kelagirls.com/bizhi_findForIndexMore
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import traceback
import urllib.parse
from pyquery import PyQuery as pq
from common import *


# 获取指定一页的壁纸
def get_one_page_wallpaper(page_count):
    wallpaper_pagination_url = "https://www.kelagirls.com/wallpapers-page-%s.html" % page_count
    wallpaper_pagination_response = net.http_request(wallpaper_pagination_url, method="GET")
    result = {
        "photo_info_list": [],  # 全部图片地址
        "is_over": False,  # 是否最后一页壁纸
    }
    if wallpaper_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(wallpaper_pagination_response.status))
    wallpaper_pagination_response_content = wallpaper_pagination_response.data.decode(errors="ignore")
    photo_list_selector = pq(wallpaper_pagination_response_content).find(".bizhinmore .bizhi")
    if photo_list_selector.length == 0:
        raise crawler.CrawlerException("页面匹配图片列失败\n%s" % wallpaper_pagination_response_content)
    for photo_index in range(0, photo_list_selector.length):
        photo_selector = photo_list_selector.eq(photo_index)
        result_photo_info = {
            "photo_id": None,  # 图片id
            "photo_url": None,  # 图片地址
            "model_name": "",  # 模特名字
        }
        # 获取图片id
        photo_id = photo_selector.find(".bizhibigwrap").attr("id")
        if not photo_id:
            raise crawler.CrawlerException("图片列表匹配图片id失败\n%s" % photo_selector.html())
        if not (photo_id[0:3] == "big" and crawler.is_integer(photo_id[3:])):
            raise crawler.CrawlerException("图片列表匹配的图片id格式不正确\n%s" % photo_selector.html())
        result_photo_info["photo_id"] = int(photo_id[3:])
        # 获取图片地址
        result_photo_info["photo_url"] = "http://kelagirls.com/" + photo_selector.find(".bizhibig img").eq(1).attr("src")
        # 获取模特名字
        model_name = photo_selector.find(".bzwdown span:first").text()
        if not model_name:
            raise crawler.CrawlerException("图片列表匹配模特名字失败\n%s" % photo_selector.html())
        result_photo_info["model_name"] = model_name
        result["photo_info_list"].append(result_photo_info)
    # 判断是不是最后一页
    max_page_count = tool.find_sub_string(wallpaper_pagination_response_content, "pageCount: ", ",")
    if not crawler.is_integer(max_page_count):
        raise crawler.CrawlerException("页面截取总页数失败\n%s" % wallpaper_pagination_response_content)
    result["is_over"] = page_count >= int(max_page_count)
    return result


class Wallpaper(crawler.Crawler):
    def __init__(self):
        # 设置APP目录
        tool.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_NOT_CHECK_SAVE_DATA: True,
        }
        crawler.Crawler.__init__(self, sys_config)

    def main(self):
        last_photo_id = 0
        if os.path.exists(self.save_data_path):
            file_save_info = tool.read_file(self.save_data_path)
            if not crawler.is_integer(file_save_info):
                log.error("存档内数据格式不正确")
                tool.process_exit()
            last_photo_id = int(file_save_info)

        try:
            page_count = 1
            photo_info_list = []
            is_over = False
            # 获取全部还未下载过需要解析的壁纸
            while not is_over:
                if not self.is_running():
                    tool.process_exit(0)
                log.step("开始解析第%s页壁纸" % page_count)

                # 获取一页壁纸
                try:
                    wallpaper_pagination_response = get_one_page_wallpaper(page_count)
                except crawler.CrawlerException as e:
                    log.error("第%s页壁纸解析失败，原因：%s" % (page_count, e.message))
                    break
                except SystemExit:
                    log.step("提前退出")
                    photo_info_list = []
                    break

                log.trace("第%s页壁纸解析的全部图片：%s" % (page_count, wallpaper_pagination_response["photo_info_list"]))
                log.step("第%s页壁纸解析获取%s张图片" % (page_count, len(wallpaper_pagination_response["photo_info_list"])))

                for photo_info in wallpaper_pagination_response["photo_info_list"]:
                    # 检查是否达到存档记录
                    if photo_info["photo_id"] > last_photo_id:
                        photo_info_list.append(photo_info)
                    else:
                        is_over = True
                        break

                if not is_over:
                    if wallpaper_pagination_response["is_over"]:
                        is_over = True
                    else:
                        page_count += 1

            log.step("需要下载的全部图片解析完毕，共%s个" % len(photo_info_list))

            # 从最早的图片开始下载
            while len(photo_info_list) > 0:
                if not self.is_running():
                    tool.process_exit(0)
                photo_info = photo_info_list.pop()

                log.step("开始下载第%s张图片 %s" % (photo_info["photo_id"], photo_info["photo_url"]))

                file_path = os.path.join(self.photo_download_path, "%03d %s.%s" % (photo_info["photo_id"], path.filter_text(photo_info["model_name"]), net.get_file_type(photo_info["photo_url"])))
                photo_url_split = urllib.parse.urlsplit(photo_info["photo_url"])
                photo_url = photo_url_split[0] + "://" + photo_url_split[1] + urllib.parse.quote(photo_url_split[2])
                save_file_return = net.save_net_file(photo_url, file_path)
                if save_file_return["status"] == 1:
                    log.step("第%s张图片下载成功" % photo_info["photo_id"])
                else:
                    log.error("第%s张图片 %s 下载失败，原因：%s" % (photo_info["photo_id"], photo_info["photo_url"], crawler.download_failre(save_file_return["code"])))
                    continue
                # 图片下载完毕
                self.total_photo_count += 1  # 计数累加
                last_photo_id = str(photo_info["photo_id"])  # 设置存档记录
        except SystemExit as se:
            if se.code == 0:
                log.step("提前退出")
            else:
                log.error("异常退出")
        except Exception as e:
            log.error("未知异常")
            log.error(str(e) + "\n" + traceback.format_exc())

        # 重新保存存档文件
        tool.write_file(str(last_photo_id), self.save_data_path, tool.WRITE_FILE_TYPE_REPLACE)
        log.step("全部下载完毕，耗时%s秒，共计图片%s张" % (self.get_run_time(), self.total_photo_count))


if __name__ == "__main__":
    Wallpaper().main()
