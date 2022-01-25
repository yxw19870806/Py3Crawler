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
import urllib.parse
import warnings
import urllib3
from typing import Optional
from urllib3._collections import HTTPHeaderDict

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
    "TOO_MANY_REQUESTS_WAIT_TIME": 30,  # http code 429(Too Many requests)时的等待时间
    "SERVICE_INTERNAL_ERROR_WAIT_TIME": 30,  # http code 50X（服务器内部错误）时的等待时间
    "HTTP_REQUEST_RETRY_WAIT_TIME": 5,  # 请求失败后重新请求的间隔时间
    "GLOBAL_QUERY_PER_MINUTER": 1000,  # 全局每分钟请求限制
    "SINGLE_HOST_QUERY_PER_MINUTER": 1000,  # 单域名每分钟请求限制
}
NET_CONFIG = tool.json_decode(file.read_file(os.path.join(os.path.dirname(__file__), "net_config.json")), {})
for config_key in DEFAULT_NET_CONFIG:
    if config_key not in NET_CONFIG:
        NET_CONFIG[config_key] = DEFAULT_NET_CONFIG[config_key]

# qps队列
QPS = {}

# 连接池
HTTP_CONNECTION_POOL: Optional[urllib3.PoolManager] = None
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
HTTP_RETURN_CODE_SUCCEED = 200
# 下载文件时是否覆盖已存在的同名文件
DOWNLOAD_REPLACE_IF_EXIST = False


class ErrorResponse(object):
    """
    request()方法异常对象
    """
    def __init__(self, status=-1):
        self.status = status
        self.data = b''
        self.headers = {}
        self.json_data = []


def init_http_connection_pool():
    """
    初始化连接池
    """
    global HTTP_CONNECTION_POOL
    HTTP_CONNECTION_POOL = urllib3.PoolManager(retries=False)


def set_proxy(ip: str, port: str):
    """
    初始化代理连接池
    """
    if not str(port).isdigit() or int(port) <= 0:
        return
    match = re.match("((25[0-5]|2[0-4]\d|((1\d{2})|([1-9]?\d)))\.){3}(25[0-5]|2[0-4]\d|((1\d{2})|([1-9]?\d)))", ip)
    if not match or match.group() != ip:
        return
    global PROXY_HTTP_CONNECTION_POOL
    PROXY_HTTP_CONNECTION_POOL = urllib3.ProxyManager("http://%s:%s" % (ip, port), retries=False)
    output.print_msg("设置代理成功(%s:%s)" % (ip, port))


def build_header_cookie_string(cookies_list: dict) -> str:
    """
    根据cookies字典生成header中的cookie字符串

    :Args:
    - cookies_list
        {
            "cookie1":“value1",
            "cookie2":“value2",
            ......
        }

    :Returns:
        cookie1=value1; cookie2=value2
    """
    if not cookies_list:
        return ""
    temp_string = []
    for cookie_name in cookies_list:
        temp_string.append(cookie_name + "=" + cookies_list[cookie_name])
    return "; ".join(temp_string)


def split_cookies_from_cookie_string(cookie_string: str) -> dict:
    """
    根据response header中的cookie字符串分隔生成cookies字典
    """
    cookies_list = {}
    for single_cookie in cookie_string.split(";"):
        single_cookie = single_cookie.strip()
        if len(single_cookie) == 0:
            continue
        if single_cookie.find("=") == -1:
            continue
        cookie_name, cookie_value = single_cookie.strip().split("=", 1)
        cookies_list[cookie_name] = cookie_value
    return cookies_list


def get_cookies_from_response_header(response_headers: HTTPHeaderDict) -> dict:
    """
    根据response header获取Set-Cookie的值
    """
    if not isinstance(response_headers, HTTPHeaderDict):
        return {}
    if "Set-Cookie" not in response_headers:
        return {}
    cookies_list = {}
    for cookie in response_headers.getlist("Set-Cookie"):
        cookie_name, cookie_value = cookie.split(";")[0].split("=", 1)
        cookies_list[cookie_name] = cookie_value
    return cookies_list


