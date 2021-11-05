# -*- coding:UTF-8  -*-
"""
指定bilibili视频下载
https://www.bilibili.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import tkinter
from tkinter import filedialog
from common import *
from project.bilibili import bilibili


def main():
    # 初始化
    bilibili_class = bilibili.BiliBili(extra_sys_config={crawler.SYS_NOT_CHECK_SAVE_DATA: True})
    # GUI窗口
    gui = tkinter.Tk()
    gui.withdraw()

    while True:
        video_url = input("请输入bilibili视频地址：")
        lower_video_url = video_url.lower()
        video_id = None
        if lower_video_url.find("bilibili.com/video/av") > 0:
            video_id = tool.find_sub_string(video_url, "bilibili.com/video/av").split("?")[0]
        elif lower_video_url.find("bilibili.com/video/bv") > 0:
            bv_id = tool.find_sub_string(video_url, "bilibili.com/video/").split("?")[0]
            video_id = bilibili.bv_id_2_av_id(bv_id)
        elif crawler.is_integer(lower_video_url):
            video_id = lower_video_url
        elif lower_video_url[:2] == "av" and crawler.is_integer(lower_video_url[2:]):
            video_id = lower_video_url[2:]
        elif lower_video_url[:2] == "bv":
            video_id = bilibili.bv_id_2_av_id(video_url)
        # 无效的视频地址
        if not crawler.is_integer(video_id):
            log.step("错误的视频地址，正确的地址格式如：https://www.bilibili.com/video/av123456")
            continue
        # 访问视频播放页
        try:
            video_response = bilibili.get_video_page(video_id)
        except crawler.CrawlerException as e:
            log.error("解析视频下载地址失败，原因：%s" % e.message)
            continue
        if video_response["is_private"]:
            log.step("视频需要登录才能访问，跳过")
            continue

        if len(video_response["video_part_info_list"]) > 1:
            log.step("视频共获取%s个分段" % len(video_response["video_part_info_list"]))

        part_index = 1
        for video_part_info in video_response["video_part_info_list"]:
            if len(video_part_info["video_url_list"]) == 0:
                if len(video_response["video_part_info_list"]) > 1:
                    log.step("视频第%s个分段已删除" % part_index)
                else:
                    log.step("视频已删除")
                continue

            video_title = video_response["video_title"]
            if len(video_response["video_part_info_list"]) > 1:
                if video_part_info["video_part_title"]:
                    video_title += "_" + video_part_info["video_part_title"]
                else:
                    video_title += "_" + str(part_index)
            video_name = "%010d %s.%s" % (int(video_id), path.filter_text(video_title), net.get_file_type(video_part_info["video_url_list"][0]))
            # 选择下载目录
            options = {
                "initialdir": bilibili_class.video_download_path,
                "initialfile": video_name,
                "filetypes": [("all", "*")],
                "parent": gui,
            }
            file_path = tkinter.filedialog.asksaveasfilename(**options)
            if not file_path:
                continue

            log.step("\n视频标题：%s\n视频地址：%s\n下载路径：%s" % (video_title, video_part_info["video_url_list"], file_path))
            # 开始下载
            video_index = 1
            for video_url in video_part_info["video_url_list"]:
                if len(video_part_info["video_url_list"]) > 1:
                    temp_list = os.path.basename(file_path).split(".")
                    file_type = temp_list[-1]
                    file_name = ".".join(temp_list[:-1])
                    file_name += " (%s)" % video_index
                    file_real_path = os.path.abspath(os.path.join(os.path.dirname(file_path), "%s.%s" % (file_name, file_type)))
                else:
                    file_real_path = file_path

                save_file_return = net.save_net_file(video_url, file_real_path, header_list={"Referer": "https://www.bilibili.com/video/av%s" % video_id})
                if save_file_return["status"] == 1:
                    if len(video_part_info["video_url_list"]) == 1:
                        log.step("视频《%s》下载成功" % video_title)
                    else:
                        log.step("视频《%s》第%s段下载成功" % (video_title, video_index))
                else:
                    if len(video_part_info["video_url_list"]) == 1:
                        log.step("视频《%s》下载失败，原因：%s" % (video_title, crawler.download_failre(save_file_return["code"])))
                    else:
                        log.step("视频《%s》第%s段下载失败，原因：%s" % (video_title, video_index, crawler.download_failre(save_file_return["code"])))
                video_index += 1


if __name__ == "__main__":
    main()
