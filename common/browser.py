# -*- coding:UTF-8  -*-
"""
浏览器数据相关类
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import json
import os
import platform
import sqlite3
from typing import Optional
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.webdriver import WebDriver

if platform.system() == "Windows":
    import win32crypt

try:
    from . import crawler, file, net, output
except ImportError:
    from common import crawler, file, net, output

BROWSER_TYPE_IE = 1
BROWSER_TYPE_FIREFOX = 2
BROWSER_TYPE_CHROME = 3
BROWSER_TYPE_TEXT = 4  # 直接从文件里读取cookies


class Chrome:
    def __init__(self, url, **kwargs):
        """
        Creates a new instance of the chrome driver. (selenium.webdriver.Chrome())
        :Args:
        - url - 访问的地址，需要携带访问协议，如https://, file://
        - kwargs
            - headless - chrome-headless模式，默认值：True
        """
        if not os.path.exists(crawler.CHROME_WEBDRIVER_PATH):
            raise crawler.CrawlerException("CHROME_WEBDRIVER_PATH: %s不存在" % crawler.CHROME_WEBDRIVER_PATH)

        self.url = url
        # 浏览器参数
        chrome_options = webdriver.ChromeOptions()
        chrome_options.headless = False if ("headless" in kwargs and not kwargs["headless"]) else True  # 不打开浏览器
        while True:
            try:
                self.chrome = webdriver.Chrome(executable_path=crawler.CHROME_WEBDRIVER_PATH, options=chrome_options)
            except WebDriverException as e:
                message = str(e)
                if message.find("chrome not reachable") >= 0:
                    continue
                else:
                    raise
            break

    def __enter__(self) -> WebDriver:
        self.chrome.get(self.url)
        return self.chrome

    def __exit__(self, exception_type, exception_val, traceback):
        self.chrome.quit()


def get_default_browser_application_path(browser_type: int) -> Optional[str]:
    """
    根据浏览器和操作系统，返回浏览器程序文件所在的路径
    """
    if platform.system() != "Windows":
        return None
    if browser_type == BROWSER_TYPE_IE:
        return os.path.abspath(os.path.join(os.getenv("ProgramFiles"), "Internet Explorer\\iexplore.exe"))
    elif browser_type == BROWSER_TYPE_FIREFOX:
        return os.path.abspath(os.path.join(os.getenv("ProgramFiles"), "Mozilla Firefox\\firefox.exe"))
    elif browser_type == BROWSER_TYPE_CHROME:
        return os.path.abspath(os.path.join(os.getenv("ProgramFiles"), "Google\\Chrome\\Application\\chrome.exe"))
    else:
        output.print_msg("不支持的浏览器类型：" + str(browser_type))
    return None


def get_default_browser_cookie_path(browser_type: int) -> Optional[str]:
    """
    根据浏览器和操作系统，自动查找默认浏览器cookie路径(只支持windows)
    """
    if platform.system() != "Windows":
        return None
    if browser_type == BROWSER_TYPE_IE:
        return os.path.join(os.getenv("APPDATA"), "Microsoft\\Windows\\Cookies")
    elif browser_type == BROWSER_TYPE_FIREFOX:
        default_browser_path = os.path.join(os.getenv("APPDATA"), "Mozilla\\Firefox\\Profiles")
        for dir_name in os.listdir(default_browser_path):
            sub_path = os.path.join(default_browser_path, dir_name)
            if os.path.isdir(sub_path):
                if os.path.exists(os.path.join(sub_path, "cookies.sqlite")):
                    return os.path.abspath(sub_path)
    elif browser_type == BROWSER_TYPE_CHROME:
        profile_file_path = os.path.abspath(os.path.join(os.getenv("LOCALAPPDATA"), "Google\\Chrome\\User Data\\Local State"))
        default_profile_name = "Default"
        if os.path.exists(profile_file_path):
            with open(profile_file_path, "r", encoding="UTF-8") as file_handle:
                profile_info = json.load(file_handle)
                if "profile" in profile_info:
                    if "info_cache" in profile_info["profile"] and isinstance(profile_info["profile"]["info_cache"], dict) and len(profile_info["profile"]["info_cache"]) == 1:
                        default_profile_name = list(profile_info["profile"]["info_cache"].keys())[0]
                    elif "last_used" in profile_info["profile"]:
                        default_profile_name = profile_info["profile"]["last_used"]
                    elif "last_active_profiles" in profile_info["profile"] and isinstance(profile_info["profile"]["last_active_profiles"], dict) and len(profile_info["profile"]["last_active_profiles"]) == 1:
                        default_profile_name = profile_info["profile"]["last_active_profiles"][0]
        return os.path.abspath(os.path.join(os.getenv("LOCALAPPDATA"), "Google\\Chrome\\User Data", default_profile_name))
    elif browser_type == BROWSER_TYPE_TEXT:
        return os.path.abspath(os.path.join(crawler.PROJECT_APP_PATH, "info/cookies.data"))
    else:
        output.print_msg("不支持的浏览器类型：" + str(browser_type))
    return None


def get_all_cookie_from_browser(browser_type: int, file_path: str) -> dict:
    """
    从浏览器保存的cookie文件中读取所有cookie
    :Returns:
        {
            "domain1": {"key1": "value1", "key2": "value2", ......},
            "domain2": {"key1": "value1", "key2": "value2", ......},
            ......
        }
    """
    if not os.path.exists(file_path):
        output.print_msg("cookie目录：" + file_path + " 不存在")
        return {}
    all_cookies = {}
    if browser_type == BROWSER_TYPE_IE:
        # win10，IE 11已不支持该方法读取
        for cookie_name in os.listdir(file_path):
            if cookie_name.find(".txt") == -1:
                continue
            with open(os.path.join(file_path, cookie_name), "r", encoding="UTF-8") as cookie_file:
                cookie_info = cookie_file.read()
            for cookies in cookie_info.split("*"):
                cookie_list = cookies.strip("\n").split("\n")
                if len(cookie_list) < 8:
                    continue
                cookie_domain = cookie_list[2].split("/")[0]
                cookie_key = cookie_list[0]
                cookie_value = cookie_list[1]
                if cookie_domain not in all_cookies:
                    all_cookies[cookie_domain] = {}
                all_cookies[cookie_domain][cookie_key] = cookie_value
    elif browser_type == BROWSER_TYPE_FIREFOX:
        con = sqlite3.connect(os.path.join(file_path, "cookies.sqlite"))
        cur = con.cursor()
        cur.execute("SELECT host, path, name, value FROM moz_cookies")
        for cookie_info in cur.fetchall():
            cookie_domain = cookie_info[0]
            cookie_key = cookie_info[2]
            cookie_value = cookie_info[3]
            if cookie_domain not in all_cookies:
                all_cookies[cookie_domain] = {}
            all_cookies[cookie_domain][cookie_key] = cookie_value
        con.close()
    elif browser_type == BROWSER_TYPE_CHROME:
        # chrome仅支持windows系统的解密
        # Chrome 80以上版本已不支持使用该方法对https协议保存的cookies
        if platform.system() != "Windows":
            return {}
        con = sqlite3.connect(os.path.join(file_path, "Cookies"))
        cur = con.cursor()
        cur.execute("SELECT host_key, path, name, value, encrypted_value FROM cookies")
        for cookie_info in cur.fetchall():
            cookie_domain = cookie_info[0]
            cookie_key = cookie_info[2]
            try:
                cookie_value = win32crypt.CryptUnprotectData(cookie_info[4], None, None, None, 0)[1]
            except:
                continue
            if cookie_domain not in all_cookies:
                all_cookies[cookie_domain] = {}
            all_cookies[cookie_domain][cookie_key] = cookie_value.decode()
        con.close()
    elif browser_type == BROWSER_TYPE_TEXT:
        all_cookies["DEFAULT"] = net.split_cookies_from_cookie_string(file.read_file(file_path, file.READ_FILE_TYPE_FULL))
    else:
        output.print_msg("不支持的浏览器类型：" + str(browser_type))
        return {}
    return all_cookies
