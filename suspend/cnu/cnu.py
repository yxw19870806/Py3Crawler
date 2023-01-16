# -*- coding:UTF-8  -*-
"""
CNU图片爬虫
http://www.cnu.cc/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from common import *


# 获取作品页面
def get_album_page(album_id):
    album_url = "http://www.cnu.cc/works/%s" % album_id
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

        self.album_id = 105000  # 初始值
        self.temp_path = ""  # 临时目录

    def _main(self):
        # 解析存档文件，获取上一次的album id
        if os.path.exists(self.save_data_path):
            file_save_info = file.read_file(self.save_data_path)
            if not tool.is_integer(file_save_info):
                log.error("存档内数据格式不正确")
                tool.process_exit()
            self.album_id = int(file_save_info)

        # http://www.cnu.cc/about/ 全部作品
        # todo 获取最新的作品id
        while True:
            if not self.is_running():
                tool.process_exit(tool.PROCESS_EXIT_CODE_NORMAL)
            log.step("开始解析第%s页作品" % self.album_id)

            # 获取作品
            try:
                album_response = get_album_page(self.album_id)
            except crawler.CrawlerException as e:
                log.error(e.http_error("作品%s" % self.album_id))
                raise

            if album_response["is_delete"]:
                log.step("作品%s已被删除，跳过" % self.album_id)
                self.album_id += 1
                continue

            log.trace("作品%s解析的全部图片：%s" % (self.album_id, album_response["photo_url_list"]))
            log.step("作品%s解析获取%s张图片" % (self.album_id, len(album_response["photo_url_list"])))

            photo_index = 1
            # 过滤标题中不支持的字符
            self.temp_path = album_path = os.path.join(self.photo_download_path, "%06d %s" % (self.album_id, path.filter_text(album_response["album_title"])))
            thread_list = []
            for photo_url in album_response["photo_url_list"]:
                if not self.is_running():
                    tool.process_exit(tool.PROCESS_EXIT_CODE_NORMAL)
                log.step("作品%s《%s》开始下载第%s张图片 %s" % (self.album_id, album_response["album_title"], photo_index, photo_url))

                # 开始下载
                file_path = os.path.join(album_path, "%03d.%s" % (photo_index, net.get_file_extension(photo_url)))
                thread = Download(self, file_path, photo_url, photo_index)
                thread.start()
                thread_list.append(thread)
                photo_index += 1

            # 等待所有线程下载完毕
            for thread in thread_list:
                thread.join()
                download_return = thread.get_result()
                if self.is_running() and download_return.status == net.Download.DOWNLOAD_FAILED:
                    log.error("作品%s《%s》 %s 第%s张图片 %s 下载失败，原因：%s" % (self.album_id, album_response["album_title"], album_response["album_url"], thread.photo_index, thread.photo_url, crawler.download_failre(download_return.code)))
            if self.is_running():
                log.step("作品%s《%s》全部图片下载完毕" % (self.album_id, album_response["album_title"]))
            else:
                tool.process_exit(tool.PROCESS_EXIT_CODE_NORMAL)

            # 作品内图片全部下载完毕
            self.temp_path = ""  # 临时目录设置清除
            self.total_photo_count += photo_index - 1  # 计数累加
            self.album_id += 1  # 设置存档记录

    def done(self):
        if self.temp_path:
            path.delete_dir_or_file(self.temp_path)

    def rewrite_save_file(self):
        # 重新保存存档文件
        file.write_file(str(self.album_id), self.save_data_path, file.WRITE_FILE_TYPE_REPLACE)


if __name__ == "__main__":
    CNU().main()