def get_file_type(file_url: str, default_file_type: str = ""):
    """
    获取url地址的文件类型
    """
    # http://www.example.com/sub_path/file_name.file_type?parm1=value1&parm2=value2/value3
    file_name_and_type = urllib.parse.urlparse(file_url)[2].split("/")[-1].split(".")
    if len(file_name_and_type) == 1:
        return default_file_type
    else:
        return file_name_and_type[-1]


def url_encode(url):
    """
    url编码：百分号编码(Percent-Encoding)
    e.g. 'https://www.example.com/测 试/' -> 'https://www.example.com/%E6%B5%8B%20%E8%AF%95/'
    """
    return urllib.parse.quote(url, safe=";/?:@&=+$,%")


def request(url, method="GET", fields=None, binary_data=None, header_list=None, cookies_list=None, encode_multipart=False, json_decode=False,
            is_auto_proxy=True, is_auto_redirect=True, is_gzip=True, is_url_encode=True, is_auto_retry=True, is_random_ip=True,
            is_check_qps=True, connection_timeout=NET_CONFIG["HTTP_CONNECTION_TIMEOUT"], read_timeout=NET_CONFIG["HTTP_READ_TIMEOUT"]):
    """
    HTTP请求

    :Args:
    - url - the url which you want visit, start with "http://" or "https://"
    - method - request method, value in ["GET", "POST", "HEAD", "PUT", "DELETE", "OPTIONS", "TRACE"]
    - fields - dictionary type of request data, will urlencode() them to string. like post data, query string, etc
        not work with binary_data
    - binary_data - binary type of request data, not work with post_data
    - header_list - customize header dictionary
    - cookies_list - customize cookies dictionary, will replaced header_list["Cookie"]
    - encode_multipart - see "encode_multipart" in urllib3.request_encode_body
    - is_auto_proxy - is auto use proxy when init PROXY_HTTP_CONNECTION_POOL
    - is_auto_redirect - is auto redirect, when response.status in [301, 302, 303, 307, 308]
    - is_auto_retry - is auto retry, when response.status in [500, 502, 503, 504]
    - connection_timeout - customize connection timeout seconds
    - read_timeout - customize read timeout seconds
    - is_random_ip - is counterfeit a request header with random ip, will replaced header_list["X-Forwarded-For"] and header_list["X-Real-Ip"]
    - json_decode - is return a decoded json data when response status = 200
        if decode failure will replace response status with HTTP_RETURN_CODE_JSON_DECODE_ERROR
    """
    url = str(url).strip()
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
    if is_url_encode:
        url = url_encode(url)

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
    if is_gzip:
        header_list["Accept-Encoding"] = "gzip"

    # 超时设置
    timeout = urllib3.Timeout(connect=float(connection_timeout) if connection_timeout > 0 else None, read=read_timeout if read_timeout > 0 else None)

    retry_count = 0
    while True:
        thread_event.wait()
        if EXIT_FLAG:
            tool.process_exit(0)

        if is_check_qps and _qps(url):
            time.sleep(random.randint(60, 120))
            continue

        try:
            if method in ['DELETE', 'GET', 'HEAD', 'OPTIONS']:
                response = connection_pool.request(method, url, headers=header_list, redirect=is_auto_redirect, timeout=timeout, fields=fields)
            else:
                if binary_data is None:
                    response = connection_pool.request(method, url, fields=fields, encode_multipart=encode_multipart, headers=header_list,
                                                       redirect=is_auto_redirect, timeout=timeout)
                else:
                    response = connection_pool.request(method, url, body=binary_data, encode_multipart=encode_multipart, headers=header_list,
                                                       redirect=is_auto_redirect, timeout=timeout)
            if response.status == HTTP_RETURN_CODE_SUCCEED and json_decode:
                try:
                    response.json_data = json.loads(response.data.decode())
                except ValueError:
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
                time.sleep(NET_CONFIG["TOO_MANY_REQUESTS_WAIT_TIME"])
                continue
            elif response.status in [500, 502, 503, 504] and is_auto_retry:  # 服务器临时性错误，重试
                if retry_count < NET_CONFIG["HTTP_REQUEST_RETRY_COUNT"]:
                    retry_count += 1
                    time.sleep(NET_CONFIG["SERVICE_INTERNAL_ERROR_WAIT_TIME"])
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
            elif isinstance(e, urllib3.exceptions.DecodeError):
                if message.find("'Received response with content-encoding: gzip, but failed to decode it.'") >= 0:
                    return request(url, method=method, fields=fields, binary_data=binary_data, header_list=header_list, cookies_list=cookies_list,
                                   encode_multipart=encode_multipart, json_decode=json_decode, is_auto_proxy=is_auto_proxy, is_auto_redirect=is_auto_redirect,
                                   is_gzip=False, is_url_encode=False, is_auto_retry=is_auto_retry, is_random_ip=is_random_ip, is_check_qps=is_check_qps,
                                   connection_timeout=connection_timeout, read_timeout=read_timeout)
            # import traceback
            # output.print_msg(message)
            # output.print_msg(traceback.format_exc())
            output.print_msg(url + " 访问超时，重试中")
            time.sleep(NET_CONFIG["HTTP_REQUEST_RETRY_WAIT_TIME"])

        retry_count += 1
        if retry_count >= NET_CONFIG["HTTP_REQUEST_RETRY_COUNT"]:
            output.print_msg("无法访问页面：" + url)
            return ErrorResponse(HTTP_RETURN_CODE_RETRY)


