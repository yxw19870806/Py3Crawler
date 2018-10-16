# -*- coding:UTF-8  -*-
"""
小咖秀视频爬虫
https://www.xiaokaxiu.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import time
import traceback
from common import *

EACH_PAGE_VIDEO_COUNT = 10  # 每次请求获取的视频数量


# 获取指定页数的全部视频
def get_one_page_video(account_id, page_count):
    # https://v.xiaokaxiu.com/video/web/get_member_videos?memberid=562273&limit=10&page=1
    video_pagination_url = "https://v.xiaokaxiu.com/video/web/get_member_videos"
    query_data = {
        "limit": EACH_PAGE_VIDEO_COUNT,
        "memberid": account_id,
        "page": page_count,
    }
    video_pagination_response = net.http_request(video_pagination_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "video_info_list": [],  # 全部视频信息
    }
    if video_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_pagination_response.status))
    if not crawler.check_sub_key(("result",), video_pagination_response.json_data):
        raise crawler.CrawlerException("返回数据'result'字段不存在\n%s" % video_pagination_response.json_data)
    # 没有视频了
    if video_pagination_response.json_data["result"] == 500:
        return result
    if not crawler.check_sub_key(("data",), video_pagination_response.json_data):
        raise crawler.CrawlerException("返回数据'data'字段不存在\n%s" % video_pagination_response.json_data)
    if not crawler.check_sub_key(("list",), video_pagination_response.json_data["data"]):
        raise crawler.CrawlerException("返回数据'list'字段不存在\n%s" % video_pagination_response.json_data)
    for media_data in video_pagination_response.json_data["data"]["list"]:
        result_video_info = {
            "video_id": None,  # 视频id
            "video_url": None,  # 视频地址
        }
        # 获取视频id
        if not crawler.check_sub_key(("videoid",), media_data):
            raise crawler.CrawlerException("视频信息'videoid'字段不存在\n%s" % media_data)
        if not crawler.is_integer(media_data["videoid"]):
            raise crawler.CrawlerException("视频信息'videoid'字段类型不正确\n%s" % media_data)
        result_video_info["video_id"] = int(media_data["videoid"])
        # 获取视频下载地址
        if not crawler.check_sub_key(("download_linkurl",), media_data):
            raise crawler.CrawlerException("视频信息'download_linkurl'字段不存在\n%s" % media_data)
        result_video_info["video_url"] = media_data["download_linkurl"]
        result["video_info_list"].append(result_video_info)
    return result


class XiaoKaXiu(crawler.Crawler):
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
        file_path = os.path.join(self.main_thread.video_download_path, self.display_name, "%09d.mp4" % video_info["video_id"])
        save_file_return = net.save_net_file(video_info["video_url"], file_path)
        if save_file_return["status"] == 1:
            self.step("%s视频下载成功" % video_info["video_id"])
        else:
            self.error("%s视频 %s 下载失败，原因：%s" % (video_info["video_id"], video_info["video_url"], crawler.download_failre(save_file_return["code"])))

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
                video_info = video_info_list.pop()
                self.step("开始下载%s视频 %s" % (video_info["video_id"], video_info["video_url"]))
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
            self.main_thread.account_list.pop(self.account_id)
        self.step("下载完毕，总共获得%s个视频" % self.total_video_count)
        self.notify_main_thread()


if __name__ == "__main__":
    XiaoKaXiu().main()
