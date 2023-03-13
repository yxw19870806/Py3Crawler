# -*- coding:UTF-8  -*-
"""
ivssek视频源地址爬虫
http://www.ivseek.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import re
import time
from pyquery import PyQuery as pq
from common import *
from suspend.niconico import niconico

DONE_SING = "~"


# 读取存档文件
def read_save_data(save_data_path):
    result_list = []
    if not os.path.exists(save_data_path):
        return result_list
    for single_save_data in file.read_file(save_data_path, const.ReadFileMode.LINE):
        single_save_data = single_save_data.replace("\xef\xbb\xbf", "").replace("\n", "").replace("\r", "")
        if len(single_save_data) == 0:
            continue
        single_save_list = single_save_data.split("\t")
        while len(single_save_list) < 5:
            single_save_list.append("")
        result_list.append(single_save_list)
    return result_list


# 获取首页
def get_index_page():
    index_url = "http://www.ivseek.com/"
    index_response = net.request(index_url, method="GET")
    result = {
        "max_archive_id": 0,  # 最新图集id
    }
    if index_response.status != const.ResponseCode.SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(index_response.status))
    index_response_content = index_response.data.decode(errors="ignore")
    archive_id_find = re.findall(r'<a class="no-deco" href="http://www.ivseek.com/archives/(\d*).html">', index_response_content)
    if len(archive_id_find) == 0:
        raise crawler.CrawlerException("页面匹配视频id失败\n" + index_response_content)
    result["max_archive_id"] = max(list(map(int, archive_id_find)))
    return result


def get_archive_page(archive_id):
    archive_url = "http://www.ivseek.com/archives/%s.html" % archive_id
    archive_response = net.request(archive_url, method="GET")
    result = {
        "is_delete": "",  # 是否已删除
        "video_title": "",  # 标题
        "video_info_list": [],  # 全部视频信息
    }
    if archive_response.status == 404:
        result["is_delete"] = True
        return result
    elif archive_response.status != const.ResponseCode.SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(archive_response.status))
    archive_response_content = archive_response.data.decode(errors="ignore")
    # 获取视频地址
    video_url_find1 = re.findall(r'<iframe[\s|\S]*?src="([^"]*)"', archive_response_content)
    video_url_find2 = re.findall(r'<script type="\w*/javascript" src="(https?://\w*.nicovideo.jp/[^"]*)"></script>', archive_response_content)
    video_url_find = video_url_find1 + video_url_find2
    if len(video_url_find) == 0:
        return result
    for video_url in video_url_find:
        result_video_info = {
            "account_id": "",  # 视频发布账号
            "video_url": "",  # 视频信息
        }
        # 'http://embed.share-videos.se/auto/embed/40537536?uid=6050'
        if video_url.find("//embed.share-videos.se/") >= 0:
            video_id = video_url.split("/")[-1]
            result_video_info["video_url"] = "http://share-videos.se/auto/video/%s" % video_id
        # https://www.youtube.com/embed/9GSEOmLD_zc?feature=oembed
        elif video_url.find("//www.youtube.com/") >= 0:
            video_id = video_url.split("/")[-1].split("?")[0]
            result_video_info["video_url"] = "https://www.youtube.com/watch?v=%s" % video_id
            # 获取视频发布账号
            video_play_response = net.request(result_video_info["video_url"], method="GET", header_list={"accept-language": "en-US"})
            if video_play_response.status != const.ResponseCode.SUCCEED:
                raise crawler.CrawlerException("视频播放页 %s，%s" % (result_video_info["video_url"], crawler.request_failre(video_play_response.status)))
            video_play_response_content = video_play_response.data.decode(errors="ignore")
            # 账号已被删除，跳过
            if video_play_response_content.find('"reason":"This video is no longer available because the YouTube account associated with this video has been terminated."') >= 0:
                continue
            account_id = tool.find_sub_string(video_play_response_content, '"webNavigationEndpointData":{"url":"/channel/', '"')
            if not account_id:
                account_id = tool.find_sub_string(video_play_response_content, '{"webCommandMetadata":{"url":"/channel/', '"')
            if not account_id:
                account_id = tool.find_sub_string(video_play_response_content, '<meta itemprop="channelId" content="', '">')
            if account_id:
                result_video_info["account_id"] = account_id
            else:
                log.warning("视频 %s 发布账号截取失败\n%s" % (result_video_info["video_url"], video_play_response_content))
        elif video_url.find(".nicovideo.jp/") >= 0:
            # https://embed.nicovideo.jp/watch/sm23008734/script?w=640&#038;h=360
            if video_url.find("embed.nicovideo.jp/watch") >= 0:
                video_id = video_url.split("/")[-2]
            # http://ext.nicovideo.jp/thumb_watch/sm21088018?w=490&#038;h=307
            # https://ext.nicovideo.jp/thumb/sm31656014
            elif video_url.find("ext.nicovideo.jp/thumb_watch/") >= 0 or video_url.find("ext.nicovideo.jp/thumb/") >= 0:
                video_id = video_url.split("/")[-1].split("?")[0]
            else:
                raise crawler.CrawlerException("未知视频来源" + video_url)
            result_video_info["video_url"] = "http://www.nicovideo.jp/watch/%s" % video_id
            # 获取视频发布账号
            video_play_response = net.request(result_video_info["video_url"], method="GET", cookies_list=niconico.COOKIE_INFO)
            while video_play_response.status == 403:
                log.info("视频%s访问异常，重试" % video_id)
                time.sleep(60)
                video_play_response = net.request(result_video_info["video_url"], method="GET", cookies_list=niconico.COOKIE_INFO)
            if video_play_response.status != const.ResponseCode.SUCCEED:
                raise crawler.CrawlerException("视频播放页 %s，%s" % (result_video_info["video_url"], crawler.request_failre(video_play_response.status)))
            video_play_response_content = video_play_response.data.decode(errors="ignore")
            script_json: dict = tool.json_decode(pq(video_play_response_content).find("#js-initial-watch-data").attr("data-api-data"))
            if not script_json or not crawler.check_sub_key(("owner",), script_json):
                raise crawler.CrawlerException("视频播放页 %s 截取视频信息失败，%s" % (result_video_info["video_url"], crawler.request_failre(video_play_response.status)))
            if script_json["owner"]:
                if crawler.check_sub_key(("id",), script_json["owner"]):
                    result_video_info["account_id"] = script_json["owner"]["id"]
                else:
                    log.warning("视频 %s 发布账号截取失败\n%s" % (result_video_info["video_url"], video_play_response_content))
        # http://www.dailymotion.com/embed/video/x5oi0x
        elif video_url.find("//www.dailymotion.com/") >= 0:
            video_url = video_url.replace("http://", "https://")
            video_id = video_url.split("/")[-1][0]
            result_video_info["video_url"] = "http://www.dailymotion.com/video/%s" % video_id
            # 获取视频发布账号
            video_play_response = net.request(result_video_info["video_url"], method="GET")
            if video_play_response.status != const.ResponseCode.SUCCEED:
                raise crawler.CrawlerException("视频播放页%s，%s" % (result_video_info["video_url"], crawler.request_failre(video_play_response.status)))
            account_id = tool.find_sub_string(video_play_response.data.decode(errors="ignore"), '"screenname":"', '"')
            if account_id:
                result_video_info["account_id"] = account_id
        # 无效的视频地址
        elif video_url.find("//rcm-fe.amazon-adsystem.com") >= 0:
            continue
        else:
            result_video_info["video_url"] = video_url
        result["video_info_list"].append(result_video_info)
    # 获取标题
    title = tool.find_sub_string(archive_response_content, '<meta property="og:title" content="', '"')
    if not title:
        raise crawler.CrawlerException("页面截取标题失败")
    result["video_title"] = title.strip()
    return result


class IvSeek(crawler.Crawler):
    def __init__(self, **kwargs):
        # 初始化相关cookies
        niconico.NicoNico()

        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            const.SysConfigKey.NOT_CHECK_SAVE_DATA: True,
            const.SysConfigKey.NOT_DOWNLOAD: True,
            const.SysConfigKey.SET_PROXY: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

    def _main(self):
        self.save_id = 1
        save_info_list = file.read_file(self.save_data_path, const.ReadFileMode.LINE)
        if len(save_info_list) > 0:
            self.save_id = int(save_info_list[-1].split("\t")[0]) + 1

        # 获取首页
        try:
            index_response = get_index_page()
        except crawler.CrawlerException as e:
            log.error(e.http_error("首页"))
            raise

        log.info("最新视频id：%s" % index_response["max_archive_id"])

        for archive_id in range(self.save_id, index_response["max_archive_id"]):
            archive_description = "视频%s" % archive_id
            self.start_parse(archive_description)
            try:
                archive_response = get_archive_page(archive_id)
            except crawler.CrawlerException as e:
                log.error(e.http_error(archive_description))
                raise
            if archive_response["is_delete"]:
                continue
            self.parse_result(archive_description, archive_response["video_info_list"])

            for video_info in archive_response["video_info_list"]:
                log.info("视频%s《%s》: %s" % (archive_id, archive_response["video_title"], video_info["video_url"]))
                file.write_file("%s\t%s\t%s\t%s\t" % (archive_id, archive_response["video_title"], video_info["video_url"], video_info["account_id"]), self.save_data_path)

    def rewrite_save_file(self):
        pass


if __name__ == "__main__":
    IvSeek().main()
