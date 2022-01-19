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

# 项目根目录
PROJECT_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# 全局config.ini路径
PROJECT_CONFIG_PATH = os.path.abspath(os.path.join(PROJECT_ROOT_PATH, "common/config.ini"))
# 默认当前进程的工作目录，应用在初始化时应该对该变量进行赋值
PROJECT_APP_PATH = os.getcwd()
# webdriver文件路径
CHROME_WEBDRIVER_PATH = os.path.abspath(os.path.join(PROJECT_ROOT_PATH, "common/chromedriver.exe"))
try:
    from . import browser, file, log, net, output, path, portListenerEvent, tool
except ImportError:
    from common import browser, file, log, net, output, path, portListenerEvent, tool
if platform.system() == "Windows":
    try:
        from . import keyboardEvent
    except ImportError:
        from common import keyboardEvent

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
# 应用额外配置
# 传入参数类型为tuple，每一位参数为长度3的tuple，顺序为(配置名字，默认值，配置读取方式)，同analysis_config方法后三个参数
SYS_APP_CONFIG = "app_config"
# 自定义的app配置文件路径（默认
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

    # 程序全局变量的设置
    def __init__(self, sys_config, **kwargs):
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
        if not sys_not_check_save_data:
            if not os.path.exists(self.save_data_path):
                # 存档文件不存在
                output.print_msg("存档文件%s不存在！" % self.save_data_path)
                tool.process_exit()
                return
            temp_file_name = time.strftime("%m-%d_%H_%M_", time.localtime(time.time())) + os.path.basename(self.save_data_path)
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
        self.is_thread_exit_after_download_failure = analysis_config(config, "IS_THREAD_EXIT_AFTER_DOWNLOAD_FAILURE", "\\\\content", CONFIG_ANALYSIS_MODE_BOOLEAN)

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
            listener_event_bind = {}
            # 暂停进程
            listener_event_bind[str(portListenerEvent.PROCESS_STATUS_PAUSE)] = net.pause_request
            # 继续进程
            listener_event_bind[str(portListenerEvent.PROCESS_STATUS_RUN)] = net.resume_request
            # 结束进程（取消当前的线程，完成任务）
            listener_event_bind[str(portListenerEvent.PROCESS_STATUS_STOP)] = self.stop_process

            listener_port = analysis_config(config, "LISTENER_PORT", 12345, CONFIG_ANALYSIS_MODE_INTEGER)
            process_control_thread = portListenerEvent.PortListenerEvent(port=listener_port, event_list=listener_event_bind)
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
                keyboard_control_thread = keyboardEvent.KeyboardEvent(keyboard_event_bind)
                keyboard_control_thread.setDaemon(True)
                keyboard_control_thread.start()

        self.total_photo_count = 0
        self.total_video_count = 0
        self.total_audio_count = 0

        output.print_msg("初始化完成")

    def pause_process(self):
        net.pause_request()

    def resume_process(self):
        net.resume_request()

    def stop_process(self):
        output.print_msg("stop process")
        net.resume_request()
        self.process_status = False
        net.EXIT_FLAG = True

    # 获取程序已运行时间（seconds）
    def get_run_time(self):
        """Get process runned time(seconds)"""
        return int(time.time() - self.start_time)

    def is_running(self):
        return self.process_status


class DownloadThread(threading.Thread):
    """Download sub-thread"""
    main_thread = None
    thread_lock = None
    display_name = None

    def __init__(self, account_info, main_thread):
        """
        :param account_info:

        :param main_thread:
            object of main thread(class Crawler)
        """
        if not isinstance(main_thread, Crawler):
            output.print_msg("下载线程参数异常")
            tool.process_exit()
        try:
            threading.Thread.__init__(self)
            self.account_info = account_info
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

    # 检测主线程是否已经结束（外部中断）
    def main_thread_check(self):
        if not self.main_thread.is_running():
            self.notify_main_thread()
            tool.process_exit(0)

    # 线程下完完成后唤醒主线程，开启新的线程（必须在线程完成后手动调用，否则会卡死主线程）
    def notify_main_thread(self):
        if isinstance(self.main_thread, Crawler):
            self.main_thread.thread_semaphore.release()

    # 当下载失败，检测是否要退出线程
    def check_thread_exit_after_download_failure(self, is_process_exit=True):
        if self.main_thread.is_thread_exit_after_download_failure:
            if is_process_exit:
                tool.process_exit(0)
            else:
                return True
        return False

    # 中途退出，删除临时文件/目录
    def clean_temp_path(self):
        for temp_path in self.temp_path_list:
            path.delete_dir_or_file(temp_path)

    # Trace log
    def trace(self, message, include_display_name=True):
        if include_display_name and self.display_name is not None:
            message = self.display_name + " " + message
        log.trace(message)

    # step log
    def step(self, message, include_display_name=True):
        if include_display_name and self.display_name is not None:
            message = self.display_name + " " + message
        log.step(message)

    # error log
    def error(self, message, include_display_name=True):
        if include_display_name and self.display_name is not None:
            message = self.display_name + " " + message
        log.error(message)


class CrawlerException(SystemExit):
    def __init__(self, msg="", print=True):
        SystemExit.__init__(self, 1)
        if print:
            output.print_msg(msg)
        self.exception_message = msg

    @property
    def message(self):
        return self.exception_message


def read_config(config_path):
    if not os.path.exists(config_path):
        return {}
    """Read config file"""
    config = {}
    with codecs.open(config_path, encoding="UTF-8-SIG") as file_handle:
        config_file = configparser.ConfigParser()
        config_file.read_file(file_handle)
        for key, value in config_file.items("setting"):
            config[key] = value
    return config


