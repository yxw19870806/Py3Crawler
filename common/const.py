# -*- coding:UTF-8  -*-
"""
常量类
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from enum import Enum, unique, EnumMeta
from typing import Final

SIZE_KB: Final[int] = 2 ** 10  # 1KB = 多少字节
SIZE_MB: Final[int] = 2 ** 20  # 1MB = 多少字节
SIZE_GB: Final[int] = 2 ** 30  # 1GB = 多少字节

# 网络访问返回值
HTTP_RETURN_CODE_RETRY = 0
HTTP_RETURN_CODE_URL_INVALID = -1  # 地址不符合规范（非http:// 或者 https:// 开头）
HTTP_RETURN_CODE_JSON_DECODE_ERROR = -2  # 返回数据不是JSON格式，但返回状态是200
HTTP_RETURN_CODE_DOMAIN_NOT_RESOLVED = -3  # 域名无法解析
HTTP_RETURN_CODE_RESPONSE_TO_LARGE = -4  # 文件太大
HTTP_RETURN_CODE_TOO_MANY_REDIRECTS = -5  # 重定向次数过多
HTTP_RETURN_CODE_SUCCEED = 200

# 下载返回值
DOWNLOAD_RETURN_CODE_URL_INVALID = -1
DOWNLOAD_RETURN_CODE_RETRY_MAX_COUNT = -2
DOWNLOAD_RETURN_CODE_FILE_SIZE_INVALID = -3
DOWNLOAD_RETURN_CODE_PROCESS_EXIT = -10
DOWNLOAD_RETURN_CODE_FILE_CREATE_FAILED = -11

# 下载状态
DOWNLOAD_STATUS_SUCCEED = 1
DOWNLOAD_STATUS_FAILED = 0


class CrawlerEnumMeta(EnumMeta):
    def __getitem__(self, name):
        try:
            return super().__getitem__(name.upper())
        except (TypeError, KeyError):
            return "unknown"


@unique
class BrowserType(Enum, metaclass=CrawlerEnumMeta):
    IE: str = "ie"
    FIREFOX: str = "firefox"
    CHROME: str = "chrome"
    TEXT: str = "text"  # 直接从文件里读取cookies


@unique
class SysConfigKey(Enum):
    # 程序是否支持下载图片功能
    DOWNLOAD_PHOTO = "download_photo"
    # 程序是否支持下载视频功能
    DOWNLOAD_VIDEO = "download_video"
    # 程序是否支持下载音频功能
    DOWNLOAD_AUDIO = "download_audio"
    # 程序是否支持下载文本内容功能
    DOWNLOAD_CONTENT = "download_content"
    # 程序是否默认需要设置代理
    SET_PROXY = "set_proxy"
    # 程序是否支持不需要存档文件就可以开始运行
    NOT_CHECK_SAVE_DATA = "no_save_data"
    # 程序没有任何下载行为
    NOT_DOWNLOAD = "no_download"
    # 程序是否需要从浏览器存储的cookie中获取指定cookie的值
    GET_COOKIE = "get_cookie"
    # 程序额外应用配置
    # 传入参数类型为tuple，每一位参数为长度3的tuple，顺序为(配置名字，默认值，配置读取方式)，同analysis_config方法后三个参数
    APP_CONFIG = "app_config"
    # 程序默认的app配置文件路径
    APP_CONFIG_PATH = "app_config_path"


@unique
class ConfigAnalysisMode(Enum):
    RAW = "raw"
    INTEGER = "int"
    BOOLEAN = "bool"
    FLOAT = "float"
    PATH = "path"


@unique
class ReadFileMode(Enum):
    FULL: str = "full"  # 读取整个文件 ，返回字符串
    LINE: str = "line"  # 按行读取，返回list


@unique
class WriteFileMode(Enum):
    APPEND: str = "append"  # 追加写入文件
    REPLACE: str = "replace"  # 覆盖写入文件


@unique
class CreateDirMode(Enum):
    IGNORE: str = "ignore"  # 目录存在时忽略
    DELETE: str = "delete"  # 目录存在时先删除再创建


@unique
class OrderType(Enum):
    ASC: str = "asc"  # 升序
    DESC: str = "desc"  # 降序
    DEFAULT: str = "default"  # 默认


@unique
class ProcessStatus(Enum):
    RUN: int = 0  # 进程运行中
    PAUSE: int = 1  # 进程暂停，知道状态变为0时才继续下载
    STOP: int = 2  # 进程立刻停止，删除还未完成的数据


@unique
class IncludeStringMode(Enum):
    NONE: str = "none"  # 不包含start_string和end_string
    START: str = "start"  # 只包含start_string
    END: str = "end"  # 只包含end_string
    ALL: str = "all"  # 同时包含start_string和end_string


@unique
class ExitCode(Enum):
    NORMAL: int = 0
    ERROR: int = 1
