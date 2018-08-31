# -*- coding:UTF-8  -*-
"""
网络访问类
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import json
import math
import os
import random
import re
import ssl
import time
import threading
import urllib3

try:
    from . import file, output, path, tool
except ImportError:
    from common import file, output, path, tool

# https://www.python.org/dev/peps/pep-0476/
# disable urllib3 HTTPS warning
urllib3.disable_warnings()
# disable URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed (_ssl.c:590)>
ssl._create_default_https_context = ssl._create_unverified_context

SIZE_KB = 2 ** 10  # 1KB = 多少字节
SIZE_MB = 2 ** 20  # 1MB = 多少字节
SIZE_GB = 2 ** 30  # 1GB = 多少字节

# 读取网络相关配置
DEFAULT_NET_CONFIG = {
    "HTTP_CONNECTION_TIMEOUT": 10,  # 网络访问连接超时的秒数
    "HTTP_READ_TIMEOUT": 30,  # 网络访问读取超时的秒数
    "HTTP_REQUEST_RETRY_COUNT": 10,  # 网络访问自动重试次数
    "DOWNLOAD_CONNECTION_TIMEOUT": 10,  # 下载文件连接超时的秒数
    "DOWNLOAD_READ_TIMEOUT": 60,  # 下载文件读取超时的秒数
    "DOWNLOAD_RETRY_COUNT": 10,  # 下载文件自动重试次数
    "DOWNLOAD_LIMIT_SIZE": 1.5 * SIZE_GB,  # 下载文件超过多少字节跳过不下载
    "DOWNLOAD_MULTI_THREAD_MIN_SIZE": 50 * SIZE_MB,  # 下载文件超过多少字节后开始使用多线程下载
    "DOWNLOAD_MULTI_THREAD_MIN_BLOCK_SIZE": 10 * SIZE_MB,  # 多线程下载中单个线程下载的字节数下限（线程总数下限=文件大小/单个线程下载的字节数下限）
    "DOWNLOAD_MULTI_THREAD_MAX_BLOCK_SIZE": 100 * SIZE_MB,  # 多线程下载中单个线程下载的字节数上限（线程总数上限=文件大小/单个线程下载的字节数上限）
}
NET_CONFIG = tool.json_decode(file.read_file(os.path.join(os.path.dirname(__file__), "net_config.json")), DEFAULT_NET_CONFIG)

# 连接池
HTTP_CONNECTION_POOL = None
PROXY_HTTP_CONNECTION_POOL = None
# 网络访问相关阻塞/继续事件
thread_event = threading.Event()
thread_event.set()
# 退出标志
EXIT_FLAG = False
# response header中Content-Type对应的Mime字典
MIME_DICTIONARY = None
# 网络访问返回值
HTTP_RETURN_CODE_RETRY = 0
HTTP_RETURN_CODE_URL_INVALID = -1  # 地址不符合规范（非http:// 或者 https:// 开头）
HTTP_RETURN_CODE_JSON_DECODE_ERROR = -2  # 返回数据不是JSON格式，但返回状态是200
HTTP_RETURN_CODE_DOMAIN_NOT_RESOLVED = -3  # 域名无法解析
HTTP_RETURN_CODE_RESPONSE_TO_LARGE = -4  # 文件太大
HTTP_RETURN_CODE_TOO_MANY_REDIRECTS = -5  # 重定向次数过多
HTTP_RETURN_CODE_EXCEPTION_CATCH = -10
HTTP_RETURN_CODE_SUCCEED = 200


class ErrorResponse(object):
    """Default http_request() response object(exception return)"""
    def __init__(self, status=-1):
        self.status = status
        self.data = b''
        self.headers = {}
        self.json_data = []


def init_http_connection_pool():
    """init urllib3 connection pool"""
    global HTTP_CONNECTION_POOL
    HTTP_CONNECTION_POOL = urllib3.PoolManager(retries=False)


def set_proxy(ip, port):
    """init urllib3 proxy connection pool"""
    if not str(port).isdigit() or int(port) <= 0:
        return
    match = re.match("((25[0-5]|2[0-4]\d|((1\d{2})|([1-9]?\d)))\.){3}(25[0-5]|2[0-4]\d|((1\d{2})|([1-9]?\d)))", ip)
    if not match or match.group() != ip:
        return
    global PROXY_HTTP_CONNECTION_POOL
    PROXY_HTTP_CONNECTION_POOL = urllib3.ProxyManager("http://%s:%s" % (ip, port), retries=False)
    output.print_msg("设置代理成功(%s:%s)" % (ip, port))


def build_header_cookie_string(cookies_list):
    """generate cookies string for http request header

    :param cookies_list:
        {
            "cookie1":“value1",
            "cookie2":“value2"
        }

    :return:
        cookie1=value1; cookie2=value2
    """
    if not cookies_list:
        return ""
    temp_string = []
    for cookie_name in cookies_list:
        temp_string.append(cookie_name + "=" + cookies_list[cookie_name])
    return "; ".join(temp_string)


def get_cookies_from_response_header(response_headers):
    """Get dictionary of cookies values from http response header list"""
    if not isinstance(response_headers, urllib3._collections.HTTPHeaderDict):
        return {}
    if "Set-Cookie" not in response_headers:
        return {}
    cookies_list = {}
    for cookie in response_headers.getlist("Set-Cookie"):
        cookie_name, cookie_value = cookie.split(";")[0].split("=", 1)
        cookies_list[cookie_name] = cookie_value
    return cookies_list


def get_file_type(file_url, default_file_type=""):
    # http://www.example.com/sub_path/file_name.file_type?parm1=value1&parm2=value2
    file_name_and_type = file_url.split("/")[-1].split("?")[0].split(".")
    if len(file_name_and_type) == 1:
        return default_file_type
    else:
        return file_name_and_type[-1]


def http_request(url, method="GET", fields=None, binary_data=None, header_list=None, cookies_list=None, encode_multipart=False, is_auto_proxy=True, is_auto_redirect=True,
                 is_auto_retry=True, connection_timeout=NET_CONFIG["HTTP_CONNECTION_TIMEOUT"], read_timeout=NET_CONFIG["HTTP_READ_TIMEOUT"], is_random_ip=True, json_decode=False):
    """Http request via urllib3

    :param url:
        the url which you want visit, start with "http://" or "https://"

    :param method:
        request method, value in ["GET", "POST", "HEAD", "PUT", "DELETE", "OPTIONS", "TRACE"]

    :param fields:
        dictionary type of request data, will urlencode() them to string. like post data, query string, etc
        not work with binary_data

    :param binary_data:
        binary type of request data, not work with post_data

    :param header_list:
        customize header dictionary

    :param cookies_list:
        customize cookies dictionary, will replaced header_list["Cookie"]

    :param encode_multipart:
        see "encode_multipart" in urllib3.request_encode_body

    :param is_auto_proxy:
        is auto use proxy when init PROXY_HTTP_CONNECTION_POOL

    :param is_auto_redirect:
        is auto redirect, when response.status in [301, 302, 303, 307, 308]

    :param is_auto_retry:
        is auto retry, when response.status in [500, 502, 503, 504]

    :param connection_timeout:
        customize connection timeout seconds

    :param read_timeout:
        customize read timeout seconds

    :param is_random_ip:
        is counterfeit a request header with random ip, will replaced header_list["X-Forwarded-For"] and header_list["X-Real-Ip"]

    :param json_decode:
        is return a decoded json data when response status = 200
        if decode failure will replace response status with HTTP_RETURN_CODE_JSON_DECODE_ERROR
    """
    if not (url.find("http://") == 0 or url.find("https://") == 0):
        return ErrorResponse(HTTP_RETURN_CODE_URL_INVALID)
    method = method.upper()
    if method not in ["GET", "POST", "HEAD", "PUT", "DELETE", "OPTIONS", "TRACE"]:
        return ErrorResponse(HTTP_RETURN_CODE_URL_INVALID)
    if HTTP_CONNECTION_POOL is None:
        init_http_connection_pool()
    connection_pool = HTTP_CONNECTION_POOL
    if PROXY_HTTP_CONNECTION_POOL is not None and is_auto_proxy:
        connection_pool = PROXY_HTTP_CONNECTION_POOL

    if header_list is None:
        header_list = {}

    # 设置User-Agent
    if "User-Agent" not in header_list:
        header_list["User-Agent"] = _random_user_agent()

    # 设置一个随机IP
    if is_random_ip:
        random_ip = _random_ip_address()
        header_list["X-Forwarded-For"] = random_ip
        header_list["X-Real-Ip"] = random_ip

    # 设置cookie
    if cookies_list:
        header_list["Cookie"] = build_header_cookie_string(cookies_list)

    # 设置压缩格式
    header_list["Accept-Encoding"] = "gzip"

    # 超时设置
    if connection_timeout == 0 and read_timeout == 0:
        timeout = None
    elif connection_timeout == 0:
        timeout = urllib3.Timeout(read=read_timeout)
    elif read_timeout == 0:
        timeout = urllib3.Timeout(connect=connection_timeout)
    else:
        timeout = urllib3.Timeout(connect=connection_timeout, read=read_timeout)

    retry_count = 0
    while True:
        thread_event.wait()
        if EXIT_FLAG:
            tool.process_exit(0)

        try:
            if method in ['DELETE', 'GET', 'HEAD', 'OPTIONS']:
                response = connection_pool.request(method, url, headers=header_list, redirect=is_auto_redirect, timeout=timeout, fields=fields)
            else:
                if binary_data is None:
                    response = connection_pool.request(method, url, fields=fields, encode_multipart=encode_multipart, headers=header_list, redirect=is_auto_redirect, timeout=timeout)
                else:
                    response = connection_pool.request(method, url, body=binary_data, encode_multipart=encode_multipart, headers=header_list, redirect=is_auto_redirect, timeout=timeout)
            if response.status == HTTP_RETURN_CODE_SUCCEED and json_decode:
                try:
                    response.json_data = json.loads(response.data.decode())
                except ValueError as ve:
                    is_error = True
                    content_type = response.getheader("Content-Type")
                    if content_type is not None:
                        charset = tool.find_sub_string(content_type, "charset=", None)
                        if charset:
                            if charset == "gb2312":
                                charset = "GBK"
                            try:
                                response.json_data = json.loads(response.data.decode(charset))
                            except:
                                pass
                            else:
                                is_error = False
                    if is_error:
                        response.status = HTTP_RETURN_CODE_JSON_DECODE_ERROR
            elif response.status == 429:  # Too Many Requests
                output.print_msg(url + " Too Many Requests, sleep")
                time.sleep(30)
                continue
            elif response.status in [500, 502, 503, 504] and is_auto_retry:  # 服务器临时性错误，重试
                if retry_count < NET_CONFIG["HTTP_REQUEST_RETRY_COUNT"]:
                    retry_count += 1
                    time.sleep(30)
                    continue
                else:
                    return response
            return response
        except MemoryError:
            return ErrorResponse(HTTP_RETURN_CODE_RESPONSE_TO_LARGE)
        except Exception as e:
            message = str(e)
            if isinstance(e, urllib3.exceptions.ConnectTimeoutError):
                # 域名无法解析
                if message.find("[Errno 11004] getaddrinfo failed") >= 0:
                    return ErrorResponse(HTTP_RETURN_CODE_DOMAIN_NOT_RESOLVED)
                elif message.find("[Errno 11001] getaddrinfo failed") >= 0:
                    return ErrorResponse(HTTP_RETURN_CODE_DOMAIN_NOT_RESOLVED)
            elif isinstance(e, urllib3.exceptions.MaxRetryError):
                if message.find("Caused by ResponseError('too many redirects'") >= 0:
                    return ErrorResponse(HTTP_RETURN_CODE_TOO_MANY_REDIRECTS)
            # output.print_msg(message)
            # output.print_msg(traceback.format_exc())
            output.print_msg(url + " 访问超时，重试中")
            time.sleep(5)

        retry_count += 1
        if retry_count >= NET_CONFIG["HTTP_REQUEST_RETRY_COUNT"]:
            output.print_msg("无法访问页面：" + url)
            return ErrorResponse(HTTP_RETURN_CODE_RETRY)


def _random_user_agent():
    """Get a random valid Firefox or Chrome user agent

        Common firefox user agent   "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0"
        Common chrome user agent    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
        Common IE user agent        "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; WOW64)"
    """
    firefox_version_max = 61
    # https://zh.wikipedia.org/zh-cn/Google_Chrome
    chrome_version_list = ["59.0.3071", "60.0.3112", "61.0.3163", "62.0.3202", "63.0.3239", "64.0.3282", "65.0.3325", "66.0.3359", "67.0.3396", "68.0.3423"]
    windows_version_dict = {
        "Windows 2000": "Windows NT 5.0",
        "Windows XP": "Windows NT 5.1",
        "Windows Vista": "Windows NT 6.0",
        "Windows 7": "Windows NT 6.1",
        "Windows 8": "Windows NT 6.2",
        "Windows 8.1": "Windows NT 6.3",
        "Windows 10": "Windows NT 10.0",
    }
    # browser_type = random.choice(["IE", "firefox", "chrome"])
    browser_type = random.choice(["firefox", "chrome"])
    os_type = random.choice(list(windows_version_dict.values()))
    if browser_type == "IE":
        sub_version = random.randint(6, 10)
        return "Mozilla/4.0 (compatible; MSIE %s.0; %s; WOW64)" % (sub_version, os_type)
    elif browser_type == "firefox":
        firefox_version = random.randint(firefox_version_max - 10, firefox_version_max)
        return "Mozilla/5.0 (%s; WOW64; rv:%s.0) Gecko/20100101 Firefox/%s.0" % (os_type, firefox_version, firefox_version)
    elif browser_type == "chrome":
        sub_version = random.randint(1, 100)
        chrome_version = random.choice(chrome_version_list)
        return "Mozilla/5.0 (%s; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/%s.%s Safari/537.36" % (os_type, chrome_version, sub_version)
    return ""


def _random_ip_address():
    """Get a random IP address(not necessarily correct)"""
    return "%s.%s.%s.%s" % (random.randint(1, 254), random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))


def save_net_file(file_url, file_path, need_content_type=False, header_list=None, cookies_list=None, head_check=False, is_auto_proxy=True):
    """Visit web and save to local

    :param file_url:
        the remote resource URL which you want to save

    :param file_path:
        the local file path which you want to save remote resource

    :param need_content_type:
        is auto rename file according to "Content-Type" in response headers

    :param header_list:
        customize header dictionary

    :param cookies_list:
        customize cookies dictionary, will replaced header_list["Cookie"]

    :param head_check:
        "HEAD" method request to check response status and file size before download file

    :return:
        status      0 download failure, 1 download successful
        code        failure reason
        file_path   finally local file path(when need_content_type is True, will rename it)
    """
    # 判断保存目录是否存在
    if not path.create_dir(os.path.dirname(file_path)):
        return False
    is_create_file = False
    is_multi_thread = False
    return_code = {"status": 0, "code": -3}
    for retry_count in range(0, NET_CONFIG["DOWNLOAD_RETRY_COUNT"]):
        if head_check and retry_count == 0:
            request_method = "HEAD"
        else:
            request_method = "GET"
        # 获取头信息
        response = http_request(file_url, request_method, header_list=header_list, cookies_list=cookies_list, is_auto_proxy=is_auto_proxy,
                                connection_timeout=NET_CONFIG["HTTP_CONNECTION_TIMEOUT"], read_timeout=NET_CONFIG["HTTP_READ_TIMEOUT"])
        # 其他返回状态，退出
        if response.status != HTTP_RETURN_CODE_SUCCEED:
            # URL格式不正确
            if response.status == HTTP_RETURN_CODE_URL_INVALID:
                return_code = {"status": 0, "code": -1}
            # 超过重试次数
            elif response.status == HTTP_RETURN_CODE_RETRY:
                return_code = {"status": 0, "code": -2}
            # 其他http code
            else:
                return_code = {"status": 0, "code": response.status}
            break

        # 判断文件是不是过大
        content_length = response.getheader("Content-Length")
        if content_length is not None:
            content_length = int(content_length)
            # 超过限制
            if content_length > NET_CONFIG["DOWNLOAD_LIMIT_SIZE"]:
                return {"status": 0, "code": -4}
            # 文件比较大，使用多线程下载（必须是head_check=True的情况下，否则整个文件内容都已经返回了）
            elif head_check and content_length > NET_CONFIG["DOWNLOAD_MULTI_THREAD_MIN_SIZE"]:
                is_multi_thread = True

        # response中的Content-Type作为文件后缀名
        if need_content_type:
            content_type = response.getheader("Content-Type")
            if content_type is not None and content_type != "octet-stream":
                global MIME_DICTIONARY
                if MIME_DICTIONARY is None:
                    MIME_DICTIONARY = tool.json_decode(file.read_file(os.path.join(os.path.dirname(__file__), "mime.json")), {})
                if content_type in MIME_DICTIONARY:
                    new_file_type = MIME_DICTIONARY[content_type]
                else:
                    new_file_type = content_type.split("/")[-1]
                file_path = os.path.splitext(file_path)[0] + "." + new_file_type

        if not is_multi_thread:  # 单线程下载
            # 如果是先调用HEAD方法的，需要重新获取完整数据
            if head_check:
                response = http_request(file_url, method="GET", header_list=header_list, cookies_list=cookies_list, is_auto_proxy=is_auto_proxy,
                                        connection_timeout=NET_CONFIG["DOWNLOAD_CONNECTION_TIMEOUT"], read_timeout=NET_CONFIG["DOWNLOAD_READ_TIMEOUT"])
                if response.status != HTTP_RETURN_CODE_SUCCEED:
                    continue
            # 下载
            with open(file_path, "wb") as file_handle:
                is_create_file = True
                file_handle.write(response.data)
        else:  # 多线程下载
            # 单线程下载文件大小（100MB）
            multi_thread_block_size = int(math.ceil(content_length / 10 / SIZE_MB)) * SIZE_MB
            multi_thread_block_size = min(NET_CONFIG["DOWNLOAD_MULTI_THREAD_MIN_BLOCK_SIZE"], max(NET_CONFIG["DOWNLOAD_MULTI_THREAD_MAX_BLOCK_SIZE"], multi_thread_block_size))
            # 创建文件
            with open(file_path, "w"):
                is_create_file = True
            thread_list = []
            error_flag = []
            with open(file_path, "rb+") as file_handle:
                file_no = file_handle.fileno()
                end_pos = -1
                while end_pos < content_length - 1:
                    start_pos = end_pos + 1
                    end_pos = min(content_length - 1, start_pos + multi_thread_block_size - 1)
                    # 创建一个副本
                    fd_handle = os.fdopen(os.dup(file_no), "rb+", -1)
                    thread = MultiThreadDownload(file_url, start_pos, end_pos, fd_handle, error_flag)
                    thread.start()
                    thread_list.append(thread)
            # 等待所有线程下载完毕
            for thread in thread_list:
                thread.join()
            # 有任意一个线程下载失败了，跳出（重试机制在MultiThreadDownload类中有）
            if len(error_flag) > 0:
                return_code = {"status": 0, "code": -2}
                break
        if content_length is None:
            return {"status": 1, "code": 0, "file_path": file_path}
        # 判断文件下载后的大小和response中的Content-Length是否一致
        file_size = os.path.getsize(file_path)
        if content_length == file_size:
            return {"status": 1, "code": 0, "file_path": file_path}
        else:
            output.print_msg("本地文件%s：%s和网络文件%s：%s不一致" % (file_path, content_length, file_url, file_size))
            time.sleep(10)
    if is_create_file:
        path.delete_dir_or_file(file_path)
    return return_code


def save_net_file_list(file_url_list, file_path, header_list=None, cookies_list=None):
    """Visit web and save to local(multiple remote resource, single local file)

    :param file_url_list:
        the list of remote resource URL which you want to save

    :param file_path:
        the local file path which you want to save remote resource

    :param header_list:
        customize header dictionary

    :param cookies_list:
        customize cookies dictionary, will replaced header_list["Cookie"]

    :return:
        status      0 download failure, 1 download successful
        code        failure reason
    """
    # 判断保存目录是否存在
    if not path.create_dir(os.path.dirname(file_path)):
        return False
    for retry_count in range(0, NET_CONFIG["DOWNLOAD_RETRY_COUNT"]):
        # 下载
        with open(file_path, "wb") as file_handle:
            for file_url in file_url_list:
                response = http_request(file_url, header_list=header_list, cookies_list=cookies_list,
                                        connection_timeout=NET_CONFIG["DOWNLOAD_CONNECTION_TIMEOUT"], read_timeout=NET_CONFIG["DOWNLOAD_READ_TIMEOUT"])
                if response.status == HTTP_RETURN_CODE_SUCCEED:
                    file_handle.write(response.data)
                # 超过重试次数，直接退出
                elif response.status == HTTP_RETURN_CODE_RETRY:
                    path.delete_dir_or_file(file_path)
                    return {"status": 0, "code": -2}
                # 其他http code，退出
                else:
                    path.delete_dir_or_file(file_path)
                    return {"status": 0, "code": response.status}
        return {"status": 1, "code": 0}
    # path.delete_dir_or_file(file_path)
    return {"status": 0, "code": -2}


def pause_request():
    """Block thread when use http_request()"""
    if thread_event.isSet():
        output.print_msg("pause process")
        thread_event.clear()


def resume_request():
    """Resume thread"""
    if not thread_event.isSet():
        output.print_msg("resume process")
        thread_event.set()


class MultiThreadDownload(threading.Thread):
    def __init__(self, file_url, start_pos, end_pos, fd_handle, error_flag):
        threading.Thread.__init__(self)
        self.file_url = file_url
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.fd_handle = fd_handle
        self.error_flag = error_flag

    def run(self):
        headers_list = {"Range": "bytes=%s-%s" % (self.start_pos, self.end_pos)}
        range_size = self.end_pos - self.start_pos + 1
        for retry_count in range(0, NET_CONFIG["DOWNLOAD_RETRY_COUNT"]):
            response = http_request(self.file_url, method="GET", header_list=headers_list)
            if response.status == 206:
                # 下载的文件和请求的文件大小不一致
                if len(response.data) != range_size:
                    output.print_msg("网络文件%s：range %s - %s实际下载大小 %s 不一致" % (self.file_url, self.start_pos, self.end_pos, len(response.data)))
                    time.sleep(10)
                else:
                    # 写入本地文件后退出
                    self.fd_handle.seek(self.start_pos)
                    self.fd_handle.write(response.data)
                    return
        self.error_flag.append(self)
