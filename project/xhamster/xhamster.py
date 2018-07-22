# -*- coding:UTF-8  -*-
"""
xhamster视频爬虫
https://xhamster.com
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import traceback
from common import *


# 获取指定视频
def get_video_page(video_id):
    # https://www.youtube.com/watch?v=GCOSw4WSXqU
    video_play_url = "https://xhamster.com/videos/%s" % video_id
    # 强制使用英语
    video_play_response = net.http_request(video_play_url, method="GET")
    result = {
        "is_delete": False,  # 是否已被删除
        "is_skip": False,  # 是否跳过
        "video_title": "",  # 视频标题
        "video_url": None,  # 视频地址
    }
    if video_play_response.status == 404 or video_play_response.status == 410 or video_play_response.status == 423:
        result["is_delete"] = True
        return result
    if video_play_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_play_response.status))
    video_play_response_content = video_play_response.data.decode()
    video_info_html = tool.find_sub_string(video_play_response_content, "window.initials = ", ";\n")
    if not video_info_html:
        raise crawler.CrawlerException("页面截取视频信息失败\n%s" % video_play_response_content)
    video_info = tool.json_decode(video_info_html)
    if video_info is None:
        raise crawler.CrawlerException("视频信息加载失败\n%s" % video_info_html)
    # 判断是否需要跳过
    if not crawler.check_sub_key(("orientation",), video_info):
        raise crawler.CrawlerException("视频列表信息'orientation'字段不存在\n%s" % video_info)
    if video_info["orientation"] == "gay":
        result["is_skip"] = True
        return result
    if not crawler.check_sub_key(("videoModel",), video_info):
        raise crawler.CrawlerException("视频列表信息'videoModel'字段不存在\n%s" % video_info)
    # 获取视频标题
    if not crawler.check_sub_key(("title",), video_info["videoModel"]):
        raise crawler.CrawlerException("视频列表信息'title'字段不存在\n%s" % video_info["videoModel"])
    result["video_title"] = video_info["videoModel"]["title"]
    # 获取视频下载地址
    if not crawler.check_sub_key(("sources",), video_info["videoModel"]):
        raise crawler.CrawlerException("视频列表信息'sources'字段不存在\n%s" % video_info["videoModel"])
    if not crawler.check_sub_key(("mp4",), video_info["videoModel"]["sources"]):
        raise crawler.CrawlerException("视频列表信息'mp4'字段不存在\n%s" % video_info["videoModel"]["sources"])
    max_resolution = 0
    for resolution_string in video_info["videoModel"]["sources"]["mp4"]:
        resolution = resolution_string.replace("p", "")
        if not crawler.is_integer(resolution):
            raise crawler.CrawlerException("视频信息分辨率字段类型不正确\n%s" % resolution_string)
        resolution = int(resolution)
        if resolution not in [240, 480, 720]:
            log.error("新的分辨率: %s" % video_info["videoModel"]["sources"]["mp4"])
        if resolution > max_resolution:
            result["video_url"] = video_info["videoModel"]["sources"]["mp4"][resolution_string]
            max_resolution = resolution
    return result


class Xhamster(crawler.Crawler):
    def __init__(self):
        # 设置APP目录
        tool.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_VIDEO: True,
            crawler.SYS_SET_PROXY: True,
            crawler.SYS_NOT_CHECK_SAVE_DATA: True,
        }
        crawler.Crawler.__init__(self, sys_config)


    def main(self):
        # 解析存档文件，获取上一次的album id
        video_id = 1
        if os.path.exists(self.save_data_path):
            file_save_info = tool.read_file(self.save_data_path)
            if not crawler.is_integer(file_save_info):
                log.error("存档内数据格式不正确")
                tool.process_exit()
            video_id = int(file_save_info)
        temp_path = ""

        try:
            while video_id:
                if not self.is_running():
                    tool.process_exit(0)
                log.step("开始解析视频%s" % video_id)

                # 获取相册
                try:
                    video_play_response = get_video_page(video_id)
                except crawler.CrawlerException as e:
                    log.error("视频%s解析失败，原因：%s" % (video_id, e.message))
                    raise

                if video_play_response["is_delete"]:
                    log.step("视频%s已删除，跳过" % video_id)
                    video_id += 1
                    continue

                if video_play_response["is_skip"]:
                    log.error("视频%s已过滤，跳过" % video_id)
                    video_id += 1
                    continue

                log.step("开始下载视频%s 《%s》 %s" % (video_id, video_play_response["video_title"], video_play_response["video_url"]))

                video_title = path.filter_text(video_play_response["video_title"])
                file_path = os.path.join(self.video_download_path, "%08d %s.mp4" % (video_id, video_title))
                save_file_return = net.save_net_file(video_play_response["video_url"], file_path)
                if save_file_return["status"] == 1:
                    log.step("视频%s 下载成功" % video_id)
                else:
                    log.error("视频%s %s 下载失败，原因：%s" % (video_id, video_play_response["video_url"], crawler.download_failre(save_file_return["code"])))

                self.total_video_count += 1  # 计数累加
                video_id += 1  # 设置存档记录
        except SystemExit as se:
            if se.code == 0:
                log.step("提前退出")
            else:
                log.error("异常退出")
            # 如果临时目录变量不为空，表示某个图集正在下载中，需要把下载了部分的内容给清理掉
            if temp_path:
                path.delete_dir_or_file(temp_path)
        except Exception as e:
            log.error("未知异常")
            log.error(str(e) + "\n" + traceback.format_exc())

        # 重新保存存档文件
        tool.write_file(str(video_id), self.save_data_path, tool.WRITE_FILE_TYPE_REPLACE)
        log.step("全部下载完毕，耗时%s秒，共计视频%s个" % (self.get_run_time(), self.total_video_count))


if __name__ == "__main__":
    Xhamster().main()
