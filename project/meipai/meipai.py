# -*- coding:UTF-8  -*-
"""
美拍视频爬虫
http://www.meipai.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import base64
import os
import time
import traceback
from functools import reduce
from pyquery import PyQuery as pq
from common import *

EACH_PAGE_VIDEO_COUNT = 20  # 每次请求获取的视频数量


# 获取指定页数的全部视频
def get_one_page_video(account_id, page_count):
    # http://www.meipai.com/users/user_timeline?uid=22744352&page=1&count=20&single_column=1
    video_pagination_url = "http://www.meipai.com/users/user_timeline"
    query_data = {
        "uid": account_id,
        "page": page_count,
        "count": EACH_PAGE_VIDEO_COUNT,
        "single_column": 1,
    }
    video_pagination_response = net.request(video_pagination_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "video_info_list": [],  # 全部视频信息
    }
    if video_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_pagination_response.status))
    for media_info in crawler.get_json_value(video_pagination_response.json_data, "medias", type_check=list):
        # 历史直播，跳过
        if crawler.check_sub_key(("lives",), media_info):
            continue
        result_video_info = {
            "video_id": None,  # 视频id
            "video_url": None,  # 视频地址
        }
        # 获取视频id
        result_video_info["video_id"] = crawler.get_json_value(media_info, "id", type_check=int)
        # 获取视频下载地址
        video_url = decrypt_video_url(crawler.get_json_value(media_info, "video", type_check=str))
        if video_url is None:
            raise crawler.CrawlerException("加密视频地址解密失败\n%s" % media_info)
        result_video_info["video_url"] = video_url
        result["video_info_list"].append(result_video_info)
    return result


# 获取指定视频播放页
def get_video_play_page(video_id):
    video_play_url = "http://www.meipai.com/media/%s" % video_id
    video_play_response = net.request(video_play_url, method="GET")
    result = {
        "is_delete": False,  # 是否已删除
        "video_url": None,  # 视频地址
    }
    if video_play_response.status == 404:
        result["is_delete"] = True
        return result
    elif video_play_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_play_response.status))
    video_play_response_content = video_play_response.data.decode(errors="ignore")
    video_url_crypt_string = pq(video_play_response_content).find("meta[property='og:video:url']").attr("content")
    if not video_url_crypt_string:
        if pq(video_play_response_content).find(".error-p").length == 1:
            error_message = pq(video_play_response_content).find(".error-p").text()
            if error_message == "为建设清朗网络空间，视频正在审核中，暂时无法播放。" or error_message == "可能已被删除或网址输入错误,请再核对下吧~":
                result["is_delete"] = True
                return result
        raise crawler.CrawlerException("页面截取加密视频地址失败\n%s" % video_play_response_content)
    video_url = decrypt_video_url(video_url_crypt_string)
    if not video_url:
        raise crawler.CrawlerException("加密视频地址解密失败\n%s" % video_url_crypt_string)
    result["video_url"] = video_url
    return result


# 视频地址解谜
# 破解于播放器swf文件中com.meitu.cryptography.meipai.Default.decode
def decrypt_video_url(encrypted_string):
    loc1 = _get_hex(encrypted_string)
    loc2 = _get_dec(loc1["hex"])
    loc3 = _sub_str(loc1["str"], loc2["pre"])
    encryption_video_url = _sub_str(loc3, _get_pos(loc3, loc2["tail"]))
    try:
        video_url = base64.b64decode(encryption_video_url).decode(errors="ignore")
    except TypeError:
        return None
    if video_url.find("http") != 0:
        return None
    return video_url


def _get_hex(arg1):
    return {"str": arg1[4:], "hex": reduce(lambda x, y: y + x, arg1[0:4])}


def _get_dec(arg1):
    loc1 = str(int(arg1, 16))
    return {"pre": [int(loc1[0]), int(loc1[1])], "tail": [int(loc1[2]), int(loc1[3])]}


def _sub_str(arg1, arg2):
    loc1 = arg1[:arg2[0]]
    loc2 = arg1[arg2[0]: arg2[0] + arg2[1]]
    return loc1 + arg1[arg2[0]:].replace(loc2, "", 1)


def _get_pos(arg1, arg2):
    arg2[0] = len(arg1) - arg2[0] - arg2[1]
    return arg2


class MeiPai(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_VIDEO: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 解析存档文件
        # account_id  last_video_id
        self.account_list = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

    def main(self):
        try:
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
        except KeyboardInterrupt:
            self.stop_process()

        # 未完成的数据保存
        if len(self.account_list) > 0:
            file.write_file(tool.list_to_string(list(self.account_list.values())), self.temp_save_data_path)

        # 重新排序保存存档文件
        crawler.rewrite_save_file(self.temp_save_data_path, self.save_data_path)

        log.step("全部下载完毕，耗时%s秒，共计视频%s个" % (self.get_run_time(), self.total_video_count))


class Download(crawler.DownloadThread):
    def __init__(self, account_info, main_thread):
        crawler.DownloadThread.__init__(self, account_info, main_thread)
        self.account_id = self.account_info[0]
        if len(self.account_info) >= 3 and self.account_info[2]:
            self.display_name = self.account_info[2]
        else:
            self.display_name = self.account_info[0]
        self.step("开始")

    # 获取所有可下载视频
    def get_crawl_list(self):
        page_count = 1
        unique_list = []
        video_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的视频
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析第%s页视频" % page_count)

            # 获取一页视频
            try:
                video_pagination_response = get_one_page_video(self.account_id, page_count)
            except crawler.CrawlerException as e:
                self.error("第%s页视频解析失败，原因：%s" % (page_count, e.message))
                raise

            self.trace("第%s页解析的全部视频：%s" % (page_count, video_pagination_response["video_info_list"]))
            self.step("第%s页解析获取%s个视频" % (page_count, len(video_pagination_response["video_info_list"])))

            # 寻找这一页符合条件的视频
            for video_info in video_pagination_response["video_info_list"]:
                # 检查是否达到存档记录
                if video_info["video_id"] > int(self.account_info[1]):
                    # 新增视频导致的重复判断
                    if video_info["video_id"] in unique_list:
                        continue
                    else:
                        video_info_list.append(video_info)
                        unique_list.append(video_info["video_id"])
                else:
                    is_over = True
                    break

            if not is_over:
                # 获取的视频数量少于1页的上限，表示已经到结束了
                # 如果视频数量正好是页数上限的倍数，则由下一页获取是否为空判断
                if len(video_pagination_response["video_info_list"]) < EACH_PAGE_VIDEO_COUNT:
                    is_over = True
                else:
                    page_count += 1

        return video_info_list

    # 下载单个视频
    def crawl_video(self, video_info):
        self.step("开始下载视频%s %s" % (video_info["video_id"], video_info["video_url"]))

        file_path = os.path.join(self.main_thread.video_download_path, self.display_name, "%010d.mp4" % video_info["video_id"])
        save_file_return = net.download(video_info["video_url"], file_path)
        if save_file_return["status"] == 1:
            self.step("视频%s下载成功" % video_info["video_id"])
        else:
            self.error("视频%s %s 下载失败，原因：%s" % (video_info["video_id"], video_info["video_url"], crawler.download_failre(save_file_return["code"])))

        # 视频下载完毕
        self.account_info[1] = str(video_info["video_id"])  # 设置存档记录
        self.total_video_count += 1  # 计数累加

    def run(self):
        try:
            # 获取所有可下载视频
            video_info_list = self.get_crawl_list()
            self.step("需要下载的全部视频解析完毕，共%s个" % len(video_info_list))

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

        # 保存最后的信息
        with self.thread_lock:
            file.write_file("\t".join(self.account_info), self.main_thread.temp_save_data_path)
            self.main_thread.total_video_count += self.total_video_count
            self.main_thread.account_list.pop(self.account_id)
        self.step("下载完毕，总共获得%s个视频" % self.total_video_count)
        self.notify_main_thread()


if __name__ == "__main__":
    MeiPai().main()
