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
import re
import sys
import threading
import time
import traceback
import warnings
from typing import Union

# 项目根目录
PROJECT_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# 全局config.ini路径
PROJECT_CONFIG_PATH = os.path.abspath(os.path.join(PROJECT_ROOT_PATH, "common/config.ini"))
# 默认当前进程的工作目录，应用在初始化时应该对该变量进行赋值
PROJECT_APP_PATH = os.getcwd()
# webdriver文件路径
CHROME_WEBDRIVER_PATH = os.path.abspath(os.path.join(PROJECT_ROOT_PATH, "common/chromedriver.exe"))
try:
    from . import browser, file, log, net, output, path, port_listener_event, tool
except ImportError:
    from common import browser, file, log, net, output, path, port_listener_event, tool
if platform.system() == "Windows":
    try:
        from . import keyboard_event
    except ImportError:
        from common import keyboard_event

# 程序是否支持下载图片功能
SYS_DOWNLOAD_PHOTO = "download_photo"
# 程序是否支持下载视频功能
SYS_DOWNLOAD_VIDEO = "download_video"
# 程序是否支持下载音频功能
SYS_DOWNLOAD_AUDIO = "download_audio"
# 程序是否支持下载文本内容功能
SYS_DOWNLOAD_CONTENT = "download_content"
# 程序是否默认需要设置代理
SYS_SET_PROXY = "set_proxy"
# 程序是否支持不需要存档文件就可以开始运行
SYS_NOT_CHECK_SAVE_DATA = "no_save_data"
# 程序没有任何下载行为
SYS_NOT_DOWNLOAD = "no_download"
# 程序是否需要从浏览器存储的cookie中获取指定cookie的值
SYS_GET_COOKIE = "get_cookie"
# 程序额外应用配置
# 传入参数类型为tuple，每一位参数为长度3的tuple，顺序为(配置名字，默认值，配置读取方式)，同analysis_config方法后三个参数
SYS_APP_CONFIG = "app_config"
# 程序默认的app配置文件路径
SYS_APP_CONFIG_PATH = 'app_config_path'

CONFIG_ANALYSIS_MODE_RAW = "raw"
CONFIG_ANALYSIS_MODE_INTEGER = "int"
CONFIG_ANALYSIS_MODE_BOOLEAN = "bool"
CONFIG_ANALYSIS_MODE_FLOAT = "float"
CONFIG_ANALYSIS_MODE_PATH = "path"


