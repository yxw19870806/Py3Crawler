# -*- coding:UTF-8  -*-
"""
nico nico视频列表（My List）视频爬虫
http://www.nicovideo.jp/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import html
import os
import time
import traceback
from pyquery import PyQuery as pq
from common import *

COOKIE_INFO = {}


# 检测登录状态
def check_login():
    if not COOKIE_INFO:
        return False
    index_url = "http://www.nicovideo.jp/"
    index_response = net.http_request(index_url, method="GET", cookies_list=COOKIE_INFO)
    if index_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        return pq(index_response.data.decode(errors="ignore")).find('#siteHeaderUserNickNameContainer').length > 0
    return False


# 获取视频列表全部视频信息
# list_id => 15614906
def get_mylist_index(list_id):
    # http://www.nicovideo.jp/mylist/15614906
    mylist_index_url = "http://www.nicovideo.jp/mylist/%s" % list_id
    mylist_index_response = net.http_request(mylist_index_url, method="GET")
    result = {
        "video_info_list": [],  # 全部视频信息
    }
    if mylist_index_response.status == 404:
        raise crawler.CrawlerException("视频列表不存在")
    elif mylist_index_response.status == 403:
        raise crawler.CrawlerException("视频列表未公开")
    elif mylist_index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(mylist_index_response.status))
    mylist_index_response_content = mylist_index_response.data.decode(errors="ignore")
    all_video_info = tool.find_sub_string(mylist_index_response_content, "Mylist.preload(%s," % list_id, ");").strip()
    if not all_video_info:
        raise crawler.CrawlerException("截取视频列表失败\n%s" % mylist_index_response_content)
    all_video_info = tool.json_decode(all_video_info)
    if all_video_info is None:
        raise crawler.CrawlerException("视频列表加载失败\n%s" % mylist_index_response_content)
    # 倒序排列，时间越晚的越前面
    all_video_info.reverse()
    for video_info in all_video_info:
        result_video_info = {
            "video_id": None,  # 视频id
            "video_title": "",  # 视频标题
        }
        if not crawler.check_sub_key(("item_data",), video_info):
            raise crawler.CrawlerException("视频信息'item_data'字段不存在\n%s" % video_info)
        # 获取视频id
        if not crawler.check_sub_key(("video_id",), video_info["item_data"]):
            raise crawler.CrawlerException("视频信息'video_id'字段不存在\n%s" % video_info)
        video_id = video_info["item_data"]["video_id"].replace("sm", "")
        if not crawler.is_integer(video_id):
            raise crawler.CrawlerException("视频信息'video_id'字段类型不正确\n%s" % video_info)
        result_video_info["video_id"] = int(video_id)
        # 获取视频辩题
        if not crawler.check_sub_key(("title",), video_info["item_data"]):
            raise crawler.CrawlerException("视频信息'title'字段不存在\n%s" % video_info)
        result_video_info["video_title"] = video_info["item_data"]["title"]
        result["video_info_list"].append(result_video_info)
    return result


# 根据视频id，获取视频的下载地址
def get_video_info(video_id):
    video_play_url = "http://www.nicovideo.jp/watch/sm%s" % video_id
    video_play_response = net.http_request(video_play_url, method="GET", cookies_list=COOKIE_INFO)
    result = {
        "extra_cookie": {},  # 额外的cookie
        "is_delete": False,  # 是否已删除
        "is_private": False,  # 是否未公开
        "video_title": "",  # 视频标题
        "video_url": None,  # 视频地址
    }
    if video_play_response.status == 403:
        log.step("视频%s访问异常，重试" % video_id)
        time.sleep(30)
        return get_video_info(video_id)
    elif video_play_response.status == 404:
        result["is_delete"] = True
        return result
    elif video_play_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException("视频播放页访问失败，" + crawler.request_failre(video_play_response.status))
    video_play_response_content = video_play_response.data.decode(errors="ignore")
    video_info_string = tool.find_sub_string(video_play_response_content, 'data-api-data="', '" data-environment="')
    if not video_info_string:
        # 播放页面提示flash没有安装，重新访问
        if pq(video_play_response_content).find("div.notify_update_flash_player").length > 0:
            return get_video_info(video_id)
        if video_play_response_content.find("<p>この動画が投稿されている公開コミュニティはありません。</p>") > 0:
            result["is_private"] = True
            return result
        raise crawler.CrawlerException("视频信息截取失败\n%s" % video_play_response_content)
    video_info_string = html.unescape(video_info_string)
    video_info = tool.json_decode(video_info_string)
    if video_info is None:
        raise crawler.CrawlerException("视频信息加载失败\n%s" % video_play_response_content)
    if not crawler.check_sub_key(("video",), video_info):
        raise crawler.CrawlerException("视频信息'video'字段不存在\n%s" % video_info)
    # 获取视频标题
    if not crawler.check_sub_key(("title",), video_info["video"]):
        raise crawler.CrawlerException("视频信息'title'字段不存在\n%s" % video_info)
    result["video_title"] = video_info["video"]["title"]
    # 获取视频地址
    if not crawler.check_sub_key(("smileInfo",), video_info["video"]):
        raise crawler.CrawlerException("视频信息'smileInfo'字段不存在\n%s" % video_info)
    if not crawler.check_sub_key(("url",), video_info["video"]["smileInfo"]):
        raise crawler.CrawlerException("视频信息'url'字段不存在\n%s" % video_info)
    result["video_url"] = video_info["video"]["smileInfo"]["url"]
    # 返回的cookies
    set_cookie = net.get_cookies_from_response_header(video_play_response.headers)
    result["extra_cookie"] = set_cookie
    return result


class NicoNico(crawler.Crawler):
    def __init__(self, **kwargs):
        global COOKIE_INFO

        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_VIDEO: True,
            crawler.SYS_SET_PROXY: True,
            crawler.SYS_GET_COOKIE: ("nicovideo.jp",),
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 设置全局变量，供子线程调用
        COOKIE_INFO = self.cookie_value

        # 解析存档文件
        # mylist_id  last_video_id
        self.account_list = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

        # 检测登录状态
        if not check_login():
            log.error("没有检测到账号登录状态，退出程序！")
            tool.process_exit()

    def main(self):
        # 循环下载每个id
        thread_list = []
        for list_id in sorted(self.account_list.keys()):
            # 提前结束
            if not self.is_running():
                break

            # 开始下载
            thread = Download(self.account_list[list_id], self)
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

        log.step("全部下载完毕，耗时%s秒，共计视频%s个" % (self.get_run_time(), self.total_video_count))


class Download(crawler.DownloadThread):
    def __init__(self, account_info, main_thread):
        crawler.DownloadThread.__init__(self, account_info, main_thread)
        self.list_id = self.account_info[0]
        if len(self.account_info) >= 3 and self.account_info[2]:
            self.display_name = self.account_info[2]
        else:
            self.display_name = self.account_info[0]
        self.step("开始")

    # 获取所有可下载图片
    def get_crawl_list(self):
        # 获取视频信息列表
        try:
            mylist_index_response = get_mylist_index(self.list_id)
        except crawler.CrawlerException as e:
            self.error("视频列表解析失败，原因：%s" % e.message)
            raise

        self.trace("解析的全部视频：%s" % mylist_index_response["video_info_list"])
        self.step("解析获取%s个视频" % len(mylist_index_response["video_info_list"]))

        video_info_list = []
        # 寻找这一页符合条件的视频
        for video_info in mylist_index_response["video_info_list"]:
            self.main_thread_check()  # 检测主线程运行状态
            # 检查是否达到存档记录
            if video_info["video_id"] > int(self.account_info[1]):
                video_info_list.append(video_info)
            else:
                break

        return video_info_list

    # 解析单个视频
    def crawl_video(self, video_info):
        try:
            video_info_response = get_video_info(video_info["video_id"])
        except crawler.CrawlerException as e:
            self.error("视频%s 《%s》解析失败，原因：%s" % (video_info["video_id"], video_info["video_title"], e.message))
            return

        if video_info_response["is_delete"]:
            self.error("视频%s 《%s》已删除，跳过" % (video_info["video_id"], video_info["video_title"]))
            return

        if video_info_response["is_private"]:
            self.error("视频%s 《%s》未公开，跳过" % (video_info["video_id"], video_info["video_title"]))
            return

        self.step("视频%s 《%s》 %s 开始下载" % (video_info["video_id"], video_info["video_title"], video_info_response["video_url"]))

        video_file_path = os.path.join(self.main_thread.video_download_path, self.display_name, "%08d - %s.mp4" % (video_info["video_id"], path.filter_text(video_info["video_title"])))
        cookies_list = COOKIE_INFO
        if video_info_response["extra_cookie"]:
            cookies_list.update(video_info_response["extra_cookie"])
        save_file_return = net.save_net_file(video_info_response["video_url"], video_file_path, cookies_list=cookies_list)
        if save_file_return["status"] == 1:
            self.step("视频%s 《%s》下载成功" % (video_info["video_id"], video_info["video_title"]))
        else:
            self.error("视频%s 《%s》 %s 下载失败，原因：%s" % (video_info["video_id"], video_info["video_title"], video_info_response["video_url"], crawler.download_failre(save_file_return["code"])))
            return

        # 视频下载完毕
        self.total_video_count += 1  # 计数累加
        self.account_info[1] = str(video_info["video_id"])  # 设置存档记录

    def run(self):
        try:
            # 获取所有可下载视频
            video_info_list = self.get_crawl_list()
            self.step("需要下载的全部视频解析完毕，共%s个" % len(video_info_list))

            # 从最早的视频开始下载
            while len(video_info_list) > 0:
                video_info = video_info_list.pop()
                self.step("开始解析视频 %s 《%s》" % (video_info["video_id"], video_info["video_title"]))
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
            self.main_thread.total_video_count += self.total_video_count
            self.main_thread.account_list.pop(self.list_id)
        self.step("完成")
        self.notify_main_thread()


if __name__ == "__main__":
    NicoNico().main()
