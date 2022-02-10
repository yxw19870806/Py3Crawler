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
    index_response = net.request(index_url, method="GET", cookies_list=COOKIE_INFO)
    if index_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        return pq(index_response.data.decode(errors="ignore")).find('#siteHeaderUserNickNameContainer').length > 0
    return False


# 获取指定账号下的所有视频列表
def get_account_mylist(account_id):
    account_mylist_url = f"https://www.nicovideo.jp/user/{account_id}/mylist"
    account_mylist_response = net.request(account_mylist_url, method="GET", is_auto_retry=False)
    result = {
        "list_id_list": [],  # 全部视频列表id
        "is_private": False,  # 是否未公开
    }
    if account_mylist_response.status in [404, 500]:
        raise crawler.CrawlerException("账号不存在")
    elif account_mylist_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(account_mylist_response.status))
    account_mylist_response_content = account_mylist_response.data.decode(errors="ignore")
    if pq(account_mylist_response_content).find(".articleBody .noListMsg").length == 1:
        message = pq(account_mylist_response_content).find(".articleBody .noListMsg .att").text()
        if message == "非公開です":
            result["is_private"] = True
            return result
        elif message == "公開マイリストはありません":
            return result
        else:
            raise crawler.CrawlerException(f"未知视频列表状态: {message}")
    mylist_list_selector = pq(account_mylist_response_content).find(".articleBody .outer")
    for mylist_index in range(0, mylist_list_selector.length):
        mylist_selector = mylist_list_selector.eq(mylist_index)
        mylist_url = mylist_selector.find(".section h4 a").attr("href")
        if mylist_url is None:
            raise crawler.CrawlerException("视频列表信息截取视频列表地址失败\n" + mylist_selector.html())
        list_id = tool.find_sub_string(mylist_url, "mylist/")
        if not tool.is_integer(list_id):
            raise crawler.CrawlerException("视频列表地址截取视频列表id失败\n" + mylist_selector.html())
        result["list_id_list"].append(int(list_id))
    return result


# 获取指定账号下的一页投稿视频
def get_one_page_account_video(account_id, page_count):
    video_index_url = f"https://www.nicovideo.jp/user/{account_id}/video"
    query_data = {"page": page_count}
    video_index_response = net.request(video_index_url, method="GET", fields=query_data)
    result = {
        "video_info_list": [],  # 全部视频信息
        "is_over": False,  # 是否最后页
        "is_private": False,  # 是否未公开
    }
    if video_index_response.status == 404:
        raise crawler.CrawlerException("账号不存在")
    elif video_index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_index_response.status))
    video_index_response_content = video_index_response.data.decode(errors="ignore")
    if pq(video_index_response_content).find(".articleBody .noListMsg").length == 1:
        message = pq(video_index_response_content).find(".articleBody .noListMsg .att").text()
        if message == "非公開です":
            result["is_private"] = True
            return result
        else:
            raise crawler.CrawlerException(f"未知视频列表状态: {message}")
    video_list_selector = pq(video_index_response_content).find(".articleBody .outer")
    # 第一个是排序选择框，跳过
    for video_index in range(1, video_list_selector.length):
        result_video_info = {
            "video_id": None,  # 视频id
            "video_title": "",  # 视频标题
        }
        video_selector = video_list_selector.eq(video_index)
        # 获取视频id
        video_url = video_selector.find(".section h5 a").attr("href")
        if video_url is None:
            raise crawler.CrawlerException("视频信息截取视频地址失败\n" + video_selector.html())
        video_id = tool.find_sub_string(video_url, "watch/sm", "?")
        if not tool.is_integer(video_id):
            raise crawler.CrawlerException("视频地址截取视频id失败\n" + video_selector.html())
        result_video_info["video_id"] = int(video_id)
        # 获取视频标题
        video_title = video_selector.find(".section h5 a").text()
        if not video_title:
            raise crawler.CrawlerException("视频信息截取视频标题失败\n" + video_selector.html())
        result_video_info["video_title"] = video_title
        result["video_info_list"].append(result_video_info)
    # 判断是不是最后页
    if pq(video_index_response_content).find(".articleBody .pager a:last").text() != "次へ":
        result["is_over"] = True
    return result


