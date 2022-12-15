# -*- coding:UTF-8  -*-
"""
Youtube视频爬虫
https://www.youtube.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import json
import os
import re
import time
import urllib.parse
from common import *

IS_LOGIN = False
COOKIE_INFO = {}
FIRST_CHOICE_RESOLUTION = 720


# 检测登录状态
def check_login():
    if not COOKIE_INFO:
        return False
    account_index_url = "https://www.youtube.com/account"
    index_response = net.request(account_index_url, method="GET", cookies_list=COOKIE_INFO, is_auto_redirect=False)
    if index_response.status == 303 and index_response.getheader("Location").find("https://accounts.google.com/ServiceLogin?") == 0:
        return False
    elif index_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        return True
    return False


# 获取用户首页
def get_one_page_video(account_id, token):
    # token = "4qmFsgJAEhhVQ2xNXzZHRU9razY2STFfWWJTUFFqSWcaJEVnWjJhV1JsYjNNZ0FEZ0JZQUZxQUhvQk1yZ0JBQSUzRCUzRA%3D%3D"
    result = {
        "channel_name": "",  # 账号名字
        "video_id_list": [],  # 全部视频id
        "next_page_token": "",  # 下一页token
    }
    if token == "":
        # todo 更好的分辨方法
        if len(account_id) == 24:
            index_url = "https://www.youtube.com/channel/%s/videos" % account_id
        else:
            index_url = "https://www.youtube.com/user/%s/videos" % account_id
        post_data = {
            "sort": "dd",
            "view": "0",
        }
        index_response = net.request(index_url, method="GET", fields=post_data, header_list={"accept-language": "en"})
        if index_response.status == 404:
            raise crawler.CrawlerException("账号不存在")
        elif index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
            raise crawler.CrawlerException(crawler.request_failre(index_response.status))
        index_response_content = index_response.data.decode(errors="ignore")
        if index_response_content.find('<button id="a11y-skip-nav" class="skip-nav"') >= 0:
            log.step("首页 %s 访问出现跳转，再次访问" % index_url)
            return get_one_page_video(account_id, token)
        # 截取初始化数据
        script_json_html = tool.find_sub_string(index_response_content, 'var ytInitialData = ', ";</script>").strip()
        if not script_json_html:
            raise crawler.CrawlerException("页面截取视频信息失败\n" + index_response_content)
        script_json = tool.json_decode(script_json_html)
        if script_json is None:
            raise crawler.CrawlerException("视频信息加载失败\n" + script_json_html)
        # 获取频道名字
        try:
            result["channel_name"] = crawler.get_json_value(script_json, "metadata", "channelMetadataRenderer", "title", type_check=str)
        except crawler.CrawlerException:
            reason = crawler.get_json_value(script_json, "alerts", 0, "alertRenderer", "text", "simpleText", default_value="", type_check=str)
            if reason == "This channel does not exist.":
                raise crawler.CrawlerException("账号不存在")
            elif reason:
                raise crawler.CrawlerException("账号无法访问，原因：%s" % reason)
            else:
                raise
        # 获取频道标签
        channel_tab_json = crawler.get_json_value(script_json, "contents", "twoColumnBrowseResultsRenderer", "tabs", type_check=list)
        # 没有视频标签
        if len(channel_tab_json) < 2:
            return result
        try:
            video_info_list = crawler.get_json_value(channel_tab_json, 1, "tabRenderer", "content", "richGridRenderer", "contents", original_data=script_json, type_check=list)
        except crawler.CrawlerException:
            # 没有上传过任何视频
            if crawler.get_json_value(video_tab_json, "messageRenderer", "text", "simpleText", default_value="", type_check=str) == "This channel has no videos.":
                return result
            raise
    else:
        query_url = "https://www.youtube.com/youtubei/v1/browse"
        query_data = {
            "key": "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8",
            "prettyPrint": "false",
        }
        query_url += "?" + urllib.parse.urlencode(query_data)
        post_data = {
            "context": {
                "client": {
                    "clientName": "WEB",
                    "clientVersion": "2.20221101.00.00",
                },
            },
            "continuation": token
        }
        header_list = {
            "accept-language": "en",
            "x-youtube-client-name": "1",
            "x-youtube-client-version": "2.20221101.00.00",
        }
        video_pagination_response = net.request(query_url, method="POST", binary_data=json.dumps(post_data), header_list=header_list, json_decode=True)
        if video_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
            raise crawler.CrawlerException(crawler.request_failre(video_pagination_response.status))
        video_info_list = crawler.get_json_value(video_pagination_response.json_data, "onResponseReceivedActions", 0, "appendContinuationItemsAction", "continuationItems", type_check=list)
    # 获取所有video id
    for video_info in video_info_list:
        if not crawler.check_sub_key(("continuationItemRenderer",), video_info):
            result["video_id_list"].append(crawler.get_json_value(video_info, "richItemRenderer", "content", "videoRenderer", "videoId", type_check=str))
        else:
            # 获取下一页token
            result["next_page_token"] = crawler.get_json_value(video_info, "continuationItemRenderer", "continuationEndpoint", "continuationCommand", "token", type_check=str)
    return result


# 获取指定视频
def get_video_page(video_id):
    # https://www.youtube.com/watch?v=GCOSw4WSXqU
    video_play_url = "https://www.youtube.com/watch"
    query_data = {"v": video_id}
    if IS_LOGIN:
        video_play_response = net.request(video_play_url, method="GET", fields=query_data, cookies_list=COOKIE_INFO)
    else:
        # 没有登录时默认使用英语
        video_play_response = net.request(video_play_url, method="GET", fields=query_data, header_list={"accept-language": "en"})
    result = {
        "skip_reason": "",  # 跳过原因
        "video_time": "",  # 视频上传时间
        "video_title": "",  # 视频标题
        "video_url": "",  # 视频地址
    }
    if video_play_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_play_response.status))
    video_play_response_content = video_play_response.data.decode(errors="ignore")

    # window["ytInitialPlayerResponse"]
    script_json_html = tool.find_sub_string(video_play_response_content, "var ytInitialPlayerResponse = ", ";var meta = ")
    if not script_json_html:
        raise crawler.CrawlerException("页面截取ytInitialPlayerResponse失败\n" + video_play_response_content)
    script_json = tool.json_decode(script_json_html.strip())
    if script_json is None:
        raise crawler.CrawlerException("ytInitialPlayerResponse加载失败\n" + script_json_html)
    video_status = crawler.get_json_value(script_json, "playabilityStatus", "status", type_check=str, value_check=["OK", "ERROR", "UNPLAYABLE", "LOGIN_REQUIRED"])
    if video_status != "OK":
        reason = crawler.get_json_value(script_json, "playabilityStatus", "reason", type_check=str)
        # https://www.youtube.com/watch?v=f8K4FFjgL88
        if video_status == "LOGIN_REQUIRED":
            if IS_LOGIN:
                raise crawler.CrawlerException("登录状态丢失")
            result["skip_reason"] = "需要登录账号才能访问，" + reason
        else:
            # ERROR
            # https://www.youtube.com/watch?v=_8zpXuXj_Tw
            # UNPLAYABLE
            # https://www.youtube.com/watch?v=ku0Jf8yiH-k
            result["skip_reason"] = reason
    # 获取视频标题
    result["video_title"] = crawler.get_json_value(script_json, "videoDetails", "title", type_check=str)
    # 获取视频时间
    video_time_string = crawler.get_json_value(script_json, "microformat", "playerMicroformatRenderer", "uploadDate", type_check=str)
    try:
        video_time = time.strptime(video_time_string, "%Y-%m-%d")
    except ValueError:
        raise crawler.CrawlerException("时间%s解析失败" % video_time_string)
    result["video_time"] = int(time.mktime(video_time))

    if result["skip_reason"]:
        return result

    # 获取视频地址
    resolution_to_url = {}  # 各个分辨率下的视频地址
    decrypt_function_step = []  # signature生成步骤
    for video_info in crawler.get_json_value(script_json, "streamingData", "formats", type_check=list):
        video_mime = crawler.get_json_value(video_info, "mimeType", type_check=str)
        if video_mime.find("video/mp4") != 0:
            continue
        video_quality = crawler.get_json_value(video_info, "quality", type_check=str)
        if video_quality == "tiny":
            video_resolution = 144
        elif video_quality == "small":
            video_resolution = 240
        elif video_quality == "medium":
            video_resolution = 360
        elif video_quality == "large":
            video_resolution = 480
        elif video_quality[:2] == "hd" and tool.is_integer(video_quality[2:]):
            video_resolution = int(video_quality[2:])
        else:
            video_resolution = 1
            log.notice("未知视频画质：" + video_quality)
        try:
            video_url = crawler.get_json_value(video_info, "url", type_check=str)
        except crawler.CrawlerException:
            decrypted_video_url = crawler.get_json_value(video_info, "signatureCipher", type_check=str)
            video_url = ""
            video_signature = ""
            for sub_param in decrypted_video_url.split("&"):
                key, value = sub_param.split("=")
                if key == "s":
                    video_signature = urllib.parse.unquote(value)
                elif key == "url":
                    video_url = urllib.parse.unquote(value)
            # 解析JS文件，获取对应的加密方法
            if len(decrypt_function_step) == 0:
                js_file_path = tool.find_sub_string(video_play_response_content, '<script src="/s/player/', '"')
                if js_file_path:
                    js_file_url = "https://www.youtube.com/s/player/%s" % js_file_path
                else:
                    raise crawler.CrawlerException("播放器JS文件地址截取失败\n" + video_play_response_content)
                decrypt_function_step = get_decrypt_step(js_file_url)
            signature = decrypt_signature(decrypt_function_step, video_signature)
            video_url += "&sig=" + signature
        resolution_to_url[video_resolution] = video_url

    if len(resolution_to_url) == 0:
        raise crawler.CrawlerException("返回信息%s中视频地址解析错误" % script_json)
    # 优先使用配置中的分辨率
    if FIRST_CHOICE_RESOLUTION in resolution_to_url:
        result["video_url"] = resolution_to_url[FIRST_CHOICE_RESOLUTION]
    # 如果没有这个分辨率的视频
    else:
        # 大于配置中分辨率的所有视频中分辨率最小的那个
        for resolution in sorted(resolution_to_url.keys()):
            if resolution > FIRST_CHOICE_RESOLUTION:
                result["video_url"] = resolution_to_url[resolution]
                break
        else:
            # 如果还是没有，则所有视频中分辨率最大的那个
            result["video_url"] = resolution_to_url[max(resolution_to_url)]
    return result


# 部分版权视频需要的signature字段取值
# 每隔一段时间访问视频播放页面后会插入一个动态生成JS地址
# 里面包含3个子加密方法，但调用顺序、参数、次数每个JS文件中各不相
# 其中一个例子：https://www.youtube.com/s/player/a0703e0f/player_ias.vflset/en_US/base.js
# jC.av(a,2);jC.TI(a,1);jC.xB(a,31);jC.TI(a,2);jC.av(a,67);jC.av(a,41);jC.xB(a,44);jC.av(a,46);jC.TI(a,2);
# var jC={TI:function(a,b){a.splice(0,b)},av:function(a,b){var c=a[0];a[0]=a[b%a.length];a[b%a.length]=c},xB:function(a){a.reverse()}};
def get_decrypt_step(js_file_url):
    # 最终的调用子加密方法的顺序
    decrypt_function_step = []
    js_file_response = net.request(js_file_url, method="GET")
    if js_file_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException("播放器JS文件 %s 访问失败，原因：%s" % (js_file_url, crawler.request_failre(js_file_response.status)))
    js_file_response_content = js_file_response.data.decode(errors="ignore")
    # 加密方法体（包含子加密方法的调用参数&顺序）
    # jC.av(a,2);jC.TI(a,1);jC.xB(a,31);jC.TI(a,2);jC.av(a,67);jC.av(a,41);jC.xB(a,44);jC.av(a,46);jC.TI(a,2);
    main_function_body = tool.find_sub_string(js_file_response_content, 'function(a){a=a.split("");', 'return a.join("")};')
    if not main_function_body:
        raise crawler.CrawlerException("播放器JS文件 %s，加密方法体截取失败" % js_file_url)
    # 子加密方法所在的变量名字
    decrypt_function_var = None
    for sub_decrypt_step in main_function_body.split(";"):
        # jC.av(a,2);jC.TI(a,1);jC.xB(a,31);jC.TI(a,2);jC.av(a,67);jC.av(a,41);jC.xB(a,44);jC.av(a,46);jC.TI(a,2);
        if not sub_decrypt_step:
            continue
        # (加密方法所在变量名，加密方法名，加密方法参数)
        sub_decrypt_step_find = re.findall(r"([\w$_]*)\.(\w*)\(a,(\d*)\)", sub_decrypt_step)
        if len(sub_decrypt_step_find) != 1:
            raise crawler.CrawlerException("播放器JS文件 %s，加密步骤匹配失败\n%s" % (js_file_url, sub_decrypt_step))
        if decrypt_function_var is None:
            decrypt_function_var = sub_decrypt_step_find[0][0]
        elif decrypt_function_var != sub_decrypt_step_find[0][0]:
            raise crawler.CrawlerException("播放器JS文件 %s，加密子方法所在变量不一致\n%s" % (js_file_url, main_function_body))
        decrypt_function_step.append([sub_decrypt_step_find[0][1], sub_decrypt_step_find[0][2]])  # 方法名，参数
    # 子加密方法所在的变量内容
    # TI:function(a,b){a.splice(0,b)},
    # av:function(a,b){var c=a[0];a[0]=a[b%a.length];a[b%a.length]=c},
    # xB:function(a){a.reverse()}
    decrypt_function_var_body = tool.find_sub_string(js_file_response_content, "var %s={" % decrypt_function_var, "};")
    if not main_function_body:
        raise crawler.CrawlerException("播放器JS文件 %s，加密子方法截取失败" % js_file_url)
    # 所有子加密方法具体内容
    decrypt_function_body_list = decrypt_function_var_body.split(",\n")
    if len(decrypt_function_body_list) != 3:
        raise crawler.CrawlerException("播放器JS文件 %s，加密子方法已更新\n%s" % (js_file_url, decrypt_function_var_body))
    # JS文件里的方法名对应爬虫里的方法
    js_function_to_local_function = {}
    for decrypt_function_body in decrypt_function_body_list:
        decrypt_function_name = decrypt_function_body.split(":function")[0]
        if decrypt_function_body.find("a.reverse()") > 0:
            js_function_to_local_function[decrypt_function_name] = _decrypt_function2
        elif decrypt_function_body.find("a.splice(") > 0:
            js_function_to_local_function[decrypt_function_name] = _decrypt_function3
        else:
            js_function_to_local_function[decrypt_function_name] = _decrypt_function1
    # 子加密方法调用顺序中JS文件里的方法名，替换成爬虫里的方法名
    for step in decrypt_function_step:
        step[0] = js_function_to_local_function[step[0]]
    return decrypt_function_step


def decrypt_signature(decrypt_function_step, encrypt_string):
    encrypt_string_list = list(encrypt_string)
    for step in decrypt_function_step:
        step[0](encrypt_string_list, int(step[1]))
    return "".join(encrypt_string_list)


def _decrypt_function1(a, b):
    c = a[0]
    a[0] = a[b % len(a)]
    a[b] = c


def _decrypt_function2(a, b):
    a.reverse()


def _decrypt_function3(a, b):
    for i in range(b):
        a.pop(0)
    # return a[b:]


class Youtube(crawler.Crawler):
    def __init__(self, **kwargs):
        global COOKIE_INFO, FIRST_CHOICE_RESOLUTION, IS_LOGIN

        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_VIDEO: True,
            crawler.SYS_SET_PROXY: True,
            crawler.SYS_GET_COOKIE: ("youtube.com",),
            crawler.SYS_APP_CONFIG: (
                ("VIDEO_QUALITY", 6, crawler.CONFIG_ANALYSIS_MODE_INTEGER),
            ),
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 设置全局变量，供子线程调用
        COOKIE_INFO = self.cookie_value
        video_quality = self.app_config["VIDEO_QUALITY"]
        if video_quality == 1:
            FIRST_CHOICE_RESOLUTION = 144
        elif video_quality == 2:
            FIRST_CHOICE_RESOLUTION = 240
        elif video_quality == 3:
            FIRST_CHOICE_RESOLUTION = 360
        elif video_quality == 4:
            FIRST_CHOICE_RESOLUTION = 480
        elif video_quality == 5:
            FIRST_CHOICE_RESOLUTION = 720
        elif video_quality == 6:
            FIRST_CHOICE_RESOLUTION = 1080
        else:
            log.error("配置文件config.ini中key为'video_quality'的值必须是一个1~6的整数，使用程序默认设置")

        # 解析存档文件
        # account_id  video_string_id  video_number_id
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "", "0"])

        # 下载线程
        self.download_thread = Download

    def init(self):
        # 检测登录状态
        if check_login():
            global IS_LOGIN
            IS_LOGIN = True
        else:
            while True:
                input_str = input(tool.get_time() + " 没有检测到账号登录状态，可能无法解析受限制的视频，继续程序(C)ontinue？或者退出程序(E)xit？:")
                input_str = input_str.lower()
                if input_str in ["e", "exit"]:
                    tool.process_exit()
                elif input_str in ["c", "continue"]:
                    break


class Download(crawler.DownloadThread):
    is_find = False

    def __init__(self, single_save_data, main_thread):
        self.index_key = single_save_data[0]  # account id
        if len(single_save_data) >= 4 and single_save_data[3]:
            self.display_name = single_save_data[3]
        else:
            self.display_name = single_save_data[0]
        crawler.DownloadThread.__init__(self, single_save_data, main_thread)

    def _run(self):
        # 获取所有可下载视频
        video_id_list = self.get_crawl_list()
        self.step("需要下载的全部视频解析完毕，共%s个" % len(video_id_list))
        if not self.is_find:
            self.step("存档所在视频已删除，需要在下载时进行过滤")

        # 从最早的视频开始下载
        while len(video_id_list) > 0:
            self.crawl_video(video_id_list.pop(), len(video_id_list) == 0)
            self.main_thread_check()  # 检测主线程运行状态

    # 获取所有可下载视频
    def get_crawl_list(self):
        token = ""
        video_id_list = []
        # 是否有根据视频id找到上一次的记录
        if self.single_save_data[1] == "":
            self.is_find = True
        is_over = False
        # 获取全部还未下载过需要解析的相册
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态

            pagination_description = "token：%s后一页视频" % token
            self.start_parse(pagination_description)

            # 获取一页视频
            try:
                video_pagination_response = get_one_page_video(self.index_key, token)
            except crawler.CrawlerException as e:
                self.error(e.http_error(pagination_description))
                raise

            self.parse_result(pagination_description, video_pagination_response["video_id_list"])

            if len(self.single_save_data) < 4:
                self.step("频道名：%s" % video_pagination_response["channel_name"])
                self.display_name = video_pagination_response["channel_name"]
                self.single_save_data.append(self.display_name)

            # 寻找这一页符合条件的日志
            for video_id in video_pagination_response["video_id_list"]:
                # 检查是否达到存档记录
                if video_id != self.single_save_data[1]:
                    video_id_list.append(video_id)
                else:
                    is_over = True
                    self.is_find = True
                    break

            if not is_over:
                if video_pagination_response["next_page_token"]:
                    # 设置下一页token
                    token = video_pagination_response["next_page_token"]
                else:
                    is_over = True

        return video_id_list

    # 解析单个视频
    def crawl_video(self, video_id, is_last):
        video_description = "视频%s" % video_id
        self.start_parse(video_description)

        # 获取指定视频信息
        try:
            video_response = get_video_page(video_id)
        except crawler.CrawlerException as e:
            self.error(e.http_error(video_description))
            raise

        # 如果解析需要下载的视频时没有找到上次的记录，表示存档所在的视频已被删除，则判断数字id
        if not self.is_find:
            if video_response["video_time"] < int(self.single_save_data[2]):
                self.step("%s 跳过" % video_description)
                # 如果最后一个视频仍然没有找到，重新设置存档
                if is_last:
                    self.single_save_data[1] = video_id  # 设置存档记录
                    self.single_save_data[2] = str(video_response["video_time"])  # 设置存档记录
                return
            elif video_response["video_time"] == int(self.single_save_data[2]):
                self.error("%s 与存档视频发布日期一致，无法过滤，再次下载" % video_description)
            else:
                self.is_find = True

        if video_response["skip_reason"]:
            self.error("%s 已跳过，原因：%s" % (video_description, video_response["skip_reason"]))
        else:
            video_name = "%s - %s.mp4" % (video_id, path.filter_text(video_response["video_title"]))
            video_path = os.path.join(self.main_thread.video_download_path, self.display_name, video_name)
            video_description = "视频%s《%s》" % (video_id, video_response["video_title"])
            if self.download(video_response["video_url"], video_path, video_description, auto_multipart_download=True).is_success():
                self.total_video_count += 1  # 计数累加

        # 媒体内图片和视频全部下载完毕
        self.single_save_data[1] = video_id  # 设置存档记录
        self.single_save_data[2] = str(video_response["video_time"])  # 设置存档记录


if __name__ == "__main__":
    Youtube().main()
