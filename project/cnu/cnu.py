# -*- coding:UTF-8  -*-
"""
CNU图片爬虫
http://www.cnu.cc/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import traceback
from common import *


# 获取作品页面
def get_album_page(album_id):
    album_url = f"http://www.cnu.cc/works/{album_id}"
    album_response = net.request(album_url, method="GET")
    result = {
        "album_title": "",  # 作品标题
        "photo_url_list": [],  # 全部图片地址
        "is_delete": False,  # 是否已删除
    }
    if album_response.status == 404:
        result["is_delete"] = True
        return result
    elif album_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_response.status))
    album_response_content = album_response.data.decode(errors="ignore")
    # 获取作品标题
    album_title = tool.find_sub_string(album_response_content, '<h2 class="work-title">', "</h2>")
    if not album_title:
        raise crawler.CrawlerException("页面截取作品标题失败\n" + album_response_content)
    result["album_title"] = album_title
    # 获取图片地址
    script_json_html = tool.find_sub_string(album_response_content, '<div id="imgs_json" style="display:none">', "</div>")
    if not script_json_html:
        raise crawler.CrawlerException("页面截取图片列表失败\n" + album_response_content)
    script_json = tool.json_decode(script_json_html)
    if script_json is None:
        raise crawler.CrawlerException("图片列表加载失败\n" + script_json_html)
    photo_url_list = []
    for photo_info in script_json:
        photo_url_list.append("http://img.cnu.cc/uploads/images/920/" + crawler.get_json_value(photo_info, "img", type_check=str))
    result["photo_url_list"] = photo_url_list
    return result


class CNU(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_NOT_CHECK_SAVE_DATA: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

    def main(self):
        # 解析存档文件，获取上一次的album id
        album_id = 105000
        if os.path.exists(self.save_data_path):
            file_save_info = file.read_file(self.save_data_path)
            if not tool.is_integer(file_save_info):
                log.error("存档内数据格式不正确")
                tool.process_exit()
            album_id = int(file_save_info)
        temp_path = ""

        try:
            # http://www.cnu.cc/about/ 全部作品
            # todo 获取最新的作品id
            while True:
                if not self.is_running():
                    tool.process_exit(tool.PROCESS_EXIT_CODE_NORMAL)
                log.step(f"开始解析第{album_id}页作品")

                # 获取作品
                try:
                    album_response = get_album_page(album_id)
                except crawler.CrawlerException as e:
                    log.error(e.http_error(f"作品{album_id}"))
                    raise

                if album_response["is_delete"]:
                    log.step(f"作品{album_id}已被删除，跳过")
                    album_id += 1
                    continue

                log.trace(f"作品{album_id}解析的全部图片：{album_response['photo_url_list']}")
                log.step(f"作品{album_id}解析获取{len(album_response['photo_url_list'])}张图片")

                photo_index = 1
                # 过滤标题中不支持的字符
                temp_path = album_path = os.path.join(self.photo_download_path, f"%06d {path.filter_text(album_response['album_title'])}" % album_id)
                thread_list = []
                for photo_url in album_response["photo_url_list"]:
                    if not self.is_running():
                        tool.process_exit(tool.PROCESS_EXIT_CODE_NORMAL)
                    log.step(f"作品{album_id}《{album_response['album_title']}》开始下载第{photo_index}张图片 {photo_url}")

                    # 开始下载
                    file_path = os.path.join(album_path, f"%03d.{net.get_file_extension(photo_url)}" % photo_index)
                    thread = Download(self, file_path, photo_url, photo_index)
                    thread.start()
                    thread_list.append(thread)
                    photo_index += 1

                # 等待所有线程下载完毕
                for thread in thread_list:
                    thread.join()
                    download_return = thread.get_result()
                    if self.is_running() and download_return.status == net.Download.DOWNLOAD_FAILED:
                        log.error(f"作品{album_id}《{album_response['album_title']}》 {album_response['album_url']} 第{thread.photo_index}张图片 {thread.photo_url} 下载失败，原因：{crawler.download_failre(download_return.code)}")
                if self.is_running():
                    log.step(f"作品{album_id}《{album_response['album_title']}》全部图片下载完毕")
                else:
                    tool.process_exit(tool.PROCESS_EXIT_CODE_NORMAL)

                # 作品内图片全部下载完毕
                temp_path = ""  # 临时目录设置清除
                self.total_photo_count += photo_index - 1  # 计数累加
                album_id += 1  # 设置存档记录
        except (SystemExit, KeyboardInterrupt) as e:
            if isinstance(e, SystemExit) and e.code == 1:
                log.error("异常退出")
            else:
                log.step("提前退出")
            # 如果临时目录变量不为空，表示某个作品正在下载中，需要把下载了部分的内容给清理掉
            if temp_path:
                path.delete_dir_or_file(temp_path)
        except Exception as e:
            log.error("未知异常")
            log.error(str(e) + "\n" + traceback.format_exc())

        # 重新保存存档文件
        file.write_file(str(album_id), self.save_data_path, file.WRITE_FILE_TYPE_REPLACE)

        self.end_message()


class Download(crawler.DownloadThread):
    def __init__(self, main_thread, file_path, photo_url, photo_index):
        crawler.DownloadThread.__init__(self, [], main_thread)
        self.file_path = file_path
        self.photo_url = photo_url
        self.photo_index = photo_index
        self.result = None

    def run(self):
        self.result = net.Download(self.photo_url, self.file_path)
        self.notify_main_thread()

    def get_result(self):
        return self.result


if __name__ == "__main__":
    CNU().main()
