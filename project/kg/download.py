# -*- coding:UTF-8  -*-
"""
指定全民K歌歌曲下载
https://kg.qq.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import tkinter
from tkinter import filedialog
from common import *
from project.kg import kg


def main():
    # 初始化
    kg_obj = kg.KG(extra_config={crawler.SYS_NOT_CHECK_SAVE_DATA: True})
    # GUI窗口
    gui = tkinter.Tk()
    gui.withdraw()

    while True:
        audio_url = input(crawler.get_time() + " 请输入全民K歌歌曲地址：")
        audio_id = None
        # https://node.kg.qq.com/play?s=JLm8h1J64lEyXJ6n&g_f=personal
        if audio_url.lower().find("//node.kg.qq.com/play") > 0:
            query_string_list = audio_url.split("?")[-1].split("&")
            for query_string in query_string_list:
                if query_string.find("=") == -1:
                    continue
                key, value = query_string.split("=", 1)
                if key == "s":
                    audio_id = value
                    break
        if audio_id is None:
            log.step("错误的歌曲地址，正确的地址格式如：https://node.kg.qq.com/play?s=JLm8h1J64lEyXJ6n")
            continue
        # 访问歌曲播放页
        try:
            audio_response = kg.get_audio_play_page(audio_id)
        except crawler.CrawlerException as e:
            log.error("解析歌曲下载地址失败，原因：%s" % e.message)
            tool.process_exit()
        # 选择下载目录
        file_type = kg.get_file_type(audio_response["audio_url"])
        options = {
            "initialdir": kg_obj.audio_download_path,
            "initialfile": "%s - %s.%s" % (audio_id, path.filter_text(audio_response["audio_title"]), file_type),
            "filetypes": [(file_type, "." + file_type)],
            "parent": gui,
        }
        file_path = tkinter.filedialog.asksaveasfilename(**options)
        if not file_path:
            continue
        # 开始下载
        log.step("\n歌曲标题：%s\n歌曲地址：%s\n下载路径：%s" % (audio_response["audio_title"], audio_response["audio_url"], file_path))
        save_file_return = net.save_net_file(audio_response["audio_url"], file_path, head_check=True)
        if save_file_return["status"] == 1:
            log.step("歌曲《%s》下载成功" % audio_response["audio_title"])
        else:
            log.error("歌曲《%s》下载失败，原因：%s" % (audio_response["audio_title"], crawler.download_failre(save_file_return["code"])))


if __name__ == "__main__":
    main()
