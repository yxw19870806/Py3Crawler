# -*- coding:UTF-8  -*-
"""
快速读取配置，并设置对应属性
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import configparser
import os
from common import browser, crawler, net
from typing import Optional


def quickly_set_proxy(config: Optional[dict] = None, is_auto: bool = True) -> None:
    """
    读取配置文件，快速设置代理

    :Args:
    - is_auto
        False   始终使用代理
        True    配置文件未禁止时使用代理（IS_PROXY = 1 or 2)
    """
    if not isinstance(config, configparser.SafeConfigParser):
        config = _get_config()
    # 设置代理
    if is_auto:
        is_proxy = crawler.analysis_config(config, "IS_PROXY", 2, crawler.ConfigAnalysisMode.INTEGER)
        if is_proxy == 0:
            return
    proxy_ip = crawler.analysis_config(config, "PROXY_IP", "127.0.0.1")
    proxy_port = crawler.analysis_config(config, "PROXY_PORT", "8087")
    # 使用代理的线程池
    net.set_proxy(proxy_ip, proxy_port)


def quickly_get_save_data_path(config: Optional[dict] = None) -> str:
    """
    读取配置文件，返回存档文件所在路径

    :Args:
    - is_auto
        False   始终使用代理
        True    配置文件未禁止时使用代理（IS_PROXY = 1 or 2)
    """
    if not isinstance(config, configparser.SafeConfigParser):
        config = _get_config()
    return crawler.analysis_config(config, "SAVE_DATA_PATH", r"\\info/save.data", crawler.ConfigAnalysisMode.PATH)


def quickly_get_all_cookies_from_browser(config: Optional[dict] = None) -> dict:
    """
    读取配置文件，读取浏览器cookies
    """
    if not isinstance(config, configparser.SafeConfigParser):
        config = _get_config()
    # 是否自动查找cookies路径
    # 操作系统&浏览器
    browser_type = browser.BrowserType[crawler.analysis_config(config, "BROWSER_TYPE", browser.BrowserType.CHROME, crawler.ConfigAnalysisMode.RAW)]
    cookie_path = browser.get_default_browser_cookie_path(browser_type)
    return browser.get_all_cookie_from_browser(browser_type, cookie_path)


def _get_config() -> dict:
    config = crawler.read_config(crawler.PROJECT_CONFIG_PATH)
    app_config_path = os.path.abspath(os.path.join(crawler.PROJECT_APP_PATH, "app.ini"))
    if os.path.exists(app_config_path):
        app_config = crawler.read_config(app_config_path)
        config.update(app_config)
    return config