class Crawler(object):
    print_function = None
    thread_event = None
    process_status = True  # 主进程是否在运行
    download_thread = None  # 下载子线程

    # 程序全局变量的设置
    def __init__(self, sys_config, **kwargs):
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
        self.start_time = time.time()

        # 程序启动配置
        if not isinstance(sys_config, dict):
            output.print_msg("程序启动配置不存在，请检查代码！")
            tool.process_exit()
            return
        # 额外初始化配置（直接通过实例化中传入，可覆盖子类__init__方法传递的sys_config参数）
        if "extra_sys_config" in kwargs and isinstance(kwargs["extra_sys_config"], dict):
            sys_config.update(kwargs["extra_sys_config"])
        sys_download_photo = SYS_DOWNLOAD_PHOTO in sys_config and sys_config[SYS_DOWNLOAD_PHOTO]
        sys_download_video = SYS_DOWNLOAD_VIDEO in sys_config and sys_config[SYS_DOWNLOAD_VIDEO]
        sys_download_audio = SYS_DOWNLOAD_AUDIO in sys_config and sys_config[SYS_DOWNLOAD_AUDIO]
        sys_download_content = SYS_DOWNLOAD_CONTENT in sys_config and sys_config[SYS_DOWNLOAD_CONTENT]
        sys_set_proxy = SYS_SET_PROXY in sys_config and sys_config[SYS_SET_PROXY]
        sys_get_cookie = SYS_GET_COOKIE in sys_config and sys_config[SYS_GET_COOKIE]
        sys_not_check_save_data = SYS_NOT_CHECK_SAVE_DATA in sys_config and sys_config[SYS_NOT_CHECK_SAVE_DATA]
        sys_not_download = SYS_NOT_DOWNLOAD in sys_config and sys_config[SYS_NOT_DOWNLOAD]

        # exe程序
        if tool.IS_EXECUTABLE:
            application_path = os.path.dirname(sys.executable)
            os.chdir(application_path)
            config_path = os.path.join(os.getcwd(), "data/config.ini")
        else:
            config_path = PROJECT_CONFIG_PATH

        # 程序配置
        config = read_config(config_path)
        # 应用配置
        if SYS_APP_CONFIG_PATH in sys_config:
            app_config_path = sys_config[SYS_APP_CONFIG_PATH]
        else:
            app_config_path = os.path.abspath(os.path.join(PROJECT_APP_PATH, "app.ini"))
        if os.path.exists(app_config_path):
            config.update(read_config(app_config_path))
        # 额外应用配置（直接通过实例化中传入，可覆盖配置文件中参数）
        if "extra_app_config" in kwargs and isinstance(kwargs["extra_app_config"], dict):
            config.update(kwargs["extra_app_config"])

        # 应用配置
        self.app_config = {}
        if SYS_APP_CONFIG in sys_config and len(sys_config[SYS_APP_CONFIG]) > 0:
            for app_config_template in sys_config[SYS_APP_CONFIG]:
                if len(app_config_template) == 3:
                    self.app_config[app_config_template[0]] = analysis_config(config, app_config_template[0], app_config_template[1], app_config_template[2])

        # 是否下载
        self.is_download_photo = analysis_config(config, "IS_DOWNLOAD_PHOTO", True, CONFIG_ANALYSIS_MODE_BOOLEAN) and sys_download_photo
        self.is_download_video = analysis_config(config, "IS_DOWNLOAD_VIDEO", True, CONFIG_ANALYSIS_MODE_BOOLEAN) and sys_download_video
        self.is_download_audio = analysis_config(config, "IS_DOWNLOAD_AUDIO", True, CONFIG_ANALYSIS_MODE_BOOLEAN) and sys_download_audio
        self.is_download_content = analysis_config(config, "IS_DOWNLOAD_CONTENT", True, CONFIG_ANALYSIS_MODE_BOOLEAN) and sys_download_content

        if not sys_not_download and not self.is_download_photo and not self.is_download_video and not self.is_download_audio and not self.is_download_content:
            if sys_download_photo or sys_download_video or sys_download_audio or sys_download_content:
                output.print_msg("所有支持的下载都没有开启，请检查配置！")
                tool.process_exit()
                return

        # 下载文件时是否覆盖已存在的同名文件
        net.DOWNLOAD_REPLACE_IF_EXIST = analysis_config(config, "IS_DOWNLOAD_REPLACE_IF_EXIST", False, CONFIG_ANALYSIS_MODE_BOOLEAN)

        # 存档
        self.save_data_path = analysis_config(config, "SAVE_DATA_PATH", "\\\\info/save.data", CONFIG_ANALYSIS_MODE_PATH)
        self.temp_save_data_path = ""
        if not sys_not_check_save_data:
            if not os.path.exists(self.save_data_path):
                # 存档文件不存在
                output.print_msg("存档文件%s不存在！" % self.save_data_path)
                tool.process_exit()
                return
            temp_file_name = tool.get_time("%m-%d_%H_%M_") + os.path.basename(self.save_data_path)
            self.temp_save_data_path = os.path.join(os.path.dirname(self.save_data_path), temp_file_name)
            if os.path.exists(self.temp_save_data_path):
                # 临时文件已存在
                output.print_msg("存档临时文件%s已存在！" % self.temp_save_data_path)
                tool.process_exit()
                return

        # cache
        self.cache_data_path = analysis_config(config, "CACHE_DATA_PATH", "\\\\cache", CONFIG_ANALYSIS_MODE_PATH)

        # session
        self.session_data_path = analysis_config(config, "SESSION_DATA_PATH", "\\\\info/session.data", CONFIG_ANALYSIS_MODE_PATH)

        # 是否需要下载图片
        if self.is_download_photo:
            # 图片保存目录
            self.photo_download_path = analysis_config(config, "PHOTO_DOWNLOAD_PATH", "\\\\photo", CONFIG_ANALYSIS_MODE_PATH)
        else:
            self.photo_download_path = ""
        # 是否需要下载视频
        if self.is_download_video:
            # 视频保存目录
            self.video_download_path = analysis_config(config, "VIDEO_DOWNLOAD_PATH", "\\\\video", CONFIG_ANALYSIS_MODE_PATH)
        else:
            self.video_download_path = ""
        # 是否需要下载音频
        if self.is_download_audio:
            # 音频保存目录
            self.audio_download_path = analysis_config(config, "AUDIO_DOWNLOAD_PATH", "\\\\audio", CONFIG_ANALYSIS_MODE_PATH)
        else:
            self.audio_download_path = ""
        # 是否需要下载文本内容
        if self.is_download_content:
            # 音频保存目录
            self.content_download_path = analysis_config(config, "CONTENT_DOWNLOAD_PATH", "\\\\content", CONFIG_ANALYSIS_MODE_PATH)
        else:
            self.content_download_path = ""

        # 是否在下载失败后退出线程的运行
        self.thread_exit_after_download_failure = analysis_config(config, "THREAD_EXIT_AFTER_DOWNLOAD_FAILURE", "\\\\content", CONFIG_ANALYSIS_MODE_BOOLEAN)

        # 代理
        is_proxy = analysis_config(config, "IS_PROXY", 2, CONFIG_ANALYSIS_MODE_INTEGER)
        if is_proxy == 1 or (is_proxy == 2 and sys_set_proxy):
            proxy_ip = analysis_config(config, "PROXY_IP", "127.0.0.1")
            proxy_port = analysis_config(config, "PROXY_PORT", "8087")
            # 使用代理的线程池
            net.set_proxy(proxy_ip, proxy_port)
        else:
            # 初始化urllib3的线程池
            net.init_http_connection_pool()

        # cookies
        self.cookie_value = {}
        if sys_get_cookie:
            # 操作系统&浏览器
            browser_type = analysis_config(config, "BROWSER_TYPE", 2, CONFIG_ANALYSIS_MODE_INTEGER)
            # cookie
            cookie_path = analysis_config(config, "COOKIE_PATH", "", CONFIG_ANALYSIS_MODE_RAW)
            if cookie_path:
                cookie_path = analysis_config(config, "COOKIE_PATH", "", CONFIG_ANALYSIS_MODE_PATH)
            else:
                cookie_path = browser.get_default_browser_cookie_path(browser_type)
            all_cookie_from_browser = browser.get_all_cookie_from_browser(browser_type, cookie_path)
            if browser_type == browser.BROWSER_TYPE_TEXT:
                if "DEFAULT" in all_cookie_from_browser:
                    self.cookie_value.update(all_cookie_from_browser["DEFAULT"])
            else:
                for cookie_domain in sys_config[SYS_GET_COOKIE]:
                    check_domain_list = [cookie_domain]
                    if cookie_domain[0] != ".":
                        check_domain_list.append("." + cookie_domain)
                    elif cookie_domain[0] == ".":
                        check_domain_list.append(cookie_domain[1:])
                    for check_domain in check_domain_list:
                        if check_domain in all_cookie_from_browser:
                            self.cookie_value.update(all_cookie_from_browser[check_domain])

        # 线程数
        self.thread_count = analysis_config(config, "THREAD_COUNT", 10, CONFIG_ANALYSIS_MODE_INTEGER)
        self.thread_lock = threading.Lock()  # 线程锁，避免操作一些全局参数
        self.thread_semaphore = threading.Semaphore(self.thread_count)  # 线程总数信号量

        # 启用线程监控是否需要暂停其他下载线程
        if analysis_config(config, "IS_PORT_LISTENER_EVENT", False, CONFIG_ANALYSIS_MODE_BOOLEAN):
            listener_port = analysis_config(config, "LISTENER_PORT", 12345, CONFIG_ANALYSIS_MODE_INTEGER)
            listener_event_bind = {
                str(port_listener_event.PROCESS_STATUS_PAUSE): net.pause_request,  # 暂停进程
                str(port_listener_event.PROCESS_STATUS_RUN): net.resume_request,  # 继续进程
                str(port_listener_event.PROCESS_STATUS_STOP): self.stop_process  # 结束进程（取消当前的线程，完成任务）
            }
            process_control_thread = port_listener_event.PortListenerEvent(port=listener_port, event_list=listener_event_bind)
            process_control_thread.setDaemon(True)
            process_control_thread.start()

        # 键盘监控线程（仅支持windows）
        if platform.system() == "Windows" and analysis_config(config, "IS_KEYBOARD_EVENT", False, CONFIG_ANALYSIS_MODE_BOOLEAN):
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
                keyboard_control_thread.setDaemon(True)
                keyboard_control_thread.start()

        self.save_data = {}
        self.total_photo_count = 0
        self.total_video_count = 0
        self.total_audio_count = 0

        output.print_msg("初始化完成")

    def main(self):
        try:
            self.init()

            self._main()
        except (KeyboardInterrupt, SystemExit) as e:
            if self.download_thread and issubclass(self.download_thread, DownloadThread):
                self.stop_process()
            else:
                if isinstance(e, SystemExit) and e.code == tool.PROCESS_EXIT_CODE_ERROR:
                    log.step("异常退出")
                else:
                    log.step("提前退出")
        except Exception as e:
            log.error("未知异常")
            log.error(str(e) + "\n" + traceback.format_exc())

        # 未完成的数据保存
        self.write_remaining_save_data()

        # 重新排序保存存档文件
        self.rewrite_save_file()

        # 其他结束操作
        self.done()

        # 结束日志
        self.end_message()

    def _main(self):
        if self.download_thread and issubclass(self.download_thread, DownloadThread):
            # 循环下载每个id
            thread_list = []
            for index_key in sorted(self.save_data.keys()):
                # 提前结束
                if not self.is_running():
                    break

                # 开始下载
                thread = self.download_thread(self.save_data[index_key], self)
                thread.start()
                thread_list.append(thread)

                time.sleep(1)

            # 等待子线程全部完成
            while len(thread_list) > 0:
                thread_list.pop().join()

    def init(self):
        """
        其他初始化的方法
        """
        pass

    def done(self):
        """
        其他结束操作
        """
        pass

    @staticmethod
    def pause_process():
        net.pause_request()

    @staticmethod
    def resume_process():
        net.resume_request()

    def stop_process(self):
        output.print_msg("stop process")
        self.process_status = False
        net.EXIT_FLAG = True
        net.resume_request()

    def get_run_time(self):
        """
        获取程序已运行时间（秒）
        """
        return int(time.time() - self.start_time)

    def is_running(self):
        return self.process_status

    def write_remaining_save_data(self):
        """
        将剩余未处理的存档数据写入临时存档文件
        """
        if len(self.save_data) > 0 and self.temp_save_data_path:
            file.write_file(tool.list_to_string(list(self.save_data.values())), self.temp_save_data_path)

    def rewrite_save_file(self):
        """
        将临时存档文件按照主键排序后写入原始存档文件
        只支持一行一条记录，每条记录格式相同的存档文件
        """
        if self.temp_save_data_path:
            save_data = read_save_data(self.temp_save_data_path, 0, [])
            temp_list = [save_data[key] for key in sorted(save_data.keys())]
            file.write_file(tool.list_to_string(temp_list), self.save_data_path, file.WRITE_FILE_TYPE_REPLACE)
            path.delete_dir_or_file(self.temp_save_data_path)

    def end_message(self):
        message = f"全部下载完毕，耗时{self.get_run_time()}秒"
        download_result = []
        if self.is_download_photo:
            download_result.append(f"图片{self.total_photo_count}张")
        if self.is_download_video:
            download_result.append(f"视频{self.total_video_count}个")
        if self.is_download_audio:
            download_result.append(f"音频{self.total_audio_count}个")
        if download_result:
            message += "，共计下载" + "，".join(download_result)
        log.step(message)

    @staticmethod
    def start_parse(description: str):
        log.step("开始解析 " + description)

    @staticmethod
    def parse_result(description: str, parse_result_list: Union[list, dict]):
        log.trace("%s 解析结果：%s" % (description, parse_result_list))
        log.step("%s 解析数量：%s" % (description, len(parse_result_list)))