# 获取视频列表全部视频信息
# list_id => 15614906
def get_mylist_index(list_id):
    # http://www.nicovideo.jp/mylist/15614906
    mylist_index_url = f"http://www.nicovideo.jp/mylist/{list_id}"
    mylist_index_response = net.request(mylist_index_url, method="GET")
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
    all_video_info = tool.find_sub_string(mylist_index_response_content, f"Mylist.preload({list_id},", ");").strip()
    if not all_video_info:
        raise crawler.CrawlerException("截取视频列表失败\n" + mylist_index_response_content)
    all_video_info = tool.json_decode(all_video_info)
    if all_video_info is None:
        raise crawler.CrawlerException("视频列表加载失败\n" + mylist_index_response_content)
    # 倒序排列，时间越晚的越前面
    all_video_info.reverse()
    for video_info in all_video_info:
        result_video_info = {
            "video_id": None,  # 视频id
            "video_title": "",  # 视频标题
        }
        # 获取视频id
        video_id = crawler.get_json_value(video_info, "item_data", "video_id", type_check=str).replace("sm", "")
        if not tool.is_integer(video_id):
            raise crawler.CrawlerException(f"视频信息{video_info}中'video_id'字段类型不正确")
        result_video_info["video_id"] = int(video_id)
        # 获取视频辩题
        result_video_info["video_title"] = crawler.get_json_value(video_info, "item_data", "title", type_check=str)
        result["video_info_list"].append(result_video_info)
    return result


# 根据视频id，获取视频的下载地址
def get_video_info(video_id):
    video_play_url = f"http://www.nicovideo.jp/watch/sm{video_id}"
    video_play_response = net.request(video_play_url, method="GET", cookies_list=COOKIE_INFO)
    result = {
        "extra_cookie": {},  # 额外的cookie
        "is_delete": False,  # 是否已删除
        "is_private": False,  # 是否未公开
        "video_title": "",  # 视频标题
        "video_url": None,  # 视频地址
    }
    if video_play_response.status == 403:
        log.step(f"视频{video_id}访问异常，重试")
        time.sleep(30)
        return get_video_info(video_id)
    elif video_play_response.status == 404:
        result["is_delete"] = True
        return result
    elif video_play_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException("视频播放页访问失败，" + crawler.request_failre(video_play_response.status))
    video_play_response_content = video_play_response.data.decode(errors="ignore")
    script_json_html = tool.find_sub_string(video_play_response_content, 'data-api-data="', '" data-environment="')
    if not script_json_html:
        # 播放页面提示flash没有安装，重新访问
        if pq(video_play_response_content).find("div.notify_update_flash_player").length > 0:
            return get_video_info(video_id)
        if video_play_response_content.find("<p>この動画が投稿されている公開コミュニティはありません。</p>") > 0:
            result["is_private"] = True
            return result
        raise crawler.CrawlerException("视频信息截取失败\n" + video_play_response_content)
    script_json = tool.json_decode(html.unescape(script_json_html))
    if script_json is None:
        raise crawler.CrawlerException("视频信息加载失败\n" + video_play_response_content)
    # 获取视频标题
    result["video_title"] = crawler.get_json_value(script_json, "video", "title", type_check=str)
    # 获取视频地址
    result["video_url"] = crawler.get_json_value(script_json, "video", "smileInfo", "url", type_check=str)
    # 返回的cookies
    result["extra_cookie"] = net.get_cookies_from_response_header(video_play_response.headers)
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
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

        # 检测登录状态
        if not check_login():
            log.error("没有检测到账号登录状态，退出程序！")
            tool.process_exit()

    def main(self):
        try:
            # 循环下载每个id
            thread_list = []
            for list_id in sorted(self.save_data.keys()):
                # 提前结束
                if not self.is_running():
                    break

                # 开始下载
                thread = Download(self.save_data[list_id], self)
                thread.start()
                thread_list.append(thread)

                time.sleep(1)

            # 等待子线程全部完成
            while len(thread_list) > 0:
                thread_list.pop().join()
        except KeyboardInterrupt:
            self.stop_process()

        # 未完成的数据保存
        self.write_remaining_save_data()

        # 重新排序保存存档文件
        self.rewrite_save_file()

        self.end_message()


