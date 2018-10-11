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
from project.nicoNico import nicoNico

NICONICO_VIDEO_DOWNLOAD_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "niconico_video"))


def main():
    config = crawler._get_config()
    # 获取cookies
    all_cookie_from_browser = crawler.quickly_get_all_cookies_from_browser(config)
    if ".nicovideo.jp" in all_cookie_from_browser:
        for cookie_key in all_cookie_from_browser[".nicovideo.jp"]:
            nicoNico.COOKIE_INFO[cookie_key] = all_cookie_from_browser[".nicovideo.jp"][cookie_key]
    # 设置代理
    crawler.quickly_set_proxy(config)

    # 检测登录状态
    if not nicoNico.check_login():
        output.print_msg("没有检测到账号登录状态，退出程序！")
        tool.process_exit()

    save_data_path = crawler.quickly_get_save_data_path(config)
    save_data_list = ivseek.read_save_data(save_data_path)
    for single_save_list in save_data_list:
        if single_save_list[2].find(".nicovideo.jp/") == -1:
            continue

        # 已完成
        if single_save_list[4] == ivseek.DONE_SING:
            continue

        output.print_msg("开始解析视频%s" % single_save_list[2])
        video_id = single_save_list[2].split("/")[-1].replace("sm", "")
        if not crawler.is_integer(video_id):
            output.print_msg("视频 %s 截取video id失败" % single_save_list[2])
            continue

        try:
            video_info_response = nicoNico.get_video_info(video_id)
        except crawler.CrawlerException as e:
            log.error("视频%s解析失败，原因：%s" % (single_save_list[2], e.message))
            continue

        if video_info_response["is_delete"]:
            continue

        output.print_msg("开始下载视频%s 《%s》 %s" % (video_id, video_info_response["video_title"], video_info_response["video_url"]))
        file_path = os.path.join(NICONICO_VIDEO_DOWNLOAD_PATH, "%08d - %s.mp4" % (int(video_id), path.filter_text(video_info_response["video_title"])))
        cookies_list = nicoNico.COOKIE_INFO
        if video_info_response["extra_cookie"]:
            cookies_list.update(video_info_response["extra_cookie"])
        save_file_return = net.save_net_file(video_info_response["video_url"], file_path, cookies_list=cookies_list)
        if save_file_return["status"] == 1:
            output.print_msg("视频%s 《%s》下载成功" % (video_id, video_info_response["video_title"]))
        else:
            log.error("视频%s 《%s》 %s 下载失败，原因：%s" % (video_id, video_info_response["video_title"], video_info_response["video_url"], crawler.download_failre(save_file_return["code"])))
            continue

        # 增加已处理标记
        single_save_list[4] = ivseek.DONE_SING
        # 保存记录
        file.write_file(tool.list_to_string(save_data_list), save_data_path, file.WRITE_FILE_TYPE_REPLACE)


if __name__ == "__main__":
    main()
