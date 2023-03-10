# -*- coding:UTF-8  -*-
"""
浏览器数据相关类
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import base64
import json
import os
import platform
import pywintypes
import sqlite3
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.webdriver import WebDriver
from typing import Optional

if platform.system() == "Windows":
    import win32crypt

from common import crawler, file, net, output, enum


class Chrome:
    def __init__(self, url: str, **kwargs):
        """
        返回selenium.webdriver.Chrome()方法创建的chrome驱动对象

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
        if "add_argument" in kwargs and isinstance(kwargs["add_argument"], list):
            for argument in kwargs["add_argument"]:
                chrome_options.add_argument(argument)

        if "desired_capabilities" in kwargs:
            desired_capabilities = kwargs["desired_capabilities"]
        else:
            desired_capabilities = None

        while True:
            try:
                self.chrome = webdriver.Chrome(executable_path=crawler.CHROME_WEBDRIVER_PATH, options=chrome_options, desired_capabilities=desired_capabilities)
            except WebDriverException as e:
                message = str(e)
                if message.find("chrome not reachable") >= 0:
                    continue
                else:
                    raise
            else:
                break

    def __enter__(self) -> WebDriver:
        self.chrome.get(self.url)
        return self.chrome

    def __exit__(self, exception_type, exception_val, traceback):
        self.chrome.quit()


def _get_chrome_user_data_path() -> str:
    return os.path.abspath(os.path.join(os.getenv("LOCALAPPDATA"), "Google", "Chrome", "User Data"))


def get_default_browser_application_path(browser_type: enum.BrowserType) -> Optional[str]:
    """
    根据浏览器和操作系统，返回浏览器程序文件所在的路径
    """
    if platform.system() != "Windows":
        return None
    if browser_type == enum.BrowserType.IE:
        return os.path.abspath(os.path.join(os.getenv("ProgramFiles"), "Internet Explorer", "iexplore.exe"))
    elif browser_type == enum.BrowserType.FIREFOX:
        return os.path.abspath(os.path.join(os.getenv("ProgramFiles"), "Mozilla Firefox", "firefox.exe"))
    elif browser_type == enum.BrowserType.CHROME:
        return os.path.abspath(os.path.join(os.getenv("ProgramFiles"), "Google", "Chrome", "Application", "chrome.exe"))
    else:
        output.print_msg("不支持的浏览器类型：%s" % browser_type)
    return None


def get_default_browser_cookie_path(browser_type: enum.BrowserType) -> Optional[str]:
    """
    根据浏览器和操作系统，自动查找默认浏览器cookie路径(只支持windows)
    """
    if platform.system() != "Windows":
        return None
    if browser_type == enum.BrowserType.IE:
        return os.path.join(os.getenv("APPDATA"), "Microsoft", "Windows", "Cookies")
    elif browser_type == enum.BrowserType.FIREFOX:
        default_browser_path = os.path.join(os.getenv("APPDATA"), "Mozilla", "Firefox", "Profiles")
        for dir_name in os.listdir(default_browser_path):
            sub_path = os.path.join(default_browser_path, dir_name)
            if os.path.isdir(sub_path):
                if os.path.exists(os.path.join(sub_path, "cookies.sqlite")):
                    return os.path.abspath(sub_path)
    elif browser_type == enum.BrowserType.CHROME:
        browser_data_path = _get_chrome_user_data_path()
        profile_file_path = os.path.join(browser_data_path, "Local State")
        default_profile_name = "Default"
        if os.path.exists(profile_file_path):
            with open(profile_file_path, "r", encoding="UTF-8") as file_handle:
                profile_info = json.load(file_handle)
                if "profile" in profile_info and "last_used" in profile_info["profile"]:
                    default_profile_name = profile_info["profile"]["last_used"]
        return os.path.join(browser_data_path, default_profile_name)
    elif browser_type == enum.BrowserType.TEXT:
        return os.path.abspath(os.path.join(crawler.PROJECT_APP_PATH, "info", "cookies.data"))
    else:
        output.print_msg("不支持的浏览器类型：%s" % browser_type)
    return None


def get_all_cookie_from_browser(browser_type: enum.BrowserType, file_path: str) -> dict:
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
    if browser_type == enum.BrowserType.IE:
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
    elif browser_type == enum.BrowserType.FIREFOX:
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
    elif browser_type == enum.BrowserType.CHROME:
        # chrome仅支持windows系统的解密
        if platform.system() != "Windows":
            return {}
        profile_file_path = os.path.join(_get_chrome_user_data_path(), "Local State")
        encrypted_key = ""
        if os.path.exists(profile_file_path):
            with open(profile_file_path, "r", encoding="UTF-8") as file_handle:
                profile_info = json.load(file_handle)
                if "os_crypt" in profile_info and "encrypted_key" in profile_info["os_crypt"]:
                    encrypted_key = profile_info["os_crypt"]["encrypted_key"]
        if not encrypted_key:
            output.print_msg("encrypted_key获取失败")
            return {}
        encrypted_key = base64.b64decode(encrypted_key.encode())[5:]
        try:
            encrypted_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
        except pywintypes.error:
            output.print_msg("encrypted_key解密失败")
            return {}
        cipher = Cipher(algorithms.AES(encrypted_key), None, backend=default_backend())

        con = sqlite3.connect(os.path.join(file_path, "Network", "Cookies"))
        cur = con.cursor()
        cur.execute("SELECT host_key, path, name, value, encrypted_value FROM cookies")
        for cookie_info in cur.fetchall():
            cookie_domain = cookie_info[0]
            cookie_key = cookie_info[2]
            if cookie_info[3]:
                cookie_value = cookie_info[3]
            else:
                decrypt_value = cookie_info[4]
                if decrypt_value.startswith(b"x01x00x00x00"):
                    try:
                        cookie_value = win32crypt.CryptUnprotectData(decrypt_value, None, None, None, 0)[1]
                    except pywintypes.error:
                        continue
                elif decrypt_value.startswith(b"v10"):
                    cipher.mode = modes.GCM(decrypt_value[len(b"v10"):15])
                    value = cipher.decryptor().update(decrypt_value[15:])
                    cookie_value = value[:-16]
                else:
                    continue
            if cookie_domain not in all_cookies:
                all_cookies[cookie_domain] = {}
            all_cookies[cookie_domain][cookie_key] = cookie_value.decode()
        con.close()
    elif browser_type == enum.BrowserType.TEXT:
        all_cookies["DEFAULT"] = net.split_cookies_from_cookie_string(file.read_file(file_path))
    else:
        output.print_msg("不支持的浏览器类型：%s" % browser_type)
        return {}
    return all_cookies
