# -*- coding:UTF-8  -*-
"""
一直播图片&视频爬虫
http://www.yizhibo.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import re
import threading
import time
import traceback
from common import *


# 获取全部图片地址列表
def get_photo_index_page(account_id):
    # https://www.yizhibo.com/member/personel/user_photos?memberid=6066534
    photo_index_url = "https://www.yizhibo.com/member/personel/user_photos"
    query_data = {"memberid": account_id}
    photo_index_response = net.http_request(photo_index_url, method="GET", fields=query_data)
    result = {
        "photo_url_list": [],  # 全部图片地址
    }
    if photo_index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(photo_index_response.status))
    photo_index_response_content = photo_index_response.data.decode(errors="ignore")
    if photo_index_response_content == '<script>window.location.href="/404.html";</script>':
        raise crawler.CrawlerException("账号不存在")
    # 获取全部图片地址
    if photo_index_response_content.find("还没有照片哦") == -1:
        result["photo_url_list"] = re.findall('<img src="([^"]*)@[^"]*" alt="" class="index_img_main">', photo_index_response_content)
        if len(result["photo_url_list"]) == 0:
            raise crawler.CrawlerException("页面匹配图片地址失败\n%s" % photo_index_response_content)
    return result


#  获取图片的header
def get_photo_header(photo_url):
    photo_head_response = net.http_request(photo_url, method="HEAD")
    result = {
        "photo_time": None,  # 图片上传时间
    }
    if photo_head_response.status == 404:
        return result
    elif photo_head_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(photo_head_response.status))
    last_modified = photo_head_response.headers.get("Last-Modified")
    if last_modified is None:
        raise crawler.CrawlerException("图片header'Last-Modified'字段不存在\n%s" % photo_head_response.headers)
    try:
        last_modified_time = time.strptime(last_modified, "%a, %d %b %Y %H:%M:%S %Z")
    except ValueError:
        raise crawler.CrawlerException("图片上传时间文本格式不正确\n%s" % last_modified)
    result["photo_time"] = int(time.mktime(last_modified_time)) - time.timezone
    return result


# 获取全部视频ID列表
def get_video_index_page(account_id):
    # https://www.yizhibo.com/member/personel/user_videos?memberid=6066534
    video_pagination_url = "https://www.yizhibo.com/member/personel/user_videos"
    query_data = {"memberid": account_id}
    video_pagination_response = net.http_request(video_pagination_url, method="GET", fields=query_data)
    result = {
        "is_exist": True,  # 是否存在视频
        "video_id_list": [],  # 全部视频id
    }
    if video_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_pagination_response.status))
    video_pagination_response_content = video_pagination_response.data.decode(errors="ignore")
    if video_pagination_response_content == '<script>window.location.href="/404.html";</script>':
        raise crawler.CrawlerException("账号不存在")
    if video_pagination_response_content.find("还没有直播哦") == -1:
        result["video_id_list"] = re.findall('<div class="scid" style="display:none;">([^<]*?)</div>', video_pagination_response_content)
        if len(result["video_id_list"]) == 0:
            raise crawler.CrawlerException("页面匹配视频id失败\n%s" % video_pagination_response_content)
    return result


# 根据video id获取指定视频的详细信息（上传时间、视频列表的下载地址等）
# video_id -> qxonW5XeZru03nUB
def get_video_info_page(video_id):
    # https://api.xiaoka.tv/live/web/get_play_live?scid=xX9-TLVx0xTiSZ69
    video_info_url = "https://api.xiaoka.tv/live/web/get_play_live"
    query_data = {"scid": video_id}
    video_info_response = net.http_request(video_info_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "video_time": False,  # 视频上传时间
        "video_url_list": [],  # 全部视频分集地址
    }
    if video_info_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_info_response.status))
    if not crawler.check_sub_key(("result", "data"), video_info_response.json_data):
        raise crawler.CrawlerException("返回信息'result'或'data'字段不存在\n%s" % video_info_response.json_data)
    if not crawler.is_integer(video_info_response.json_data["result"]):
        raise crawler.CrawlerException("返回信息'result'字段类型不正确\n%s" % video_info_response.json_data)
    if int(video_info_response.json_data["result"]) != 1:
        raise crawler.CrawlerException("返回信息'result'字段取值不正确\n%s" % video_info_response.json_data)
    # 获取视频上传时间
    if not crawler.check_sub_key(("createtime",), video_info_response.json_data["data"]):
        raise crawler.CrawlerException("返回信息'createtime'字段不存在\n%s" % video_info_response.json_data)
    if not crawler.is_integer(video_info_response.json_data["data"]["createtime"]):
        raise crawler.CrawlerException("返回信息'createtime'字段类型不正确\n%s" % video_info_response.json_data)
    result["video_time"] = int(video_info_response.json_data["data"]["createtime"])
    # 获取视频地址所在文件地址
    if not crawler.check_sub_key(("linkurl",), video_info_response.json_data["data"]):
        raise crawler.CrawlerException("返回信息'linkurl'字段不存在\n%s" % video_info_response.json_data)
    video_file_url = video_info_response.json_data["data"]["linkurl"]
    video_file_response = net.http_request(video_file_url, method="GET")
    if video_file_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_info_response.status))
    video_file_response_content = video_file_response.data.decode(errors="ignore")
    ts_id_list = re.findall("([\S]*.ts)", video_file_response_content)
    if len(ts_id_list) == 0:
        raise crawler.CrawlerException("分集文件匹配视频地址失败\n%s" % video_file_response_content)
    # http://alcdn.hls.xiaoka.tv/20161122/6b6/c5f/xX9-TLVx0xTiSZ69/
    prefix_url = video_file_url[:video_file_url.rfind("/") + 1]
    for ts_id in ts_id_list:
        result["video_url_list"].append(prefix_url + ts_id)
    return result


class YiZhiBo(crawler.Crawler):
    def __init__(self):
        # 设置APP目录
        tool.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_DOWNLOAD_VIDEO: True,
        }
        crawler.Crawler.__init__(self, sys_config)

        # 解析存档文件
        # account_id  video_count  last_video_time  photo_count  last_photo_time(account_name)
        self.account_list = crawler.read_save_data(self.save_data_path, 0, ["", "0", "0", "0", "0"])

    def main(self):
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
        if len(self.account_info) >= 6 and self.account_info[5]:
            self.display_name = self.account_info[5]
        else:
            self.display_name = self.account_info[0]
        self.step("开始")

    # 获取所有可下载图片
    def get_crawl_photo_list(self):
        # 获取全部图片地址列表
        try:
            photo_index_response = get_photo_index_page(self.account_id)
        except crawler.CrawlerException as e:
            self.error("图片首页解析失败，原因：%s" % e.message)
            return []

        self.trace("解析的全部图片：%s" % photo_index_response["photo_url_list"])
        self.step("解析获取%s张图片" % len(photo_index_response["photo_url_list"]))

        # 寻找这一页符合条件的图片
        photo_info_list = []
        for photo_url in photo_index_response["photo_url_list"]:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析图片%s" % photo_url)

            try:
                photo_head_response = get_photo_header(photo_url)
            except crawler.CrawlerException as e:
                self.error("图片%s解析失败，原因：%s" % (photo_url, e.message))
                return []

            # 检查是否达到存档记录
            if photo_head_response["photo_time"] > int(self.account_info[4]):
                photo_info_list.append({"photo_url": photo_url, "photo_time": photo_head_response["photo_time"]})
            else:
                break

        return photo_info_list

    # 解析单张图片
    def crawl_photo(self, photo_info):
        photo_index = int(self.account_info[3]) + 1
        photo_file_path = os.path.join(self.main_thread.photo_download_path, self.display_name, "%04d.%s" % (photo_index, net.get_file_type(photo_info["photo_url"])))
        save_file_return = net.save_net_file(photo_info["photo_url"], photo_file_path)
        if save_file_return["status"] == 1:
            self.step("第%s张图片下载成功" % photo_index)
        else:
            self.error("第%s张图片 %s 下载失败，原因：%s" % (photo_index, photo_info["photo_url"], crawler.download_failre(save_file_return["code"])))
            return

        # 图片下载完毕
        self.total_photo_count += 1  # 计数累加
        self.account_info[3] = str(photo_index)  # 设置存档记录
        self.account_info[4] = str(photo_info["photo_time"])  # 设置存档记录

    # 获取所有可下载视频
    def get_crawl_video_list(self):
        video_info_list = []
        # 获取全部视频ID列表
        try:
            video_pagination_response = get_video_index_page(self.account_id)
        except crawler.CrawlerException as e:
            self.error("视频首页解析失败，原因：%s" % e.message)
            return []

        self.trace("解析的全部视频：%s" % video_pagination_response["video_id_list"])
        self.step("解析获取%s个视频" % len(video_pagination_response["video_id_list"]))

        # 寻找这一页符合条件的视频
        for video_id in video_pagination_response["video_id_list"]:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析视频%s" % video_id)

            # 获取视频的时间和下载地址
            try:
                video_info_response = get_video_info_page(video_id)
            except crawler.CrawlerException as e:
                self.error("视频%s解析失败，原因：%s" % (video_id, e.message))
                return []

            # 检查是否达到存档记录
            if video_info_response["video_time"] > int(self.account_info[2]):
                video_info_list.append(video_info_response)
            else:
                break

        return video_info_list

    # 解析单个视频
    def crawl_video(self, video_info):
        video_index = int(self.account_info[1]) + 1
        video_file_path = os.path.join(self.main_thread.video_download_path, self.display_name, "%04d.ts" % video_index)
        save_file_return = net.save_net_file_list(video_info["video_url_list"], video_file_path)
        if save_file_return["status"] == 1:
            self.step("第%s个视频下载成功" % video_index)
        else:
            self.error("第%s个视频 %s 下载失败" % (video_index, video_info["video_url_list"]))
            return

        # 视频下载完毕
        self.total_video_count += 1  # 计数累加
        self.account_info[1] = str(video_index)  # 设置存档记录
        self.account_info[2] = str(video_info["video_time"])  # 设置存档记录

    def run(self):
        try:
            # 图片下载
            if self.main_thread.is_download_photo:
                # 获取所有可下载图片
                photo_info_list = self.get_crawl_photo_list()
                self.step("需要下载的全部图片解析完毕，共%s张" % len(photo_info_list))

                # 从最早的图片开始下载
                while len(photo_info_list) > 0:
                    photo_info = photo_info_list.pop()
                    self.step("开始下载第%s张图片 %s" % (int(self.account_info[3]) + 1, photo_info["photo_url"]))
                    self.crawl_photo(photo_info)
                    self.main_thread_check()  # 检测主线程运行状态

            # 视频下载
            if self.main_thread.is_download_video:
                # 获取所有可下载视频
                video_info_list = self.get_crawl_video_list()
                self.step("需要下载的全部视频解析完毕，共%s个" % len(video_info_list))

                # 从最早的视频开始下载
                while len(video_info_list) > 0:
                    video_info = video_info_list.pop()
                    self.step("开始下载第%s个视频 %s" % (int(self.account_info[1]) + 1, video_info["video_url_list"]))
                    self.crawl_video(video_info)
                    self.main_thread_check()  # 检测主线程运行状态
        except SystemExit as se:
            if se.code == 0:
                self.step("提前退出")
            else:
                self.error("异常退出")
        except Exception as e:
            self.error("未知异常")
            self.error(str(e) + "\n" + traceback.format_exc(), False)

        # 保存最后的信息
        with self.thread_lock:
            file.write_file("\t".join(self.account_info), self.main_thread.temp_save_data_path)
            self.main_thread.total_photo_count += self.total_photo_count
            self.main_thread.total_video_count += self.total_video_count
            self.main_thread.account_list.pop(self.account_id)
        self.step("下载完毕，总共获得%s张图片和%s个视频" % (self.total_photo_count, self.total_video_count))
        self.notify_main_thread()


if __name__ == "__main__":
    YiZhiBo().main()
