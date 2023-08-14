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

        console.log(f"开始解析视频{single_save_list[2]}")
        video_id = tool.remove_string_prefix(url.get_basename(single_save_list[2]), "sm")
        if not tool.is_integer(video_id):
            console.log(f"视频{single_save_list[2]}截取video id失败")
            continue

        try:
            video_info_response = niconico.get_video_info(video_id)
        except CrawlerException as e:
            log.error(e.http_error(f"视频{single_save_list[2]}"))
            continue

        if video_info_response["is_delete"]:
            continue

        video_name = "%08d - %s.mp4" % (int(video_id), video_info_response["video_title"])
        video_path = os.path.join(NICONICO_VIDEO_DOWNLOAD_PATH, video_name)
        cookies = niconico.COOKIES
        if video_info_response["extra_cookie"]:
            cookies.update(video_info_response["extra_cookie"])
        video_description = f"视频{video_id}《{video_info_response['video_title']}》 {video_info_response['video_url']}"
        if not ivseek_class.download(video_info_response["video_url"], video_path, video_description, cookies=cookies):
            continue

        # 增加已处理标记
        single_save_list[4] = ivseek.DONE_SING
        # 保存记录
        file.write_file(tool.dyadic_list_to_string(save_data_list), ivseek_class.save_data_path, const.WriteFileMode.REPLACE)


if __name__ == "__main__":
    main()