def _qps(url):
    # 当前分钟
    day_minuter = int(time.strftime("%Y%m%d%H%M"))
    if day_minuter not in QPS:
        QPS[day_minuter] = {}

    # host
    host = urllib.parse.urlparse(url).netloc
    if host not in QPS[day_minuter]:
        QPS[day_minuter][host] = 0

    # 当前域名、当前分钟的请求数
    if QPS[day_minuter][host] > NET_CONFIG["SINGLE_HOST_QUERY_PER_MINUTER"]:
        return True

    # 所有域名、当前分钟的请求数
    total_query = 0
    for temp_host in QPS[day_minuter]:
        total_query += QPS[day_minuter][temp_host]
    if total_query > NET_CONFIG["GLOBAL_QUERY_PER_MINUTER"]:
        return True

    QPS[day_minuter][host] += 1

    return False


def _random_user_agent():
    """
    随机获取一个user agent
        Common firefox user agent   "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0"
        Common chrome user agent    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
        Common IE user agent        "Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; WOW64)"
    """
    windows_version_dict = {
        "Windows 7": "Windows NT 6.1",
        "Windows 8": "Windows NT 6.2",
        "Windows 8.1": "Windows NT 6.3",
        "Windows 10": "Windows NT 10.0",
    }
    firefox_version_max = 96
    # https://zh.wikipedia.org/zh-cn/Google_Chrome
    chrome_version_list = ["94.0.4606.54", "94.0.4606.61", "94.0.4606.71", "94.0.4606.81", "95.0.4638.54", "95.0.4638.69", "96.0.4664.45", "96.0.4664.93", "96.0.4664.110", "97.0.4692.71"]
    # browser_type = random.choice(["IE", "firefox", "chrome", "Edge"])
    browser_type = random.choice(["firefox", "chrome"])
    if browser_type == "firefox":
        firefox_version = random.randint(firefox_version_max - 10, firefox_version_max)
        os_type = random.choice(list(windows_version_dict.values()))
        return "Mozilla/5.0 (%s; WOW64; rv:%s.0) Gecko/20100101 Firefox/%s.0" % (os_type, firefox_version, firefox_version)
    elif browser_type == "chrome":
        chrome_version = random.choice(chrome_version_list)
        os_type = random.choice(list(windows_version_dict.values()))
        return "Mozilla/5.0 (%s; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/%s Safari/537.36" % (os_type, chrome_version)
    return ""


