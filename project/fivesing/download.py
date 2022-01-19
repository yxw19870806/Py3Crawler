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
from project.fiveSing import fiveSing


def main():
    # 初始化
    fiveSing_class = fiveSing.FiveSing(extra_sys_config={crawler.SYS_NOT_CHECK_SAVE_DATA: True})
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
        if not crawler.is_integer(audio_id) or audio_type not in ["yc", "fc", "bz"]:
            log.step("错误的歌曲地址，正确的地址格式如：http://5sing.kugou.com/fc/15887314.html")
            continue
        # 访问歌曲播放页
        try:
            audio_response = fiveSing.get_audio_play_page(audio_id, audio_type)
        except crawler.CrawlerException as e:
            log.error("解析歌曲下载地址失败，原因：%s" % e.message)
            tool.process_exit()
        if audio_response["is_delete"]:
            log.step("歌曲不存在，跳过")
            continue
        # 选择下载目录
        file_type = net.get_file_type(audio_response["audio_url"])
        options = {
            "initialdir": fiveSing_class.audio_download_path,
            "initialfile": "%08d - %s.%s" % (int(audio_id), path.filter_text(audio_response["audio_title"]), file_type),
            "filetypes": [(file_type, "." + file_type)],
            "parent": gui,
        }
        file_path = tkinter.filedialog.asksaveasfilename(**options)
        if not file_path:
            continue
        # 开始下载
        log.step("\n歌曲标题：%s\n歌曲地址：%s\n下载路径：%s" % (audio_response["audio_title"], audio_response["audio_url"], file_path))
        save_file_return = net.download(audio_response["audio_url"], file_path, head_check=True)
        if save_file_return["status"] == 1:
            log.step("歌曲《%s》下载成功" % audio_response["audio_title"])
        else:
            log.error("歌曲《%s》下载失败，原因：%s" % (audio_response["audio_title"], crawler.download_failre(save_file_return["code"])))


if __name__ == "__main__":
    main()
