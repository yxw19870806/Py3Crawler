# -*- coding:UTF-8  -*-
"""
微博批量关注账号
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import time
from common import *
from project.weibo import weibo


# 关注指定账号
def follow_account(account_id):
    api_url = "https://weibo.com/aj/f/followed?ajwvr=6"
    post_data = {
        "uid": account_id,
        "refer_flag": "1005050001_",
    }
    header_list = {"Referer": "https://weibo.com/%s/follow" % account_id}
    cookies_list = {"SUB": weibo.COOKIE_INFO["SUB"]}
    follow_response = net.request(api_url, method="POST", fields=post_data, header_list=header_list, cookies_list=cookies_list, json_decode=True)
    if follow_response.status != const.HTTP_RETURN_CODE_SUCCEED:
        output.print_msg("关注%s失败，请求返回结果：%s" % (account_id, crawler.request_failre(follow_response.status)))
        tool.process_exit()
    try:
        return_code = crawler.get_json_value(follow_response.json_data, "code", type_check=int)
    except crawler.CrawlerException():
        output.print_msg("关注%s失败，返回内容：%s，退出程序！" % (account_id, follow_response.json_data))
        tool.process_exit()
    else:
        if return_code == 100000:
            output.print_msg("关注%s成功" % account_id)
            time.sleep(5)
            return True
        elif return_code == 100027:
            output.print_msg("关注%s失败，连续关注太多用户需要输入验证码，等待一会儿继续尝试" % account_id)
            # sleep 一段时间后再试
            time.sleep(60)
        elif return_code == 100001:
            output.print_msg("达到今日关注上限，退出程序")
            tool.process_exit()
        else:
            output.print_msg("关注%s失败，返回内容：%s，退出程序！" % (account_id, follow_response.json_data))
            tool.process_exit()

    return False


class WeiboFollow(weibo.Weibo):
    def __init__(self, **kwargs):
        weibo.Weibo.__init__(self, **kwargs)

    def main(self):
        # 读取存档文件
        for account_id in sorted(self.save_data.keys()):
            while not follow_account(account_id):
                pass

        output.print_msg("关注完成")


if __name__ == "__main__":
    WeiboFollow().main()