def _random_ip_address():
    """
    Get a random IP address(not necessarily correct)
    """
    return "%s.%s.%s.%s" % (random.randint(1, 254), random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))


def download(file_url, file_path, need_content_type=False, head_check=False, replace_if_exist=None, **kwargs):
    """
    现在远程文件到本地

    :Args:
    - file_url - the remote resource URL which you want to save
    - file_path - the local file path which you want to save remote resource
    - need_content_type - is auto rename file according to "Content-Type" in response headers
    - head_check -"HEAD" method request to check response status and file size before download file

    :Returns:
        - status - 0 download failure, 1 download successful
        - code - failure reason
        - file_path - finally local file path(when need_content_type is True, will rename it)
    """
    if not isinstance(replace_if_exist, bool):
        replace_if_exist = DOWNLOAD_REPLACE_IF_EXIST
    if not replace_if_exist and os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        output.print_msg("文件%s（%s）已存在，跳过" % (file_path, file_url))
        return {"status": 1, "code": 0, "file_path": file_path}
    # 判断保存目录是否存在
    if not path.create_dir(os.path.dirname(file_path)):
        return {"status": 1, "code": -11, "file_path": file_path}
    is_create_file = False
    is_multi_thread = False
    return_code = {"status": 0, "code": -3}
    for retry_count in range(0, NET_CONFIG["DOWNLOAD_RETRY_COUNT"]):
        if head_check and retry_count == 0:
            request_method = "HEAD"
        else:
            request_method = "GET"
        # 获取头信息
        response = request(file_url, request_method, is_check_qps=False, connection_timeout=NET_CONFIG["HTTP_CONNECTION_TIMEOUT"], read_timeout=NET_CONFIG["HTTP_READ_TIMEOUT"], **kwargs)
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
                response = request(file_url, method="GET", connection_timeout=NET_CONFIG["DOWNLOAD_CONNECTION_TIMEOUT"], read_timeout=NET_CONFIG["DOWNLOAD_READ_TIMEOUT"], **kwargs)
                if response.status != HTTP_RETURN_CODE_SUCCEED:
                    continue
            # 下载
            with open(file_path, "wb") as file_handle:
                is_create_file = True
                try:
                    file_handle.write(response.data)
                except OSError as ose:
                    if str(ose).find("No space left on device") != -1:
                        global EXIT_FLAG
                        EXIT_FLAG = True
                    raise
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
            # 有任意一个线程下载失败了，或者文件存在连续1K以上的空字节
            if len(error_flag) > 0:
                continue
            if not _check_multi_thread_download_file(file_path):
                output.print_msg("网络文件%s多线程下载后发现无效字节" % file_url)
                continue
        if content_length is None:
            return {"status": 1, "code": 0, "file_path": file_path}
        # 判断文件下载后的大小和response中的Content-Length是否一致
        file_size = os.path.getsize(file_path)
        if content_length == file_size:
            return {"status": 1, "code": 0, "file_path": file_path}
        else:
            output.print_msg("本地文件%s：%s和网络文件%s：%s不一致" % (file_path, content_length, file_url, file_size))
            time.sleep(NET_CONFIG["HTTP_REQUEST_RETRY_WAIT_TIME"])
    if is_create_file:
        path.delete_dir_or_file(file_path)
    return return_code


def _check_multi_thread_download_file(file_path):
    """
    Check fhe file download with multi thread

    :Returns:
        True    file is valid
        False   file is invalid(download failure)
    """
    file_path = os.path.abspath(file_path)
    if not os.path.exists(file_path):
        return True
    with open(file_path, "rb") as file_handle:
        buffer_size = 2 ** 20  # 1M
        while True:
            file_buffer = file_handle.read(buffer_size)
            if not file_buffer:
                break
            if file_buffer.find(b"\x00" * (2 ** 10)) >= 0:
                return False
    return True


