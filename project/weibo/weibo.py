# -*- coding:UTF-8  -*-
"""
微博图片爬虫
https://www.weibo.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import re
import time
import urllib.parse
from common import *
from project.meipai import meipai

EACH_PAGE_PHOTO_COUNT = 20  # 每次请求获取的图片数量
INIT_SINCE_ID = "9999999999999999"
COOKIE_INFO = {}


# 检测登录状态
def check_login():
    if "SUB" not in COOKIE_INFO or not COOKIE_INFO["SUB"]:
        return False
    index_url = "https://weibo.com/"
    index_response = net.request(index_url, method="GET", cookies_list=COOKIE_INFO)
    if index_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        return index_response.data.decode(errors="ignore").find("$CONFIG[\'uid\']=\'") >= 0
    return False


# 使用浏览器保存的cookie模拟登录请求，获取一个session级别的访问cookie
def init_session():
    login_url = "https://login.sina.com.cn/sso/login.php"
    query_data = {"url": "https://weibo.com"}
    login_response = net.request(login_url, method="GET", fields=query_data, cookies_list=COOKIE_INFO)
    if login_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        COOKIE_INFO.update(net.get_cookies_from_response_header(login_response.headers))
        return True
    return False


# 获取账号首页
def get_account_index_page(account_id):
    account_index_url = f"https://weibo.com/{account_id}"
    result = {
        "account_page_id": None,  # 账号page id
    }
    account_index_response = net.request(account_index_url, method="GET", cookies_list=COOKIE_INFO)
    if account_index_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        # 获取账号page id
        account_page_id = tool.find_sub_string(account_index_response.data.decode(errors="ignore"), "$CONFIG['page_id']='", "'")
        if not tool.is_integer(account_page_id):
            raise crawler.CrawlerException("账号不存在")
        result["account_page_id"] = account_page_id
    else:
        raise crawler.CrawlerException(crawler.request_failre(account_index_response.status))
    return result


# 检测图片是不是被微博自动删除的文件
def check_photo_invalid(file_path):
    file_md5 = file.get_file_md5(file_path)
    if file_md5 in ["14f2559305a6c96608c474f4ca47e6b0", "37b9e6dec174b68a545c852c63d4645a", "4cf24fe8401f7ab2eba2c6cb82dffb0e", "78b5b9e32f3b30b088fef0e6c5ed0901",
                    "7bd88df2b5be33e1a79ac91e7d0376b5", "7e80fb31ec58b1ca2fb3548480e1b95e", "82af4714a8b2a5eea3b44726cfc9920d"]:
        return True
    return False


# 获取一页的图片信息
def get_one_page_photo(account_id, page_count):
    photo_pagination_url = "https://photo.weibo.com/photos/get_all"
    query_data = {
        "uid": account_id,
        "count": EACH_PAGE_PHOTO_COUNT,
        "page": page_count,
        "type": "3",
    }
    result = {
        "photo_info_list": [],  # 全部图片信息
        "is_over": False,  # 是否最后一页图片
    }
    photo_pagination_response = net.request(photo_pagination_url, method="GET", fields=query_data, cookies_list=COOKIE_INFO, json_decode=True)
    if photo_pagination_response.status == net.HTTP_RETURN_CODE_JSON_DECODE_ERROR and photo_pagination_response.data.find('<p class="txt M_txtb">用户不存在或者获取用户信息失败</p>'.encode()) >= 0:
        raise crawler.CrawlerException("账号不存在")
    elif photo_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(photo_pagination_response.status))
    for photo_info in crawler.get_json_value(photo_pagination_response.json_data, "data", "photo_list", type_check=list):
        result_photo_info = {
            "photo_id": None,  # 图片上传时间
            "photo_time": None,  # 图片上传时间
            "photo_url": None,  # 图片地址
        }
        # 获取图片上传时间
        result_photo_info["photo_time"] = crawler.get_json_value(photo_info, "timestamp", type_check=int)
        # 获取图片id
        result_photo_info["photo_id"] = crawler.get_json_value(photo_info, "photo_id", type_check=int)
        # 获取图片地址
        result_photo_info["photo_url"] = crawler.get_json_value(photo_info, "pic_host", type_check=str) + "/large/" + crawler.get_json_value(photo_info, "pic_name", type_check=str)
        result["photo_info_list"].append(result_photo_info)
    # 检测是不是还有下一页 总的图片数量 / 每页显示的图片数量 = 总的页数
    result["is_over"] = len(result["photo_info_list"]) == 0 or page_count >= (crawler.get_json_value(photo_pagination_response.json_data, "data", "total", type_check=int) / EACH_PAGE_PHOTO_COUNT)
    return result


# 获取一页的视频信息
# page_id -> 1005052535836307
def get_one_page_video(account_id, account_page_id, since_id):
    # https://weibo.com/p/aj/album/loading?ajwvr=6&type=video&owner_uid=1642591402&viewer_uid=&since_id=4341680691744416&page_id=1002061642591402&page=2&ajax_call=1&__rnd=1551011542206
    video_pagination_url = "https://weibo.com/p/aj/album/loading"
    query_data = {
        "type": "video",
        "owner_uid": account_id,
        "viewer_uid": "0",
        "since_id": since_id,
        "page_id": account_page_id,
        "ajax_call": "1",
        "__rnd": int(time.time() * 1000),
    }
    result = {
        "next_page_since_id": None,  # 下一页视频指针
        "video_play_url_list": [],  # 全部视频地址
    }
    video_pagination_response = net.request(video_pagination_url, method="GET", fields=query_data, cookies_list=COOKIE_INFO, json_decode=True)
    if video_pagination_response.status == net.HTTP_RETURN_CODE_JSON_DECODE_ERROR:
        time.sleep(5)
        log.step(f"since_id：{since_id}页视频解返回异常")
        return get_one_page_video(account_id, account_page_id, since_id)
    if video_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_pagination_response.status))
    response_data = crawler.get_json_value(video_pagination_response.json_data, "data", type_check=str)
    # 获取视频播放地址
    result["video_play_url_list"] = re.findall('<a target="_blank" href="([^"]*)"><div ', response_data)
    if len(result["video_play_url_list"]) == 0:
        if response_data.find("还没有发布过视频") == -1 and response_data.find("<!-- 懒加载的加载条，当不出现加载条时，懒加载停止 -->") == -1:
            raise crawler.CrawlerException(f"返回信息{video_pagination_response.json_data}中匹配视频地址失败")
    # 获取下一页视频的指针
    next_page_since_id = tool.find_sub_string(response_data, "&since_id=", '">')
    if next_page_since_id:
        if not tool.is_integer(next_page_since_id):
            raise crawler.CrawlerException(f"返回信息{video_pagination_response.json_data}中截取下一页指针失败")
        result["next_page_since_id"] = next_page_since_id
    return result


# 从视频播放页面中提取下载地址
def get_video_url(video_play_url, error_count=0):
    video_url = ""
    # http://miaopai.com/show/Gmd7rwiNrc84z5h6S9DhjQ__.htm
    if video_play_url.find("miaopai.com/") >= 0:  # 秒拍
        pass
        # if video_play_url.find("miaopai.com/show/") >= 0:
        #     video_id = tool.find_sub_string(video_play_url, "miaopai.com/show/", ".htm")
        #     video_url = miaopai.get_video_info_page(video_id)["video_url"]
        # # http://n.miaopai.com/media/SJ9InO25bxrtVhOfGA3KoniJM3gP2XX0.htm
        # elif video_play_url.find("miaopai.com/media/") >= 0:
        #     video_id = tool.find_sub_string(video_play_url, "miaopai.com/media/", ".htm")
        #     video_url = miaopai.get_video_info_page_new(video_id)["video_url"]
        # else:
        #     raise crawler.CrawlerException(f"未知的第三方视频 {video_play_url}")
    # https://video.weibo.com/show?fid=1034:e608e50d5fa95410748da61a7dfa2bff
    elif video_play_url.find("video.weibo.com/show?fid=") >= 0 or video_play_url.find("weibo.com/tv/v") >= 0:  # 微博视频
        video_play_response = net.request(video_play_url, method="GET", cookies_list=COOKIE_INFO)
        if video_play_response.status == net.HTTP_RETURN_CODE_SUCCEED:
            video_play_response_content = video_play_response.data.decode(errors="ignore")
            video_sources = tool.find_sub_string(video_play_response_content, 'video-sources="', '"')
            if video_sources:
                video_url = ""
                resolution_to_url = {}
                for video_info in video_sources.split("&"):
                    video_quality, temp_video_url = video_info.split("=")
                    if temp_video_url:
                        if video_quality == "fluency":
                            video_url = temp_video_url
                        elif tool.is_integer(video_quality):
                            resolution_to_url[int(video_quality)] = temp_video_url
                if len(resolution_to_url) > 0:
                    video_url = resolution_to_url[max(resolution_to_url)]
                video_url = urllib.parse.unquote(video_url)
            else:
                video_url = tool.find_sub_string(video_play_response_content, 'flashvars="list=', '"')
            if not video_url:
                if video_play_response_content.find("抱歉，网络繁忙") > 0:  # https://video.weibo.com/show?fid=1034:15691c2fd85cb3986bcbc0fecc20f373
                    if error_count >= 5:
                        return video_url
                    log.step(f"视频{video_play_url}播放页访问异常，重试")
                    time.sleep(5)
                    error_count += 1
                    return get_video_url(video_play_url, error_count)
                elif video_play_response_content.find("啊哦，此视频已被删除。") > 0:  # http://video.weibo.com/show?fid=1034:14531c4838e14a8c3f2a3d35e33cab5e
                    video_url = ""
                    return video_url
                raise crawler.CrawlerException("页面截取视频地址失败\n" + video_play_response_content)
            video_url = urllib.parse.unquote(video_url)
            if video_url.find("//") == 0:
                video_url = "https:" + video_url
        elif video_play_response.status in [404, net.HTTP_RETURN_CODE_TOO_MANY_REDIRECTS]:
            video_url = ""
        else:
            raise crawler.CrawlerException(crawler.request_failre(video_play_response.status))
    # https://www.meipai.com/media/98089758
    elif video_play_url.find("www.meipai.com/media") >= 0:  # 美拍
        video_id = tool.find_sub_string(video_play_url, "www.meipai.com/media/")
        video_info_response = meipai.get_video_play_page(video_id)
        if not video_info_response["is_delete"]:
            video_url = video_info_response["video_url"]
    # https://v.xiaokaxiu.com/v/0YyG7I4092d~GayCAhwdJQ__.html
    elif video_play_url.find("v.xiaokaxiu.com/v/") >= 0:  # 小咖秀
        video_id = video_play_url.split("/")[-1].split(".")[0]
        video_url = f"https://gslb.miaopai.com/stream/{video_id}.mp4"
    elif video_play_url.find("//v.youku.com/v_show/") > 0 or video_play_url.find("//www.weishi.com/t/") > 0:
        pass
    else:  # 其他视频，暂时不支持，收集看看有没有
        log.notice(f"未知的第三方视频 {video_play_url}")
    return video_url


class Weibo(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_DOWNLOAD_VIDEO: True,
            crawler.SYS_GET_COOKIE: ("sina.com.cn", "login.sina.com.cn"),
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 设置全局变量，供子线程调用
        COOKIE_INFO.update(self.cookie_value)

        # 解析存档文件
        # account_id  last_photo_id  video_count  last_video_url  (account_name)
        self.save_data = crawler.read_save_data(self.save_data_path, 0, ["", "0", "0", ""])

        # 检测登录状态
        if not check_login():
            # 如果没有获得登录相关的cookie，则模拟登录并更新cookie
            if init_session() and check_login():
                pass
            else:
                log.error("没有检测到登录信息")
                tool.process_exit()

        # 下载线程
        self.download_thread = Download


class Download(crawler.DownloadThread):
    def __init__(self, single_save_data, main_thread):
        self.index_key = single_save_data[0]  # account id
        if len(single_save_data) >= 5 and single_save_data[4]:
            self.display_name = single_save_data[4]
        else:
            self.display_name = single_save_data[0]
        crawler.DownloadThread.__init__(self, single_save_data, main_thread)

    def _run(self):
        # 图片下载
        if self.main_thread.is_download_photo:
            # 获取所有可下载图片
            photo_info_list = self.get_crawl_photo_list()
            self.step(f"需要下载的全部图片解析完毕，共{len(photo_info_list)}张")

            # 从最早的图片开始下载
            while len(photo_info_list) > 0:
                if not self.crawl_photo(photo_info_list.pop()):
                    break
                self.main_thread_check()  # 检测主线程运行状态

        # 视频下载
        if self.main_thread.is_download_video:
            # 获取所有可下载视频
            video_play_url_list = self.get_crawl_video_list()
            self.step(f"需要下载的全部视频片解析完毕，共{len(video_play_url_list)}个")

            # 从最早的图片开始下载
            while len(video_play_url_list) > 0:
                if not self.crawl_video(video_play_url_list.pop()):
                    break
                self.main_thread_check()  # 检测主线程运行状态

    # 获取所有可下载图片
    def get_crawl_photo_list(self):
        page_count = 1
        unique_list = []
        photo_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的图片
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step(f"开始解析第{page_count}页图片")

            # 获取指定一页图片的信息
            try:
                photo_pagination_response = get_one_page_photo(self.index_key, page_count)
            except crawler.CrawlerException as e:
                self.error(e.http_error(f"第{page_count}页图片"))
                raise

            self.trace(f"第{page_count}页解析的全部图片：{photo_pagination_response['photo_info_list']}")
            self.step(f"第{page_count}页解析获取{len(photo_pagination_response['photo_info_list'])}张图片")

            # 寻找这一页符合条件的图片
            for photo_info in photo_pagination_response["photo_info_list"]:
                # 检查是否达到存档记录
                if photo_info["photo_id"] > int(self.single_save_data[1]):
                    # 新增图片导致的重复判断
                    if photo_info["photo_id"] in unique_list:
                        continue
                    else:
                        photo_info_list.append(photo_info)
                        unique_list.append(photo_info["photo_id"])
                else:
                    is_over = True
                    break

            if not is_over:
                if photo_pagination_response["is_over"]:
                    is_over = True
                else:
                    page_count += 1

        return photo_info_list

    # 获取所有可下载视频
    def get_crawl_video_list(self):
        # 获取账号首页
        try:
            account_index_response = get_account_index_page(self.index_key)
        except crawler.CrawlerException as e:
            self.error(e.http_error("首页"))
            raise

        video_play_url_list = []
        since_id = INIT_SINCE_ID
        is_over = False
        # 获取全部还未下载过需要解析的视频
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step(f"开始解析since_id：{since_id}页视频")

            # 获取指定时间点后的一页视频信息
            try:
                video_pagination_response = get_one_page_video(self.index_key, account_index_response["account_page_id"], since_id)
            except crawler.CrawlerException as e:
                self.error(e.http_error(f"since_id：{since_id}后一页视频"))
                raise

            self.trace(f"since_id：{since_id}页解析的全部视频：{video_pagination_response['video_play_url_list']}")
            self.step(f"since_id：{since_id}页解析获取{len(video_pagination_response['video_play_url_list'])}个视频")

            # 寻找这一页符合条件的视频
            for video_play_url in video_pagination_response["video_play_url_list"]:
                # 检查是否达到存档记录
                if self.single_save_data[3] != video_play_url:
                    video_play_url_list.append(video_play_url)
                else:
                    is_over = True
                    break

            if not is_over:
                if video_pagination_response["next_page_since_id"] is None:
                    is_over = True
                    # todo 没有找到历史记录如何处理
                    # 有历史记录，但此次直接获取了全部视频
                    if self.single_save_data[3] != "" and len(video_play_url_list) > 0:
                        self.error("没有找到上次下载的最后一个视频地址")
                else:
                    # 设置下一页指针
                    since_id = video_pagination_response["next_page_since_id"]

        return video_play_url_list

    # 下载图片
    def crawl_photo(self, photo_info):
        self.step(f"开始下载图片{photo_info['photo_id']} {photo_info['photo_url']}")

        photo_file_path = os.path.join(self.main_thread.photo_download_path, self.display_name, f"%16d.{net.get_file_extension(photo_info['photo_url'], 'jpg')}" % photo_info["photo_id"])
        download_return = net.Download(photo_info["photo_url"], photo_file_path)
        if download_return.status == net.Download.DOWNLOAD_SUCCEED:
            if check_photo_invalid(photo_file_path):
                path.delete_dir_or_file(photo_file_path)
                self.error(f"图片{photo_info['photo_id']} {photo_info['photo_url']} 资源已被限制，跳过")
            else:
                self.total_photo_count += 1  # 计数累加
                self.step(f"图片{photo_info['photo_id']}下载成功")
        else:
            if download_return.code == 403:
                self.error(f"图片{photo_info['photo_id']} {photo_info['photo_url']} 资源已被限制，跳过")
            else:
                self.error(f"图片{photo_info['photo_id']} {photo_info['photo_url']} 下载失败，原因：{crawler.download_failre(download_return.code)}")
                if self.check_download_failure_exit(False):
                    return False

        # 图片下载完毕
        self.single_save_data[1] = str(photo_info["photo_id"])  # 设置存档记录
        return True

    # 解析单个视频
    def crawl_video(self, video_play_url):
        video_index = int(self.single_save_data[2]) + 1
        self.step(f"开始解析第{video_index}个视频 {video_play_url}")

        # 获取这个视频的下载地址
        try:
            video_url = get_video_url(video_play_url)
        except crawler.CrawlerException as e:
            self.error(e.http_error(f"第{video_index}个视频 {video_play_url}"))
            raise

        if video_url == "":
            self.single_save_data[3] = video_play_url  # 设置存档记录
            self.error(f"第{video_index}个视频 {video_play_url} 跳过")
            return

        self.step(f"开始下载第{video_index}个视频 {video_url}")

        video_file_path = os.path.join(self.main_thread.video_download_path, self.display_name, "%04d.mp4" % video_index)
        download_return = net.Download(video_url, video_file_path, auto_multipart_download=True)
        if download_return.status == net.Download.DOWNLOAD_SUCCEED:
            self.total_video_count += 1  # 计数累加
            self.step(f"第{video_index}个视频下载成功")
        else:
            self.error(f"第{video_index}个视频 {video_play_url}（{video_url}) 下载失败，原因：{crawler.download_failre(download_return.code)}")
            if self.check_download_failure_exit(False):
                return False

        # 视频下载完毕
        self.single_save_data[2] = str(video_index)  # 设置存档记录
        self.single_save_data[3] = video_play_url  # 设置存档记录
        return True


if __name__ == "__main__":
    Weibo().main()
