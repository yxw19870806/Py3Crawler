# -*- coding:UTF-8  -*-
"""
astats相关数据解析爬虫
http://astats.astats.nl/astats/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import const, console, net, tool


# 获取指定游戏是否存在无效成就
def get_game_invalid_achievements(game_id):
    game_index_url = "http://astats.astats.nl/astats/Steam_Game_Info.php"
    query_data = {"AppID": game_id}
    game_index_response = net.Request(game_index_url, method="GET", fields=query_data)
    if game_index_response.status != const.ResponseCode.SUCCEED:
        console.log(f"游戏{game_id}访问失败")
        tool.process_exit()
    # game id 不存在
    if game_index_response.content.find("This game cannot be found in the database.") >= 0:
        return
    achievement_text = tool.find_sub_string(game_index_response.content, '<span class="GameInfoBoxRow">Achievements</span><br>', "</td>")
    # 没有成就
    if not achievement_text:
        return
    achievement_text = achievement_text.strip()
    if not tool.is_integer(achievement_text):
        invalid_achievement_text = tool.find_sub_string(achievement_text, '<font color="#FF0000">', "</font>")
        if invalid_achievement_text:
            console.log(f"游戏{game_id}存在无效成就：{invalid_achievement_text}")
        else:
            console.log(f"游戏{game_id}存在未知成就文字：{invalid_achievement_text}")
