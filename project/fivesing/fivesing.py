# -*- coding:UTF-8  -*-
"""
5sing歌曲爬虫
http://5sing.kugou.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import re
import time
import traceback
from common import *


# 获取指定页数的全部歌曲
# page_type 页面类型：yc - 原唱、fc - 翻唱
def get_one_page_audio(account_id, page_type, page_count):
    # http://5sing.kugou.com/inory/yc/1.html
    audio_pagination_url = "http://5sing.kugou.com/%s/%s/%s.html" % (account_id, page_type, page_count)
    audio_pagination_response = net.request(audio_pagination_url, method="GET")
    result = {
        "audio_info_list": [],  # 全部歌曲信息
    }
    if audio_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(audio_pagination_response.status))
    audio_pagination_response_content = audio_pagination_response.data.decode(errors="ignore")
    if audio_pagination_response_content.find("var OwnerNickName = '';") >= 0:
        raise crawler.CrawlerException("账号不存在")
    # 获取歌曲信息
    # 单首歌曲信息的格式：[歌曲id，歌曲标题]
    audio_info_list = re.findall('<a href="http://5sing.kugou.com/' + page_type + '/([\d]*).html" [\s|\S]*? title="([^"]*)">', audio_pagination_response_content)
    for audio_info in audio_info_list:
        result_audio_info = {
            "audio_id": int(audio_info[0]),
            "audio_title": audio_info[1],
        }
        result["audio_info_list"].append(result_audio_info)
    return result


# 获取指定id的歌曲播放页
def get_audio_play_page(audio_id, song_type):
    audio_info_url = "http://service.5sing.kugou.com/song/getsongurl"
    query_data = {
        "songid": audio_id,
        "songtype": song_type,
    }
    audio_info_response = net.request(audio_info_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "audio_title": "",  # 歌曲标题
        "audio_url": None,  # 歌曲地址
        "is_delete": False,  # 是否已删除
    }
    if audio_info_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(audio_info_response.status))
    if crawler.get_json_value(audio_info_response.json_data, "success", type_check=bool) is False:
        if crawler.get_json_value(audio_info_response.json_data, "message", type_check=str) in ["该歌曲已下架", "歌曲不存在"]:
            result["is_delete"] = True
            return result
    response_data = crawler.get_json_value(audio_info_response.json_data, "data", type_check=dict)
    # 获取歌曲地址
    if crawler.check_sub_key(("squrl",), response_data) and response_data["squrl"]:
        result["audio_url"] = response_data["squrl"]
    elif crawler.check_sub_key(("lqurl",), response_data) and response_data["lqurl"]:
        result["audio_url"] = response_data["lqurl"]
    elif crawler.check_sub_key(("hqurl",), response_data) and response_data["hqurl"]:
        result["audio_url"] = response_data["hqurl"]
    else:
        raise crawler.CrawlerException("歌曲信息'squrl'、'lqurl'、'hqurl'字段都不存在\n%s" % audio_info_response.json_data)
    # 获取歌曲标题
    if not crawler.check_sub_key(("songName",), audio_info_response.json_data["data"]):
        raise crawler.CrawlerException("歌曲信息'songName'字段不存在\n%s" % audio_info_response.json_data)
    result["audio_title"] = audio_info_response.json_data["data"]["songName"]
    return result


class FiveSing(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_AUDIO: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 解析存档文件
        # account_id  last_yc_audio_id  last_fc_audio_id
        self.account_list = crawler.read_save_data(self.save_data_path, 0, ["", "0", "0"])

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

        log.step("全部下载完毕，耗时%s秒，共计歌曲%s首" % (self.get_run_time(), self.total_audio_count))


class Download(crawler.DownloadThread):
    EACH_PAGE_AUDIO_COUNT = 20  # 每页歌曲数量上限（请求数量是无法修改的，只做判断使用）
    AUDIO_TYPE_YC = "yc"  # 歌曲类型：原唱
    AUDIO_TYPE_FC = "fc"  # 歌曲类型：翻唱
    # 原创、翻唱
    audio_type_to_index_dict = {AUDIO_TYPE_YC: 1, AUDIO_TYPE_FC: 2}  # 存档文件里的下标
    audio_type_name_dict = {AUDIO_TYPE_YC: "原唱", AUDIO_TYPE_FC: "翻唱"}  # 显示名字

    def __init__(self, account_info, main_thread):
        crawler.DownloadThread.__init__(self, account_info, main_thread)
        self.account_id = self.account_info[0]
        if len(self.account_info) >= 4 and self.account_info[3]:
            self.display_name = self.account_info[3]
        else:
            self.display_name = self.account_info[0]
        self.step("开始")

    # 获取所有可下载歌曲
    def get_crawl_list(self, audio_type):
        audio_type_index = self.audio_type_to_index_dict[audio_type]
        audio_type_name = self.audio_type_name_dict[audio_type]

        page_count = 1
        unique_list = []
        audio_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的歌曲
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析第%s页%s歌曲" % (page_count, audio_type_name))

            # 获取一页歌曲
            try:
                audio_pagination_response = get_one_page_audio(self.account_id, audio_type, page_count)
            except crawler.CrawlerException as e:
                self.error("第%s页%s歌曲解析失败，原因：%s" % (page_count, audio_type_name, e.message))
                break

            self.trace("第%s页%s解析的全部歌曲：%s" % (page_count, audio_type_name, audio_pagination_response["audio_info_list"]))
            self.step("第%s页%s解析获取%s首歌曲" % (page_count, audio_type_name, len(audio_pagination_response["audio_info_list"])))

            # 寻找这一页符合条件的歌曲
            for audio_info in audio_pagination_response["audio_info_list"]:
                # 检查是否达到存档记录
                if audio_info["audio_id"] > int(self.account_info[audio_type_index]):
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
                if len(audio_pagination_response["audio_info_list"]) < self.EACH_PAGE_AUDIO_COUNT:
                    is_over = True
                else:
                    page_count += 1

        return audio_info_list

    # 解析单首歌曲
    def crawl_audio(self, audio_type, audio_info):
        audio_type_name = self.audio_type_name_dict[audio_type]
        self.step("开始解析%s歌曲%s《%s》" % (audio_type_name, audio_info["audio_id"], audio_info["audio_title"]))

        # 获取歌曲的详情页
        try:
            audio_info_response = get_audio_play_page(audio_info["audio_id"], audio_type)
        except crawler.CrawlerException as e:
            self.error("%s歌曲%s《%s》解析失败，原因：%s" % (audio_type_name, audio_info["audio_id"], audio_info["audio_title"], e.message))
            return

        self.step("开始下载%s歌曲%s《%s》 %s" % (audio_type_name, audio_info["audio_id"], audio_info["audio_title"], audio_info_response["audio_url"]))

        file_path = os.path.join(self.main_thread.audio_download_path, self.display_name, audio_type_name, "%08d - %s.%s" % (audio_info["audio_id"], path.filter_text(audio_info["audio_title"]), net.get_file_type(audio_info_response["audio_url"])))
        save_file_return = net.save_net_file(audio_info_response["audio_url"], file_path)
        if save_file_return["status"] == 1:
            self.total_audio_count += 1  # 计数累加
            self.step("%s歌曲%s《%s》下载成功" % (audio_type_name, audio_info["audio_id"], audio_info["audio_title"]))
        else:
            self.error("%s歌曲%s《%s》 %s 下载失败，原因：%s" % (audio_type_name, audio_info["audio_id"], audio_info["audio_title"], audio_info_response["audio_url"], crawler.download_failre(save_file_return["code"])))
            self.check_thread_exit_after_download_failure()

        # 歌曲下载完毕
        self.account_info[self.audio_type_to_index_dict[audio_type]] = str(audio_info["audio_id"])  # 设置存档记录

    def run(self):
        try:
            for audio_type in list(self.audio_type_to_index_dict.keys()):
                # 获取所有可下载歌曲
                audio_info_list = self.get_crawl_list(audio_type)
                self.step("需要下载的全部%s歌曲解析完毕，共%s首" % (self.audio_type_name_dict[audio_type], len(audio_info_list)))

                # 从最早的歌曲开始下载
                while len(audio_info_list) > 0:
                    self.crawl_audio(audio_type, audio_info_list.pop())
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
            self.main_thread.total_audio_count += self.total_audio_count
            self.main_thread.account_list.pop(self.account_id)
        self.step("下载完毕，总共获得%s首歌曲" % self.total_audio_count)
        self.notify_main_thread()


if __name__ == "__main__":
    FiveSing().main()
