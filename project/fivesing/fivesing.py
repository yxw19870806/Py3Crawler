# -*- coding:UTF-8  -*-
"""
5sing歌曲爬虫
http://5sing.kugou.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import re
from common import *


# 获取指定页数的全部歌曲
# page_type 页面类型：yc - 原唱、fc - 翻唱
def get_one_page_audio(account_id, page_type, page_count):
    # http://5sing.kugou.com/inory/yc/1.html
    audio_pagination_url = f"http://5sing.kugou.com/{account_id}/{page_type}/{page_count}.html"
    audio_pagination_response = net.Request(audio_pagination_url, method="GET")
    result = {
        "audio_info_list": [],  # 全部歌曲信息
    }
    if audio_pagination_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(audio_pagination_response.status))
    if audio_pagination_response.content.find("var OwnerNickName = '';") >= 0:
        raise CrawlerException("账号不存在")
    # 获取歌曲信息
    # 单首歌曲信息的格式：[歌曲id，歌曲标题]
    audio_info_list = re.findall(r'<a href="http://5sing.kugou.com/%s/(\d*).html" [\s|\S]*? title="([^"]*)">' % page_type, audio_pagination_response.content)
    for audio_info in audio_info_list:
        result_audio_info = {
            "audio_id": int(audio_info[0]),
            "audio_title": audio_info[1],
        }
        result["audio_info_list"].append(result_audio_info)
    return result


# 获取指定id的歌曲播放页
def get_audio_play_page(audio_id, song_type):
    audio_info_url = "http://service.5sing.kugou.com/song/getsongurl"
    query_data = {
        "songid": audio_id,
        "songtype": song_type,
    }
    audio_info_response = net.Request(audio_info_url, method="GET", fields=query_data).enable_json_decode()
    result = {
        "audio_title": "",  # 歌曲标题
        "audio_url": "",  # 歌曲地址
        "is_delete": False,  # 是否已删除
    }
    if audio_info_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(audio_info_response.status))
    if crawler.get_json_value(audio_info_response.json_data, "success", type_check=bool) is False:
        if crawler.get_json_value(audio_info_response.json_data, "message", type_check=str) in ["该歌曲已下架", "歌曲不存在", "歌曲不存在或状态不正常"]:
            result["is_delete"] = True
            return result
    response_data = crawler.get_json_value(audio_info_response.json_data, "data", type_check=dict)
    # 获取歌曲地址
    if tool.check_dict_sub_key(["squrl"], response_data) and response_data["squrl"]:
        result["audio_url"] = response_data["squrl"]
    elif tool.check_dict_sub_key(["lqurl"], response_data) and response_data["lqurl"]:
        result["audio_url"] = response_data["lqurl"]
    elif tool.check_dict_sub_key(["hqurl"], response_data) and response_data["hqurl"]:
        result["audio_url"] = response_data["hqurl"]
    else:
        raise CrawlerException("歌曲信息'squrl'、'lqurl'、'hqurl'字段都不存在\n" + str(audio_info_response.json_data))
    # 获取歌曲标题
    result["audio_title"] = crawler.get_json_value(audio_info_response.json_data, "data", "songName", type_check=str)
    return result


class FiveSing(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            const.SysConfigKey.DOWNLOAD_AUDIO: True,
            const.SysConfigKey.SAVE_DATA_FORMATE: (0, ["", "0", "0"]),  # account_id  last_yc_audio_id  last_fc_audio_id
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 下载线程
        self.set_crawler_thread(CrawlerThread)


class CrawlerThread(crawler.CrawlerThread):
    EACH_PAGE_AUDIO_COUNT = 20  # 每页歌曲数量上限（请求数量是无法修改的，只做判断使用）
    AUDIO_TYPE_YC = "yc"  # 歌曲类型：原唱
    AUDIO_TYPE_FC = "fc"  # 歌曲类型：翻唱
    # 原创、翻唱
    audio_type_to_index_dict = {AUDIO_TYPE_YC: 1, AUDIO_TYPE_FC: 2}  # 存档文件里的下标
    audio_type_name_dict = {AUDIO_TYPE_YC: "原唱", AUDIO_TYPE_FC: "翻唱"}  # 显示名字

    def __init__(self, main_thread, single_save_data):
        self.index_key = single_save_data[0]  # account id
        if len(single_save_data) >= 4 and single_save_data[3]:
            self.display_name = single_save_data[3]
        else:
            self.display_name = single_save_data[0]
        crawler.CrawlerThread.__init__(self, main_thread, single_save_data)

    # 获取所有可下载歌曲
    def get_crawl_list(self, audio_type):
        audio_type_index = self.audio_type_to_index_dict[audio_type]
        audio_type_name = self.audio_type_name_dict[audio_type]

        page_count = 1
        unique_list = []
        audio_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的歌曲
        while not is_over:
            audio_pagination_description = f"第{page_count}页{audio_type_name}歌曲"
            self.start_parse(audio_pagination_description)
            try:
                audio_pagination_response = get_one_page_audio(self.index_key, audio_type, page_count)
            except CrawlerException as e:
                self.error(e.http_error(audio_pagination_description))
                raise
            self.parse_result(audio_pagination_description, audio_pagination_response["audio_info_list"])

            # 寻找这一页符合条件的歌曲
            for audio_info in audio_pagination_response["audio_info_list"]:
                # 检查是否达到存档记录
                if audio_info["audio_id"] > int(self.single_save_data[audio_type_index]):
                    # 新增歌曲导致的重复判断
                    if audio_info["audio_id"] in unique_list:
                        continue
                    else:
                        audio_info_list.append(audio_info)
                        unique_list.append(audio_info["audio_id"])
                else:
                    is_over = True
                    break

            if not is_over:
                # 获取的歌曲数量少于1页的上限，表示已经到结束了
                # 如果歌曲数量正好是页数上限的倍数，则由下一页获取是否为空判断
                if len(audio_pagination_response["audio_info_list"]) < self.EACH_PAGE_AUDIO_COUNT:
                    is_over = True
                else:
                    page_count += 1

        return audio_info_list

    # 解析单首歌曲
    def crawl_audio(self, audio_type, audio_info):
        audio_type_name = self.audio_type_name_dict[audio_type]

        audio_description = f"{audio_type_name}歌曲{audio_info['audio_id']}《{audio_info['audio_title']}》"
        self.start_parse(audio_description)
        try:
            audio_info_response = get_audio_play_page(audio_info["audio_id"], audio_type)
        except CrawlerException as e:
            self.error(e.http_error(audio_description))
            raise
        if audio_info_response["is_delete"]:
            self.error(f"{audio_description} 已删除")
            return

        audio_extension = url.get_file_ext(audio_info_response["audio_url"])
        audio_name = f"%08d - %s.{audio_extension}" % (audio_info["audio_id"], audio_info["audio_title"])
        audio_path = os.path.join(self.main_thread.audio_download_path, self.display_name, audio_type_name, audio_name)
        if self.download(audio_info_response["audio_url"], audio_path, audio_description):
            self.total_audio_count += 1  # 计数累加

        # 歌曲下载完毕
        self.single_save_data[self.audio_type_to_index_dict[audio_type]] = str(audio_info["audio_id"])  # 设置存档记录

    def _run(self):
        for audio_type in list(self.audio_type_to_index_dict.keys()):
            # 获取所有可下载歌曲
            audio_info_list = self.get_crawl_list(audio_type)
            self.info(f"需要下载的全部{self.audio_type_name_dict[audio_type]}歌曲解析完毕，共{len(audio_info_list)}首")

            # 从最早的歌曲开始下载
            while len(audio_info_list) > 0:
                self.crawl_audio(audio_type, audio_info_list.pop())


if __name__ == "__main__":
    FiveSing().main()
