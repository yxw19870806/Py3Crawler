# -*- coding:UTF-8  -*-
"""
唱吧歌曲爬虫
https://changba.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import base64
import os
import re
import threading
import time
import traceback
from common import *


# 获取账号首页页面
def get_account_index_page(account_id):
    account_index_url = "https://changba.com/u/%s" % account_id
    account_index_response = net.http_request(account_index_url, method="GET", is_auto_redirect=False)
    result = {
        "user_id": None,  # user id
    }
    if account_index_response.status == 302 and account_index_response.getheader("Location") == "https://changba.com":
        raise crawler.CrawlerException("账号不存在")
    elif account_index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(account_index_response.status))
    account_index_response_content = account_index_response.data.decode(errors="ignore")
    # 获取user id
    user_id = tool.find_sub_string(account_index_response_content, "var userid = '", "'")
    if not crawler.is_integer(user_id):
        raise crawler.CrawlerException("页面截取userid失败\n%s" % account_index_response_content)
    result["user_id"] = user_id
    return result


# 获取指定页数的全部歌曲信息
# user_id -> 4306405
def get_one_page_audio(user_id, page_count):
    # https://changba.com/member/personcenter/loadmore.php?userid=4306405&pageNum=1
    audit_pagination_url = "https://changba.com/member/personcenter/loadmore.php"
    query_data = {
        "userid": user_id,
        "pageNum": page_count - 1,
    }
    audit_pagination_response = net.http_request(audit_pagination_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "audio_info_list": [],  # 全部歌曲信息
    }
    if audit_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(audit_pagination_response.status))
    for audio_info in audit_pagination_response.json_data:
        result_audio_info = {
            "audio_id": None,  # 歌曲id
            "audio_key": None,  # 歌曲唯一key
            "audio_title": "",  # 歌曲标题
        }
        # 获取歌曲id
        if not crawler.check_sub_key(("workid",), audio_info):
            raise crawler.CrawlerException("歌曲信息'workid'字段不存在\n%s" % audio_info)
        if not crawler.is_integer(audio_info["workid"]):
            raise crawler.CrawlerException("歌曲信息'workid'字段类型不正确\n%s" % audio_info)
        result_audio_info["audio_id"] = audio_info["workid"]
        # 获取歌曲标题
        if not crawler.check_sub_key(("songname",), audio_info):
            raise crawler.CrawlerException("歌曲信息'songname'字段不存在\n%s" % audio_info)
        result_audio_info["audio_title"] = audio_info["songname"]
        # 获取歌曲key
        if not crawler.check_sub_key(("enworkid",), audio_info):
            raise crawler.CrawlerException("歌曲信息'enworkid'字段不存在\n%s" % audio_info)
        result_audio_info["audio_key"] = audio_info["enworkid"]
        result["audio_info_list"].append(result_audio_info)
    return result


# 获取指定id的歌曲播放页
# audio_en_word_id => w-ptydrV23KVyIPbWPoKsA
def get_audio_play_page(audio_en_word_id):
    audio_play_url = "https://changba.com/s/%s" % audio_en_word_id
    result = {
        "audio_id": None,  # 歌曲id
        "audio_title": "",  # 歌曲标题
        "audio_url": None,  # 歌曲地址
        "is_delete": False,  # 是不是已经被删除
    }
    audio_play_response = net.http_request(audio_play_url, method="GET")
    if audio_play_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(audio_play_response.status))
    audio_play_response_content = audio_play_response.data.decode(errors="ignore")
    if audio_play_response_content.find("该作品可能含有不恰当内容将不能显示。") > -1:
        result["is_delete"] = True
        return result
    # 获取歌曲id
    audio_id = tool.find_sub_string(audio_play_response_content, "export_song.php?workid=", "&")
    if not crawler.is_integer(audio_id):
        raise crawler.CrawlerException("页面截取歌曲id失败\n%s" % audio_play_response_content)
    result["audio_id"] = audio_id
    # 获取歌曲标题
    audio_title = tool.find_sub_string(audio_play_response_content, '<div class="title">', "</div>")
    if not audio_title:
        raise crawler.CrawlerException("页面截取歌曲标题失败\n%s" % audio_play_response_content)
    result["audio_title"] = audio_title.strip()
    # 判断歌曲类型（音频或者视频）
    is_video = tool.find_sub_string(audio_play_response_content, "&isvideo=", "'")
    if not crawler.is_integer(is_video):
        raise crawler.CrawlerException("页面截取歌曲类型失败\n%s" % audio_play_response_content)
    is_video = False if is_video == "0" else True
    # 获取歌曲地址
    if not is_video:  # 音频
        audio_source_url = tool.find_sub_string(audio_play_response_content, 'var a="', '"')
        if not audio_source_url:
            raise crawler.CrawlerException("页面截取歌曲原始地址失败\n%s" % audio_play_response_content)
        # 从JS处解析的规则
        special_find = re.findall("userwork/([abc])(\d+)/(\w+)/(\w+)\.mp3", audio_source_url)
        if len(special_find) == 0:
            result["audio_url"] = audio_source_url
        elif len(special_find) == 1:
            e = int(special_find[0][1], 8)
            f = int(int(special_find[0][2], 16) / e / e)
            g = int(int(special_find[0][3], 16) / e / e)
            if "a" == special_find[0][0] and g % 1000 == f:
                result["audio_url"] = "https://a%smp3.changba.com/userdata/userwork/%s/%g.mp3" % (e, f, g)
            else:
                result["audio_url"] = "https://aliuwmp3.changba.com/userdata/userwork/%s.mp3" % g
        else:
            raise crawler.CrawlerException("歌曲原始地址解密歌曲地址失败\n%s" % audio_source_url)
    else:  # 视频
        video_source_string = tool.find_sub_string(audio_play_response_content, "video_url: '", "',")
        if not video_source_string:
            raise crawler.CrawlerException("页面截取加密视频地址失败\n%s" % audio_play_response_content)
        try:
            video_url = base64.b64decode(video_source_string)
        except TypeError:
            raise crawler.CrawlerException("歌曲加密地址解密失败\n%s" % video_source_string)
        video_url = "https:" + video_url.decode()
        result["audio_url"] = video_url
    return result


class ChangBa(crawler.Crawler):
    def __init__(self):
        # 设置APP目录
        tool.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_VIDEO: True,
        }
        crawler.Crawler.__init__(self, sys_config)

        # 解析存档文件
        # account_id  last_audio_id
        self.account_list = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

    def main(self):
        # 循环下载每个id
        main_thread_count = threading.activeCount()
        for account_id in sorted(self.account_list.keys()):
            # 检查正在运行的线程数
            if threading.activeCount() >= self.thread_count + main_thread_count:
                self.wait_sub_thread()

            # 提前结束
            if not self.is_running():
                break

            # 开始下载
            thread = Download(self.account_list[account_id], self)
            thread.start()

            time.sleep(1)

        # 检查除主线程外的其他所有线程是不是全部结束了
        while threading.activeCount() > main_thread_count:
            self.wait_sub_thread()

        # 未完成的数据保存
        if len(self.account_list) > 0:
            tool.write_file(tool.list_to_string(list(self.account_list.values())), self.temp_save_data_path)

        # 重新排序保存存档文件
        crawler.rewrite_save_file(self.temp_save_data_path, self.save_data_path)

        log.step("全部下载完毕，耗时%s秒，共计歌曲%s首" % (self.get_run_time(), self.total_video_count))


class Download(crawler.DownloadThread):
    AUDIO_COUNT_PER_PAGE = 20  # 每页歌曲数量上限

    def __init__(self, account_info, main_thread):
        crawler.DownloadThread.__init__(self, account_info, main_thread)
        self.account_id = self.account_info[0]
        if len(self.account_info) >= 3 and self.account_info[2]:
            self.display_name = self.account_info[2]
        else:
            self.display_name = self.account_info[0]
        self.step("开始")

    # 获取所有可下载歌曲
    def get_crawl_list(self, user_id):
        page_count = 1
        unique_list = []
        audio_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的歌曲
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析第%s页歌曲" % page_count)

            # 获取一页歌曲
            try:
                audit_pagination_response = get_one_page_audio(user_id, page_count)
            except crawler.CrawlerException as e:
                self.error("第%s页歌曲解析失败，原因：%s" % (page_count, e.message))
                raise

            # 如果为空，表示已经取完了
            if len(audit_pagination_response["audio_info_list"]) == 0:
                break

            self.trace("第%s页解析的全部歌曲：%s" % (page_count, audit_pagination_response["audio_info_list"]))
            self.step("第%s页解析获取%s首歌曲" % (page_count, len(audit_pagination_response["audio_info_list"])))

            # 寻找这一页符合条件的歌曲
            for audio_info in audit_pagination_response["audio_info_list"]:
                # 检查是否达到存档记录
                if int(audio_info["audio_id"]) > int(self.account_info[1]):
                    # 新增歌曲导致的重复判断
                    if audio_info["audio_id"] in unique_list:
                        continue
                    else:
                        audio_info_list.append(audio_info)
                        unique_list.append(audio_info["audio_id"])
                else:
                    is_over = True
                    break

            if not is_over:
                # 获取的歌曲数量少于1页的上限，表示已经到结束了
                # 如果歌曲数量正好是页数上限的倍数，则由下一页获取是否为空判断
                if len(audit_pagination_response["audio_info_list"]) < self.AUDIO_COUNT_PER_PAGE:
                    is_over = True
                else:
                    page_count += 1

        return audio_info_list

    # 解析单首歌曲
    def crawl_audio(self, audio_info):
        self.main_thread_check()  # 检测主线程运行状态
        # 获取歌曲播放页
        try:
            audio_play_response = get_audio_play_page(audio_info["audio_key"])
        except crawler.CrawlerException as e:
            self.error("歌曲%s《%s》解析失败，原因：%s" % (audio_info["audio_key"], audio_info["audio_title"], e.message))
            raise

        if audio_play_response["is_delete"]:
            self.error("歌曲%s《%s》异常，跳过" % (audio_info["audio_key"], audio_info["audio_title"]))
            return

        self.main_thread_check()  # 检测主线程运行状态
        self.step("开始下载歌曲%s《%s》 %s" % (audio_info["audio_key"], audio_info["audio_title"], audio_play_response["audio_url"]))

        file_type = audio_play_response["audio_url"].split(".")[-1]
        file_path = os.path.join(self.main_thread.video_download_path, self.display_name, "%010d - %s.%s" % (int(audio_info["audio_id"]), path.filter_text(audio_info["audio_title"]), file_type))
        save_file_return = net.save_net_file(audio_play_response["audio_url"], file_path)
        if save_file_return["status"] == 1:
            self.step("歌曲%s《%s》下载成功" % (audio_info["audio_key"], audio_info["audio_title"]))
        else:
            self.error("歌曲%s《%s》 %s 下载失败，原因：%s" % (audio_info["audio_key"], audio_info["audio_title"], audio_play_response["audio_url"], crawler.download_failre(save_file_return["code"])))
            return

        # 歌曲下载完毕
        if save_file_return["status"] == 1:
            self.total_video_count += 1  # 计数累加
        self.account_info[1] = audio_info["audio_id"]  # 设置存档

    def run(self):
        try:
            # 查找账号user id
            try:
                account_index_response = get_account_index_page(self.account_id)
            except crawler.CrawlerException as e:
                self.error("主页解析失败，原因：%s" % e.message)
                raise

            # 获取所有可下载歌曲
            audio_info_list = self.get_crawl_list(account_index_response["user_id"])
            self.step("需要下载的全部歌曲解析完毕，共%s首" % len(audio_info_list))

            # 从最早的歌曲开始下载
            while len(audio_info_list) > 0:
                audio_info = audio_info_list.pop()
                self.step("开始解析歌曲%s《%s》" % (audio_info["audio_key"], audio_info["audio_title"]))
                self.crawl_audio(audio_info)
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
            tool.write_file("\t".join(self.account_info), self.main_thread.temp_save_data_path)
            self.main_thread.total_video_count += self.total_video_count
            self.main_thread.account_list.pop(self.account_id)
        self.step("下载完毕，总共获得%s首歌曲" % self.total_video_count)
        self.notify_main_thread()


if __name__ == "__main__":
    ChangBa().main()
