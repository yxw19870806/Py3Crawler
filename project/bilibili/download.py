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


class BiliBiliDownload(bilibili.BiliBili):
    def __init__(self, **kwargs):
        extra_sys_config = {
            const.SysConfigKey.NOT_CHECK_SAVE_DATA: True
        }
        bilibili.BiliBili.__init__(self, extra_sys_config=extra_sys_config, **kwargs)

        # GUI窗口
        self.gui = tkinter.Tk()
        self.gui.withdraw()

    @staticmethod
    def get_video_id_from_console():
        video_url = input(tool.convert_timestamp_to_formatted_time() + " 请输入bilibili视频地址：")
        lower_video_url = video_url.lower()
        video_id = None
        if lower_video_url.find("bilibili.com/video/av") > 0:
            video_id = tool.remove_string_prefix(url.get_basename(video_url), "av")
        elif lower_video_url.find("bilibili.com/video/bv") > 0:
            bv_id = url.get_basename(video_url)
            video_id = bilibili.bv_id_2_av_id(bv_id)
        elif tool.is_integer(lower_video_url):
            video_id = lower_video_url
        elif lower_video_url.startswith("av") and tool.is_integer(tool.remove_string_prefix(lower_video_url, "av")):
            video_id = tool.remove_string_prefix(lower_video_url, "av")
        elif lower_video_url.startswith("bv"):
            video_id = bilibili.bv_id_2_av_id(video_url)
        return video_id

    def main(self):
        try:
            while True:
                self.download_from_console()
        except KeyboardInterrupt:
            return

    def download_from_console(self):
        # 输入需要解析的视频
        video_id = self.get_video_id_from_console()
        if not tool.is_integer(video_id):
            log.info("错误的视频地址，正确的地址格式如：https://www.bilibili.com/video/av123456")
            return

        # 获取下载地址
        try:
            video_response = bilibili.get_video_page(video_id)
        except CrawlerException as e:
            log.error(e.http_error("视频"))
            return
        if video_response["is_private"]:
            log.info("视频需要登录才能访问，跳过")
            return
        if len(video_response["video_part_info_list"]) > 1:
            log.info(f"视频共获取{len(video_response['video_part_info_list'])}个分段")

        part_index = 1
        for video_part_info in video_response["video_part_info_list"]:
            if len(video_part_info["video_url_list"]) == 0:
                if len(video_response["video_part_info_list"]) > 1:
                    log.info(f"视频第{part_index}个分段已删除")
                else:
                    log.info("视频已删除")
                return

            video_title = video_response["video_title"]
            if len(video_response["video_part_info_list"]) > 1:
                if video_part_info["video_part_title"]:
                    video_title += "_" + video_part_info["video_part_title"]
                else:
                    video_title += "_" + str(part_index)
            video_name = f"%010d %s.{url.get_file_ext(video_part_info['video_url_list'][0])}" % (int(video_id), video_title)

            # 选择下载目录
            log.info("请选择下载目录")
            options = {
                "initialdir": self.video_download_path,
                "initialfile": video_name,
                "filetypes": [("all", "*")],
                "parent": self.gui,
            }
            video_path = tkinter.filedialog.asksaveasfilename(**options)
            if not video_path:
                continue

            # 开始下载
            log.info(f"\n视频标题：{video_title}\n视频地址：{video_part_info['video_url_list']}\n下载路径：{video_path}")
            video_index = 1
            for video_url in video_part_info["video_url_list"]:
                if len(video_part_info["video_url_list"]) > 1:
                    temp_list = os.path.basename(video_path).split(".")
                    file_extension = temp_list[-1]
                    video_name = ".".join(temp_list[:-1])
                    video_name += f" ({video_index})"
                    video_real_path = os.path.abspath(os.path.join(os.path.dirname(video_path), f"{video_name}.{file_extension}"))
                else:
                    video_real_path = video_path

                headers = {"Referer": f"https://www.bilibili.com/video/av{video_id}"}
                if len(video_part_info["video_url_list"]) == 1:
                    video_description = f"视频《{video_title}》"
                else:
                    video_description = f"视频《{video_title}》第{video_index}段"
                self.download(video_url, video_real_path, video_description, headers=headers, auto_multipart_download=True)
                video_index += 1


if __name__ == "__main__":
    BiliBiliDownload().main()
