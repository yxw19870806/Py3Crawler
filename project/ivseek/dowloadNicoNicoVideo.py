# -*- coding:UTF-8  -*-
"""
ivseek已解析文件中下载全部nico nico视频
http://www.ivseek.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from common import *
from project.ivseek import ivseek
from suspend.niconico import niconico

NICONICO_VIDEO_DOWNLOAD_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "niconico_video"))


def main():
    # 初始化类
    niconico.NicoNico()
    ivseek_class = ivseek.IvSeek()

    save_data_list = ivseek.read_save_data(ivseek_class.save_data_path)
    for single_save_list in save_data_list:
        if single_save_list[2].find(".nicovideo.jp/") == -1:
            continue

        # 已完成
        if single_save_list[4] == ivseek.DONE_SING:
            continue

        output.print_msg(f"开始解析视频{single_save_list[2]}")
        video_id = single_save_list[2].split("/")[-1].replace("sm", "")
        if not tool.is_integer(video_id):
            output.print_msg(f"视频 {single_save_list[2]} 截取video id失败")
            continue

        try:
            video_info_response = niconico.get_video_info(video_id)
        except crawler.CrawlerException as e:
            log.error(e.http_error(f"视频{single_save_list[2]}"))
            continue

        if video_info_response["is_delete"]:
            continue

        output.print_msg(f"开始下载视频{video_id} 《{video_info_response['video_title']}》 {video_info_response['video_url']}")
        file_path = os.path.join(NICONICO_VIDEO_DOWNLOAD_PATH, f"%08d - {path.filter_text(video_info_response['video_title'])}.mp4" % int(video_id))
        cookies_list = niconico.COOKIE_INFO
        if video_info_response["extra_cookie"]:
            cookies_list.update(video_info_response["extra_cookie"])
        download_return = net.Download(video_info_response["video_url"], file_path, cookies_list=cookies_list)
        if download_return.status == net.Download.DOWNLOAD_SUCCEED:
            output.print_msg(f"视频{video_id} 《{video_info_response['video_title']}》下载成功")
        else:
            log.error(f"视频{video_id} 《{video_info_response['video_title']}》 {video_info_response['video_url']} 下载失败，原因：{crawler.download_failre(download_return.code)}")
            continue

        # 增加已处理标记
        single_save_list[4] = ivseek.DONE_SING
        # 保存记录
        file.write_file(tool.list_to_string(save_data_list), ivseek_class.save_data_path, file.WRITE_FILE_TYPE_REPLACE)


if __name__ == "__main__":
    main()
