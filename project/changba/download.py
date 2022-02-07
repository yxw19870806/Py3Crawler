# -*- coding:UTF-8  -*-
"""
指定唱吧歌曲下载
https://changba.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import re
import tkinter
from tkinter import filedialog
from common import *
from project.changba import changba


def main():
    # 初始化
    changba_class = changba.ChangBa(extra_sys_config={crawler.SYS_NOT_CHECK_SAVE_DATA: True})
    # GUI窗口
    gui = tkinter.Tk()
    gui.withdraw()

    while True:
        audio_url = input(crawler.get_time() + " 请输入唱吧歌曲地址：")
        audio_key = None
        # https://changba.com/s/LBdSlkRwmqApasSCCVp5VA
        if audio_url.lower().find("//changba.com/s/") > 0:
            audio_key = audio_url.split("/")[-1].split("?")[0]
        elif re.match("[a-zA-Z0-9]+$", audio_url) is not None:
            audio_key = audio_url
        if audio_key is None:
            log.step("错误的歌曲地址，正确的地址格式如：https://changba.com/s/LBdSlkRwmqApasSCCVp5VA")
            continue
        # 访问歌曲播放页
        try:
            audio_response = changba.get_audio_play_page(audio_key)
        except crawler.CrawlerException as e:
            log.error(f"解析歌曲下载地址失败，原因：{e.message}")
            break
        if audio_response["is_delete"]:
            log.step("歌曲不存在，跳过")
            continue
        # 选择下载目录
        file_type = net.get_file_type(audio_response["audio_url"])
        options = {
            "initialdir": changba_class.audio_download_path,
            "initialfile": f"%010d - {path.filter_text(audio_response['audio_title'])}.{file_type}" % audio_response["audio_id"],
            "filetypes": [(file_type, "." + file_type)],
            "parent": gui,
        }
        file_path = tkinter.filedialog.asksaveasfilename(**options)
        if not file_path:
            continue
        # 开始下载
        log.step(f"\n歌曲标题：{audio_response['audio_title']}\n歌曲地址：{audio_response['audio_url']}\n下载路径：{file_path}")
        save_file_return = net.download(audio_response["audio_url"], file_path, head_check=True)
        if save_file_return["status"] == 1:
            log.step(f"歌曲《{audio_response['audio_title']}》下载成功")
        else:
            log.error(f"歌曲《{audio_response['audio_title']}》下载失败，原因：{crawler.download_failre(save_file_return['code'])}")


if __name__ == "__main__":
    main()
