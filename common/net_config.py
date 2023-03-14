# -*- coding:UTF-8  -*-
"""
网络配置
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import re
from common import const, console, file, tool, PROJECT_LIB_PATH


def convert_to_bytes(value, default_value: int) -> int:
    """
    将字符串转换为字节数

    :Args:
    - value - 待转换的字符串，例如 1 KB，2 MB，3 GB等
    """
    value = str(value).strip()
    size = default_value
    if tool.is_integer(value):
        size = int(value)
    else:
        search_result = re.findall(r"^(\d+) *([a-zA-z]*)$", value)
        if len(search_result) == 1:
            unit = search_result[0][1].upper()
            if unit == "" or unit == "B":
                size = int(search_result[0][0])
            elif unit == "KB":
                size = int(search_result[0][0]) * const.SIZE_KB
            elif unit == "MB":
                size = int(search_result[0][0]) * const.SIZE_MB
            elif unit == "GB":
                size = int(search_result[0][0]) * const.SIZE_GB
            else:
                console.log("无效的字节单位'%s'，只支持B、KB、MB、GB" % unit)
        else:
            console.log("无效的字节数设置'%s'" % value)
    return size


class NetConfig:
    HTTP_CONNECTION_TIMEOUT = 10  # 网络访问连接超时的秒数
    HTTP_READ_TIMEOUT = 30  # 网络访问读取超时的秒数
    HTTP_REQUEST_RETRY_COUNT = 10  # 网络访问自动重试次数
    DOWNLOAD_CONNECTION_TIMEOUT = 10  # 下载文件连接超时的秒数
    DOWNLOAD_READ_TIMEOUT = 60  # 下载文件读取超时的秒数
    DOWNLOAD_RETRY_COUNT = 10  # 下载文件自动重试次数
    DOWNLOAD_MULTIPART_MIN_SIZE = "10 MB"  # 下载文件超过多少字节后开始使用分段下载
    DOWNLOAD_MULTIPART_BLOCK_SIZE = "1 MB"  # 分段下载中单次获取的字节数
    TOO_MANY_REQUESTS_WAIT_TIME = 60  # http code 429(Too Many requests)时的等待时间
    SERVICE_INTERNAL_ERROR_WAIT_TIME = 30  # http code 50X（服务器内部错误）时的等待时间
    HTTP_REQUEST_RETRY_WAIT_TIME = 5  # 请求失败后重新请求的间隔时间
    GLOBAL_QUERY_PER_MINUTER = 1000  # 全局每分钟请求限制
    SINGLE_HOST_QUERY_PER_MINUTER = 1000  # 单域名每分钟请求限制

    CONFIG_KEYS = {
        "HTTP_CONNECTION_TIMEOUT", "HTTP_READ_TIMEOUT", "HTTP_REQUEST_RETRY_COUNT",
        "DOWNLOAD_CONNECTION_TIMEOUT", "DOWNLOAD_READ_TIMEOUT", "DOWNLOAD_RETRY_COUNT",
        "DOWNLOAD_MULTIPART_MIN_SIZE", "DOWNLOAD_MULTIPART_BLOCK_SIZE", "TOO_MANY_REQUESTS_WAIT_TIME",
        "SERVICE_INTERNAL_ERROR_WAIT_TIME", "HTTP_REQUEST_RETRY_WAIT_TIME", "GLOBAL_QUERY_PER_MINUTER",
        "SINGLE_HOST_QUERY_PER_MINUTER",
    }

    def __init__(self):
        config = tool.json_decode(file.read_file(os.path.join(PROJECT_LIB_PATH, "net_config.json")), {})
        for config_key in self.CONFIG_KEYS:
            default_value = self.__getattribute__(config_key)
            config_value = default_value if (config_key not in config) else config[config_key]
            if config_key in ["DOWNLOAD_MULTIPART_MIN_SIZE", "DOWNLOAD_MULTIPART_BLOCK_SIZE"]:
                config_value = convert_to_bytes(config_value, default_value)
            self.__setattr__(config_key, config_value)
