# -*- coding:UTF-8  -*-
"""
爬虫父类
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import codecs
import configparser
import os
import platform
import sys
import threading
import time
import traceback
from typing import Any, Callable, Optional, Union, Type, Self
from common import const, browser, file, log, net, path, port_listener_event, tool, CrawlerException
from common import IS_EXECUTABLE, PROJECT_ROOT_PATH, PROJECT_CONFIG_PATH
if platform.system() == "Windows":
    from common import keyboard_event

# 默认当前进程的工作目录，应用在初始化时应该对该变量进行赋值
PROJECT_APP_PATH = os.getcwd()


class CrawlerSingleValueSaveData:
    def __init__(self, save_data_path: str, type_check: Optional[str] = None) -> None:
        self._save_data_path: str = save_data_path
        self._save_data: str = ""
        if type_check == "int":
            self._save_data = "0"
        elif type_check.startswith("int_"):
            default_value = tool.remove_string_prefix(type_check, "int_")
            if tool.is_integer(default_value):
                self._save_data = default_value
            else:
                raise CrawlerException(f"无效的type_check：{type_check}", True)
        if os.path.exists(self._save_data_path):
            self._save_data = file.read_file(self._save_data_path).strip()
            if type_check is not None:
                type_check_error = False
                if type_check == "int" or (type_check.startswith("int_") and tool.is_integer(tool.remove_string_prefix(type_check, "int_"))):
                    type_check_error = not tool.is_integer(self._save_data)
                elif type_check == "date":
                    type_check_error = not tool.is_date(self._save_data)
                elif type_check == "datetime":
                    type_check_error = not tool.is_datetime(self._save_data)
                elif type_check == "url":
                    type_check_error = not (self._save_data.startswith("http://") or self._save_data.startswith("https://"))
                if type_check_error:
                    raise CrawlerException("存档内数据格式不正确", True)

    def value(self) -> str:
        return self._save_data

    def update(self, data: str) -> None:
        self._save_data = data

    def incr(self, step: int) -> None:
        self._save_data = str(int(self._save_data) + step)

    def save(self) -> None:
        file.write_file(self._save_data, self._save_data_path, const.WriteFileMode.REPLACE)


class CrawlerMultiValueSaveData:
    def __init__(self, save_data_path: str, type_check_list: Optional[list[str]] = None) -> None:
        self._save_data_path: str = save_data_path
        if not isinstance(type_check_list, list):
            raise CrawlerException("类型检测参数错误", True)
        self._save_data: list[str] = []
        if os.path.exists(self._save_data_path):
            file_save_data = file.read_file(self._save_data_path).strip()
            self._save_data = file_save_data.split("\t")
        for index in range(len(type_check_list)):
            type_check = type_check_list[index]
            if len(self._save_data) > index:
                self._save_data[index] = self._save_data[index].strip()
                type_check_error = False
                if type_check == "int" or (type_check.startswith("int_") and tool.is_integer(tool.remove_string_prefix(type_check, "int_"))):
                    type_check_error = not tool.is_integer(self._save_data[index])
                elif type_check == "date":
                    type_check_error = not tool.is_date(self._save_data[index])
                elif type_check == "datetime":
                    type_check_error = not tool.is_datetime(self._save_data[index])
                elif type_check == "url":
                    type_check_error = not (self._save_data[index].startswith("http://") or self._save_data[index].startswith("https://"))
                if type_check_error:
                    raise CrawlerException("存档内数据格式不正确", True)
            else:
                defalut_value = ""
                if type_check == "int":
                    defalut_value = "0"
                elif type_check == "int_1":
                    defalut_value = "1"
                self._save_data.append(defalut_value)

    def get(self, index: int) -> str:
        return self._save_data[index]

    def set(self, index: int, data: str) -> None:
        self._save_data[index] = data

    def update(self, data: list[str]) -> None:
        self._save_data = data

    def save(self) -> None:
        file.write_file("\t".join(self._save_data), self._save_data_path, const.WriteFileMode.REPLACE)


class CrawlerSaveData:
    def __init__(self, save_data_path: str, save_data_format: Optional[tuple[int, list[str]]] = None) -> None:
        self._save_data_path: str = save_data_path
        if not os.path.exists(self._save_data_path):
            raise CrawlerException(f"存档文件 {self._save_data_path} 不存在！", True)
        temp_file_name = tool.convert_timestamp_to_formatted_time("%m-%d_%H_%M_") + os.path.basename(self._save_data_path)
        self._temp_save_data_path: str = os.path.join(os.path.dirname(self._save_data_path), temp_file_name)
        if os.path.exists(self._temp_save_data_path):
            raise CrawlerException(f"存档临时文件 {self._temp_save_data_path} 已存在！", True)
        self._save_data: dict[str, list] = {}
        if save_data_format is not None:
            if isinstance(save_data_format, tuple) and len(save_data_format) == 2 and \
                    tool.is_integer(save_data_format[0]) and isinstance(save_data_format[1], list):
                self._save_data = read_save_data(self._save_data_path, save_data_format[0], save_data_format[1])
            else:
                raise CrawlerException(f"存档文件默认格式 {save_data_format} 不正确", True)
        self._thread_lock: threading.Lock = threading.Lock()  # 线程锁，避免同时读写存档文件
        self._completed_save_data: dict[str, list] = {}

    def keys(self):
        return self._save_data.keys()

    def get(self, key: str) -> list:
        return self._save_data[key]

    def update(self, key: str, data: list) -> None:
        self._save_data[key] = data

    def save(self, key: str, data: list) -> None:
        # 从待执行的记录里删除
        self._save_data.pop(key)
        self._completed_save_data[key] = data

        # 写入临时存档
        if data:
            with self._thread_lock:
                file.write_file("\t".join(data), self._temp_save_data_path)

    def done(self) -> None:
        # 将剩余未处理的存档数据写入临时存档文件
        if len(self._save_data) > 0:
            file.write_file(tool.dyadic_list_to_string(list(self._save_data.values())), self._temp_save_data_path)
            self._completed_save_data.update(self._save_data)
            self._save_data = {}

        # 将临时存档文件按照主键排序后写入原始存档文件
        # 只支持一行一条记录，每条记录格式相同的存档文件
        save_data = read_save_data(self._temp_save_data_path, 0, [])
        temp_list = [save_data[key] for key in sorted(save_data.keys())]
        file.write_file(tool.dyadic_list_to_string(temp_list), self._save_data_path, const.WriteFileMode.REPLACE)
        path.delete_dir_or_file(self._temp_save_data_path)


class CrawlerCache:
    def __init__(self, file_path: str, cache_type: const.FileType) -> None:
        if not isinstance(cache_type, const.FileType):
            raise ValueError("invalid cache_type")
        self._cache_path = file_path
        self._cache_type = cache_type

    def read(self) -> Any:
        if self._cache_type == const.FileType.LINES:
            return file.read_file(self._cache_path, const.ReadFileMode.LINE)
        elif self._cache_type == const.FileType.JSON:
            return file.read_json_file(self._cache_path)
        else:
            file_string = file.read_file(self._cache_path, const.ReadFileMode.FULL).strip()
            if self._cache_type == const.FileType.COMMA_DELIMITED:
                return file_string.split(",")
            else:
                return file_string

    def write(self, msg: Any) -> bool:
        if self._cache_type == const.FileType.JSON:
            return file.write_json_file(msg, self._cache_path)
        else:
            if self._cache_type in [const.FileType.LINES, const.FileType.COMMA_DELIMITED] and not isinstance(msg, list):
                raise ValueError(f"type of msg must is list when cache_type = {self._cache_type}")
            if self._cache_type == const.FileType.LINES:
                write_string = "\n".join(msg)
            elif self._cache_type == const.FileType.COMMA_DELIMITED:
                write_string = ",".join(msg)
            else:
                write_string = str(msg)
            return file.write_file(write_string, self._cache_path, const.WriteFileMode.REPLACE)

    def append(self, msg: str) -> bool:
        if self._cache_type != const.FileType.LINES:
            raise ValueError(f"can't append msg when cache_type != {const.FileType.LINES}")
        return file.write_file(msg, self._cache_path, const.WriteFileMode.APPEND)

    def clear(self) -> bool:
        return path.delete_dir_or_file(self._cache_path)

    @property
    def cache_path(self) -> str:
        return self._cache_path


class Crawler(object):
    # 程序全局变量的设置
    def __init__(self, sys_config: dict[const.SysConfigKey, Any], **kwargs) -> None:
        """
        :Args:
        - sys_config
            - download_photo - 程序是否支持下载图片功能，默认值：False
            - download_video - 程序是否支持下载视频功能，默认值：False
            - download_audio - 程序是否支持下载音频功能，默认值：False
            - download_content - 程序是否支持下载文本内容功能，默认值：False
            - set_proxy - 程序是否默认需要设置代理，默认值：False
            - no_save_data - 程序是否支持不需要存档文件就可以开始运行，默认值：False
            - no_download - 程序没有任何下载行为，默认值：False
            - get_cookie - 程序是否需要从浏览器存储的cookie中获取指定cookie的值，默认值：False
            - app_config - 程序额外应用配置，存在相同配置参数时将会将其他值覆盖
            - app_config_path - 程序默认的app配置文件路径，赋值后将不会读取原本的app.ini文件
        - kwargs
            - extra_sys_config - 通过类实例化时传入的程序配置
            - extra_app_config - 通过类实例化时传入的应用配置
        """
        self.start_time: float = time.time()
        self.process_status: bool = True  # 主进程是否在运行

        # 程序启动配置
        if not isinstance(sys_config, dict):
            raise CrawlerException("程序启动配置不存在，请检查代码！", True)
        # 额外初始化配置（直接通过实例化中传入，可覆盖子类__init__方法传递的sys_config参数）
        if "extra_sys_config" in kwargs and isinstance(kwargs["extra_sys_config"], dict):
            sys_config.update(kwargs["extra_sys_config"])
        sys_download_photo = sys_config.get(const.SysConfigKey.DOWNLOAD_PHOTO, False)
        sys_download_video = sys_config.get(const.SysConfigKey.DOWNLOAD_VIDEO, False)
        sys_download_audio = sys_config.get(const.SysConfigKey.DOWNLOAD_AUDIO, False)
        sys_download_content = sys_config.get(const.SysConfigKey.DOWNLOAD_CONTENT, False)
        sys_set_proxy = sys_config.get(const.SysConfigKey.SET_PROXY, False)
        sys_get_cookie = sys_config.get(const.SysConfigKey.GET_COOKIE, set())
        sys_not_check_save_data = sys_config.get(const.SysConfigKey.NOT_CHECK_SAVE_DATA, False)
        sys_not_download = sys_config.get(const.SysConfigKey.NOT_DOWNLOAD, False)

        if IS_EXECUTABLE:
            application_path = os.path.dirname(sys.executable)
            os.chdir(application_path)
            config_path = os.path.join(os.getcwd(), "data/config.ini")
        else:
            config_path = PROJECT_CONFIG_PATH

        # 程序配置
        config = read_config(config_path)
        # 应用配置
        app_config_path = sys_config.get(const.SysConfigKey.APP_CONFIG_PATH, os.path.abspath(os.path.join(PROJECT_APP_PATH, "app.ini")))
        if os.path.exists(app_config_path):
            config.update(read_config(app_config_path))
        # 额外应用配置（直接通过实例化中传入，可覆盖配置文件中参数）
        if "extra_app_config" in kwargs and isinstance(kwargs["extra_app_config"], dict):
            config.update(kwargs["extra_app_config"])

        # 应用配置
        self.app_config: dict[str, Any] = {}
        for app_config_temp in sys_config.get(const.SysConfigKey.APP_CONFIG, set()):
            if len(app_config_temp) != 3:
                continue
            self.app_config[app_config_temp[0]] = analysis_config(config, app_config_temp[0], app_config_temp[1], app_config_temp[2])

        # 是否下载
        self.is_download_photo: bool = sys_download_photo and analysis_config(config, "IS_DOWNLOAD_PHOTO", True, const.ConfigAnalysisMode.BOOLEAN)
        self.is_download_video: bool = sys_download_video and analysis_config(config, "IS_DOWNLOAD_VIDEO", True, const.ConfigAnalysisMode.BOOLEAN)
        self.is_download_audio: bool = sys_download_audio and analysis_config(config, "IS_DOWNLOAD_AUDIO", True, const.ConfigAnalysisMode.BOOLEAN)
        self.is_download_content: bool = sys_download_content and analysis_config(config, "IS_DOWNLOAD_CONTENT", True, const.ConfigAnalysisMode.BOOLEAN)

        if not sys_not_download and (sys_download_photo or sys_download_video or sys_download_audio or sys_download_content):
            if not (self.is_download_photo or self.is_download_video or self.is_download_audio or self.is_download_content):
                raise CrawlerException("所有支持的下载都没有开启，请检查配置！", True)

        # 下载文件时是否覆盖已存在的同名文件
        net.DOWNLOAD_REPLACE_IF_EXIST = analysis_config(config, "IS_DOWNLOAD_REPLACE_IF_EXIST", False, const.ConfigAnalysisMode.BOOLEAN)

        # 存档
        self.save_data_path: str = analysis_config(config, "SAVE_DATA_PATH", r"\\info/save.data", const.ConfigAnalysisMode.PATH)
        self.save_data: Optional[CrawlerSaveData] = None
        if not sys_not_check_save_data:
            self.save_data = CrawlerSaveData(self.save_data_path, sys_config.get(const.SysConfigKey.SAVE_DATA_FORMATE, None))

        # cache
        self.cache_data_path: str = analysis_config(config, "CACHE_DATA_PATH", r"\\cache", const.ConfigAnalysisMode.PATH)

        # session
        self.session_data_path: str = analysis_config(config, "SESSION_DATA_PATH", r"\\info/session.data", const.ConfigAnalysisMode.PATH)

        # 图片保存目录
        self.photo_download_path: str = ""
        if self.is_download_photo:
            self.photo_download_path = analysis_config(config, "PHOTO_DOWNLOAD_PATH", r"\\photo", const.ConfigAnalysisMode.PATH)
        # 视频保存目录
        self.video_download_path: str = ""
        if self.is_download_video:
            self.video_download_path = analysis_config(config, "VIDEO_DOWNLOAD_PATH", r"\\video", const.ConfigAnalysisMode.PATH)
        # 音频保存目录
        self.audio_download_path: str = ""
        if self.is_download_audio:
            self.audio_download_path = analysis_config(config, "AUDIO_DOWNLOAD_PATH", r"\\audio", const.ConfigAnalysisMode.PATH)
        # 文本保存目录
        self.content_download_path: str = ""
        if self.is_download_content:
            self.content_download_path = analysis_config(config, "CONTENT_DOWNLOAD_PATH", r"\\content", const.ConfigAnalysisMode.PATH)

        # 是否在下载失败后退出线程的运行
        self.exit_after_download_failure: bool = analysis_config(config, "EXIT_AFTER_DOWNLOAD_FAILURE", r"\\content", const.ConfigAnalysisMode.BOOLEAN)

        # 代理
        is_proxy = analysis_config(config, "IS_PROXY", 2, const.ConfigAnalysisMode.INTEGER)
        if is_proxy == 1 or (is_proxy == 2 and sys_set_proxy):
            proxy_ip = analysis_config(config, "PROXY_IP", "127.0.0.1")
            proxy_port = analysis_config(config, "PROXY_PORT", "8087")
            # 使用代理的线程池
            net.set_proxy(proxy_ip, proxy_port)
        else:
            # 初始化urllib3的线程池
            net.init_http_connection_pool()

        # cookies
        self.cookie_value: dict[str, str] = {}
        if sys_get_cookie:
            # 操作系统&浏览器
            browser_type = const.BrowserType[analysis_config(config, "BROWSER_TYPE", "chrome", const.ConfigAnalysisMode.RAW)]
            # cookie
            cookie_path = analysis_config(config, "COOKIE_PATH", "", const.ConfigAnalysisMode.RAW)
            if cookie_path:
                cookie_path = analysis_config(config, "COOKIE_PATH", "", const.ConfigAnalysisMode.PATH)
            else:
                cookie_path = browser.get_default_browser_cookie_path(browser_type)
            all_cookie_from_browser = browser.get_all_cookie_from_browser(browser_type, cookie_path)
            if browser_type == const.BrowserType.TEXT:
                if "DEFAULT" in all_cookie_from_browser:
                    self.cookie_value.update(all_cookie_from_browser["DEFAULT"])
            else:
                for cookie_domain in sys_get_cookie:
                    check_domain_list = [cookie_domain]
                    if cookie_domain[0].startswith("."):
                        check_domain_list.append(cookie_domain[1:])
                    else:
                        check_domain_list.append("." + cookie_domain)
                    for check_domain in check_domain_list:
                        if check_domain in all_cookie_from_browser:
                            self.cookie_value.update(all_cookie_from_browser[check_domain])

        # 线程数
        self.thread_count: int = analysis_config(config, "THREAD_COUNT", 10, const.ConfigAnalysisMode.INTEGER)
        self.thread_lock: threading.Lock = threading.Lock()  # 线程锁，避免操作一些全局参数
        self.thread_semaphore: threading.Semaphore = threading.Semaphore(self.thread_count)  # 线程总数信号量

        # 启用线程监控是否需要暂停其他下载线程
        if analysis_config(config, "IS_PORT_LISTENER_EVENT", False, const.ConfigAnalysisMode.BOOLEAN):
            listener_port = analysis_config(config, "LISTENER_PORT", 12345, const.ConfigAnalysisMode.INTEGER)
            listener_event_bind = {
                str(const.ProcessStatus.PAUSE): net.pause_request,  # 暂停进程
                str(const.ProcessStatus.RUN): net.resume_request,  # 继续进程
                str(const.ProcessStatus.STOP): self.stop_process  # 结束进程（取消当前的线程，完成任务）
            }
            process_control_thread = port_listener_event.PortListenerEvent(port=listener_port, event_list=listener_event_bind)
            process_control_thread.daemon = True
            process_control_thread.start()

        # 键盘监控线程（仅支持windows）
        if platform.system() == "Windows" and analysis_config(config, "IS_KEYBOARD_EVENT", False, const.ConfigAnalysisMode.BOOLEAN):
            keyboard_event_bind = {}
            pause_process_key = analysis_config(config, "PAUSE_PROCESS_KEYBOARD_KEY", "F9")
            # 暂停进程
            if pause_process_key:
                keyboard_event_bind[pause_process_key] = self.pause_process
            # 继续进程
            continue_process_key = analysis_config(config, "CONTINUE_PROCESS_KEYBOARD_KEY", "F10")
            if continue_process_key:
                keyboard_event_bind[continue_process_key] = self.resume_process
            # 结束进程（取消当前的线程，完成任务）
            stop_process_key = analysis_config(config, "STOP_PROCESS_KEYBOARD_KEY", "CTRL + F12")
            if stop_process_key:
                keyboard_event_bind[stop_process_key] = self.stop_process

            if keyboard_event_bind:
                keyboard_control_thread = keyboard_event.KeyboardEvent(keyboard_event_bind)
                keyboard_control_thread.daemon = True
                keyboard_control_thread.start()

        self.total_photo_count: int = 0
        self.total_video_count: int = 0
        self.total_audio_count: int = 0
        self.total_content_count: int = 0

        self.download_thead_list: list["DownloadThread"] = []  # 下载线程
        self.crawler_thread: Optional[Type["CrawlerThread"]] = None  # 下载子线程
        log.info("初始化完成")

    def main(self) -> None:
        try:
            self.init()

            self._main()
        except (KeyboardInterrupt, SystemExit) as e:
            if self.crawler_thread and issubclass(self.crawler_thread, CrawlerThread):
                self.stop_process()
            else:
                if isinstance(e, SystemExit) and e.code == const.ExitCode.ERROR:
                    log.info("异常退出")
                else:
                    log.info("提前退出")
        except Exception as e:
            log.error("未知异常")
            log.error(str(e) + "\n" + traceback.format_exc())

        # 保存剩余未完成的数据，并重新排序保存存档文件
        self.complete_save_data()

        # 其他结束操作
        self.done()

        # 结束日志
        self.end_message()

    def _main(self) -> None:
        if self.crawler_thread and issubclass(self.crawler_thread, CrawlerThread):
            # 循环下载每个id
            thread_list = []
            for index_key in sorted(self.save_data.keys()):
                # 提前结束
                if not self.is_running():
                    break

                # 开始下载
                thread = self.crawler_thread(self, self.save_data.get(index_key))
                thread.start()
                thread_list.append(thread)

                time.sleep(1)

            # 等待子线程全部完成
            while len(thread_list) > 0:
                thread_list.pop().join()

    def init(self) -> None:
        """
        其他初始化的方法
        """
        pass

    def done(self) -> None:
        """
        其他结束操作
        """
        pass

    def set_crawler_thread(self, crawler_thread: Type["CrawlerThread"]) -> Self:
        self.crawler_thread = crawler_thread
        return self

    @staticmethod
    def pause_process() -> None:
        net.pause_request()

    @staticmethod
    def resume_process() -> None:
        net.resume_request()

    def stop_process(self) -> None:
        log.info("stop process")
        self.process_status = False
        net.EXIT_FLAG = True
        net.resume_request()

    def get_run_time(self) -> int:
        """
        获取程序已运行时间（秒）
        """
        return int(time.time() - self.start_time)

    def is_running(self) -> bool:
        return self.process_status

    def running_check(self) -> None:
        if not self.is_running():
            tool.process_exit(const.ExitCode.NORMAL)

    def complete_save_data(self) -> None:
        if isinstance(self.save_data, CrawlerSaveData):
            self.save_data.done()

    def end_message(self) -> None:
        message = f"全部下载完毕，耗时{self.get_run_time()}秒"
        download_result = []
        if self.is_download_photo:
            download_result.append(f"图片{self.total_photo_count}张")
        if self.is_download_video:
            download_result.append(f"视频{self.total_video_count}个")
        if self.is_download_audio:
            download_result.append(f"音频{self.total_audio_count}个")
        if self.is_download_content:
            download_result.append(f"文本{self.total_content_count}个")
        if download_result:
            message += "，共计下载" + "，".join(download_result)
        log.info(message)

    def start_parse(self, description: str) -> None:
        self.running_check()
        log.info("开始解析 " + description)

    @staticmethod
    def parse_result(description: str, parse_result_list: Union[list, dict]) -> None:
        log.debug(f"{description} 解析结果：{parse_result_list}")
        log.info(f"{description} 解析数量：{len(parse_result_list)}")

    def download(self, file_url: str, file_path: str, file_description: str, headers: Optional[dict[str, str]] = None, cookies: Optional[dict[str, str]] = None,
                 success_callback: Callable[[str, str, str, net.Download], bool] = None, failure_callback: Callable[[str, str, str, net.Download], bool] = None,
                 auto_multipart_download=False) -> net.Download:
        """
        下载
        :Args:
        - file_url - 远程地址
        - file_path - 本地下载路径
        - file_description - 文件描述
        - headers - 请求的headers
        - cookies - 请求的cookies
        - success_callback - 成功回调方法
            :Returns: 是否需要输出下载成功的日志
                True - 需要
                False - 不需要
        - failure_callback - 失败回调方法
            :Returns: 是否需要输出下载失败的日志并根据exit_after_download_failure检测程序是否退出
                True - 需要
                False - 不需要
        """
        self.running_check()
        log.info(f"开始下载 {file_description} {file_url}")
        download_return = net.Download(file_url, file_path, headers=headers, cookies=cookies, auto_multipart_download=auto_multipart_download)
        if download_return.status == const.DownloadStatus.SUCCEED:
            if success_callback is None or success_callback(file_url, file_path, file_description, download_return):
                log.info(f"{file_description} 下载成功")
        else:
            if failure_callback is None or failure_callback(file_url, file_path, file_description, download_return):
                log.error(f"{file_description} 下载失败，原因：{download_failre(download_return.code)}")
                if self.exit_after_download_failure:
                    tool.process_exit(const.ExitCode.NORMAL)
        return download_return

    def multi_thread_download(self, thread_class: Type["DownloadThread"], file_url: str, file_path: str, file_description: str,
                              headers: Optional[dict[str, str]] = None, cookies: Optional[dict[str, str]] = None) -> None:
        """
        多线程下载
        """
        self.running_check()
        thread = thread_class(self, file_url, file_path, file_description)
        if headers is not None:
            thread.set_download_header(headers)
        if cookies is not None:
            thread.set_download_cookies(cookies)
        thread.start()
        self.download_thead_list.append(thread)

    def wait_multi_thead_complete(self) -> None:
        """
        等待通过multi_thread_download()方法提交的多线程下载全部完成
        """
        is_error = False
        while len(self.download_thead_list) > 0:
            thread = self.download_thead_list.pop()
            thread.join()
            if self.is_running() and not thread.get_result():
                is_error = True
        if is_error and self.exit_after_download_failure:
            tool.process_exit(const.ExitCode.NORMAL)

    def new_cache(self, file_name: str, cache_type: const.FileType) -> CrawlerCache:
        cache_path = os.path.join(self.cache_data_path, file_name)
        return CrawlerCache(cache_path, cache_type)


class CrawlerThread(threading.Thread):
    main_thread: Optional[Crawler] = None
    thread_lock: Optional[threading.Lock] = None
    display_name: Optional[str] = None
    index_key: str = ""

    def __init__(self, main_thread: Crawler, single_save_data: list[str]) -> None:
        """
        多线程下载

        :Args:
        - main_thread - 主线程对象
        - single_save_data - 线程用到的数据
        """
        if not isinstance(main_thread, Crawler):
            raise CrawlerException("下载线程参数异常", True)
        try:
            threading.Thread.__init__(self)
            self.main_thread = main_thread
            self.thread_lock = main_thread.thread_lock
            main_thread.thread_semaphore.acquire()
        except KeyboardInterrupt:
            self.main_thread.stop_process()
        self.single_save_data = single_save_data
        self.total_photo_count = 0
        self.total_video_count = 0
        self.total_audio_count = 0
        self.total_content_count = 0
        self.temp_path_list = []
        if single_save_data:
            self.info("开始")

    def run(self) -> None:
        try:
            self._run()
        except KeyboardInterrupt:
            self.info("提前退出")
        except SystemExit as e:
            if e.code == const.ExitCode.ERROR:
                self.error("异常退出")
            else:
                self.info("提前退出")
        except Exception as e:
            self.error("未知异常")
            self.error(str(e) + "\n" + traceback.format_exc(), False)

        # 更新存档
        if self.index_key:
            self.main_thread.save_data.save(self.index_key, self.single_save_data)

        # 主线程计数累加
        if self.main_thread.is_download_photo:
            self.main_thread.total_photo_count += self.total_photo_count
        if self.main_thread.is_download_video:
            self.main_thread.total_video_count += self.total_video_count
        if self.main_thread.is_download_audio:
            self.main_thread.total_audio_count += self.total_audio_count
        if self.main_thread.is_download_content:
            self.main_thread.total_content_count += self.total_content_count

        # 清理临时文件（未完整下载的内容）
        for temp_path in self.temp_path_list:
            path.delete_dir_or_file(temp_path)

        self.end_message()

        # 唤醒主线程
        self.notify_main_thread()

    def _run(self) -> None:
        pass

    def main_thread_check(self) -> None:
        """
        检测主线程是否已经结束（外部中断）
        """
        if not self.main_thread.is_running():
            self.notify_main_thread()
            tool.process_exit(const.ExitCode.NORMAL)

    def notify_main_thread(self) -> None:
        """
        线程下完完成后唤醒主线程，开启新的线程（必须在线程完成后手动调用，否则会卡死主线程）
        """
        if isinstance(self.main_thread, Crawler):
            self.main_thread.thread_semaphore.release()

    def check_download_failure_exit(self, is_process_exit: bool = True) -> bool:
        """
        当下载失败，检测是否要退出线程
        """
        if self.main_thread.exit_after_download_failure:
            if is_process_exit:
                tool.process_exit(const.ExitCode.ERROR)
            else:
                return True
        return False

    def format_message(self, message: str) -> str:
        if self.display_name is not None:
            return self.display_name + " " + message
        else:
            return message

    def debug(self, message: str, include_display_name: bool = True) -> None:
        """
        trace log
        """
        if include_display_name:
            message = self.format_message(message)
        log.debug(message)

    def info(self, message: str, include_display_name: bool = True) -> None:
        """
        step log
        """
        if include_display_name:
            message = self.format_message(message)
        log.info(message)

    def warning(self, message: str, include_display_name: bool = True) -> None:
        """
        error log
        """
        if include_display_name:
            message = self.format_message(message)
        log.warning(message)

    def error(self, message: str, include_display_name: bool = True) -> None:
        """
        error log
        """
        if include_display_name:
            message = self.format_message(message)
        log.error(message)

    def start_parse(self, description: str) -> None:
        self.main_thread_check()
        self.info("开始解析 " + description)

    def parse_result(self, description: str, parse_result_list: Union[list, dict]) -> None:
        self.debug(f"{description} 解析结果：{parse_result_list}")
        self.info(f"{description} 解析数量：{len(parse_result_list)}")

    def end_message(self) -> None:
        message = "下载完毕"
        download_result = []
        if self.main_thread.is_download_photo:
            download_result.append(f"图片{self.total_photo_count}张")
        if self.main_thread.is_download_video:
            download_result.append(f"视频{self.total_video_count}个")
        if self.main_thread.is_download_audio:
            download_result.append(f"音频{self.total_audio_count}个")
        if self.main_thread.is_download_content:
            download_result.append(f"文本{self.total_content_count}个")
        if download_result:
            message += "，共计下载" + "，".join(download_result)
        self.info(message)

    def download(self, file_url: str, file_path: str, file_description: str, headers: Optional[dict[str, str]] = None, cookies: Optional[dict[str, str]] = None,
                 success_callback: Callable[[str, str, str, net.Download], bool] = None, failure_callback: Callable[[str, str, str, net.Download], bool] = None,
                 auto_multipart_download=False, is_failure_exit: bool = True, **kwargs) -> net.Download:
        """
        下载

        :Args:
        - file_url - 远程地址
        - file_path - 本地下载路径
        - file_description - 文件描述
        - success_callback - 成功回调方法
            :Returns: 是否需要输出下载成功的日志
                True - 需要
                False - 不需要
        - failure_callback - 失败回调方法
            :Returns: 是否需要输出下载失败的日志并根据exit_after_download_failure检测程序是否退出
                True - 需要
                False - 不需要
        """
        self.main_thread_check()
        self.info(f"开始下载 {file_description} {file_url}")
        download_return = net.Download(file_url, file_path, headers=headers, cookies=cookies, auto_multipart_download=auto_multipart_download, **kwargs)
        if download_return.status == const.DownloadStatus.SUCCEED:
            if success_callback is None or success_callback(file_url, file_path, file_description, download_return):
                self.info(f"{file_description} 下载成功")
        else:
            if failure_callback is None or failure_callback(file_url, file_path, file_description, download_return):
                self.error(f"{file_description} {file_url} 下载失败，原因：{download_failre(download_return.code)}")
                self.check_download_failure_exit(is_failure_exit)
        return download_return


class DownloadThread(CrawlerThread):
    def __init__(self, main_thread: Crawler, file_url: str, file_path: str, file_description: str) -> None:
        CrawlerThread.__init__(self, main_thread, [])
        self.file_url: str = file_url
        self.file_path: str = file_path
        self.file_description: str = file_description
        self.result: Optional[net.Download] = None
        self.headers: Optional[dict[str, str]] = None
        self.cookies: Optional[dict[str, str]] = None

    def run(self) -> None:
        self.result = self.download(self.file_url, self.file_path, self.file_description, headers=self.headers, cookies=self.cookies)
        self.notify_main_thread()

    def get_result(self) -> bool:
        return bool(self.result)

    def set_download_header(self, headers: dict[str, str]) -> Self:
        self.headers = headers
        return self

    def set_download_cookies(self, cookies: dict[str, str]) -> Self:
        self.cookies = cookies
        return self


def read_config(config_path: str) -> dict[str, str]:
    """
    读取配置文件
    """
    config = {}
    if not os.path.exists(config_path):
        return config
    with codecs.open(config_path, encoding="UTF-8-SIG") as file_handle:
        config_file = configparser.ConfigParser()
        config_file.read_file(file_handle)
        for key, value in config_file.items("setting"):
            config[key] = value
    return config


def analysis_config(config: dict[str, str], key: str, default_value: Any, mode: const.ConfigAnalysisMode = const.ConfigAnalysisMode.RAW) -> Any:
    """
    解析配置

    :Args:
    - config - 配置文件字典，通过read_config()获取
    - key - 配置key
    - default_value - 默认值
    - mode - 解析模式
        raw     直接读取
        int     转换成int类型
        float   转换成float类型
        bool    转换成bool类型
                    等价于False的值，或者值为"0"或"false"的字符串将转换为False
                    其他字符串将转换为True
        path    转换成路径
                    当字符串以'\'开头，相对于PROJECT_ROOT_PATH
                    当字符串以'\\'开头，相对于PROJECT_APP_PATH
    """
    key = key.lower()
    if isinstance(config, dict) and key in config:
        value = config[key]
    else:
        if not IS_EXECUTABLE:
            log.warning("配置文件config.ini中没有找到key为'" + key + "'的参数，使用程序默认设置")
        value = default_value
    if mode == const.ConfigAnalysisMode.INTEGER:
        if isinstance(value, int) or isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
            value = int(value)
        else:
            log.warning("配置文件config.ini中key为'" + key + "'的值必须是一个整数，使用程序默认设置")
            value = default_value
    elif mode == const.ConfigAnalysisMode.BOOLEAN:
        if not value or value == "0" or (isinstance(value, str) and value.lower() == "false"):
            value = False
        else:
            value = True
    elif mode == const.ConfigAnalysisMode.FLOAT:
        try:
            value = float(value)
        except ValueError:
            log.warning("配置文件config.ini中key为'" + key + "'的值必须是一个浮点数，使用程序默认设置")
            value = default_value
    elif mode == const.ConfigAnalysisMode.PATH:
        if len(value) > 2 and value.startswith(r"\\"):  # \\ 开头，程序所在目录
            value = os.path.join(PROJECT_APP_PATH, value[len(r"\\"):])  # \\ 仅做标记使用，实际需要去除
        elif len(value) > 1 and value.startswith("\\"):  # \ 开头，项目根目录（common目录上级）
            value = os.path.join(PROJECT_ROOT_PATH, value[len("\\"):])  # \ 仅做标记使用，实际需要去除
        elif not value:
            value = "."
        value = os.path.abspath(value)
    return value


def read_save_data(save_data_path: str, key_index: int = 0, default_value_list: Optional[list[str]] = None, check_duplicate_index: bool = True) -> dict[str, list]:
    """
    读取存档文件，并根据指定列生成存档字典

    :Args:
    - save_data_path - 存档路径
    - key_index - 配置文件的主键（唯一）
    - default_value_list - 每一位的默认值
    - check_duplicate_index - 是否检测主键的唯一性
    """
    if default_value_list is None:
        default_value_list = []
    result_list = {}
    if not os.path.exists(save_data_path):
        return result_list
    for single_save_data in file.read_file(save_data_path, const.ReadFileMode.LINE):
        single_save_data = single_save_data.strip("\n\r")
        if len(single_save_data) == 0:
            continue
        single_save_list = single_save_data.split("\t")

        if check_duplicate_index and single_save_list[key_index] in result_list:
            raise CrawlerException(f"存档中存在重复行 {key_index} / {single_save_list[key_index]}", True)

        # 去除前后空格
        single_save_list = [value.strip() for value in single_save_list]

        # 根据default_value_list给没给字段默认值
        index = 0
        for default_value in default_value_list:
            # _开头表示和该数组下标的值一致，如["", "_0"] 表示第1位为空时数值和第0位一致
            if default_value != "" and default_value.startswith("_"):
                default_value = single_save_list[int(tool.remove_string_prefix(default_value, "_"))]
            if len(single_save_list) <= index:
                single_save_list.append(default_value)
            if single_save_list[index] == "":
                single_save_list[index] = default_value
            index += 1
        result_list[single_save_list[key_index]] = single_save_list
    return result_list


def get_json_value(json_data, *args, **kwargs) -> Any:
    """
    获取一个json文件的指定字段

    :Args:
    - json_data - 原始json数据
    - args - 如果是字母，取字典对应key；如果是整数，取列表对应下标
    - kwargs
        - original_data     原始数据，主要用于异常输出
        - default_value     当json对象中没有找到对应key的数据时的默认值，如果不设置则会在没有找到数据时抛出异常
        - type_check        验证数据类型是否一致
        - value_check       验证数值是否一致
    """
    if "original_data" in kwargs:
        original_data = kwargs["original_data"]
    else:
        original_data = json_data

    last_arg = ""
    exception_string = ""
    for arg in args:
        if isinstance(arg, str):
            if not isinstance(json_data, dict):
                exception_string = f"'{last_arg}'字段不是字典\n{original_data}"
            elif arg not in json_data:
                exception_string = f"'{arg}'字段不存在\n{original_data}"
        elif isinstance(arg, int):
            if not isinstance(json_data, list):
                exception_string = f"'{last_arg}'字段不是列表\n{original_data}"
            elif len(json_data) <= arg:
                exception_string = f"'{last_arg}'字段长度不正确\n{original_data}"
        else:
            exception_string = f"arg: {arg}类型不正确"
        if exception_string:
            break
        last_arg = arg
        json_data = json_data[arg]

    # 检测结果类型
    if not exception_string and "type_check" in kwargs:
        type_error = False
        type_check = kwargs["type_check"]
        if type_check is int:  # 整数（包含int和符合整型规则的字符串）
            if tool.is_integer(json_data):
                json_data = int(json_data)
            else:
                type_error = True
        elif type_check is float:  # 浮点数（包含float、int和符合浮点数规则的字符串）
            try:
                json_data = float(json_data)
            except TypeError:
                type_error = True
            except ValueError:
                type_error = True
        elif type_check is str:  # 直接强制类型转化
            json_data = str(json_data)
        elif type_check is dict or type_check is list or type_check is bool:  # 标准数据类型
            type_error = type(json_data) is not type_check
        else:
            exception_string = f"type_check: {kwargs['type_check']}类型不正确"
        if type_error:
            exception_string = f"'{last_arg}'字段类型不正确\n{original_data}"

    # 检测结果数值
    if not exception_string and "value_check" in kwargs:
        value_error = False
        if isinstance(kwargs["value_check"], list):
            if json_data not in kwargs["value_check"]:
                value_error = True
        else:
            if not (json_data == kwargs["value_check"]):
                value_error = True
        if value_error:
            exception_string = f"'{last_arg}'字段取值不正确\n{original_data}"

    if exception_string:
        if "default_value" in kwargs:
            return kwargs["default_value"]
        else:
            raise CrawlerException(exception_string)
    return json_data


def download_failre(return_code: int) -> str:
    """
    获取网络文件下载失败的原因
    """
    if return_code == 404:
        return "源文件已被删除"
    elif return_code == 403:
        return "源文件没有权限下载"
    elif return_code == const.DownloadCode.URL_INVALID:
        return "源文件地址格式不正确"
    elif return_code == const.DownloadCode.RETRY_MAX_COUNT:
        return "源文件多次获取失败，可能无法访问"
    elif return_code == const.DownloadCode.FILE_SIZE_INVALID:
        return "源文件多次下载后和原始文件大小不一致，可能网络环境较差"
    elif return_code == const.DownloadCode.PROCESS_EXIT:
        return "程序中途退出"
    elif return_code == const.DownloadCode.FILE_CREATE_FAILED:
        return "文件所在保存目录创建失败"
    elif return_code > 0:
        return f"未知错误，http code {return_code}"
    else:
        return f"未知错误，下载返回码 {return_code}"


def request_failre(return_code: int) -> str:
    """
    获取网络文件下载失败的原因
    return_code = response.status
    """
    if return_code == 404:
        return "页面已被删除"
    elif return_code == 403:
        return "页面没有权限访问"
    elif return_code == const.ResponseCode.RETRY:
        return "页面多次访问失败，可能无法访问"
    elif return_code == const.ResponseCode.URL_INVALID:
        return "URL格式错误"
    elif return_code == const.ResponseCode.JSON_DECODE_ERROR:
        return "返回信息不是一个有效的JSON格式"
    elif return_code == const.ResponseCode.DOMAIN_NOT_RESOLVED:
        return "域名无法解析"
    elif return_code == const.ResponseCode.RESPONSE_TO_LARGE:
        return "返回文本过大"
    elif return_code == const.ResponseCode.TOO_MANY_REDIRECTS:
        return "重定向次数过多"
    elif return_code > 0:
        return f"未知错误，http code {return_code}"
    else:
        return f"未知错误，return code {return_code}"
