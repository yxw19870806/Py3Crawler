# -*- coding:UTF-8  -*-
"""
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from common import *

if __name__ == "__main__":
    attribute_list_file_path = os.path.join("attribute.txt")
    attribute_list = file.read_file(attribute_list_file_path).split("\t")

    equip_list_file_path = os.path.join("equip.txt")
    equip_info_list = []
    for equip_info_string in file.read_file(equip_list_file_path, file.READ_FILE_TYPE_LINE):
        equip_info = equip_info_string.split("\t")
        equip_name = equip_info[0]
        equip_level = equip_info[1]
        equip_attr = {}
        if len(equip_info) >= 4 and equip_info[2]:
            if equip_info[2] not in attribute_list:
                print(equip_info[2])
            equip_attr[equip_info[2]] = equip_info[3]
        if len(equip_info) >= 6 and equip_info[4]:
            if equip_info[4] not in attribute_list:
                print(equip_info[4])
            equip_attr[equip_info[4]] = equip_info[5]
        if len(equip_info) >= 8 and equip_info[6]:
            if equip_info[6] not in attribute_list:
                print(equip_info[6])
            equip_attr[equip_info[6]] = equip_info[7]
        if len(equip_info) >= 10:
            equip_attr[equip_info[8]] = equip_info[9]
        equip_info_list.append({
            'name': equip_name,
            'level': equip_level,
            'attribute': equip_attr,
        })

    for equip_info in equip_info_list:
        result = [
            equip_info['name'],
            equip_info['level']
        ]
        for attribute in attribute_list:
            if attribute in equip_info['attribute']:
                result.append(equip_info['attribute'][attribute])
            else:
                result.append("")
        print("\t".join(result))