class Download(crawler.DownloadThread):
    def __init__(self, single_save_data, main_thread):
        crawler.DownloadThread.__init__(self, single_save_data, main_thread)
        self.list_id = self.single_save_data[0]
        if len(self.single_save_data) >= 3 and self.single_save_data[2]:
            self.display_name = self.single_save_data[2]
        else:
            self.display_name = self.single_save_data[0]
        self.step("开始")

    # 获取所有可下载图片
    def get_crawl_list(self):
        # 获取视频信息列表
        try:
            mylist_index_response = get_mylist_index(self.list_id)
        except crawler.CrawlerException as e:
            self.error(e.http_error("视频列表"))
            raise

        self.trace(f"解析的全部视频：{mylist_index_response['video_info_list']}")
        self.step(f"解析获取{len(mylist_index_response['video_info_list'])}个视频")

        video_info_list = []
        # 寻找这一页符合条件的视频
        for video_info in mylist_index_response["video_info_list"]:
            # 检查是否达到存档记录
            if video_info["video_id"] > int(self.single_save_data[1]):
                video_info_list.append(video_info)
            else:
                break

        return video_info_list

    # 解析单个视频
    def crawl_video(self, video_info):
        self.step(f"开始解析视频 {video_info['video_id']} 《{video_info['video_title']}》")

        try:
            video_info_response = get_video_info(video_info["video_id"])
        except crawler.CrawlerException as e:
            self.error(e.http_error(f"视频{video_info['video_id']} 《{video_info['video_title']}》"))
            raise

        if video_info_response["is_delete"]:
            self.error(f"视频{video_info['video_id']} 《{video_info['video_title']}》已删除，跳过")
            return

        if video_info_response["is_private"]:
            self.error(f"视频{video_info['video_id']} 《{video_info['video_title']}》未公开，跳过")
            return

        self.step(f"视频{video_info['video_id']} 《{video_info['video_title']}》 {video_info_response['video_url']} 开始下载")

        video_file_path = os.path.join(self.main_thread.video_download_path, self.display_name, f"%08d - {path.filter_text(video_info['video_title'])}.mp4" % video_info["video_id"])
        cookies_list = COOKIE_INFO
        if video_info_response["extra_cookie"]:
            cookies_list.update(video_info_response["extra_cookie"])
        save_file_return = net.download(video_info_response["video_url"], video_file_path, cookies_list=cookies_list)
        if save_file_return["status"] == 1:
            self.total_video_count += 1  # 计数累加
            self.step(f"视频{video_info['video_id']} 《{video_info['video_title']}》下载成功")
        else:
            self.error(f"视频{video_info['video_id']} 《{video_info['video_title']}》 {video_info_response['video_url']} 下载失败，原因：{crawler.download_failre(save_file_return['code'])}")
            self.check_download_failure_exit()

        # 视频下载完毕
        self.single_save_data[1] = str(video_info["video_id"])  # 设置存档记录

    def run(self):
        try:
            # 获取所有可下载视频
            video_info_list = self.get_crawl_list()
            self.step(f"需要下载的全部视频解析完毕，共{len(video_info_list)}个")

            # 从最早的视频开始下载
            while len(video_info_list) > 0:
                self.crawl_video(video_info_list.pop())
                self.main_thread_check()  # 检测主线程运行状态
        except (SystemExit, KeyboardInterrupt) as e:
            if isinstance(e, SystemExit) and e.code == 1:
                self.error("异常退出")
            else:
                self.step("提前退出")
        except Exception as e:
            self.error("未知异常")
            self.error(str(e) + "\n" + traceback.format_exc(), False)

        self.main_thread.save_data.pop(self.list_id)
        self.done()


if __name__ == "__main__":
    NicoNico().main()