class DownloadThread(threading.Thread):
    main_thread = None
    thread_lock = None
    display_name = None
    index_key = ''

    def __init__(self, single_save_data: list, main_thread: Crawler):
        """
        多线程下载

        :Args:
        - single_save_data - 线程用到的数据
        - main_thread - 主线程对象
        """
        if not isinstance(main_thread, Crawler):
            output.print_msg("下载线程参数异常")
            tool.process_exit()
        try:
            threading.Thread.__init__(self)
            self.single_save_data = single_save_data
            self.main_thread = main_thread
            self.thread_lock = main_thread.thread_lock
            main_thread.thread_semaphore.acquire()
        except KeyboardInterrupt:
            self.main_thread.stop_process()
        self.total_photo_count = 0
        self.total_video_count = 0
        self.total_audio_count = 0
        self.total_content_count = 0
        self.temp_path_list = []
        if single_save_data:
            self.step("开始")

    def run(self):
        try:
            self._run()
        except KeyboardInterrupt:
            self.step("提前退出")
        except SystemExit as e:
            if e.code == tool.PROCESS_EXIT_CODE_ERROR:
                self.error("异常退出")
            else:
                self.step("提前退出")
        except Exception as e:
            self.error("未知异常")
            self.error(str(e) + "\n" + traceback.format_exc(), False)

        # 从住线程中移除主键对应的信息
        if self.index_key:
            self.main_thread.save_data.pop(self.index_key)

        # 写入存档
        if self.single_save_data and self.main_thread.temp_save_data_path:
            with self.thread_lock:
                file.write_file("\t".join(self.single_save_data), self.main_thread.temp_save_data_path, file.WRITE_FILE_TYPE_APPEND)

        # 主线程计数累加
        if self.main_thread.is_download_photo:
            self.main_thread.total_photo_count += self.total_photo_count
        if self.main_thread.is_download_video:
            self.main_thread.total_video_count += self.total_video_count
        if self.main_thread.is_download_audio:
            self.main_thread.total_audio_count += self.total_audio_count

        # 清理临时文件（未完整下载的内容）
        for temp_path in self.temp_path_list:
            path.delete_dir_or_file(temp_path)

        # 日志
        message = "下载完毕"
        download_result = []
        if self.main_thread.is_download_photo:
            download_result.append(f"图片{self.total_photo_count}张")
        if self.main_thread.is_download_video:
            download_result.append(f"视频{self.total_video_count}个")
        if self.main_thread.is_download_audio:
            download_result.append(f"音频{self.total_audio_count}个")
        if download_result:
            message += "，共计下载" + "，".join(download_result)
        self.step(message)

        # 唤醒主线程
        self.notify_main_thread()

    def _run(self):
        pass

    def main_thread_check(self):
        """
        检测主线程是否已经结束（外部中断）
        """
        if not self.main_thread.is_running():
            self.notify_main_thread()
            tool.process_exit(tool.PROCESS_EXIT_CODE_NORMAL)

    def notify_main_thread(self):
        """
        线程下完完成后唤醒主线程，开启新的线程（必须在线程完成后手动调用，否则会卡死主线程）
        """
        if isinstance(self.main_thread, Crawler):
            self.main_thread.thread_semaphore.release()

    def check_download_failure_exit(self, is_process_exit: bool = True):
        """
        当下载失败，检测是否要退出线程
        """
        if self.main_thread.thread_exit_after_download_failure:
            if is_process_exit:
                tool.process_exit(tool.PROCESS_EXIT_CODE_ERROR)
            else:
                return True
        return False

    def trace(self, message: str, include_display_name: bool = True):
        """
        trace log
        """
        if include_display_name and self.display_name is not None:
            message = self.display_name + " " + message
        log.trace(message)

    def step(self, message: str, include_display_name: bool = True):
        """
        step log
        """
        if include_display_name and self.display_name is not None:
            message = self.display_name + " " + message
        log.step(message)

    def error(self, message: str, include_display_name: bool = True):
        """
        error log
        """
        if include_display_name and self.display_name is not None:
            message = self.display_name + " " + message
        log.error(message)

    def start_parse(self, description: str):
        self.main_thread.start_parse(description)

    def parse_result(self, description: str, parse_result_list: Union[list, dict]):
        self.main_thread.parse_result(description, parse_result_list)


