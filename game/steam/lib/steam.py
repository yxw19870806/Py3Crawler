# -*- coding:UTF-8  -*-
"""
steam相关数据解析爬虫
https://store.steampowered.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import re
from pyquery import PyQuery as pq
from common import *

INVENTORY_ITEM_TYPE_GEM = "Gems"
INVENTORY_ITEM_TYPE_TRADE_CARD = "Trading Card"
INVENTORY_ITEM_TYPE_PROFILE_BACKGROUND = "Profile Background"
INVENTORY_ITEM_TYPE_EMOTICON = "Emoticon"

MAX_BADGE_LEVEL = 5

COOKIES = {}


# 获取全部正在打折的游戏列表
def get_discount_game_list():
    page_count = 1
    discount_game_list = []
    app_id_list = []
    COOKIES.update({"Steam_Language": "schinese"})
    while True:
        console.log(f"开始解析第{page_count}页打折游戏")
        discount_game_pagination_url = f"https://store.steampowered.com/search/results?sort_by=Price_ASC&category1=996,998&os=win&specials=1&page={page_count}"
        discount_game_pagination_response = net.Request(discount_game_pagination_url, method="GET", cookies=COOKIES)
        if discount_game_pagination_response.status != const.ResponseCode.SUCCEED:
            raise CrawlerException(f"第{page_count}页打折游戏，{crawler.request_failre(discount_game_pagination_response.status)}")
        search_result_selector = pq(discount_game_pagination_response.content).find("#search_result_container")
        game_list_selector = search_result_selector.find("#search_resultsRows a")
        for game_index in range(game_list_selector.length):
            game_selector = game_list_selector.eq(game_index)
            # game app id
            app_id = game_selector.attr("data-ds-appid")
            package_id = game_selector.attr("data-ds-packageid")
            bundle_id = game_selector.attr("data-ds-bundleid")
            # 不同类型取对应唯一id
            if bundle_id is not None:
                prime_id = bundle_id
                game_type = "bundle"
                bundle_info = game_selector.attr("data-ds-bundle-data")
                app_id = []
                if bundle_info:
                    # 包含的全部app_id
                    app_id_find = re.findall(r'"m_rgIncludedAppIDs":\[([^\]]*)\]', bundle_info)
                    for temp_id_list in app_id_find:
                        temp_id_list = temp_id_list.split(",")
                        app_id += temp_id_list
                else:
                    console.log("bundle_info not found\n" + game_selector.html())
            elif package_id is not None:
                prime_id = package_id
                game_type = "package"
                # package，包含多个游戏
                if app_id.find(",") >= 0:
                    app_id = app_id.split(",")
            else:
                prime_id = app_id
                game_type = "game"
            # 过滤那些重复的游戏
            if prime_id in app_id_list:
                continue
            app_id_list.append(prime_id)
            # discount
            discount = "".join(list(filter(str.isdigit, game_selector.find(".search_discount span").text())))
            # old price
            old_price = game_selector.find(".search_price span strike").text()[1:].strip()
            try:
                old_price = float(old_price)
            except ValueError:
                old_price = 0
            # now price
            now_price = game_selector.find(".search_price").remove("span").text()[1:].strip()
            try:
                now_price = float(now_price)
            except ValueError:
                now_price = 0
            if not tool.is_integer(discount):
                if old_price == 0:
                    discount = 100
                else:
                    discount = int(now_price / old_price * 100)
            else:
                discount = int(discount)
            # 游戏打折信息
            discount_info = {"type": game_type, "id": prime_id, "app_id": app_id, "discount": discount, "old_price": old_price, "now_price": now_price}
            discount_game_list.append(discount_info)
        # 下一页
        pagination_html = search_result_selector.find(".search_pagination .search_pagination_right").html()
        if pagination_html is None:
            if pq(discount_game_pagination_response.content).find("#error_box").length == 1:
                continue
            break
        page_count_find = re.findall(r"<a [\s|\S]*?>([\d]*)</a>", pagination_html)
        if len(page_count_find) > 0:
            total_page_count = max(list(map(int, page_count_find)))
            if page_count < total_page_count:
                page_count += 1
            else:
                break
        else:
            raise CrawlerException("分页信息没有找到\n" + discount_game_pagination_response.content)
    return discount_game_list


# 获取游戏商店首页
def get_game_store_index(game_id):
    game_index_url = f"https://store.steampowered.com/app/{game_id}"
    game_index_response = net.Request(game_index_url, method="GET", cookies=COOKIES).disable_redirect()
    result = {
        "dlc_list": [],  # 游戏下的DLC列表
        "reviewed": False,  # 是否评测过
        "owned": False,  # 是否已拥有
        "restricted": False,  # 是否已资料受限制
        "deleted": False,  # 是否已删除（不再合作）
        "error": "",  # 访问错误信息
    }
    if game_index_response.status == 302:
        if game_index_response.headers.get("Location") == "https://store.steampowered.com/":
            result["deleted"] = True
            return result
        else:
            COOKIES.update(net.get_cookies_from_response_header(game_index_response.headers))
            game_index_response = net.Request(game_index_response.headers.get("Location"), method="GET", cookies=COOKIES)
    if game_index_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(game_index_response.status))
    if pq(game_index_response.content).find(".agegate_birthday_selector").length > 0:
        result["error"] = "需要检测年龄"
        return result
    if pq(game_index_response.content).find("#error_box").length > 0:
        result["error"] = pq(game_index_response.content).find("#error_box span").text()
        return result
    # 所有DLC
    dlc_list_selection = pq(game_index_response.content).find(".game_area_dlc_section a.game_area_dlc_row")
    if dlc_list_selection.length > 0:
        for index in range(dlc_list_selection.length):
            result["dlc_list"].append(dlc_list_selection.eq(index).attr("data-ds-appid"))
    # 是否已拥有
    result["owned"] = pq(game_index_response.content).find(".already_in_library").length == 1
    # 是否已评测
    result["reviewed"] = result["owned"] and pq(game_index_response.content).find("#review_create").length == 0
    # 是否已资料受限制
    result["restricted"] = pq(game_index_response.content).find(".learning_about").length == 1
    return result


# 获取全部已经没有剩余卡牌掉落且还没有收集完毕的徽章详细地址
def get_self_uncompleted_account_badges(account_id):
    # 徽章第一页
    badges_detail_url_list = []
    page_count = 1
    while True:
        console.log(f"开始解析第{page_count}页徽章")
        badges_pagination_url = f"https://steamcommunity.com/profiles/{account_id}/badges/"
        query_data = {"p": page_count}
        badges_pagination_response = net.Request(badges_pagination_url, method="GET", fields=query_data, cookies=COOKIES)
        if badges_pagination_response.status != const.ResponseCode.SUCCEED:
            raise CrawlerException(f"第{page_count}页徽章，{crawler.request_failre(badges_pagination_response.status)}")
        # 徽章div
        badges_selector = pq(badges_pagination_response.content).find(".maincontent .badges_sheet .badge_row")
        for index in range(badges_selector.length):
            badge_selector = badges_selector.eq(index)
            # 闪亮徽章，跳过
            if badge_selector.find(".badge_title").html().find("- 闪亮徽章") >= 0:
                continue
            # 获取game id
            badge_detail_url = badge_selector.find("a.badge_row_overlay").attr("href")
            if badge_detail_url is None:
                raise CrawlerException("徽章信息截取徽章详情地址失败\n" + badge_selector.html())
            # 非游戏徽章
            if badge_detail_url.find("/badges/") >= 0:
                continue
            elif badge_detail_url.find("/gamecards/") == -1:
                raise CrawlerException(f"页面截取的徽章详情地址 {badge_detail_url} 格式不正确")
            # 没有任何当前徽章的卡牌，并且有徽章等级
            if badge_selector.find("span.progress_info_bold").length == 0:
                badge_level_html = badge_selector.find(".badge_info_description div").eq(1).text()
                if not badge_level_html:
                    continue
                badge_level_find = re.findall(r"(\d*) 级,", badge_level_html)
                if len(badge_level_find) == 0:
                    badge_level_find = re.findall(r"Level (\d*),", badge_level_html)
                if len(badge_level_find) == 1 and tool.is_integer(badge_level_find[0]):
                    if int(badge_level_find[0]) == 5:
                        continue
                else:
                    raise CrawlerException("徽章信息截取徽章等级失败\n" + badge_level_html)
            else:
                # 还有掉落的卡牌，跳过
                if badge_selector.find("span.progress_info_bold").html() != "无剩余卡牌掉落":
                    continue
            badges_detail_url_list.append(badge_detail_url)
        # 判断是不是还有下一页
        next_page_selector = pq(badges_pagination_response.content).find("div.profile_paging div.pageLinks a.pagelink:last")
        if next_page_selector.length == 0:
            break
        if page_count >= int(next_page_selector.attr("href").split("?p=")[-1]):
            break
        page_count += 1
    # ['https://steamcommunity.com/profiles/76561198172925593/gamecards/459820/', 'https://steamcommunity.com/profiles/76561198172925593/gamecards/357200/']
    return badges_detail_url_list


# 获取指定徽章仍然缺少的集换式卡牌名字和对应缺少的数量
# badge_detail_url -> https://steamcommunity.com/profiles/76561198172925593/gamecards/459820/
def get_self_account_badge_card(badge_detail_url):
    badge_detail_response = net.Request(badge_detail_url, method="GET", cookies=COOKIES)
    if badge_detail_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(badge_detail_response.status))
    wanted_card_list = {}
    page_selector = pq(badge_detail_response.content)
    # 徽章等级
    badge_selector = page_selector.find(".maincontent .badge_current .badge_info")
    # 有等级
    if badge_selector.find(".badge_info_description").length == 1:
        badge_level_html = badge_selector.find(".badge_info_description div").eq(1).text()
        if not badge_level_html:
            raise CrawlerException("页面截取徽章等级信息失败\n" + badge_detail_response.content)
        badge_level_find = re.findall(r"(\d*) 级,", badge_level_html)
        if len(badge_level_find) != 1:
            badge_level_find = re.findall(r"Level (\d*),", badge_level_html)
        if len(badge_level_find) != 1:
            raise CrawlerException("徽章等级信息徽章等级失败\n" + badge_level_html)
        if not tool.is_integer(badge_level_find[0]):
            raise CrawlerException("徽章等级类型不正确\n" + badge_level_html)
        badge_level = int(badge_level_find[0])
    else:
        badge_level = 0
    wanted_count = MAX_BADGE_LEVEL - badge_level
    # 集换式卡牌div
    cards_selector = page_selector.find(".maincontent .badge_detail_tasks .badge_card_set_card")
    for card_index in range(cards_selector.length):
        card_selector = cards_selector.eq(card_index)
        owned_count_selector = card_selector.find(".badge_card_set_text .badge_card_set_text_qty")
        card_name = card_selector.find(".badge_card_set_text").eq(0).remove(".badge_card_set_text_qty").text()
        if owned_count_selector.length == 1:
            owned_count = owned_count_selector.text().replace("(", "").replace(")", "")
        else:
            owned_count = 0
        if int(owned_count) < wanted_count:
            wanted_card_list[card_name] = wanted_count - int(owned_count)
    # {'Mio': 2}
    return wanted_card_list


# 获取某个游戏的集换式卡牌市场售价
def get_market_game_trade_card_price(game_id):
    market_search_url = "https://steamcommunity.com/market/search/render/"
    query_data = {
        "query": "",
        "count": "20",
        "appid": "753",
        "category_753_Game[0]": f"tag_app_{game_id}",
        "category_753_cardborder[0]": "tag_cardborder_0",
        "norender": "1",
    }
    market_search_response = net.Request(market_search_url, method="GET", fields=query_data, cookies=COOKIES).enable_json_decode().disable_url_encode()
    if market_search_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(market_search_response.status))
    market_item_list = {}
    for item_info in crawler.get_json_value(market_search_response.json_data, "results", type_check=list):
        item_name = crawler.get_json_value(item_info, "hash_name", type_check=str).split("-", 1)[1]
        prince = crawler.get_json_value(item_info, "sell_price_text", type_check=str).replace("¥", "").strip()
        market_item_list[item_name] = prince
    return market_item_list


# 获取指定账号所有库存
def get_account_inventory(account_id):
    # 强制使用英文，避免多语言
    # 库存大批信息 item class id => item count
    item_list = {}
    # 每次请求获取的物品数量
    each_page_inventory_count = 1000
    page_count = 1
    last_assert_id = "0"
    while True:
        console.log(f"开始解析{each_page_inventory_count * (page_count - 1) + 1} ~ {each_page_inventory_count * page_count}的库存")
        api_url = f"https://steamcommunity.com/inventory/{account_id}/753/6"
        query_data = {
            "l": "english",
            "count": each_page_inventory_count,
        }
        if last_assert_id != "0":
            query_data["start_assetid"] = last_assert_id
        api_response = net.Request(api_url, method="GET", fields=query_data).enable_json_decode()
        if api_response.status == 403:
            raise CrawlerException("账号隐私设置中未公开库存详情")
        if api_response.status != const.ResponseCode.SUCCEED:
            raise CrawlerException(crawler.request_failre(api_response.status))
        # 物品数量
        item_count_list = {}
        for asset_info in crawler.get_json_value(api_response.json_data, "assets", type_check=list):
            class_id = crawler.get_json_value(asset_info, "classid", type_check=int)
            if class_id not in item_count_list:
                item_count_list[class_id] = 0
            item_count_list[class_id] += crawler.get_json_value(asset_info, "amount", type_check=int)
        # 物品信息
        for item_info in crawler.get_json_value(api_response.json_data, "descriptions", type_check=list):
            # 物品类
            class_id = crawler.get_json_value(item_info, "classid", type_check=int)
            if class_id not in item_count_list:
                continue
            item_list[class_id] = {}
            # 物品数量
            item_list[class_id]["count"] = item_count_list[class_id]
            # 物品名字
            item_list[class_id]["name"] = crawler.get_json_value(item_info, "name", type_check=str)
            # 物品所在游戏app id
            item_list[class_id]["game_id"] = str(crawler.get_json_value(item_info, "market_fee_app", type_check=int))
            # 物品类型
            for tag_info in item_info["tags"]:
                # Gems / Trading Card / Trading Card / Profile Background / Emoticon
                if crawler.get_json_value(tag_info, "category", type_check=str) == "item_class":
                    item_list[class_id]["type"] = crawler.get_json_value(tag_info, "localized_tag_name", type_check=str)
                    break
        # 下一页起始asset id
        if crawler.get_json_value(api_response.json_data, "more_items", default_value=0, type_check=int) == 1:
            response_assert_id = crawler.get_json_value(api_response.json_data, "last_assetid", default_value=last_assert_id, type_check=str)
            if last_assert_id != response_assert_id:
                last_assert_id = api_response.json_data["last_assetid"]
                page_count += 1
            else:
                break
        else:
            break
    return item_list


# 获取指定账号的所有徽章等级
def get_account_badges(account_id):
    # 强制使用英文，避免多语言
    cookies = {
        "Steam_Language": "english",
        "steamCountry": "US",
    }
    # 徽章等级信息 game id => badge level
    badge_level_list = {}
    page_count = 1
    while True:
        console.log(f"开始解析第{page_count}页徽章")
        badges_pagination_url = f"https://steamcommunity.com/profiles/{account_id}/badges/"
        query_data = {"p": page_count}
        badges_pagination_response = net.Request(badges_pagination_url, method="GET", fields=query_data, cookies=cookies)
        if badges_pagination_response.status != const.ResponseCode.SUCCEED:
            raise CrawlerException(f"第{page_count}页徽章，{crawler.request_failre(badges_pagination_response.status)}")
        badge_list_selector = pq(badges_pagination_response.content).find("div.badge_row")
        if badge_list_selector.length == 0:
            # 如果是隐私账号，会302到主页的，这里只判断页面文字就不判断状态了
            if pq(badges_pagination_response.content).find("div.profile_private_info").length == 1:
                raise CrawlerException("账号隐私设置中未公开游戏详情")
        for badge_index in range(badge_list_selector.length):
            badge_selector = badge_list_selector.eq(badge_index)
            # 获取game id
            badge_detail_url = badge_selector.find('a.badge_row_overlay').attr("href")
            if badge_detail_url is None:
                raise CrawlerException("页面截取徽章详情地址失败\n" + badge_selector.html())
            # 非游戏徽章
            if badge_detail_url.find("/badges/") >= 0:
                continue
            elif badge_detail_url.find("/gamecards/") == -1:
                raise CrawlerException(f"页面截取的徽章详情地址 {badge_detail_url} 格式不正确")
            # https://steamcommunity.com/profiles/76561198172925593/gamecards/230410/
            game_id = url.split_path(badge_detail_url)[3]
            if not tool.is_integer(game_id):
                raise CrawlerException(f"徽章详情地址 {badge_detail_url} 截取游戏id失败")
            # 获取徽章等级
            badge_info_text = badge_selector.find('div.badge.content div.badge_info_description div').eq(1).html()
            if badge_info_text is None:
                raise CrawlerException("页面截取徽章详情失败\n" + badge_selector.html())
            badge_level_find = re.findall(r"Level (\d*),", badge_info_text)
            if len(badge_level_find) != 1:
                raise CrawlerException(f"徽章详情'{badge_info_text}'中截取徽章等级失败")
            badge_level_list[game_id] = int(badge_level_find[0])
        # 判断是不是还有下一页
        next_page_selector = pq(badges_pagination_response.content).find("div.profile_paging div.pageLinks a.pagelink:last")
        if next_page_selector.length == 0:
            break
        if page_count >= int(next_page_selector.attr("href").split("?p=")[-1]):
            break
        page_count += 1
    return badge_level_list


# 获取指定账号的全部游戏id列表
def get_account_owned_app_list(user_id, is_played=False):
    game_index_url = f"https://steamcommunity.com/profiles/{user_id}/games/?tab=all"
    game_index_response = net.Request(game_index_url, method="GET", cookies=COOKIES).set_time_out(net.NET_CONFIG.DOWNLOAD_CONNECTION_TIMEOUT, 120)
    if game_index_response.status != const.ResponseCode.SUCCEED:
        raise CrawlerException(crawler.request_failre(game_index_response.status))
    # 如果是隐私账号，会302到主页的，这里只判断页面文字就不判断状态了
    games_list_string = pq(game_index_response.content).find("#gameslist_config").attr("data-profile-gameslist")
    if not games_list_string:
        raise CrawlerException("页面截取全部游戏信息失败")
    owned_all_game_json_data = tool.json_decode(games_list_string)
    if owned_all_game_json_data is None:
        raise CrawlerException(f"全部游戏信息加载失败\n{games_list_string}")
    app_id_list = []
    for game_data in crawler.get_json_value(owned_all_game_json_data, "rgGames", type_check=list):
        if "appid" not in game_data:
            raise CrawlerException(f"游戏信息{game_data}中'appid'字段不存在")
        # 只需要玩过的游戏
        if is_played and "hours_forever" not in game_data:
            continue
        app_id_list.append(str(game_data["appid"]))
    return app_id_list


class Steam(crawler.Crawler):
    account_id = None

    def __init__(self, need_login=True, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

        # 初始化参数
        sys_config = {
            const.SysConfigKey.SET_PROXY: True,
            const.SysConfigKey.NOT_DOWNLOAD: True,
            const.SysConfigKey.NOT_CHECK_SAVE_DATA: True,
            const.SysConfigKey.APP_CONFIG_PATH: os.path.join(crawler.PROJECT_APP_PATH, "lib", "steam.ini"),
        }
        if need_login:
            sys_config[const.SysConfigKey.GET_COOKIE] = ("store.steampowered.com",)
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        self.data_path = os.path.abspath(os.path.join(crawler.PROJECT_APP_PATH, "data"))
        # 获取account id
        self.account_id_cache = self.new_cache("account.data", const.FileType.TEXT)
        self.account_id = self.get_account_id_from_cache()
        # 已删除的游戏app id
        self.deleted_app_list_cache = self.new_cache("deleted_app.txt", const.FileType.COMMA_DELIMITED)
        # 个人资料受限的游戏app id
        self.restricted_app_list_cache = self.new_cache("restricted_app.txt", const.FileType.COMMA_DELIMITED)
        # 游戏的DLC列表
        self.game_dlc_list_cache = self.new_cache("game_dlc_list.txt", const.FileType.JSON)
        # 个人评测信息缓存
        self.user_review_cache = self.new_cache(f"{self.account_id}_review.txt", const.FileType.JSON)

        self.need_login = need_login
        self.init()

    def init(self):
        global COOKIES

        if self.need_login:
            # 检测是否登录
            login_url = "https://store.steampowered.com/"
            try:
                login_response = net.Request(login_url, method="GET", cookies=self.cookie_value).disable_redirect()
            except KeyboardInterrupt:
                tool.process_exit()
                return
            if login_response.status == 302:
                self.cookie_value.update(net.get_cookies_from_response_header(login_response.headers))
                login_response = net.Request(login_url, method="GET", cookies=self.cookie_value)
            if login_response.status != const.ResponseCode.SUCCEED:
                console.log(f"登录返回code {login_response.status}不正确")
                tool.process_exit()
            if pq(login_response.content).find("#account_pulldown").length != 1:
                console.log("未检测到登录状态")
                tool.process_exit()
            self.cookie_value.update(net.get_cookies_from_response_header(login_response.headers))
            COOKIES = self.cookie_value
            # 强制使用英文
            COOKIES["Steam_Language"] = "english"
            # 年龄
            COOKIES["lastagecheckage"] = "1-January-1971"
        else:
            # 强制使用英文
            COOKIES["Steam_Language"] = "english"
            # 年龄
            COOKIES["lastagecheckage"] = "1-January-1971"
            COOKIES["birthtime"] = "1"

    # 从文件中读取account id，如果不存在提示输入
    def get_account_id_from_cache(self):
        account_id = self.account_id_cache.read()
        while not account_id:
            console_account_id = input(tool.convert_timestamp_to_formatted_time() + " 请输入STEAM账号ID: ")
            while True:
                input_str = input(f"{tool.convert_timestamp_to_formatted_time()} 是否使用输入的STEAM账号ID '{console_account_id}' 是Y(es) / 否N(o) ?")
                input_str = input_str.lower()
                if input_str in ["y", "yes"]:
                    account_id = console_account_id
                    self.account_id_cache.write(account_id)
                    break
                elif input_str in ["n", "no"]:
                    break
        return account_id

    def load_user_review_data(self):
        default_user_review_cache_data = {
            "can_review_lists": [],
            "review_list": [],
        }
        if not os.path.exists(self.user_review_cache.cache_path):
            return default_user_review_cache_data
        user_review_cache_data = self.user_review_cache.read()
        if not tool.check_dict_sub_key(["can_review_lists", "review_list"], user_review_cache_data):
            user_review_cache_data = default_user_review_cache_data
        return user_review_cache_data

    def format_cache_app_info(self):
        user_review_cache_data = self.load_user_review_data()
        if len(user_review_cache_data) == 0:
            return
        deleted_app_list = self.deleted_app_list_cache.read()
        restricted_app_list = self.restricted_app_list_cache.read()
        game_dlc_list = self.game_dlc_list_cache.read()
        # dlc从受限制的应用内删除
        for dlc_id in game_dlc_list:
            if dlc_id in restricted_app_list:
                restricted_app_list.remove(dlc_id)
        # 已经删除的游戏从受限制的应用内删除
        for game_id in deleted_app_list:
            if game_id in restricted_app_list:
                restricted_app_list.remove(game_id)
        # 排序去重
        user_review_cache_data["can_review_lists"] = sorted(list(set(user_review_cache_data["can_review_lists"])))
        user_review_cache_data["review_list"] = sorted(list(set(user_review_cache_data["review_list"])))
        deleted_app_list = sorted(list(set(deleted_app_list)))
        restricted_app_list = sorted(list(set(restricted_app_list)))
        # 保存新的数据
        self.user_review_cache.write(user_review_cache_data)
        self.deleted_app_list_cache.write(deleted_app_list)
        self.restricted_app_list_cache.write(restricted_app_list)
        self.game_dlc_list_cache.write(game_dlc_list)
