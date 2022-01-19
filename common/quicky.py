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


# 读取配置文件，快速设置代理
# is_auto = False   始终使用代理
#           True    配置文件未禁止时使用代理（IS_PROXY = 1 or 2)
def quickly_set_proxy(config=None, is_auto=True):
    if not isinstance(config, configparser.SafeConfigParser):
        config = _get_config()
    # 设置代理
    if is_auto:
        is_proxy = crawler.analysis_config(config, "IS_PROXY", 2, crawler.CONFIG_ANALYSIS_MODE_INTEGER)
        if is_proxy == 0:
            return
    proxy_ip = crawler.analysis_config(config, "PROXY_IP", "127.0.0.1")
    proxy_port = crawler.analysis_config(config, "PROXY_PORT", "8087")
    # 使用代理的线程池
    net.set_proxy(proxy_ip, proxy_port)


# 读取配置文件，返回存档文件所在路径
def quickly_get_save_data_path(config=None):
    if not isinstance(config, configparser.SafeConfigParser):
        config = _get_config()
    return crawler.analysis_config(config, "SAVE_DATA_PATH", "\\\\info/save.data", crawler.CONFIG_ANALYSIS_MODE_PATH)


# 读取浏览器cookies
def quickly_get_all_cookies_from_browser(config=None):
    if not isinstance(config, configparser.SafeConfigParser):
        config = _get_config()
    # 是否自动查找cookies路径
    # 操作系统&浏览器
    browser_type = crawler.analysis_config(config, "BROWSER_TYPE", browser.BROWSER_TYPE_CHROME, crawler.CONFIG_ANALYSIS_MODE_INTEGER)
    cookie_path = browser.get_default_browser_cookie_path(browser_type)
    return browser.get_all_cookie_from_browser(browser_type, cookie_path)


def _get_config():
    config = crawler.read_config(crawler.PROJECT_CONFIG_PATH)
    app_config_path = os.path.abspath(os.path.join(crawler.PROJECT_APP_PATH, "app.ini"))
    if os.path.exists(app_config_path):
        app_config = crawler.read_config(app_config_path)
        config.update(app_config)
    return config