def analysis_config(config, key, default_value, mode=CONFIG_ANALYSIS_MODE_RAW):
    """Analysis config

    :param config:
        Dictionary of config

    :param key:
        key of config

    :param default_value:
        default value

    :param mode:
        type of analysis mode
        None    direct assignment
        1       conversion to integer
        2       conversion to boolean
                    the value Equivalent to False, or string of "0" and "false" will conversion to False
                    other string will conversion to True
        3       conversion to file path
                    startup with '\', project root path
                    startup with '\\', application root path
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


# 将指定文件夹内的所有文件排序重命名并复制到其他文件夹中
def sort_file(source_path, destination_path, start_count, file_name_length):
    file_list = path.get_dir_files_name(source_path, path.RETURN_FILE_LIST_DESC)
    # 判断排序目标文件夹是否存在
    if len(file_list) >= 1:
        if not path.create_dir(destination_path):
            return False
        # 倒叙排列
        for file_name in file_list:
            start_count += 1
            file_type = os.path.splitext(file_name)[1]  # 包括 .扩展名
            new_file_name = str(("%0" + str(file_name_length) + "d") % start_count) + file_type
            path.copy_file(os.path.join(source_path, file_name), os.path.join(destination_path, new_file_name))
        # 删除临时文件夹
        path.delete_dir_or_file(source_path)
    return True


# 读取存档文件，并根据指定列生成存档字典
# default_value_list 每一位的默认值
def read_save_data(save_data_path, key_index=0, default_value_list=[], check_duplicate_index=True):
    result_list = {}
    if not os.path.exists(save_data_path):
        return result_list
    for single_save_data in file.read_file(save_data_path, file.READ_FILE_TYPE_LINE):
        single_save_data = single_save_data.replace("\n", "").replace("\r", "")
        if len(single_save_data) == 0:
            continue
        single_save_list = single_save_data.split("\t")

        if check_duplicate_index and single_save_list[key_index] in result_list:
            output.print_msg("存档中存在重复行 %s" % single_save_list[key_index])
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


# 将临时存档文件按照主键排序后写入原始存档文件
# 只支持一行一条记录，每条记录格式相同的存档文件
def rewrite_save_file(temp_save_data_path, save_data_path):
    account_list = read_save_data(temp_save_data_path, 0, [])
    temp_list = [account_list[key] for key in sorted(account_list.keys())]
    file.write_file(tool.list_to_string(temp_list), save_data_path, file.WRITE_FILE_TYPE_REPLACE)
    path.delete_dir_or_file(temp_save_data_path)


# 替换目录中的指定字符串
def replace_path(path):
    return path.replace("{date}", time.strftime("%y-%m-%d", time.localtime(time.time())))


# 获取当前时间
def get_time():
    return time.strftime("%m-%d %H:%M:%S", time.localtime(time.time()))


# 获取一个json文件的指定字段
# arg如果是字母，取字典对应key；如果是整数，取列表对应下标
# 支持的kwargs
#       original_data
#       default_value
#       type_check
#       value_check
def get_json_value(json_data, *args, **kwargs):
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
        if kwargs["type_check"] is int:  # 整数（包含int和符合整型规则的字符串）
            if is_integer(json_data):
                json_data = int(json_data)
            else:
                type_error = True
        elif kwargs["type_check"] is float:  # 浮点数（包含float、int和符合浮点数规则的字符串）
            try:
                json_data = float(json_data)
            except TypeError:
                type_error = True
            except ValueError:
                type_error = True
        elif kwargs["type_check"] is str:  # 直接强制类型转化
            json_data = str(json_data)
        elif kwargs["type_check"] in [dict, list, bool]:  # 标准数据类型
            type_error = not isinstance(json_data, kwargs["type_check"])
        else:
            exception_string = "type_check: %s类型不正确" % kwargs["type_check"]
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


# 判断类型是否为字典，并且检测是否存在指定的key
def check_sub_key(needles, haystack):
    if not isinstance(needles, tuple):
        needles = tuple(needles)
    if isinstance(haystack, dict):
        for needle in needles:
            if needle not in haystack:
                return False
        return True
    return False


# 判断是不是整数
def is_integer(number):
    if isinstance(number, int):
        return True
    elif isinstance(number, bool) or isinstance(number, list) or isinstance(number, dict) or number is None:
        return False
    else:
        return re.compile('^[-+]?[0-9]+$').match(str(number))


# 替换文本中的表情符号
def filter_emoji(text):
    try:
        emoji = re.compile('[\U00010000-\U0010ffff]')
    except re.error:
        emoji = re.compile('[\uD800-\uDBFF][\uDC00-\uDFFF]')
    return emoji.sub('', text)


# 获取网络文件下载失败的原因
def download_failre(return_code):
    if return_code == 404:
        return "源文件已被删除"
    elif return_code == 403:
        return "源文件没有权限下载"
    elif return_code == -1:
        return "源文件地址格式不正确"
    elif return_code == -2:
        return "源文件多次获取失败，可能无法访问"
    elif return_code == -3:
        return "源文件多次下载后和原始文件大小不一致，可能网络环境较差"
    elif return_code == -4:
        return "源文件太大，跳过"
    elif return_code == -5:
        return "重定向次数过多"
    elif return_code == -11:
        return "文件所在保存目录创建失败"
    elif return_code > 0:
        return "未知错误，http code %s" % return_code
    else:
        return "未知错误，下载返回码 %s" % return_code


# 获取网络文件下载失败的原因
def request_failre(return_code):
    # return_code = response.status
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
        return "未知错误，http code %s" % return_code
    else:
        return "未知错误，return code %s" % return_code
