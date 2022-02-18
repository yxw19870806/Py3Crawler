# -*- coding:UTF-8  -*-
"""
一些暂时用不到的方法
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import threading
import time
import zipfile
from typing import Optional
from common import file, net, output, path, tool

NET_CONFIG = {
    "DOWNLOAD_LIMIT_SIZE": 1.5 * net.SIZE_GB,  # 下载文件超过多少字节跳过不下载
    "DOWNLOAD_MULTI_THREAD_MIN_SIZE": 50 * net.SIZE_MB,  # 下载文件超过多少字节后开始使用多线程下载
    "DOWNLOAD_MULTI_THREAD_MAX_COUNT": 10,  # 多线程下载时总线程数上限
    "DOWNLOAD_MULTI_THREAD_BLOCK_SIZE": 10 * net.SIZE_MB,  # 多线程下载中单个线程下载的字节数
}


def zip_dir(source_dir: str, zip_file_path: str, need_source_dir=True) -> bool:
    """
    压缩文件夹

    :Args:
    - need_source_dir - 是否需要把文件夹名作为根目录
    """
    if not os.path.exists(source_dir) or os.path.exists(zip_file_path):
        return False

    file_list = []
    path_prefix_len = len(source_dir)  # 文件列表路径前缀的长度
    # 是文件，直接添加
    if os.path.isfile(source_dir):
        file_list.append(source_dir)
    else:
        # 如果需要包含目录
        if need_source_dir:
            path_prefix_len -= len(os.path.basename(source_dir)) + 1
        for root, dirs, files in os.walk(source_dir):
            for name in files:
                file_list.append(os.path.join(root, name))

    with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in file_list:
            in_zip_file_path = file_path[path_prefix_len:]
            zip_file.write(file_path, in_zip_file_path)

    return zipfile.is_zipfile(zip_file_path)


def unzip_file(zip_file_path: str, destination_path: str) -> bool:
    """
    解压缩文件
    """
    if not os.path.exists(zip_file_path) or os.path.exists(destination_path):
        return False

    os.makedirs(destination_path)

    zip_file = zipfile.ZipFile(zip_file_path)
    for zip_file_path in zip_file.namelist():
        zip_file_path = zip_file_path.replace("\\", "/")
        if zip_file_path.endswith("/"):  # 解压目录
            os.makedirs(os.path.join(destination_path, zip_file_path))
        else:  # 解压文件
            file_path = os.path.join(destination_path, zip_file_path)  # 文件的完整路径
            file_dir = os.path.dirname(file_path)
            if not os.path.exists(file_dir):
                os.makedirs(file_dir)
            outfile = open(file_path, "wb")
            outfile.write(zip_file.read(zip_file_path))
            outfile.close()

    return os.path.exists(destination_path)


def sort_file(source_path: str, destination_path: str, start_count: int, file_name_length: int):
    """
    将指定文件夹内的所有文件排序重命名并复制到其他文件夹中

    :Args:
    - source_path - 待排序文件所在目录
    - destination_path - 排序后所复制的目录
    - start_count - 重命名开始的序号
    - file_name_length - 复制后的文件名长度
    """
    file_list = path.get_dir_files_name(source_path, path.RETURN_FILE_LIST_DESC)
    # 判断排序目标文件夹是否存在
    if len(file_list) >= 1:
        if not path.create_dir(destination_path):
            return False
        # 倒叙排列
        for file_name in file_list:
            start_count += 1
            file_extension = os.path.splitext(file_name)[1]  # 包括 .扩展名
            new_file_name = str(("%0" + str(file_name_length) + "d") % start_count) + file_extension
            path.copy_file(os.path.join(source_path, file_name), os.path.join(destination_path, new_file_name))
        # 删除临时文件夹
        path.delete_dir_or_file(source_path)
    return True


# 多线程下载的总线程限制
multi_download_thread_semaphore = threading.Semaphore(NET_CONFIG["DOWNLOAD_MULTI_THREAD_MAX_COUNT"])


def download(file_url, file_path, recheck_file_extension=False, head_check=False, replace_if_exist: Optional[bool] = None, **kwargs):
    """
    现在远程文件到本地

    :Args:
    - file_url - the remote resource URL which you want to save
    - file_path - the local file path which you want to save remote resource
    - recheck_file_extension - is auto rename file according to "Content-Type" in response headers
    - head_check -"HEAD" method request to check response status and file size before download file

    :Returns:
        - status - 0 download failure, 1 download successful
        - code - failure reason
        - file_path - finally local file path(when recheck_file_extension is True, will rename it)
    """
    if not isinstance(replace_if_exist, bool):
        replace_if_exist = net.DOWNLOAD_REPLACE_IF_EXIST
    if not replace_if_exist and os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        output.print_msg(f"文件{file_path}（{file_url}）已存在，跳过")
        return {"status": 1, "code": 0, "file_path": file_path}
    # 判断保存目录是否存在
    if not path.create_dir(os.path.dirname(file_path)):
        return {"status": 1, "code": -11, "file_path": file_path}
    is_create_file = False
    is_multi_thread = False
    return_code = {"status": 0, "code": -3}
    for retry_count in range(0, net.NET_CONFIG["DOWNLOAD_RETRY_COUNT"]):
        if head_check and retry_count == 0:
            request_method = "HEAD"
        else:
            request_method = "GET"
        # 获取头信息
        response = net.request(file_url, request_method, is_check_qps=False, connection_timeout=net.NET_CONFIG["HTTP_CONNECTION_TIMEOUT"], read_timeout=net.NET_CONFIG["HTTP_READ_TIMEOUT"], **kwargs)
        # 其他返回状态，退出
        if response.status != net.HTTP_RETURN_CODE_SUCCEED:
            # URL格式不正确
            if response.status == net.HTTP_RETURN_CODE_URL_INVALID:
                return_code = {"status": 0, "code": -1}
            # 超过重试次数
            elif response.status == net.HTTP_RETURN_CODE_RETRY:
                return_code = {"status": 0, "code": -2}
            # 其他http code
            else:
                return_code = {"status": 0, "code": response.status}
            break

        # 判断文件是不是过大
        content_length = response.getheader("Content-Length")
        if content_length is not None:
            content_length = int(content_length)
            # 超过限制
            if content_length > NET_CONFIG["DOWNLOAD_LIMIT_SIZE"]:
                return {"status": 0, "code": -4}
            # 文件比较大，使用多线程下载（必须是head_check=True的情况下，否则整个文件内容都已经返回了）
            elif head_check and content_length > NET_CONFIG["DOWNLOAD_MULTI_THREAD_MIN_SIZE"]:
                is_multi_thread = True

        # response中的Content-Type作为文件后缀名
        if recheck_file_extension:
            content_type = response.getheader("Content-Type")
            if content_type is not None and content_type != "octet-stream":
                if net.MIME_DICTIONARY is None:
                    net.MIME_DICTIONARY = tool.json_decode(file.read_file(os.path.join(os.path.dirname(__file__), "mime.json")), {})
                if content_type in net.MIME_DICTIONARY:
                    new_file_extension = net.MIME_DICTIONARY[content_type]
                else:
                    new_file_extension = content_type.split("/")[-1]
                file_path = os.path.splitext(file_path)[0] + "." + new_file_extension

        if not is_multi_thread:  # 单线程下载
            # 如果是先调用HEAD方法的，需要重新获取完整数据
            if head_check:
                response = net.request(file_url, method="GET", connection_timeout=net.NET_CONFIG["DOWNLOAD_CONNECTION_TIMEOUT"], read_timeout=net.NET_CONFIG["DOWNLOAD_READ_TIMEOUT"], **kwargs)
                if response.status != net.HTTP_RETURN_CODE_SUCCEED:
                    continue
            # 下载
            with open(file_path, "wb") as file_handle:
                is_create_file = True
                try:
                    file_handle.write(response.data)
                except OSError as ose:
                    if str(ose).find("No space left on device") != -1:
                        net.EXIT_FLAG = True
                    raise
        else:  # 多线程下载
            # 创建文件
            with open(file_path, "w"):
                is_create_file = True
            thread_list = []
            error_flag = []
            with open(file_path, "rb+") as file_handle:
                file_no = file_handle.fileno()
                end_pos = -1
                while end_pos < content_length - 1:
                    start_pos = end_pos + 1
                    end_pos = min(content_length - 1, start_pos + NET_CONFIG["DOWNLOAD_MULTI_THREAD_BLOCK_SIZE"] - 1)
                    # 创建一个副本
                    fd_handle = os.fdopen(os.dup(file_no), "rb+", -1)
                    thread = MultiThreadDownload(file_url, start_pos, end_pos, fd_handle, error_flag)
                    thread.start()
                    thread_list.append(thread)
            # 等待所有线程下载完毕
            for thread in thread_list:
                thread.join()
            # 有任意一个线程下载失败了，或者文件存在连续1K以上的空字节
            if len(error_flag) > 0:
                continue
            if not _check_multi_thread_download_file(file_path):
                output.print_msg(f"网络文件{file_url}多线程下载后发现无效字节")
                continue
        if content_length is None:
            return {"status": 1, "code": 0, "file_path": file_path}
        # 判断文件下载后的大小和response中的Content-Length是否一致
        file_size = os.path.getsize(file_path)
        if content_length == file_size:
            return {"status": 1, "code": 0, "file_path": file_path}
        else:
            output.print_msg(f"本地文件{file_path}：{content_length}和网络文件{file_url}：{file_size}不一致")
            time.sleep(net.NET_CONFIG["HTTP_REQUEST_RETRY_WAIT_TIME"])
    if is_create_file:
        path.delete_dir_or_file(file_path)
    return return_code


def _check_multi_thread_download_file(file_path):
    """
    Check fhe file download with multi thread

    :Returns:
        True    file is valid
        False   file is invalid(download failure)
    """
    file_path = os.path.abspath(file_path)
    if not os.path.exists(file_path):
        return True
    with open(file_path, "rb") as file_handle:
        buffer_size = 2 ** 20  # 1M
        while file_buffer := file_handle.read(buffer_size):
            if file_buffer.find(b"\x00" * (2 ** 10)) >= 0:
                return False
    return True


class MultiThreadDownload(threading.Thread):
    def __init__(self, file_url, start_pos, end_pos, fd_handle, error_flag):
        threading.Thread.__init__(self)
        self.file_url = file_url
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.fd_handle = fd_handle
        self.error_flag = error_flag
        multi_download_thread_semaphore.acquire()

    def run(self):
        header_list = {"Range": f"bytes={self.start_pos}-{self.end_pos}"}
        range_size = self.end_pos - self.start_pos + 1
        for retry_count in range(0, NET_CONFIG["DOWNLOAD_RETRY_COUNT"]):
            response = net.request(self.file_url, method="GET", header_list=header_list)
            if response.status == 206:
                # 下载的文件和请求的文件大小不一致
                if len(response.data) != range_size:
                    output.print_msg(f"网络文件{self.file_url}：range {self.start_pos} - {self.end_pos}实际下载大小 {len(response.data)} 不一致")
                    time.sleep(net.NET_CONFIG["HTTP_REQUEST_RETRY_WAIT_TIME"])
                else:
                    # 写入本地文件后退出
                    self.fd_handle.seek(self.start_pos)
                    self.fd_handle.write(response.data)
                    self.fd_handle.close()
                    break
        else:
            self.error_flag.append(self)

        # 唤醒主线程
        multi_download_thread_semaphore.release()
