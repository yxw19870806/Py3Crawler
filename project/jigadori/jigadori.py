# -*- coding:UTF-8  -*-
"""
グラドル自画撮り部 图片爬虫
http://jigadori.fkoji.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import time
import traceback
from pyquery import PyQuery as pq
from common import *

EACH_LOOP_MAX_PAGE_COUNT = 50  # 单次缓存多少页的图片


# 获取指定页数的全部图片
def get_one_page_photo(page_count):
    photo_pagination_url = "http://jigadori.fkoji.com/"
    query_data = {"p": page_count}
    photo_pagination_response = net.request(photo_pagination_url, method="GET", fields=query_data)
    result = {
        "photo_info_list": [],  # 全部图片信息
    }
    if photo_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(photo_pagination_response.status))
    tweet_list_selector = pq(photo_pagination_response.data.decode(errors="ignore")).find("#wrapper .row .photo")
    for tweet_index in range(0, tweet_list_selector.length):
        tweet_selector = tweet_list_selector.eq(tweet_index)
        result_photo_info = {
            "account_name": "",  # twitter账号
            "photo_url_list": [],  # 图片地址
            "tweet_id": None,  # tweet id
            "tweet_time": None,  # tweet发布时间
        }
        # 获取tweet id
        tweet_url = tweet_selector.find(".photo-link-outer a").attr("href")
        if not tweet_url:
            raise crawler.CrawlerException("图片信息截取tweet地址失败\n" + tweet_selector.html())
        tweet_id = tool.find_sub_string(tweet_url.strip(), "status/")
        if not tool.is_integer(tweet_id):
            raise crawler.CrawlerException(f"tweet地址{tweet_url}截取tweet id失败")
        result_photo_info["tweet_id"] = int(tweet_id)
        # 获取twitter账号
        account_name = tweet_selector.find(".user-info .user-name .screen-name").text()
        if not account_name:
            raise crawler.CrawlerException("图片信息截取twitter账号失败\n" + tweet_selector.html())
        result_photo_info["account_name"] = account_name.strip().replace("@", "")
        # 获取tweet发布时间
        tweet_time = tweet_selector.find(".tweet-text .tweet-created-at").text().strip()
        if not tweet_time:
            raise crawler.CrawlerException("图片信息截取tweet发布时间失败\n" + tweet_selector.html())
        try:
            result_photo_info["tweet_time"] = int(time.mktime(time.strptime(tweet_time.strip(), "%Y-%m-%d %H:%M:%S")))
        except ValueError:
            raise crawler.CrawlerException(f"tweet发布时间{tweet_time}的格式不正确")
        # 获取图片地址
        photo_list_selector = tweet_selector.find(".photo-link-outer a img")
        for photo_index in range(0, photo_list_selector.length):
            photo_url = photo_list_selector.eq(photo_index).attr("src")
            if not photo_url:
                raise crawler.CrawlerException("图片列表截取图片地址失败" + photo_list_selector.eq(photo_index).html())
            result_photo_info["photo_url_list"].append(photo_url.strip())
        result["photo_info_list"].append(result_photo_info)
    return result


class Jigadori(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_SET_PROXY: True,
            crawler.SYS_NOT_CHECK_SAVE_DATA: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        self.unique_list = []
        self.last_tweet_id = 0
        self.temp_path_list = []

    # 获取偏移量，避免一次查询过多页数
    def get_offset_page_count(self):
        start_page_count = 1
        while EACH_LOOP_MAX_PAGE_COUNT > 0:
            if not self.is_running():
                tool.process_exit(tool.PROCESS_EXIT_CODE_NORMAL)

            start_page_count += EACH_LOOP_MAX_PAGE_COUNT
            try:
                photo_pagination_response = get_one_page_photo(start_page_count)
            except crawler.CrawlerException as e:
                log.error(e.http_error(f"第{start_page_count}页图片"))
                raise

            # 这页没有任何内容，返回上一个检查节点
            if len(photo_pagination_response["photo_info_list"]) == 0:
                start_page_count -= EACH_LOOP_MAX_PAGE_COUNT
                break

            # 这页已经匹配到存档点，返回上一个节点
            if photo_pagination_response["photo_info_list"][-1]["tweet_id"] < self.last_tweet_id:
                start_page_count -= EACH_LOOP_MAX_PAGE_COUNT
                break

            log.step(f"前{start_page_count}页图片全部符合条件，跳过{EACH_LOOP_MAX_PAGE_COUNT}页后继续查询")
        return start_page_count

    # 获取所有可下载图片
    def get_crawl_list(self, page_count):
        photo_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的图片
        while not is_over:
            if not self.is_running():
                tool.process_exit(tool.PROCESS_EXIT_CODE_NORMAL)
            log.step(f"开始解析第{page_count}页图片")

            # 获取一页图片
            try:
                photo_pagination_response = get_one_page_photo(page_count)
            except crawler.CrawlerException as e:
                log.error(e.http_error(f"第{page_count}页图片"))
                raise

            log.trace(f"第{page_count}页解析的全部图片：{photo_pagination_response['photo_info_list']}")
            log.step(f"第{page_count}页解析获取{len(photo_pagination_response['photo_info_list'])}张图片")

            # 已经没有图片了
            if len(photo_pagination_response["photo_info_list"]) == 0:
                break

            # 寻找这一页符合条件的图片
            for photo_info in photo_pagination_response["photo_info_list"]:
                # 检查是否达到存档记录
                if photo_info["tweet_id"] > self.last_tweet_id:
                    # 新增图片导致的重复判断
                    if photo_info["tweet_id"] in self.unique_list:
                        continue
                    else:
                        photo_info_list.append(photo_info)
                        self.unique_list.append(photo_info["tweet_id"])
                else:
                    is_over = True
                    break

            if not is_over:
                page_count += 1
        return photo_info_list

    # 解析单个tweet下的图片
    def crawl_photo(self, photo_info):
        log.step(f"开始解析tweet {photo_info['tweet_id']}的图片")

        photo_index = 1
        for photo_url in photo_info["photo_url_list"]:
            log.step(f"开始下载tweet {photo_info['tweet_id']}的第{photo_index}张图片 {photo_url}")

            file_path = os.path.join(self.photo_download_path, photo_info["account_name"], f"%019d_%02d.{net.get_file_extension(photo_url, 'jpg')}" % (photo_info["tweet_id"], photo_index))
            save_file_return = net.download(photo_url, file_path)
            if save_file_return["status"] == 1:
                self.temp_path_list.append(file_path)  # 设置临时目录
                self.total_photo_count += 1  # 计数累加
                log.step(f"tweet {photo_info['tweet_id']}的第{photo_index}张图片下载成功")
            else:
                log.error(f"tweet {photo_info['tweet_id']}的第{photo_index}张图片（account：{photo_info['account_name']}) {photo_url}，下载失败，原因：{crawler.download_failre(save_file_return['code'])}")
                if self.is_thread_exit_after_download_failure:
                    tool.process_exit(tool.PROCESS_EXIT_CODE_NORMAL)
            photo_index += 1

        # tweet内图片全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.last_tweet_id = photo_info["tweet_id"]  # 设置存档记录

    def main(self):
        # 解析存档文件，获取上一次的tweet id
        if os.path.exists(self.save_data_path):
            file_save_info = file.read_file(self.save_data_path)
            if not tool.is_integer(file_save_info):
                log.error("存档内数据格式不正确")
                tool.process_exit()
            self.last_tweet_id = int(file_save_info)

        try:
            # 查询当前任务大致需要从多少页开始爬取
            start_page_count = self.get_offset_page_count()

            while start_page_count >= 1:
                photo_info_list = self.get_crawl_list(start_page_count)
                log.step(f"需要下载的全部图片解析完毕，共{len(photo_info_list)}个")

                # 从最早的图片开始下载
                while len(photo_info_list) > 0:
                    self.crawl_photo(photo_info_list.pop())
                    if not self.is_running():
                        tool.process_exit(tool.PROCESS_EXIT_CODE_NORMAL)

                start_page_count -= EACH_LOOP_MAX_PAGE_COUNT
        except (SystemExit, KeyboardInterrupt) as e:
            if isinstance(e, SystemExit) and e.code == 1:
                log.error("异常退出")
            else:
                log.step("提前退出")
            # 如果临时目录变量不为空，表示某个日志正在下载中，需要把下载了部分的内容给清理掉
            if len(self.temp_path_list) > 0:
                for temp_path in self.temp_path_list:
                    path.delete_dir_or_file(temp_path)
        except Exception as e:
            log.error("未知异常")
            log.error(str(e) + "\n" + traceback.format_exc())

        # 保存新的存档文件
        file.write_file(str(self.last_tweet_id), self.save_data_path, file.WRITE_FILE_TYPE_REPLACE)

        self.end_message()


if __name__ == "__main__":
    Jigadori().main()
