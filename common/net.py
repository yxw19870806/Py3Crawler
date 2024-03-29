# -*- coding:UTF-8  -*-
"""
网络访问类
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import json
import os
import random
import re
import ssl
import time
import threading
import urllib.parse
import urllib3
import urllib3.exceptions
from typing import Optional, Union, Self, Any
from urllib3._collections import HTTPHeaderDict
from common import const, file, log, net_config, path, tool, url

# https://www.python.org/dev/peps/pep-0476/
# disable urllib3 HTTPS warning
urllib3.disable_warnings()
# disable URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed (_ssl.c:590)>
ssl._create_default_https_context = ssl._create_unverified_context

# qps队列
QPS: dict[int, dict[str, int]] = {}

# 连接池
HTTP_CONNECTION_POOL: Optional[urllib3.PoolManager] = None
PROXY_HTTP_CONNECTION_POOL: Optional[urllib3.ProxyManager] = None
# 网络访问相关阻塞/继续事件
thread_event = threading.Event()
thread_event.set()
# 退出标志
EXIT_FLAG: bool = False
# 下载文件时是否覆盖已存在的同名文件
DOWNLOAD_REPLACE_IF_EXIST: bool = False
# 是否使用固定的UA，可以通过set_default_user_agent()重新随机生成
DEFAULT_USER_AGENT: Optional[str] = None
# 默认的字符集，用于decode请求response的data（当response header的Content-Type不存在时使用）
DEFAULT_CHARSET: str = "utf-8"
# 是否伪造代理模式的IP（通过设置header中的X-Forwarded-For和X-Real-Ip）
FAKE_PROXY_IP: bool = True
# 网络请求相关配置
NET_CONFIG: net_config.NetConfig = net_config.NetConfig()
# response header中Content-Type对应的Mime字典
MIME_DICTIONARY: Optional[dict[str, str]] = file.read_json_file(os.path.join(os.path.dirname(__file__), "mime.json"), {})


def init_http_connection_pool() -> None:
    """
    初始化连接池
    """
    global HTTP_CONNECTION_POOL
    HTTP_CONNECTION_POOL = urllib3.PoolManager(retries=False)


def set_proxy(ip: str, port: str) -> None:
    """
    初始化代理连接池
    """
    if not str(port).isdigit() or int(port) <= 0:
        return
    match = re.match(r"((25[0-5]|2[0-4]\d|((1\d{2})|([1-9]?\d)))\.){3}(25[0-5]|2[0-4]\d|((1\d{2})|([1-9]?\d)))", ip)
    if not match or match.group() != ip:
        return
    global PROXY_HTTP_CONNECTION_POOL
    if PROXY_HTTP_CONNECTION_POOL is not None:
        return
    PROXY_HTTP_CONNECTION_POOL = urllib3.ProxyManager(f"http://{ip}:{port}", retries=False)
    log.info(f"设置代理成功({ip}:{port})")


def set_default_user_agent(browser_type: Optional[const.BrowserType] = None) -> None:
    global DEFAULT_USER_AGENT
    user_agent = _random_user_agent(browser_type)
    if user_agent:
        DEFAULT_USER_AGENT = user_agent


def disable_fake_proxy_ip() -> None:
    global FAKE_PROXY_IP
    FAKE_PROXY_IP = False


def set_default_charset(charset: str) -> None:
    global DEFAULT_CHARSET
    DEFAULT_CHARSET = charset


def build_header_cookie_string(cookies: dict[str, str]) -> str:
    """
    根据cookies字典生成header中的cookie字符串

    :Args:
    - cookies
        {
            "cookie1":“value1",
            "cookie2":“value2",
            ......
        }

    :Returns:
        cookie1=value1; cookie2=value2
    """
    if not cookies:
        return ""
    temp_string = []
    for cookie_name in cookies:
        temp_string.append(cookie_name + "=" + cookies[cookie_name])
    return "; ".join(temp_string)


def split_cookies_from_cookie_string(cookie_string: str) -> dict[str, str]:
    """
    根据response header中的cookie字符串分隔生成cookies字典
    """
    cookies = {}
    for single_cookie in cookie_string.split(";"):
        single_cookie = single_cookie.strip()
        if len(single_cookie) == 0:
            continue
        if single_cookie.find("=") == -1:
            continue
        cookie_name, cookie_value = single_cookie.strip().split("=", 1)
        cookies[cookie_name] = cookie_value
    return cookies


def get_cookies_from_response_header(response_headers: HTTPHeaderDict) -> dict[str, str]:
    """
    根据response header获取Set-Cookie的值
    """
    if not isinstance(response_headers, HTTPHeaderDict):
        return {}
    if "Set-Cookie" not in response_headers:
        return {}
    cookies = {}
    for cookie in response_headers.getlist("Set-Cookie"):
        cookie_name, cookie_value = cookie.split(";")[0].split("=", 1)
        cookies[cookie_name] = cookie_value
    return cookies


def _qps(requst_url: str) -> bool:
    # 当前分钟
    day_minuter = int(time.strftime("%Y%m%d%H%M"))
    if day_minuter not in QPS:
        QPS[day_minuter] = {}

    # host
    host = urllib.parse.urlparse(requst_url).netloc
    if host not in QPS[day_minuter]:
        QPS[day_minuter][host] = 0

    # 当前域名、当前分钟的请求数
    if QPS[day_minuter][host] > NET_CONFIG.SINGLE_HOST_QUERY_PER_MINUTER:
        return True

    # 所有域名、当前分钟的请求数
    total_query = 0
    for temp_host in QPS[day_minuter]:
        total_query += QPS[day_minuter][temp_host]
    if total_query > NET_CONFIG.GLOBAL_QUERY_PER_MINUTER:
        return True

    QPS[day_minuter][host] += 1

    return False


def _random_user_agent(browser_type: Optional[const.BrowserType] = None) -> str:
    """
    随机获取一个user agent
        Common firefox user agent   "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0"
        Common chrome user agent    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
    """
    windows_version_dict = {
        "Windows 7": "Windows NT 6.1",
        "Windows 8": "Windows NT 6.2",
        "Windows 8.1": "Windows NT 6.3",
        "Windows 10": "Windows NT 10.0",
    }
    firefox_version_max = 119
    chrome_version_max = 118
    if browser_type is None:
        browser_type = random.choice([const.BrowserType.FIREFOX, const.BrowserType.CHROME])
    if browser_type == const.BrowserType.FIREFOX:
        firefox_version = random.randint(firefox_version_max - 3, firefox_version_max)
        os_type = random.choice(list(windows_version_dict.values()))
        return f"Mozilla/5.0 ({os_type}; Win64; x64; rv:{firefox_version}.0) Gecko/20100101 Firefox/{firefox_version}.0"
    elif browser_type == const.BrowserType.CHROME:
        chrome_version = random.randint(chrome_version_max - 3, chrome_version_max)
        os_type = random.choice(list(windows_version_dict.values()))
        return f"Mozilla/5.0 ({os_type}; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version}.0.0.0 Safari/537.36"
    return ""


def _random_ip_address() -> str:
    """
    Get a random IP address(not necessarily correct)
    """
    return f"{random.randint(1, 254)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"


def pause_request() -> None:
    """
    Block thread when use request()
    """
    if thread_event.is_set():
        log.info("pause process")
        thread_event.clear()


def resume_request() -> None:
    """
    Resume thread
    """
    if not thread_event.is_set():
        log.info("resume process")
        thread_event.set()


def format_path(file_path: str) -> str:
    """
        获取完整路径，并去除无效的文件名字符
    """
    file_path = os.path.realpath(file_path)
    file_dir, file_name_and_ext = os.path.split(file_path)
    split_result = file_name_and_ext.rsplit(".", 1)
    new_file_name_and_ext = path.filter_text(split_result[0])
    if len(split_result) == 2:
        new_file_name_and_ext += f".{split_result[1]}"
    return os.path.join(file_dir, new_file_name_and_ext)


class ErrorResponse(object):
    def __init__(self, status: int = 0) -> None:
        """
        request()方法异常对象
        """
        self.status: int = status
        self.data: bytes = b""
        self.content: str = ""
        self.headers: HTTPHeaderDict = HTTPHeaderDict()
        self.json_data: dict = {}


class Request:
    def __init__(self, requst_url: str, method: str = "GET", fields: Optional[Union[dict, str]] = None, headers: Optional[dict[str, str]] = None, cookies: Optional[dict[str, str]] = None):
        """
        HTTP请求
        :Args:
        - requst_url - the url which you want visit, start with "http://" or "https://"
        - method - request method, value in ["GET", "POST", "HEAD", "PUT", "DELETE", "OPTIONS", "TRACE"]
        - fields - dictionary type of request data, will urlencode() them to string. like post data, query string, etc.
            not work with binary_data
        - headers - customize header dictionary
        - cookies - customize cookies dictionary, will replace headers["Cookie"]
        """
        self._url: str = str(requst_url).strip()
        self._method: str = str(method).upper()
        self._fields = fields
        self._headers: dict[str, str] = headers if isinstance(headers, dict) else {}
        self._cookies: dict[str, str] = cookies if isinstance(cookies, dict) else {}
        self._response: Optional[Union[urllib3.HTTPResponse, ErrorResponse]] = None
        # is auto retry, when response.status in [500, 502, 503, 504]
        self._is_auto_retry: bool = True
        # is check request qps
        self._is_check_qps: bool = False
        # is auto decode .data and set to .content
        self._is_decode_content: bool = True
        # see "encode_multipart" in urllib3.request_encode_body
        self._is_encode_multipart: bool = False
        # is use gzip compression request body
        self._is_gzip: bool = True
        # is return a decoded json data when response status = 200
        # if decode failure will replace response status with const.ResponseCode.JSON_DECODE_ERROR
        self._is_json_decode: bool = False
        # is auto redirect, when response.status in [301, 302, 303, 307, 308]
        self._is_redirect: bool = True
        # is use proxy when inited PROXY_HTTP_CONNECTION_POOL
        self._is_use_proxy: bool = True
        # is encode url
        self._is_url_encode: bool = True
        # customize connection timeout seconds
        self._connection_timeout: int = NET_CONFIG.HTTP_CONNECTION_TIMEOUT
        # customize read timeout seconds
        self._read_timeout: int = NET_CONFIG.HTTP_READ_TIMEOUT

    def add_headers(self, key: str, value: str) -> Self:
        self._headers[key] = value
        return self

    def set_headers(self, headers: Optional[dict[str, str]] = None) -> Self:
        self._headers = headers
        return self

    def set_cookies(self, cookies: Optional[dict[str, str]] = None) -> Self:
        self._cookies = cookies
        return self

    def enable_check_qps(self) -> Self:
        self._is_check_qps = True
        return self

    def enable_encode_multipart(self) -> Self:
        self._is_encode_multipart = True
        return self

    def enable_json_decode(self) -> Self:
        self._is_json_decode = True
        return self

    def disable_auto_retry(self) -> Self:
        self._is_auto_retry = False
        return self

    def disable_decode_content(self) -> Self:
        self._is_decode_content = False
        return self

    def disable_redirect(self) -> Self:
        self._is_redirect = False
        return self

    def disable_use_proxy(self) -> Self:
        self._is_use_proxy = False
        return self

    def disable_url_encode(self) -> Self:
        self._is_url_encode = False
        return self

    def set_time_out(self, connection_timeout: Union[int, float], read_timeout: Union[int, float]) -> Self:
        self._connection_timeout = connection_timeout
        self._read_timeout = read_timeout
        return self

    @property
    def status(self) -> int:
        return self.start_request()._response.status

    @property
    def data(self) -> bytes:
        return self.start_request()._response.data

    @property
    def content(self) -> str:
        return self.start_request()._response.content

    @property
    def headers(self) -> HTTPHeaderDict:
        return self.start_request()._response.headers

    @property
    def json_data(self) -> dict:
        return self.start_request()._response.json_data

    def start_request(self) -> Self:
        if self._response is None:
            try:
                self._response = self._start_request()
            except KeyboardInterrupt:
                self._response = ErrorResponse()
                pass
        return self

    def _start_request(self) -> Union[urllib3.HTTPResponse, ErrorResponse]:
        if not (self._url.startswith("http://") or self._url.startswith("https://")):
            return ErrorResponse(const.ResponseCode.URL_INVALID)
        if self._method not in ["GET", "POST", "HEAD", "PUT", "DELETE", "OPTIONS", "TRACE"]:
            return ErrorResponse(const.ResponseCode.URL_INVALID)

        if HTTP_CONNECTION_POOL is None:
            init_http_connection_pool()
        connection_pool = HTTP_CONNECTION_POOL
        if PROXY_HTTP_CONNECTION_POOL is not None and self._is_use_proxy:
            connection_pool = PROXY_HTTP_CONNECTION_POOL

        if self._is_url_encode:
            self._url = url.encode(self._url)

        # 设置User-Agent
        if "User-Agent" not in self._headers:
            self._headers["User-Agent"] = DEFAULT_USER_AGENT if isinstance(DEFAULT_USER_AGENT, str) else _random_user_agent()

        # 设置一个随机IP
        if FAKE_PROXY_IP:
            random_ip = _random_ip_address()
            self._headers["X-Forwarded-For"] = random_ip
            self._headers["X-Real-Ip"] = random_ip

        # 设置cookie
        if self._cookies:
            self._headers["Cookie"] = build_header_cookie_string(self._cookies)

        # 设置压缩格式
        if self._is_gzip:
            self._headers["Accept-Encoding"] = "gzip"

        # 使用json提交数据
        if self._method == "POST" and isinstance(self._fields, str):
            self._headers["Content-Type"] = "application/json"

        # 超时设置
        timeout = urllib3.Timeout(connect=float(self._connection_timeout) if self._connection_timeout > 0 else None,
                                  read=float(self._read_timeout) if self._read_timeout > 0 else None)

        retry_count = 0
        while True:
            thread_event.wait()
            if EXIT_FLAG:
                tool.process_exit(const.ExitCode.NORMAL)

            if self._is_check_qps and _qps(self._url):
                time.sleep(random.randint(60, 120))
                continue

            try:
                if self._method in ["DELETE", "GET", "HEAD", "OPTIONS"]:
                    response = connection_pool.request(self._method, self._url, fields=self._fields, headers=self._headers, redirect=self._is_redirect, timeout=timeout)
                else:
                    if self._method == "POST" and isinstance(self._fields, str):
                        response = connection_pool.request(self._method, self._url, body=self._fields, encode_multipart=self._is_encode_multipart, headers=self._headers,
                                                           redirect=self._is_redirect, timeout=timeout)
                    else:
                        response = connection_pool.request(self._method, self._url, fields=self._fields, encode_multipart=self._is_encode_multipart, headers=self._headers,
                                                           redirect=self._is_redirect, timeout=timeout)
                response.content = ""
                response.json_data = {}
                if response.status == const.ResponseCode.SUCCEED or response.status == 201:
                    if self._is_decode_content:
                        charset = DEFAULT_CHARSET
                        content_type = response.headers.get("Content-Type")
                        if content_type is not None:
                            content_charset = tool.find_sub_string(content_type, "charset=", None)
                            if content_charset:
                                if content_charset == "gb2312":
                                    charset = "GBK"
                                else:
                                    charset = content_charset
                        response.content = response.data.decode(charset, errors="ignore")
                        if self._is_json_decode:
                            try:
                                response.json_data = json.loads(response.content)
                            except json.decoder.JSONDecodeError:
                                response.status = const.ResponseCode.JSON_DECODE_ERROR
                elif response.status == 429:  # Too Many Requests
                    log.warning(self._url + " Too Many Requests, sleep")
                    time.sleep(NET_CONFIG.TOO_MANY_REQUESTS_WAIT_TIME)
                    continue
                elif response.status in [500, 502, 503, 504] and self._is_auto_retry:  # 服务器临时性错误，重试
                    if retry_count < NET_CONFIG.HTTP_REQUEST_RETRY_COUNT:
                        retry_count += 1
                        time.sleep(NET_CONFIG.SERVICE_INTERNAL_ERROR_WAIT_TIME)
                        continue
                    else:
                        return response
                return response
            except MemoryError:
                return ErrorResponse(const.ResponseCode.RESPONSE_TO_LARGE)
            except Exception as e:
                message = str(e)
                if isinstance(e, urllib3.exceptions.ConnectTimeoutError):
                    # 域名无法解析
                    if message.find("[Errno 11004] getaddrinfo failed") >= 0 or message.find("[Errno 11001] getaddrinfo failed") >= 0:
                        return ErrorResponse(const.ResponseCode.DOMAIN_NOT_RESOLVED)
                    elif message.find("[WinError 10061]") >= 0:
                        # [WinError 10061] 由于目标计算机积极拒绝，无法连接。
                        return ErrorResponse(const.ResponseCode.RETRY)
                elif isinstance(e, urllib3.exceptions.MaxRetryError):
                    if message.find("Caused by ResponseError('too many redirects'") >= 0:
                        return ErrorResponse(const.ResponseCode.TOO_MANY_REDIRECTS)
                elif isinstance(e, urllib3.exceptions.DecodeError):
                    if message.find("'Received response with content-encoding: gzip, but failed to decode it.'") >= 0:
                        self._is_url_encode = False
                        self._is_gzip = False
                        return self._start_request()
                # import traceback
                # log.error(message)
                # log.error(traceback.format_exc())
                if "Range" in self._headers:
                    range_string = "range: " + self._headers["Range"].replace("bytes=", "")
                    log.warning(self._url + f"[{range_string}] 访问超时，重试中")
                else:
                    log.warning(self._url + " 访问超时，重试中")
                time.sleep(NET_CONFIG.HTTP_REQUEST_RETRY_WAIT_TIME)

            retry_count += 1
            if retry_count >= NET_CONFIG.HTTP_REQUEST_RETRY_COUNT:
                log.warning("无法访问页面：" + self._url)
                return ErrorResponse(const.ResponseCode.RETRY)


class Download:
    def __init__(self, file_url: str, file_path: str, headers: Optional[dict[str, str]] = None, cookies: Optional[dict[str, str]] = None,
                 auto_multipart_download: bool = False, **kwargs) -> None:
        """
        下载远程文件到本地

        :Args:
        - file_url - the remote resource URL which you want to download
        - file_path - the local file path which you want to save remote resource
        - headers - customize header dictionary
        - cookies - customize cookies dictionary, will replace headers["Cookie"]
        - auto_multipart_download - "HEAD" method request to check response status and file size before download file

        :Returns:
            - status - 0 download failure, 1 download successful
            - code - failure reason
            - file_path - finally local file path(when recheck_file_extension is True, will rename it)
        """
        self._file_url: str = file_url
        self._file_path: str = format_path(file_path)
        # is auto rename file according to "Content-Type" in response headers
        self._recheck_file_extension: bool = False
        self._auto_multipart_download: bool = auto_multipart_download
        self._headers: dict[str, str] = headers if isinstance(headers, dict) else {}
        self._cookies: dict[str, str] = cookies if isinstance(cookies, dict) else {}

        # 返回长度
        self._content_length: int = 0
        # 是否开启分段下载
        self._is_multipart_download: bool = False
        # 结果
        self._is_start: bool = False
        self._status: const.DownloadStatus = const.DownloadStatus.FAILED
        self._code: const.DownloadCode = const.DownloadCode.FILE_CREATE_FAILED
        self.ext: dict[str, Any] = {}
        self.kwargs: dict[str, Any] = kwargs.copy()

    def __bool__(self) -> bool:
        return self.status == const.DownloadStatus.SUCCEED

    @property
    def status(self) -> const.DownloadStatus:
        return self.start_download()._status

    @property
    def code(self) -> const.DownloadCode:
        return self.start_download()._code

    def start_download(self) -> Self:
        if not self._is_start:
            try:
                self._start_download()
            except KeyboardInterrupt:
                tool.process_exit(const.ExitCode.NORMAL)
        return self

    def _start_download(self) -> None:
        """
        主体下载逻辑
        """
        self._is_start = True

        # 同名文件已经存在，直接返回
        if not DOWNLOAD_REPLACE_IF_EXIST and os.path.exists(self._file_path) and os.path.getsize(self._file_path) > 0:
            log.warning(f"文件{self._file_path}（{self._file_url}）已存在，跳过")
            self._status = const.DownloadStatus.SUCCEED
            return

        # 判断保存目录是否存在
        if not path.create_dir(os.path.dirname(self._file_path)):
            self._code = const.DownloadCode.FILE_CREATE_FAILED
            return

        # 是否需要分段下载
        self.check_auto_multipart_download()

        # 下载
        for retry_count in range(NET_CONFIG.DOWNLOAD_RETRY_COUNT):
            if EXIT_FLAG:
                self._code = const.DownloadCode.PROCESS_EXIT
                break

            if not self._is_multipart_download:
                # 单线程下载
                if not self.single_download():
                    continue
            else:
                # 分段下载
                if not self.multipart_download():
                    continue

            # 如果没有返回文件的长度，直接下载成功
            if self._content_length == 0:
                self._status = const.DownloadStatus.SUCCEED
                self._code = 0
                return

            # 判断文件下载后的大小和response中的Content-Length是否一致
            file_size = os.path.getsize(self._file_path)
            if self._content_length == file_size:
                self._status = const.DownloadStatus.SUCCEED
                self._code = 0
                return
            else:
                self._code = const.DownloadCode.FILE_SIZE_INVALID
                log.warning(f"本地文件{self._file_path}：{self._content_length}和网络文件{self._file_url}：{file_size}不一致")
                time.sleep(NET_CONFIG.HTTP_REQUEST_RETRY_WAIT_TIME)

        # 删除可能出现的临时文件
        path.delete_dir_or_file(self._file_path)

    def check_auto_multipart_download(self) -> None:
        """
        是否需要分段下载
        """
        # 先获取头信息
        if self._auto_multipart_download:
            head_response = Request(self._file_url, method="HEAD", headers=self._headers, cookies=self._cookies).disable_decode_content()
            if "is_url_encode" in self.kwargs:
                head_response.disable_url_encode()
            # 其他返回状态，退出
            if head_response.status != const.ResponseCode.SUCCEED:
                # URL格式不正确
                if head_response.status == const.ResponseCode.URL_INVALID:
                    self._code = const.DownloadCode.URL_INVALID
                # 域名无法解析
                elif head_response.status == const.ResponseCode.DOMAIN_NOT_RESOLVED:
                    self._code = const.DownloadCode.RETRY_MAX_COUNT
                # 重定向次数过多
                elif head_response.status == const.ResponseCode.TOO_MANY_REDIRECTS:
                    self._code = const.DownloadCode.RETRY_MAX_COUNT
                # 超过重试次数
                elif head_response.status == const.ResponseCode.RETRY:
                    self._code = const.DownloadCode.RETRY_MAX_COUNT
                # 其他http code
                else:
                    self._code = head_response.status
                return

            # 检测文件后缀名是否正确
            self.rename_file_extension(head_response.headers)

            # 根据文件大小判断是否需要分段下载
            content_length = head_response.headers.get("Content-Length")
            if content_length is not None:
                self._content_length = int(content_length)
                # 文件比较大，使用分段下载
                if self._auto_multipart_download and self._content_length > NET_CONFIG.DOWNLOAD_MULTIPART_MIN_SIZE:
                    self._is_multipart_download = True

    def rename_file_extension(self, response_headers: HTTPHeaderDict) -> None:
        """
        检测文件后缀名是否正确
        """
        if self._recheck_file_extension:
            # response中的Content-Type作为文件后缀名
            content_type = response_headers.get("Content-Type")
            if content_type is not None:
                # 重置状态，避免反复修改
                self._recheck_file_extension = False

                if content_type != "octet-stream":
                    new_file_extension = MIME_DICTIONARY.get(content_type, content_type.split("/")[-1])
                    self._file_path = os.path.splitext(self._file_path)[0] + "." + new_file_extension

    def single_download(self) -> bool:
        """
        单线程下载
        """
        try:
            file_response = Request(self._file_url, method="GET", headers=self._headers, cookies=self._cookies).disable_decode_content() \
                .set_time_out(NET_CONFIG.DOWNLOAD_CONNECTION_TIMEOUT, NET_CONFIG.DOWNLOAD_READ_TIMEOUT)
            if "is_url_encode" in self.kwargs:
                file_response.disable_url_encode()
        except SystemExit:
            return False

        if file_response.status != const.ResponseCode.SUCCEED:
            # URL格式不正确
            if file_response.status == const.ResponseCode.URL_INVALID:
                self._code = const.DownloadCode.URL_INVALID
            # 域名无法解析
            elif file_response.status == const.ResponseCode.DOMAIN_NOT_RESOLVED:
                self._code = const.DownloadCode.RETRY_MAX_COUNT
            # 重定向次数过多
            elif file_response.status == const.ResponseCode.TOO_MANY_REDIRECTS:
                self._code = const.DownloadCode.RETRY_MAX_COUNT
            # 超过重试次数
            elif file_response.status == const.ResponseCode.RETRY:
                self._code = const.DownloadCode.RETRY_MAX_COUNT
            # 其他http code
            else:
                self._code = file_response.status
            return False

        if self._content_length == 0:
            content_length = file_response.headers.get("Content-Length")
            if content_length is not None:
                self._content_length = int(content_length)

        # 检测文件后缀名是否正确
        self.rename_file_extension(file_response.headers)

        # 下载
        with open(self._file_path, "wb") as file_handle:
            try:
                file_handle.write(file_response.data)
            except OSError as ose:
                if str(ose).find("No space left on device") != -1:
                    global EXIT_FLAG
                    EXIT_FLAG = True
                raise
        return True

    def multipart_download(self) -> bool:
        """
        分段下载
        """
        # 先创建文件（同时删除之前下载失败，可能生成的临时文件）
        with open(self._file_path, "w"):
            pass
        with open(self._file_path, "rb+") as file_handle:
            file_no = file_handle.fileno()
            end_pos = -1
            while end_pos < self._content_length - 1:
                start_pos = end_pos + 1
                end_pos = min(self._content_length - 1, start_pos + NET_CONFIG.DOWNLOAD_MULTIPART_BLOCK_SIZE - 1)

                # 分段的header信息
                headers = self._headers.copy()
                headers["Range"] = f"bytes={start_pos}-{end_pos}"

                # 创建一个副本
                with os.fdopen(os.dup(file_no), "rb+", -1) as fd_handle:
                    for multipart_retry_count in range(NET_CONFIG.DOWNLOAD_RETRY_COUNT):
                        try:
                            multipart_response = Request(self._file_url, method="GET", headers=headers).disable_decode_content() \
                                .set_time_out(NET_CONFIG.DOWNLOAD_CONNECTION_TIMEOUT, NET_CONFIG.DOWNLOAD_READ_TIMEOUT)
                            if "is_url_encode" in self.kwargs:
                                multipart_response.disable_url_encode()
                        except SystemExit:
                            return False
                        if multipart_response.status == 206:
                            # 下载的文件和请求的文件大小不一致
                            if len(multipart_response.data) != (end_pos - start_pos + 1):
                                log.warning(f"网络文件{self._file_url}：range {start_pos} - {end_pos}实际下载大小 {len(multipart_response.data)} 不一致")
                                time.sleep(NET_CONFIG.HTTP_REQUEST_RETRY_WAIT_TIME)
                            else:
                                # 写入本地文件后退出
                                fd_handle.seek(start_pos)
                                fd_handle.write(multipart_response.data)
                                break
                    else:
                        self._code = const.DownloadCode.RETRY_MAX_COUNT
                        return False
        return True

    def update(self, other_download_return: Self) -> Self:
        if other_download_return._file_path == self._file_path:
            self._status = other_download_return.status
            self._code = other_download_return.code
            self._file_url = other_download_return._file_url
        return self

    def __getitem__(self, item: str) -> Any:
        return self.ext.get(item, None)

    def __setitem__(self, item: str, value: Any) -> Self:
        self.ext[item] = value
        return self


def download_from_list(file_url_list: list[str], file_path: str, headers: Optional[dict[str, str]] = None, cookies: Optional[dict[str, str]] = None) -> bool:
    """
    Visit web and save to local(multiple remote resource, single local file)

    :Args:
    - file_url_list - the list of remote resource URL which you want to save
    - file_path - the local file path which you want to save remote resource
    - headers - customize header dictionary
    - cookies - customize cookies dictionary, will replace headers["Cookie"]

    :Returns:
        - status - 0 download failure, 1 download successful
        - code - failure reason
    """
    # 同名文件已经存在，直接返回
    if not DOWNLOAD_REPLACE_IF_EXIST and os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        log.warning(f"文件{file_path}（{file_url_list}）已存在，跳过")
        return True

    index = 1
    part_file_path_list = []
    is_succeed = False
    for file_url in file_url_list:
        # 临时文件路径
        part_file_path = f"{file_path}.part{index}"
        if os.path.exists(os.path.realpath(part_file_path)):
            break
        part_file_path_list.append(part_file_path)
        # 下载
        part_download_return = Download(file_url, part_file_path, headers=headers, cookies=cookies)
        if part_download_return.status == const.DownloadStatus.FAILED:
            break
        index += 1
    else:
        with open(file_path, "wb") as file_handle:
            for part_file_path in part_file_path_list:
                with open(part_file_path, "rb") as part_file_handle:
                    file_handle.write(part_file_handle.read())
        is_succeed = True
    # 删除临时文件
    for part_file_path in part_file_path_list:
        path.delete_dir_or_file(part_file_path)

    return is_succeed


class DownloadHls:
    def __init__(self, playlist_url: str, file_path: str, headers: Optional[dict[str, str]] = None, cookies: Optional[dict[str, str]] = None, **kwargs) -> None:
        """
        下载HTTP Live Streaming协议的远程文件到本地

        :Args:
        - playlist_url - the remote playlist file URL which you want to download
        - file_path - the local file path which you want to save remote resource
        - headers - customize header dictionary
        - cookies - customize cookies dictionary, will replace headers["Cookie"]

        :Returns:
            - status - 0 download failure, 1 download successful
            - code - failure reason
            - file_path - finally local file path(when recheck_file_extension is True, will rename it)
        """
        self._playlist_url: str = playlist_url
        self._file_path: str = format_path(file_path)
        self._headers: dict[str, str] = headers if isinstance(headers, dict) else {}
        self._cookies: dict[str, str] = cookies if isinstance(cookies, dict) else {}

        # 结果
        self._is_start: bool = False
        self._status: const.DownloadStatus = const.DownloadStatus.FAILED
        self._code: const.DownloadCode = const.DownloadCode.FILE_CREATE_FAILED
        self.ext: dict[str, Any] = {}
        self.kwargs: dict[str, Any] = kwargs.copy()

    def __bool__(self) -> bool:
        return self.status == const.DownloadStatus.SUCCEED

    @property
    def status(self) -> const.DownloadStatus:
        return self.start_download()._status

    @property
    def code(self) -> const.DownloadCode:
        return self.start_download()._code

    def start_download(self) -> Self:
        if not self._is_start:
            try:
                self._start_download()
            except KeyboardInterrupt:
                tool.process_exit(const.ExitCode.NORMAL)
        return self

    def _start_download(self) -> None:
        """
        主体下载逻辑
        """
        self._is_start = True

        # 同名文件已经存在，直接返回
        if not DOWNLOAD_REPLACE_IF_EXIST and os.path.exists(self._file_path) and os.path.getsize(self._file_path) > 0:
            log.warning(f"文件{self._file_path}（{self._playlist_url}）已存在，跳过")
            self._status = const.DownloadStatus.SUCCEED
            return

        playlist_response = Request(self._playlist_url, method="GET", cookies=self._cookies, headers=self._headers)
        if playlist_response.status != const.ResponseCode.SUCCEED:
            self._code = const.DownloadCode.PLAYLIST_VISIT_FAILED
            return

        part_file_url_list = []
        for file_line in playlist_response.content.split("\n"):
            file_line = file_line.strip()
            if not file_line or file_line.startswith("#"):
                continue
            part_file_url_list.append(urllib.parse.urljoin(self._playlist_url, file_line))
        if len(part_file_url_list) == 0:
            self._code = const.DownloadCode.PLAYLIST_VISIT_FAILED
            return

        index = 1
        part_file_path_list = []
        is_succeed = False
        for part_file_url in part_file_url_list:
            if EXIT_FLAG:
                self._code = const.DownloadCode.PROCESS_EXIT
                break

            # 临时文件路径
            part_file_path = f"{self._file_path}.part{index}"
            part_file_path_list.append(part_file_path)

            # 下载
            log.info(f"HLS: {self._playlist_url} [{len(part_file_path_list)}/{len(part_file_url_list)}]")
            part_download_return = Download(part_file_url, part_file_path, headers=self._headers, cookies=self._cookies)
            if part_download_return.status == const.DownloadStatus.FAILED:
                if part_download_return.code == const.DownloadCode.PROCESS_EXIT:
                    self._code = const.DownloadCode.PROCESS_EXIT
                break
            index += 1
        else:
            with open(self._file_path, "wb") as file_handle:
                for part_file_path in part_file_path_list:
                    with open(part_file_path, "rb") as part_file_handle:
                        file_handle.write(part_file_handle.read())
            is_succeed = True
        # 删除临时文件
        for part_file_path in part_file_path_list:
            path.delete_dir_or_file(part_file_path)

        if is_succeed:
            self._status = const.DownloadStatus.SUCCEED
            self._code = 0
        else:
            self._code = const.DownloadCode.PART_FILE_DOWNLOAD_FAILED