class CrawlerException(SystemExit):
    def __init__(self, msg: str = "", is_print: bool = True):
        SystemExit.__init__(self, 1)
        if is_print:
            output.print_msg(msg)
        self.exception_message = msg

    @property
    def message(self) -> str:
        return self.exception_message

    def http_error(self, target: str):
        return "%s解析失败，原因：%s" % (target, self.message)


def read_config(config_path) -> dict:
    """
    读取配置文件
    """
    if not os.path.exists(config_path):
        return {}
    config = {}
    with codecs.open(config_path, encoding="UTF-8-SIG") as file_handle:
        config_file = configparser.ConfigParser()
        config_file.read_file(file_handle)
        for key, value in config_file.items("setting"):
            config[key] = value
    return config


def analysis_config(config: dict, key: str, default_value, mode: str = CONFIG_ANALYSIS_MODE_RAW):
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
                    当字符串以'\'开头，相对于crawler.PROJECT_ROOT_PATH
                    当字符串以'\\'开头，相对于crawler.PROJECT_APP_PATH
    """
    key = key.lower()
    if isinstance(config, dict) and key in config:
        value = config[key]
    else:
        if not tool.IS_EXECUTABLE:
            output.print_msg("配置文件config.ini中没有找到key为'" + key + "'的参数，使用程序默认设置")
        value = default_value
    if mode == CONFIG_ANALYSIS_MODE_INTEGER:
        if isinstance(value, int) or isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
            value = int(value)
        else:
            output.print_msg("配置文件config.ini中key为'" + key + "'的值必须是一个整数，使用程序默认设置")
            value = default_value
    elif mode == CONFIG_ANALYSIS_MODE_BOOLEAN:
        if not value or value == "0" or (isinstance(value, str) and value.lower() == "false"):
            value = False
        else:
            value = True
    elif mode == CONFIG_ANALYSIS_MODE_FLOAT:
        try:
            value = float(value)
        except ValueError:
            output.print_msg("配置文件config.ini中key为'" + key + "'的值必须是一个浮点数，使用程序默认设置")
            value = default_value
    elif mode == CONFIG_ANALYSIS_MODE_PATH:
        if len(value) > 2 and value[:2] == "\\\\":  # \\ 开头，程序所在目录
            value = os.path.join(PROJECT_APP_PATH, value[2:])  # \\ 仅做标记使用，实际需要去除
        elif len(value) > 1 and value[0] == "\\":  # \ 开头，项目根目录（common目录上级）
            value = os.path.join(PROJECT_ROOT_PATH, value[1:])  # \ 仅做标记使用，实际需要去除
        elif not value:
            value = "."
        value = os.path.abspath(value)
    return value


def read_save_data(save_data_path: str, key_index: int = 0, default_value_list: list = None, check_duplicate_index: bool = True) -> dict:
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
    for single_save_data in file.read_file(save_data_path, file.READ_FILE_TYPE_LINE):
        single_save_data = single_save_data.replace("\n", "").replace("\r", "")
        if len(single_save_data) == 0:
            continue
        single_save_list = single_save_data.split("\t")

        if check_duplicate_index and single_save_list[key_index] in result_list:
            output.print_msg("存档中存在重复行%s" % single_save_list[key_index])
            tool.process_exit()

        # 去除前后空格
        single_save_list = [value.strip() for value in single_save_list]

        # 根据default_value_list给没给字段默认值
        index = 0
        for default_value in default_value_list:
            # _开头表示和该数组下标的值一直，如["", "_0"] 表示第1位为空时数值和第0位一致
            if default_value != "" and default_value[0] == "_":
                default_value = single_save_list[int(default_value.replace("_", ""))]
            if len(single_save_list) <= index:
                single_save_list.append(default_value)
            if single_save_list[index] == "":
                single_save_list[index] = default_value
            index += 1
        result_list[single_save_list[key_index]] = single_save_list
    return result_list


def rewrite_save_file(temp_save_data_path: str, save_data_path: str):
    """
    将临时存档文件按照主键排序后写入原始存档文件
    只支持一行一条记录，每条记录格式相同的存档文件
    """
    warnings.warn(
        "rewrite_save_file commands are deprecated.",
        DeprecationWarning,
        stacklevel=2,
    )
    account_list = read_save_data(temp_save_data_path, 0, [])
    temp_list = [account_list[key] for key in sorted(account_list.keys())]
    file.write_file(tool.list_to_string(temp_list), save_data_path, file.WRITE_FILE_TYPE_REPLACE)
    path.delete_dir_or_file(temp_save_data_path)


def get_json_value(json_data, *args, **kwargs):
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
                exception_string = "'%s'字段不是字典\n%s" % (last_arg, original_data)
            elif arg not in json_data:
                exception_string = "'%s'字段不存在\n%s" % (arg, original_data)
        elif isinstance(arg, int):
            if not isinstance(json_data, list):
                exception_string = "'%s'字段不是列表\n%s" % (last_arg, original_data)
            elif len(json_data) <= arg:
                exception_string = "'%s'字段长度不正确\n%s" % (last_arg, original_data)
        else:
            exception_string = "arg: %s类型不正确" % arg
        if exception_string:
            break
        last_arg = arg
        json_data = json_data[arg]

    # 检测结果类型
    if not exception_string and "type_check" in kwargs:
        type_error = False
        type_check = type(kwargs["type_check"])
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
            type_error = not isinstance(json_data, type_check)
        else:
            exception_string = "type_check: %s类型不正确" % kwargs['type_check']
        if type_error:
            exception_string = "'%s'字段类型不正确\n%s" % (last_arg, original_data)

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
            exception_string = "'%s'字段取值不正确\n%s" % (last_arg, original_data)

    if exception_string:
        if "default_value" in kwargs:
            return kwargs["default_value"]
        else:
            raise CrawlerException(exception_string)
    return json_data


def check_sub_key(needles: Union[str, tuple], haystack: dict) -> bool:
    """
    判断类型是否为字典，并且检测是否存在指定的key
    """
    if not isinstance(needles, tuple):
        needles = tuple(needles)
    if isinstance(haystack, dict):
        for needle in needles:
            if needle not in haystack:
                return False
        return True
    return False


def filter_emoji(text: str) -> str:
    """
    替换文本中的表情符号
    """
    try:
        emoji = re.compile('[\U00010000-\U0010ffff]')
    except re.error:
        emoji = re.compile('[\uD800-\uDBFF][\uDC00-\uDFFF]')
    return emoji.sub('', text)


def download_failre(return_code: int) -> str:
    """
    获取网络文件下载失败的原因
    """
    if return_code == 404:
        return "源文件已被删除"
    elif return_code == 403:
        return "源文件没有权限下载"
    elif return_code == net.Download.CODE_URL_INVALID:
        return "源文件地址格式不正确"
    elif return_code == net.Download.CODE_RETRY_MAX_COUNT:
        return "源文件多次获取失败，可能无法访问"
    elif return_code == net.Download.CODE_FILE_SIZE_INVALID:
        return "源文件多次下载后和原始文件大小不一致，可能网络环境较差"
    elif return_code == net.Download.CODE_PROCESS_EXIT:
        return "程序中途退出"
    elif return_code == net.Download.CODE_FILE_CREATE_FAILED:
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
    elif return_code == net.HTTP_RETURN_CODE_RETRY:
        return "页面多次访问失败，可能无法访问"
    elif return_code == net.HTTP_RETURN_CODE_URL_INVALID:
        return "URL格式错误"
    elif return_code == net.HTTP_RETURN_CODE_JSON_DECODE_ERROR:
        return "返回信息不是一个有效的JSON格式"
    elif return_code == net.HTTP_RETURN_CODE_DOMAIN_NOT_RESOLVED:
        return "域名无法解析"
    elif return_code == net.HTTP_RETURN_CODE_RESPONSE_TO_LARGE:
        return "返回文本过大"
    elif return_code == net.HTTP_RETURN_CODE_TOO_MANY_REDIRECTS:
        return "重定向次数过多"
    elif return_code > 0:
        return f"未知错误，http code {return_code}"
    else:
        return f"未知错误，return code {return_code}"
