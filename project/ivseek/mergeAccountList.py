# -*- coding:UTF-8  -*-
"""
ivseek已解析文件中提取全部账号
http://www.ivseek.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import *
from project.ivseek import ivseek
from project.youtube import youtube
from suspend.niconico import niconico


def main():
    # 初始化类
    youtube_class = youtube.Youtube(extra_sys_config={const.SysConfigKey.NOT_CHECK_SAVE_DATA: True})
    niconico_class = niconico.NicoNico(extra_sys_config={const.SysConfigKey.NOT_CHECK_SAVE_DATA: True})
    ivseek_class = ivseek.IvSeek()

    save_data_list = ivseek.read_save_data(ivseek_class.save_data_path)
    account_id_list = {
        "youtube": {},
        "niconico": {},
    }
    for single_save_list in save_data_list:
        # 已完成
        if single_save_list[4] == ivseek.DONE_SING:
            continue
        if single_save_list[2].find("//www.youtube.com") >= 0:
            account_id_list["youtube"][single_save_list[3]] = 1
        elif single_save_list[2].find("//www.nicovideo.jp") >= 0:
            account_id_list["niconico"][single_save_list[3]] = 1
        else:
            continue

    # 获取niconico账号下的所有视频列表
    niconico_mylist_cache = ivseek_class.new_cache("niconico_mylist.json", const.FileType.JSON)
    niconico_mylist_list = niconico_mylist_cache.read()
    if isinstance(niconico_mylist_list, dict):
        niconico_mylist_list = {}
    for account_id in account_id_list["niconico"]:
        if account_id in niconico_mylist_list:
            continue
        if not tool.is_integer(account_id):
            continue
        try:
            account_mylist_response = niconico.get_account_mylist(account_id)
        except CrawlerException as e:
            print(e.http_error("niconico账号%s的视频列表" % account_id))
            continue
        niconico_mylist_list[account_id] = account_mylist_response["list_id_list"]
        niconico_mylist_cache.write(niconico_mylist_list)

    # 更新youtube的存档文件
    for account_id in account_id_list["youtube"]:
        if account_id not in youtube_class.save_data:
            youtube_class.save_data.save(account_id, [account_id])
    youtube_class.save_data.done()

    # 更新niconico的存档文件
    for account_id in niconico_mylist_list:
        for mylist_id in niconico_mylist_list[account_id]:
            mylist_id = str(mylist_id)
            if mylist_id not in niconico_class.save_data:
                niconico_class.save_data.save(mylist_id, [mylist_id])
    niconico_class.save_data.done()

    file.write_file(tool.dyadic_list_to_string(save_data_list), ivseek_class.save_data_path, const.WriteFileMode.REPLACE)


if __name__ == "__main__":
    main()