def download_from_list(file_url_list, file_path, header_list=None, cookies_list=None):
    """
    Visit web and save to local(multiple remote resource, single local file)

    :Args:
    - file_url_list - the list of remote resource URL which you want to save
    - file_path - the local file path which you want to save remote resource
    - header_list - customize header dictionary
    - cookies_list - customize cookies dictionary, will replaced header_list["Cookie"]

    :Returns:
        - status - 0 download failure, 1 download successful
        - code - failure reason
    """
    # 判断保存目录是否存在
    if not path.create_dir(os.path.dirname(file_path)):
        return False
    for retry_count in range(0, NET_CONFIG["DOWNLOAD_RETRY_COUNT"]):
        # 下载
        with open(file_path, "wb") as file_handle:
            for file_url in file_url_list:
                response = request(file_url, header_list=header_list, cookies_list=cookies_list, connection_timeout=NET_CONFIG["DOWNLOAD_CONNECTION_TIMEOUT"], read_timeout=NET_CONFIG["DOWNLOAD_READ_TIMEOUT"])
                if response.status == HTTP_RETURN_CODE_SUCCEED:
                    file_handle.write(response.data)
                # 超过重试次数，直接退出
                elif response.status == HTTP_RETURN_CODE_RETRY:
                    file_handle.close()
                    path.delete_dir_or_file(file_path)
                    return {"status": 0, "code": -2}
                # 其他http code，退出
                else:
                    file_handle.close()
                    path.delete_dir_or_file(file_path)
                    return {"status": 0, "code": response.status}
        return {"status": 1, "code": 0}
    # path.delete_dir_or_file(file_path)
    return {"status": 0, "code": -2}


def pause_request():
    """
    Block thread when use request()
    """
    if thread_event.isSet():
        output.print_msg("pause process")
        thread_event.clear()


def resume_request():
    """
    Resume thread
    """
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
            response = request(self.file_url, method="GET", header_list=headers_list)
            if response.status == 206:
                # 下载的文件和请求的文件大小不一致
                if len(response.data) != range_size:
                    output.print_msg("网络文件%s：range %s - %s实际下载大小 %s 不一致" % (self.file_url, self.start_pos, self.end_pos, len(response.data)))
                    time.sleep(NET_CONFIG["HTTP_REQUEST_RETRY_WAIT_TIME"])
                else:
                    # 写入本地文件后退出
                    self.fd_handle.seek(self.start_pos)
                    self.fd_handle.write(response.data)
                    self.fd_handle.close()
                    return
        self.error_flag.append(self)


def http_request(url, method="GET", fields=None, binary_data=None, header_list=None, cookies_list=None, encode_multipart=False, json_decode=False,
                 is_auto_proxy=True, is_auto_redirect=True, is_gzip=True, is_url_encode=True, is_auto_retry=True, is_random_ip=True,
                 is_check_qps=True, connection_timeout=NET_CONFIG["HTTP_CONNECTION_TIMEOUT"], read_timeout=NET_CONFIG["HTTP_READ_TIMEOUT"]):
    warnings.warn(
        "http_request commands are deprecated. Please use request() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return request(url, method=method, fields=fields, binary_data=binary_data, header_list=header_list, cookies_list=cookies_list, encode_multipart=encode_multipart,
                   json_decode=json_decode, is_auto_proxy=is_auto_proxy, is_auto_redirect=is_auto_redirect, is_gzip=is_gzip, is_url_encode=is_url_encode, is_auto_retry=is_auto_retry,
                   is_random_ip=is_random_ip, is_check_qps=is_check_qps, connection_timeout=connection_timeout, read_timeout=read_timeout)


def save_net_file(file_url, file_path, need_content_type=False, head_check=False, replace_if_exist=None, **kwargs):
    warnings.warn(
        "save_net_file commands are deprecated. Please use download() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return download(file_url, file_path, need_content_type=need_content_type, head_check=head_check, replace_if_exist=replace_if_exist, **kwargs)


def save_net_file_list(file_url_list, file_path, header_list=None, cookies_list=None):
    warnings.warn(
        "save_net_file_list commands are deprecated. Please use download_from_list() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return download_from_list(file_url_list, file_path, header_list=header_list, cookies_list=cookies_list)
