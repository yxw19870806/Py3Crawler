# -*- coding:UTF-8  -*-
"""
常量类
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from enum import Enum, unique, EnumMeta, IntEnum, StrEnum
from typing import Final

SIZE_KB: Final[int] = 2 ** 10  # 1KB = 多少字节
SIZE_MB: Final[int] = 2 ** 20  # 1MB = 多少字节
SIZE_GB: Final[int] = 2 ** 30  # 1GB = 多少字节


class CrawlerEnumMeta(EnumMeta):
    def __getitem__(self, name: str) -> str:
        try:
            return super().__getitem__(name.upper())
        except (TypeError, KeyError):
            return "unknown"


@unique
class BrowserType(StrEnum, metaclass=CrawlerEnumMeta):
    IE: str = "ie"
    FIREFOX: str = "firefox"
    CHROME: str = "chrome"
    TEXT: str = "text"  # 直接从文件里读取cookies


@unique
class SysConfigKey(StrEnum):
    # 程序是否支持下载图片功能
    DOWNLOAD_PHOTO: str = "download_photo"
    # 程序是否支持下载视频功能
    DOWNLOAD_VIDEO: str = "download_video"
    # 程序是否支持下载音频功能
    DOWNLOAD_AUDIO: str = "download_audio"
    # 程序是否支持下载文本内容功能
    DOWNLOAD_CONTENT: str = "download_content"
    # 程序是否默认需要设置代理
    SET_PROXY: str = "set_proxy"
    # 程序是否支持不需要存档文件就可以开始运行
    NOT_CHECK_SAVE_DATA: str = "no_save_data"
    # 程序没有任何下载行为
    NOT_DOWNLOAD: str = "no_download"
    # 程序是否需要从浏览器存储的cookie中获取指定cookie的值
    GET_COOKIE: str = "get_cookie"
    # 存档文件的格式
    SAVE_DATA_FORMATE: str = "save_data_format"
    # 程序额外应用配置
    # 传入参数类型为tuple，每一位参数为长度3的tuple，顺序为(配置名字，默认值，配置读取方式)，同analysis_config方法后三个参数
    APP_CONFIG: str = "app_config"
    # 程序默认的app配置文件路径
    APP_CONFIG_PATH: str = "app_config_path"


@unique
class ConfigAnalysisMode(StrEnum):
    RAW: str = "raw"
    INTEGER: str = "int"
    BOOLEAN: str = "bool"
    FLOAT: str = "float"
    PATH: str = "path"


@unique
class ReadFileMode(StrEnum):
    FULL: str = "full"  # 读取整个文件 ，返回字符串
    LINE: str = "line"  # 按行读取，返回list


@unique
class WriteFileMode(StrEnum):
    APPEND: str = "append"  # 追加写入文件
    REPLACE: str = "replace"  # 覆盖写入文件


@unique
class CreateDirMode(StrEnum):
    IGNORE: str = "ignore"  # 目录存在时忽略
    DELETE: str = "delete"  # 目录存在时先删除再创建


@unique
class OrderType(StrEnum):
    ASC: str = "asc"  # 升序
    DESC: str = "desc"  # 降序
    DEFAULT: str = "default"  # 默认


@unique
class IncludeStringMode(StrEnum):
    NONE: str = "none"  # 不包含start_string和end_string
    START: str = "start"  # 只包含start_string
    END: str = "end"  # 只包含end_string
    ALL: str = "all"  # 同时包含start_string和end_string


@unique
class ProcessStatus(Enum):
    RUN: int = 0  # 进程运行中
    PAUSE: int = 1  # 进程暂停，知道状态变为0时才继续下载
    STOP: int = 2  # 进程立刻停止，删除还未完成的数据


@unique
class ExitCode(IntEnum):
    NORMAL: int = 0
    ERROR: int = 1


# 下载状态
@unique
class DownloadStatus(IntEnum):
    SUCCEED: int = 1
    FAILED: int = 0


# 下载返回值
@unique
class DownloadCode(IntEnum):
    URL_INVALID: int = -1
    RETRY_MAX_COUNT: int = -2
    FILE_SIZE_INVALID: int = -3
    PROCESS_EXIT: int = -10
    FILE_CREATE_FAILED: int = -11


# 网络请求返回值
@unique
class ResponseCode(IntEnum):
    RETRY: int = 0
    URL_INVALID: int = -1  # 地址不符合规范（非http:// 或者 https:// 开头）
    JSON_DECODE_ERROR: int = -2  # 返回数据不是JSON格式，但返回状态是200
    DOMAIN_NOT_RESOLVED: int = -3  # 域名无法解析
    RESPONSE_TO_LARGE: int = -4  # 文件太大
    TOO_MANY_REDIRECTS: int = -5  # 重定向次数过多
    SUCCEED: int = 200  # 成功
