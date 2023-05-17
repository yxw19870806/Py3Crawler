# -*- coding:UTF-8  -*-
"""
url解析类
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import urllib.parse


def parse_query(url: str) -> dict[str, str]:
    """
    解析url地址中的query参数，生成字典
        scheme://username:password@host.name:123/sub/path/name1.name2.extension/?key=value&key2=value2#fragment
        ->
        {”key“: "value", "key2": "value2"}
    """
    query_dict = {}
    for query_key, query_value in urllib.parse.parse_qsl(urllib.parse.urlparse(url).query):
        query_dict[query_key] = query_value
    return query_dict


def remove_query(url: str) -> str:
    """
    去除url地址中的query参数
        scheme://username:password@host.name:123/sub/path/name1.name2.extension/?key=value&key2=value2#fragment
        ->
        scheme://username:password@host.name:123/sub/path/name1.name2.extension
    """
    return urllib.parse.urljoin(url, get_path(url))


def get_path(url: str) -> str:
    """
    获取url地址的path路径
        scheme://username:password@host.name:123/sub/path/name1.name2.extension/?key=value&key2=value2#fragment
        ->
        /sub/path/name1.name2.extension
    """
    return urllib.parse.urlparse(url).path.rstrip("/")


def split_path(url: str) -> list[str]:
    """
    分割url地址的path路径
        scheme://username:password@host.name:123/sub/path/name1.name2.extension/?key=value&key2=value2#fragment
        ->
        ["sub", "path", "name1.name2.extension"]
    """
    return get_path(url).lstrip("/").split("/")


def get_basename(url: str) -> str:
    """
    获取url地址的basename
        scheme://username:password@host.name:123/sub/path/name1.name2.extension/?key=value&key2=value2#fragment
        ->
        name1.name2.extension
    """
    return os.path.basename(get_path(url))


def get_file_name_ext(url: str, default_file_type: str = "") -> tuple[str, str]:
    """
    获取url地址的文件名+文件类型
        scheme://username:password@host.name:123/sub/path/name1.name2.extension/?key=value&key2=value2#fragment
        ->
        name1.name2, extension
    """
    split_result = get_basename(url).rsplit(".", 1)
    if len(split_result) == 1:
        return split_result[0], default_file_type
    else:
        return split_result[0], split_result[1]


def get_file_ext(url: str, default_file_type: str = "") -> str:
    """
    获取url地址的文件类型
        scheme://username:password@host.name:123/sub/path/name1.name2.extension/?key=value&key2=value2#fragment
        ->
        extension
    """
    return get_file_name_ext(url, default_file_type)[1]


def get_file_name(url: str) -> str:
    """
    获取url地址的文件名
        scheme://username:password@host.name:123/sub/path/name1.name2.extension/?key=value&key2=value2#fragment
        ->
        name1.name2
    """
    return get_file_name_ext(url)[0]


def encode(url: str) -> str:
    """
    url编码：百分号编码(Percent-Encoding)
        https://www.example.com/测 试/
        ->
        https://www.example.com/%E6%B5%8B%20%E8%AF%95/
    """
    return urllib.parse.quote(url, safe=";/?:@&=+$,%")
