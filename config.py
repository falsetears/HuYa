#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一配置文件：选择器、URL、延时
"""

# 登录
LOGIN = {
    "huya_num": "huyaNum",
}

# 充值背包
PAY_PAGE = {
    "pack_tab": "packTab",
    "hl_item_title": "个虎粮",
}

# 礼物相关（全部抽离，无硬编码）
GIFT = {
    "item_class": "m-gift-item",
    "input_css": "input[type='number'][placeholder='自定义']",
    "send_class": "c-send",
    "confirm_class": "btn-success",
}

# URL
URLS = {
    "user_index": "https://i.huya.com/",
    "room_base": "https://huya.com/{}",
    "pay_index": "https://hd.huya.com/pay/index.html?source=web",
    "gift_tab": "https://hd.huya.com/web/webPackageV2/index.html?lp={lp}&gid={gid}"
}

# 延时
TIMING = {
    "implicit_wait": 2,
    "page_load_wait": 5,    # 从 2 改成 4
    "room_enter_wait": 5,   # 从 2 改成 4
}