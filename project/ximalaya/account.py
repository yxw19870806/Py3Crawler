# -*- coding:UTF-8  -*-
"""
喜马拉雅主播音频爬虫
https://www.ximalaya.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import time
import traceback
from common import *
from project.ximalaya import ximalaya


class XiMaLaYaAccount(ximalaya.XiMaLaYa):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_NOT_CHECK_SAVE_DATA: False,
            crawler.SYS_APP_CONFIG_PATH: os.path.join(crawler.PROJECT_APP_PATH, "account.ini"),
        }
        ximalaya.XiMaLaYa.__init__(self, sys_config, **kwargs)

        # 解析存档文件
        # account_id  last_audio_id
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

    def main(self):
        try:
            # 循环下载每个id
            thread_list = []
            for account_id in sorted(self.save_data.keys()):
                # 提前结束
                if not self.is_running():
                    break

                # 开始下载
                thread = Download(self.save_data[account_id], self)
                thread.start()
                thread_list.append(thread)

                time.sleep(1)

            # 等待子线程全部完成
            while len(thread_list) > 0:
                thread_list.pop().join()
        except KeyboardInterrupt:
            self.stop_process()

        # 未完成的数据保存
        if len(self.save_data) > 0:
            file.write_file(tool.list_to_string(list(self.save_data.values())), self.temp_save_data_path)

        # 重新排序保存存档文件
        self.rewrite_save_file()

        log.step("全部下载完毕，耗时%s秒，共计音频%s首" % (self.get_run_time(), self.total_audio_count))


class Download(crawler.DownloadThread):
    def __init__(self, single_save_data, main_thread):
        crawler.DownloadThread.__init__(self, single_save_data, main_thread)
        self.account_id = self.single_save_data[0]
        if len(self.single_save_data) >= 3 and self.single_save_data[2]:
            self.display_name = self.single_save_data[2]
        else:
            self.display_name = self.single_save_data[0]
        self.total_audio_count = 0
        self.step("开始")

    # 获取所有可下载音频
    def get_crawl_list(self):
        page_count = 1
        unique_list = []
        audio_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的音频
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析第%s页音频" % page_count)

            # 获取一页音频
            try:
                audit_pagination_response = ximalaya.get_one_page_audio(self.account_id, page_count)
            except crawler.CrawlerException as e:
                self.error("第%s页音频解析失败，原因：%s" % (page_count, e.message))
                break

            self.trace("第%s页解析的全部音频：%s" % (page_count, audit_pagination_response["audio_info_list"]))
            self.step("第%s页解析获取%s首音频" % (page_count, len(audit_pagination_response["audio_info_list"])))

            # 寻找这一页符合条件的媒体
            for audio_info in audit_pagination_response["audio_info_list"]:
                # 检查是否达到存档记录
                if audio_info["audio_id"] > int(self.single_save_data[1]):
                    # 新增音频导致的重复判断
                    if audio_info["audio_id"] in unique_list:
                        continue
                    else:
                        audio_info_list.append(audio_info)
                        unique_list.append(audio_info["audio_id"])
                else:
                    is_over = True
                    break

            if not is_over:
                if audit_pagination_response["is_over"]:
                    is_over = True
                else:
                    page_count += 1

        return audio_info_list

    # 解析单首音频
    def crawl_audio(self, audio_info):
        self.step("开始解析音频%s" % audio_info["audio_id"])

        # 获取音频播放页
        try:
            audio_play_response = ximalaya.get_audio_info_page(audio_info["audio_id"])
        except crawler.CrawlerException as e:
            self.error("音频%s解析失败，原因：%s" % (audio_info["audio_id"], e.message))
            return

        if audio_play_response["is_delete"]:
            self.error("音频%s不存在" % audio_info["audio_id"])
            return

        audio_url = audio_play_response["audio_url"]
        self.step("开始下载音频%s《%s》 %s" % (audio_info["audio_id"], audio_info["audio_title"], audio_url))

        file_path = os.path.join(self.main_thread.audio_download_path, self.display_name, "%09d - %s.%s" % (audio_info["audio_id"], path.filter_text(audio_info["audio_title"]), net.get_file_type(audio_url)))
        save_file_return = net.download(audio_url, file_path)
        if save_file_return["status"] == 1:
            self.total_audio_count += 1  # 计数累加
            self.step("音频%s《%s》下载成功" % (audio_info["audio_id"], audio_info["audio_title"]))
        else:
            self.error("音频%s《%s》 %s 下载失败，原因：%s" % (audio_info["audio_id"], audio_info["audio_title"], audio_url, crawler.download_failre(save_file_return["code"])))
            self.check_thread_exit_after_download_failure()

        # 音频下载完毕
        self.single_save_data[1] = str(audio_info["audio_id"])  # 设置存档记录

    def run(self):
        try:
            # 获取所有可下载音频
            audio_info_list = self.get_crawl_list()
            self.step("需要下载的全部音频解析完毕，共%s个" % len(audio_info_list))

            # 从最早的媒体开始下载
            while len(audio_info_list) > 0:
                self.crawl_audio(audio_info_list.pop())
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
            file.write_file("\t".join(self.single_save_data), self.main_thread.temp_save_data_path)
            self.main_thread.total_audio_count += self.total_audio_count
            self.main_thread.save_data.pop(self.account_id)
        self.step("下载完毕，总共获得%s首音频" % self.total_audio_count)
        self.notify_main_thread()


if __name__ == "__main__":
    XiMaLaYaAccount().main()
