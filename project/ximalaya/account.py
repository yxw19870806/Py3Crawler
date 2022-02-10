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
        self.write_remaining_save_data()

        # 重新排序保存存档文件
        self.rewrite_save_file()

        self.end_message()


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
            self.step(f"开始解析第{page_count}页音频")

            # 获取一页音频
            try:
                audit_pagination_response = ximalaya.get_one_page_audio(self.account_id, page_count)
            except crawler.CrawlerException as e:
                self.error(e.http_error(f"第{page_count}页音频"))
                raise

            self.trace(f"第{page_count}页解析的全部音频：{audit_pagination_response['audio_info_list']}")
            self.step(f"第{page_count}页解析获取{len(audit_pagination_response['audio_info_list'])}首音频")

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
        self.step(f"开始解析音频{audio_info['audio_id']}")

        # 获取音频播放页
        try:
            audio_play_response = ximalaya.get_audio_info_page(audio_info["audio_id"])
        except crawler.CrawlerException as e:
            self.error(e.http_error(f"音频{audio_info['audio_id']}"))
            raise

        if audio_play_response["is_delete"]:
            self.error(f"音频{audio_info['audio_id']}不存在")
            raise

        audio_url = audio_play_response["audio_url"]
        self.step(f"开始下载音频{audio_info['audio_id']}《{audio_info['audio_title']}》 {audio_url}")

        file_path = os.path.join(self.main_thread.audio_download_path, self.display_name, f"%09d - {path.filter_text(audio_info['audio_title'])}.{net.get_file_extension(audio_url)}" % audio_info["audio_id"])
        save_file_return = net.download(audio_url, file_path)
        if save_file_return["status"] == 1:
            self.total_audio_count += 1  # 计数累加
            self.step(f"音频{audio_info['audio_id']}《{audio_info['audio_title']}》下载成功")
        else:
            self.error(f"音频{audio_info['audio_id']}《{audio_info['audio_title']}》 {audio_url} 下载失败，原因：{crawler.download_failre(save_file_return['code'])}")
            self.check_download_failure_exit()

        # 音频下载完毕
        self.single_save_data[1] = str(audio_info["audio_id"])  # 设置存档记录

    def run(self):
        try:
            # 获取所有可下载音频
            audio_info_list = self.get_crawl_list()
            self.step(f"需要下载的全部音频解析完毕，共{len(audio_info_list)}个")

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

        self.main_thread.save_data.pop(self.account_id)
        self.done()


if __name__ == "__main__":
    XiMaLaYaAccount().main()
