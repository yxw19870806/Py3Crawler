# -*- coding:UTF-8  -*-
"""
tumblr图片&视频爬虫
https://www.tumblr.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import re
import time
import urllib.parse
from pyquery import PyQuery as pq
from common import *

EACH_LOOP_MAX_PAGE_COUNT = 200  # 单次缓存多少页的日志
EACH_PAGE_BLOG_COUNT = 100  # 每次请求获取的日志数量
COOKIE_INFO = {}
USER_AGENT = None
IS_STEP_ERROR_403_AND_404 = False
IS_LOGIN = False


# 检测登录状态
def check_login():
    if not COOKIE_INFO:
        return False
    index_url = "https://www.tumblr.com/"
    index_response = net.request(index_url, method="GET", cookies_list=COOKIE_INFO, header_list={"User-Agent": USER_AGENT}, is_auto_redirect=False)
    if index_response.status == 302 and index_response.getheader("Location") == "https://www.tumblr.com/dashboard":
        return True
    return False


# 获取首页，判断是否支持https以及是否启用safe-mode和"Show this blog on the web"
def get_index_setting(account_id):
    index_url = "https://%s.tumblr.com/" % account_id
    index_response = net.request(index_url, method="GET", is_auto_redirect=False)
    is_https = True
    is_private = False
    if index_response.status == 301:
        redirect_url = index_response.getheader("Location")
        if redirect_url.startswith("http://"):
            is_https = False
        is_private = False
        # raise crawler.CrawlerException("此账号已重定向第三方网站")
    elif index_response.status == 302:
        redirect_url = index_response.getheader("Location")
        if redirect_url.startswith("http://%s.tumblr.com/" % account_id):
            is_https = False
            index_url = "http://%s.tumblr.com/" % account_id
            index_response = net.request(index_url, method="GET", is_auto_redirect=False)
            if index_response.status == net.HTTP_RETURN_CODE_SUCCEED:
                return is_https, is_private
            elif index_response.status != 302:
                raise crawler.CrawlerException(crawler.request_failre(index_response.status))
            redirect_url = index_response.getheader("Location")
        if redirect_url.find("www.tumblr.com/safe-mode?url=") > 0:
            is_private = True
            if tool.find_sub_string(redirect_url, "?https://www.tumblr.com/safe-mode?url=").startswith("http://"):
                is_https = False
        # "Show this blog on the web" disabled
        elif redirect_url.find("//www.tumblr.com/login_required/%s" % account_id) > 0:
            is_private = True
            index_response = net.request(redirect_url, method="GET", cookies_list=COOKIE_INFO)
            if index_response.status == 404:
                raise crawler.CrawlerException("账号不存在")
    elif index_response.status == 404:
        raise crawler.CrawlerException("账号不存在")
    elif index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(index_response.status))
    return is_https, is_private


# 获取一页的日志地址列表
def get_one_page_post(account_id, page_count, is_https):
    if is_https:
        protocol_type = "https"
    else:
        protocol_type = "http"
    if page_count == 1:
        post_pagination_url = "%s://%s.tumblr.com/" % (protocol_type, account_id)
    else:
        post_pagination_url = "%s://%s.tumblr.com/page/%s" % (protocol_type, account_id, page_count)
    post_pagination_response = net.request(post_pagination_url, method="GET")
    result = {
        "is_over": False,  # 是否最后一页日志
        "post_info_list": [],  # 全部日志信息
    }
    if post_pagination_response.status == 404:
        log.info("%s 第%s页日志异常，重试" % (account_id, page_count))
        time.sleep(5)
        return get_one_page_post(account_id, page_count, is_https)
    # elif post_pagination_response.status in [503, 504, net.HTTP_RETURN_CODE_RETRY] and page_count > 1:
    #     # 服务器错误，跳过这页
    #     log.error("%s 第%s页日志无法访问，跳过" % (account_id, page_count))
    #     return result
    elif post_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(post_pagination_response.status))
    post_pagination_response_content = post_pagination_response.data.decode(errors="ignore")
    script_json_html = tool.find_sub_string(post_pagination_response_content, '<script type="application/ld+json">', "</script>").strip()
    if not script_json_html:
        result["is_over"] = True
        return result
    script_json = tool.json_decode(script_json_html)
    if script_json is None:
        raise crawler.CrawlerException("日志信息加载失败\n" + script_json_html)
    # 单条日志
    for post_info in crawler.get_json_value(script_json, "itemListElement", type_check=list):
        result_post_info = {
            "post_id": 0,  # 日志id
            "post_url": "",  # 日志地址
        }
        # 获取日志地址
        result_post_info["post_url"] = net.url_encode(crawler.get_json_value(post_info, "url", type_check=str))
        # 获取日志id
        post_id = tool.find_sub_string(result_post_info["post_url"], "/post/").split("/")[0]
        if not tool.is_integer(post_id):
            raise crawler.CrawlerException("日志地址%s截取日志id失败" % result_post_info["post_url"])
        result_post_info["post_id"] = int(post_id)
        result["post_info_list"].append(result_post_info)
    return result


# 获取一页的私人日志地址列表
def get_one_page_private_blog(account_id, page_count):
    post_pagination_url = "https://www.tumblr.com/svc/indash_blog"
    query_data = {
        "limit": EACH_PAGE_BLOG_COUNT,
        "offset": (page_count - 1) * EACH_PAGE_BLOG_COUNT,
        "post_id": "",
        "can_modify_safe_mode": "true",
        "should_bypass_safemode": "false",
        "should_bypass_safemode_forblog": "true",
        "should_bypass_tagfiltering": "false",
        "tumblelog_name_or_id": account_id,
    }
    header_list = {
        "Host": "www.tumblr.com",
        "Referer": "https://www.tumblr.com/dashboard/blog/%s/" % account_id,
        "User-Agent": USER_AGENT,
        "X-Requested-With": "XMLHttpRequest",
    }
    post_pagination_response = net.request(post_pagination_url, method="GET", fields=query_data, header_list=header_list, cookies_list=COOKIE_INFO,
                                           json_decode=True)
    result = {
        "is_over": False,  # 是不是最后一页日志
        "post_info_list": [],  # 全部日志信息
    }
    if post_pagination_response.status == 404:
        log.info("%s 第%s页日志异常，重试" % (account_id, page_count))
        time.sleep(5)
        return get_one_page_private_blog(account_id, page_count)
    elif post_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(post_pagination_response.status))
    if crawler.get_json_value(post_pagination_response.json_data, "meta", "status", type_check=int) != 200:
        raise crawler.CrawlerException("返回信息%s中'status'字段取值不正确" % post_pagination_response.json_data)
    post_info_list = crawler.get_json_value(post_pagination_response.json_data, "response", "posts", type_check=list)
    for post_info in post_info_list:
        result_post_info = {
            "has_video": False,  # 是不是包含视频
            "photo_url_list": [],  # 全部图片地址
            "post_id": 0,  # 日志id
            "post_url": "",  # 日志地址
            "video_url": "",  # 视频地址
        }
        # 获取日志地址
        result_post_info["post_url"] = net.url_encode(crawler.get_json_value(post_info, "post_url", type_check=str))
        # 获取日志id
        post_id = tool.find_sub_string(result_post_info["post_url"], "/post/").split("/")[0]
        if not tool.is_integer(post_id):
            raise crawler.CrawlerException("日志地址 %s 截取日志id失败" % result_post_info["post_url"])
        result_post_info["post_id"] = int(post_id)
        # 视频
        if crawler.get_json_value(post_info, "type", type_check=str) == "video":
            result_post_info["has_video"] = True
            # 获取视频地址
            max_width = 0
            video_url = None
            for video_info in crawler.get_json_value(post_info, "player", type_check=list):
                video_html = crawler.get_json_value(video_info, "embed_code", type_check=str)
                if video_html is False:
                    continue
                video_width = crawler.get_json_value(video_info, "width", type_check=int)
                if video_width > max_width:
                    temp_video_url = tool.find_sub_string(video_html, '<source src="', '"')
                    if temp_video_url:
                        video_url = temp_video_url
                        max_width = video_width
            if video_url is not None:
                result_post_info["video_url"] = video_url
        # 图片
        elif crawler.check_sub_key(("photos",), post_info):
            for photo_info in crawler.get_json_value(post_info, "photos", type_check=list):
                result_post_info["photo_url_list"].append(crawler.get_json_value(photo_info, "original_size", "url", type_check=str))
        result["post_info_list"].append(result_post_info)
    if len(post_info_list) < EACH_PAGE_BLOG_COUNT:
        result["is_over"] = True
    return result


# 获取日志页面
def get_post_page(post_url, post_id):
    post_response = net.request(post_url, method="GET")
    result = {
        "has_video": False,  # 是不是包含视频
        "is_delete": False,  # 是否已删除
        "photo_url_list": [],  # 全部图片地址
        "video_url": "",  # 视频地址
    }
    if post_response.status == 404:
        result["is_delete"] = True
        return result
    elif post_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(post_response.status))
    post_response_content = post_response.data.decode(errors="ignore")
    post_page_head = tool.find_sub_string(post_response_content, "<head", "</head>", const.IncludeStringMode.ALL)
    if not post_page_head:
        raise crawler.CrawlerException("页面截取正文失败\n" + post_response_content)
    # 获取og_type（页面类型的是视频还是图片或其他）
    og_type = tool.find_sub_string(post_page_head, '<meta property="og:type" content="', '" />')
    # 视频
    if og_type == "tumblr-feed:video":
        result["has_video"] = True
        # 获取图片地址
        photo_url = tool.find_sub_string(post_page_head, '<meta property="og:image" content="', '" />')
        if photo_url and photo_url.find("assets.tumblr.com/images/og/fb_landscape_share.png") == -1:
            if not check_photo_url_invalid(photo_url):
                result["photo_url_list"].append(photo_url)
        post_selector = pq(post_response_content).find("article")
        if post_selector.length > 1:
            post_selector = pq(post_response_content).find("article[data-post-id='%s']" % post_id)
            if post_selector.length == 0:
                post_selector = pq(post_response_content).find("article[id='%s']" % post_id)
        if post_selector.length <= 1:
            if post_selector.length == 0:
                video_selector = pq(post_response_content).find("source")
            else:
                video_selector = post_selector.find("source")
            if video_selector.length == 1:
                result["video_url"] = video_selector.attr("src")
            elif video_selector.length > 1:
                log.warning("%s存在多个source标签" % post_url)
    elif not og_type:
        script_json_html = tool.find_sub_string(post_page_head, '<script type="application/ld+json">', "</script>").strip()
        if not script_json_html:
            raise crawler.CrawlerException("正文截取og_type失败\n" + post_page_head)
        script_json = tool.json_decode(script_json_html)
        if script_json is None:
            raise crawler.CrawlerException("页面脚本数据解析失败\n" + script_json_html)
        image_info = crawler.get_json_value(script_json, "image", default_value=None)
        if image_info is None:
            pass
        elif isinstance(image_info, dict):
            for photo_url in crawler.get_json_value(image_info, "@list", original_data=script_json, type_check=list):
                if not check_photo_url_invalid(photo_url):
                    result["photo_url_list"].append(photo_url)
        elif isinstance(image_info, str):
            if not check_photo_url_invalid(image_info):
                result["photo_url_list"].append(image_info)
        else:
            raise crawler.CrawlerException("页面脚本%s中'image'字段类型错误" % script_json)
    else:
        # 获取全部图片地址
        photo_url_list = re.findall(r'"(https?://\d*[.]?media.tumblr.com/[^"]*)"', post_page_head)
        new_photo_url_list = {}
        for photo_url in photo_url_list:
            # 头像，跳过
            if photo_url.find("/avatar_") != -1 or photo_url[-9:] == "_75sq.gif" or photo_url[-9:] == "_75sq.jpg" or photo_url[-9:] == "_75sq.png":
                continue
            elif len(re.findall(r"/birthday\d_", photo_url)) == 1:
                continue
            elif check_photo_url_invalid(photo_url):
                continue
            photo_id, resolution = analysis_photo(photo_url)
            # 判断是否有分辨率更小的相同图片
            if photo_id in new_photo_url_list:
                photo_id, old_resolution = analysis_photo(new_photo_url_list[photo_id])
                if resolution < old_resolution:
                    continue
            new_photo_url_list[photo_id] = photo_url
        result["photo_url_list"] = list(new_photo_url_list.values())
    return result


def check_photo_url_invalid(photo_url):
    return photo_url[-4:] == ".pnj"


def analysis_photo(photo_url):
    temp_list = photo_url.split("/")[-1].split(".")[0].split("_")
    resolution = 0
    if temp_list[0] == "tumblr":
        if temp_list[1] == "inline" and not tool.is_integer(temp_list[2]):
            photo_id = temp_list[2]
        else:
            photo_id = temp_list[1]
        # http://78.media.tumblr.com/tumblr_livevtbzL31qzk5tao1_cover.jpg
        # http://78.media.tumblr.com/tumblr_ljkiptVlj61qg3k48o1_1302659992_cover.jpg
        if temp_list[-1] in ["cover", "og", "frame1"]:
            pass
        # https://78.media.tumblr.com/tumblr_lixa2piSdw1qc4p5zo1_500.jpg
        # https://78.media.tumblr.com/tumblr_lhrk7kBVz31qbijcho1_r1_500.gif
        # https://78.media.tumblr.com/4612757fb6b608d2d14939833ed2e244/tumblr_ouao969iP51rqmr8lo1_540.jpg
        elif tool.is_integer(temp_list[-1]):
            resolution = int(temp_list[-1])
        # https://78.media.tumblr.com/19b0b807d374ed9e4ed22caf74cb1ec0/tumblr_mxukamH4GV1s4or9ao1_500h.jpg
        elif temp_list[-1].endswith("h") and tool.is_integer(temp_list[-1][:-len("h")]):
            resolution = int(temp_list[-1][:-1])
        # https://78.media.tumblr.com/5c0b9f4e8ac839a628863bb5d7255938/tumblr_inline_p6ve89vOZA1uhchy5_250sq.jpg
        elif temp_list[-1].endswith("sq") and tool.is_integer(temp_list[-1][:-len("sq")]):
            photo_url = photo_url.replace("_250sq", "1280")
            resolution = 1280
        # http://78.media.tumblr.com/tumblr_m9rwkpsRwt1rr15s5.jpg
        # http://78.media.tumblr.com/afd60c3d469055cea4544fe848eeb266/tumblr_inline_n9gff0sXMl1rzbdqg.gif
        # https://78.media.tumblr.com/tumblr_o7ec46zp5M1vpohsl_frame1.jpg
        # https://78.media.tumblr.com/tumblr_odtdlgTAbg1sg1lga_r1_frame1.jpg
        elif (
                len(temp_list) == 2 or
                (len(temp_list) == 3 and temp_list[1] == "inline") or
                (len(temp_list) == 3 and temp_list[2] == "frame1") or
                (len(temp_list) == 4 and temp_list[2] == "r1" and temp_list[3] == "frame1") or
                (len(temp_list) == 3 and temp_list[2] == "smart1") or
                (len(temp_list) == 4 and temp_list[2] == "r1" and temp_list[3] == "smart1")
        ):
            pass
        else:
            log.warning("未知图片地址类型1：" + photo_url)
    # http://78.media.tumblr.com/TVeEqrZktkygbzi2tUbbKMGXo1_1280.jpg
    elif not tool.is_integer(temp_list[0]) and tool.is_integer(temp_list[-1]):
        photo_id = temp_list[0]
        resolution = int(temp_list[-1])
    #  http://78.media.tumblr.com/_1364612391_cover.jpg
    elif len(temp_list) == 3 and temp_list[0] == "" and tool.is_integer(temp_list[1]) and temp_list[2] == "cover":
        photo_id = temp_list[1]
    # http://78.media.tumblr.com/3562275_500.jpg
    elif len(temp_list) == 2 and tool.is_integer(temp_list[0]) and tool.is_integer(temp_list[-1]):
        photo_id = temp_list[0]
        resolution = int(temp_list[1])
    # http://78.media.tumblr.com/15427139_r1_500.jpg
    elif len(temp_list) == 3 and tool.is_integer(temp_list[0]) and tool.is_integer(temp_list[-1]) and temp_list[1][0] == "r":
        photo_id = temp_list[0]
        resolution = int(temp_list[2])
    else:
        photo_id = photo_url.split("/")[-1]
        log.warning("未知图片地址类型2：" + photo_url)
    if len(photo_id) < 15 and not (tool.is_integer(photo_id) and int(photo_id) < 2000000000):
        log.warning("未知图片地址类型3：" + photo_url)
    return photo_id, resolution


# 获取视频播放页面
def get_video_play_page(account_id, post_id, is_https):
    if is_https:
        protocol_type = "https"
    else:
        protocol_type = "http"
    video_play_url = "%s://www.tumblr.com/video/%s/%s/0" % (protocol_type, account_id, post_id)
    video_play_response = net.request(video_play_url, method="GET", is_auto_redirect=False)
    result = {
        "is_password": False,  # 是否加密
        "video_url": "",  # 视频地址
    }
    if video_play_response.status == 301:
        video_play_url = video_play_response.getheader("Location")
        if video_play_url is not None:
            video_play_response = net.request(video_play_url, method="GET")
    video_play_response_content = video_play_response.data.decode(errors="ignore")
    if video_play_response.status == 403 and video_play_response_content.find("You do not have permission to access this page.") >= 0:
        result["is_password"] = True
        return result
    elif video_play_response.status == 404:
        log.info("日志%s视频信息页访问异常，重试" % post_id)
        time.sleep(30)
        return get_video_play_page(account_id, post_id, is_https)
    elif video_play_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_play_response.status))
    video_url_find = re.findall(r'<source src="(https?://%s.tumblr.com/video_file/[^"]*)" type="[^"]*"' % account_id, video_play_response_content)
    if len(video_url_find) == 1:
        if tool.is_integer(video_url_find[0].split("/")[-1]):
            result["video_url"] = "/".join(video_url_find[0].split("/")[:-1])
        result["video_url"] = video_url_find[0]
    elif len(video_url_find) == 0:
        # 第三方视频
        pass
    else:
        raise crawler.CrawlerException("页面截取视频地址失败\n" + video_play_response_content)
    return result


class Tumblr(crawler.Crawler):
    def __init__(self, **kwargs):
        global COOKIE_INFO, IS_STEP_ERROR_403_AND_404, USER_AGENT

        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            const.SysConfigKey.DOWNLOAD_PHOTO: True,
            const.SysConfigKey.DOWNLOAD_VIDEO: True,
            const.SysConfigKey.GET_COOKIE: ("tumblr.com", "www.tumblr.com"),
            const.SysConfigKey.SET_PROXY: True,
            const.SysConfigKey.APP_CONFIG: (
                ("USER_AGENT", "", const.ConfigAnalysisMode.RAW),
                ("IS_STEP_ERROR_403_AND_404", False, const.ConfigAnalysisMode.BOOLEAN)
            ),
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 设置全局变量，供子线程调用
        COOKIE_INFO = self.cookie_value
        USER_AGENT = self.app_config["USER_AGENT"]
        IS_STEP_ERROR_403_AND_404 = self.app_config["IS_STEP_ERROR_403_AND_404"]

        # 解析存档文件
        # account_id  last_post_id
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

        # 下载线程
        self.crawler_thread = CrawlerThread

    def init(self):
        global IS_LOGIN
        # 检测登录状态
        if check_login():
            IS_LOGIN = True
            return

        while True:
            input_str = input(tool.get_time() + " 没有检测到账号登录状态，可能无法解析受限制的账号，继续程序(C)ontinue？或者退出程序(E)xit？:")
            input_str = input_str.lower()
            if input_str in ["e", "exit"]:
                tool.process_exit()
            elif input_str in ["c", "continue"]:
                IS_LOGIN = False
                break


class CrawlerThread(crawler.CrawlerThread):
    is_https = True
    is_private = False

    def __init__(self, main_thread, single_save_data):
        self.index_key = self.display_name = single_save_data[0]  # account id
        crawler.CrawlerThread.__init__(self, main_thread, single_save_data)

    # 获取偏移量，避免一次查询过多页数
    def get_offset_page_count(self):
        start_page_count = 1
        while EACH_LOOP_MAX_PAGE_COUNT > 0:
            start_page_count += EACH_LOOP_MAX_PAGE_COUNT
            post_pagination_description = "第%s页日志" % start_page_count
            self.start_parse(post_pagination_description)
            try:
                if self.is_private:
                    post_pagination_response: dict = get_one_page_private_blog(self.index_key, start_page_count)
                else:
                    post_pagination_response: dict = get_one_page_post(self.index_key, start_page_count, self.is_https)
            except crawler.CrawlerException as e:
                self.error(e.http_error(post_pagination_description))
                raise
            # 这页没有任何内容，返回上一个检查节点
            if post_pagination_response["is_over"]:
                start_page_count -= EACH_LOOP_MAX_PAGE_COUNT
                break
            # 这页已经匹配到存档点，返回上一个节点
            if post_pagination_response["post_info_list"][-1]["post_id"] < int(self.single_save_data[1]):
                start_page_count -= EACH_LOOP_MAX_PAGE_COUNT
                break
            self.info("前%s页日志全部符合条件，跳过%s页后继续查询" % (start_page_count, EACH_LOOP_MAX_PAGE_COUNT))
        return start_page_count

    # 获取所有可下载日志
    def get_crawl_list(self, page_count):
        unique_list = []
        post_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的日志
        while not is_over:
            post_pagination_description = "第%s页日志" % page_count
            self.start_parse(post_pagination_description)
            try:
                if self.is_private:
                    post_pagination_response: dict = get_one_page_private_blog(self.index_key, page_count)
                else:
                    post_pagination_response: dict = get_one_page_post(self.index_key, page_count, self.is_https)
            except crawler.CrawlerException as e:
                self.error(e.http_error(post_pagination_description))
                raise
            if not self.is_private and post_pagination_response["is_over"]:
                break
            self.parse_result(post_pagination_description, post_pagination_response["post_info_list"])

            # 寻找这一页符合条件的日志
            for post_info in post_pagination_response["post_info_list"]:
                # 检查是否达到存档记录
                if post_info["post_id"] > int(self.single_save_data[1]):
                    # 新增信息页导致的重复判断
                    if post_info["post_id"] in unique_list:
                        continue
                    else:
                        post_info_list.append(post_info)
                        unique_list.append(post_info["post_id"])
                else:
                    is_over = True
                    break

            if not is_over:
                if post_pagination_response["is_over"]:
                    is_over = True
                else:
                    page_count += 1
        return post_info_list

    # 解析单个日志
    def crawl_post(self, post_info):
        post_url = post_info["post_url"][:post_info["post_url"].find(str(post_info["post_id"])) + len(str(post_info["post_id"]))]
        post_description = "日志%s(%s)" % (post_info["post_id"], post_url)
        self.start_parse(post_description)

        if self.is_private:
            has_video = post_info["has_video"]
            photo_url_list = post_info["photo_url_list"]
            video_url = post_info["video_url"]
        else:
            # 获取日志
            try:
                post_response = get_post_page(post_info["post_url"], post_info["post_id"])
            except crawler.CrawlerException as e:
                self.error(e.http_error(post_description))
                raise

            if post_response["is_delete"]:
                if post_info["post_url"].find("/hey-this-post-may-contain-adult-content-so-weve") > 0 or \
                        post_info["post_url"].find(urllib.parse.quote("/この投稿には成人向けコンテンツか含まれている可能性があるため非公開となりました-もっと知る")) > 0:
                    self.info("%s 已被删除，跳过" % post_description)
                else:
                    self.error("%s 已被删除，跳过" % post_description)

            has_video = post_response["has_video"]
            photo_url_list = post_response["photo_url_list"]
            video_url = post_response["video_url"]

        # 视频下载
        while self.main_thread.is_download_video and has_video:
            if video_url is None:
                try:
                    video_play_response = get_video_play_page(self.index_key, post_info["post_id"], self.is_https)
                except crawler.CrawlerException as e:
                    self.error(e.http_error(post_description))
                    raise

                if video_play_response["is_password"]:
                    self.error("%s 视频需要密码，跳过" % post_description)
                    break

                video_url = video_play_response["video_url"]

            # 第三方视频，跳过
            if video_url is None:
                self.error("%s 存在第三方视频，跳过" % post_description)
                break

            video_path = os.path.join(self.main_thread.video_download_path, self.index_key, "%012d.mp4" % post_info["post_id"])
            video_description = "日志%s(%s)视频" % (post_info["post_id"], post_info["post_url"])
            if self.download(video_url, video_path, video_description, failure_callback=self.video_download_failure_callback, auto_multipart_download=True):
                self.temp_path_list.append(video_path)  # 设置临时目录
                self.total_video_count += 1  # 计数累加
            break

        # 图片下载
        if self.main_thread.is_download_photo and len(photo_url_list) > 0:
            self.parse_result(post_description + "图片", photo_url_list)

            photo_index = 1
            for photo_url in photo_url_list:
                photo_name = "%012d_%02d.%s" % (post_info["post_id"], photo_index, net.get_file_extension(photo_url))
                photo_path = os.path.join(self.main_thread.photo_download_path, self.index_key, photo_name)
                photo_description = "日志%s(%s)第%s张图片" % (post_info["post_id"], post_info["post_url"], photo_index)
                if self.download(photo_url, photo_path, photo_description, failure_callback=self.photo_download_failure_callback):
                    self.temp_path_list.append(photo_path)  # 设置临时目录
                    self.total_photo_count += 1  # 计数累加
                photo_index += 1

        # 日志内图片和视频全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.single_save_data[1] = str(post_info["post_id"])  # 设置存档记录

    def video_download_failure_callback(self, video_url, video_path, video_description, download_return: net.Download):
        if download_return.code == 403 and video_url.find("_r1_720") != -1:
            video_url = video_url.replace("_r1_720", "_r1")
            download_return = net.Download(video_url, video_path, auto_multipart_download=True)
            if download_return.status == net.Download.DOWNLOAD_SUCCEED:
                self.info("%s 下载成功" % video_description)
                return False
        if IS_STEP_ERROR_403_AND_404 and download_return.code in [403, 404]:
            self.info("%s %s 下载失败，原因：%s" % (video_description, video_url, crawler.download_failre(download_return.code)))
            return False
        return True

    def photo_download_failure_callback(self, photo_url, photo_path, photo_description, download_return: net.Download):
        if IS_STEP_ERROR_403_AND_404 and download_return.code in [403, 404]:
            self.info("%s %s 下载失败，原因：%s" % (photo_description, photo_url, crawler.download_failre(download_return.code)))
            return False
        return True

    def _run(self):
        try:
            self.is_https, self.is_private = get_index_setting(self.index_key)
        except crawler.CrawlerException as e:
            self.error(e.http_error("账号设置"))
            raise

            # 未登录&开启safe mode直接退出
        if not IS_LOGIN and self.is_private:
            self.error("账号只限登录账号访问，跳过")
            tool.process_exit()

        # 查询当前任务大致需要从多少页开始爬取
        start_page_count = self.get_offset_page_count()

        while start_page_count >= 1:
            # 获取所有可下载日志
            post_info_list = self.get_crawl_list(start_page_count)
            self.info("需要下载的全部日志解析完毕，共%s个" % len(post_info_list))

            # 从最早的日志开始下载
            while len(post_info_list) > 0:
                self.crawl_post(post_info_list.pop())

            start_page_count -= EACH_LOOP_MAX_PAGE_COUNT


if __name__ == "__main__":
    Tumblr().main()
