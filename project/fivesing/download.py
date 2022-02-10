# -*- coding:UTF-8  -*-
"""
指定5sing歌曲下载
http://5sing.kugou.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import tkinter
from tkinter import filedialog
from common import *
from project.fivesing import fivesing


def main():
    # 初始化
    fiveSing_class = fivesing.FiveSing(extra_sys_config={crawler.SYS_NOT_CHECK_SAVE_DATA: True})
    # GUI窗口
    gui = tkinter.Tk()
    gui.withdraw()

    while True:
        audio_url = input(crawler.get_time() + " 请输入5sing歌曲地址：").lower()
        audio_type = None
        audio_id = None
        # http://5sing.kugou.com/fc/15887314.html
        if audio_url.find("//5sing.kugou.com/") > 0:
            temp_list = audio_url.split("/")
            audio_type = temp_list[-2]
            audio_id = temp_list[-1].split(".")[0]
        if not tool.is_integer(audio_id) or audio_type not in ["yc", "fc", "bz"]:
            log.step("错误的歌曲地址，正确的地址格式如：http://5sing.kugou.com/fc/15887314.html")
            continue
        # 访问歌曲播放页
        try:
            audio_response = fivesing.get_audio_play_page(audio_id, audio_type)
        except crawler.CrawlerException as e:
            log.error(e.http_error("歌曲"))
            break
        if audio_response["is_delete"]:
            log.step("歌曲不存在，跳过")
            continue
        # 选择下载目录
        file_extension = net.get_file_extension(audio_response["audio_url"])
        options = {
            "initialdir": fiveSing_class.audio_download_path,
            "initialfile": f"%08d - {path.filter_text(audio_response['audio_title'])}.{file_type}" % int(audio_id),
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
