#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import requests

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

import config as cfg

class HuYaAuto:
    def __init__(self):
        self.debug = ""
        self.msg_logs = []
        self.enable_push = False  
        
        self.cookie = os.getenv('HUYA_COOKIE', '').strip()
        self.rooms = self._parse_rooms(os.getenv('HUYA_ROOMS', ''))
        self.send_key = os.getenv('SEND_KEY', '').strip()

        if not self.cookie:
            print("[ERROR] 未设置 HUYA_COOKIE"); sys.exit(1)
        
        self.driver = self._init_browser()
        self.wait = WebDriverWait(self.driver, 15)

    def _parse_rooms(self, rooms_str):
        if not rooms_str: return [518512, 518511]
        return [int(s.strip()) for s in rooms_str.split(',') if s.strip().isdigit()]

    def _init_browser(self):
        chrome_options = Options()
        if not self.debug: chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--mute-audio')
        chrome_options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--window-size=1920,1080')
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.set_page_load_timeout(50)
        return driver

    def login(self):
        print("[LOGIN] 正在登录...")
        try:
            self.driver.get(cfg.URLS["user_index"])
            time.sleep(2)
            for line in self.cookie.split(';'):
                if '=' not in line: continue
                name, val = line.split('=', 1)
                self.driver.add_cookie({'name': name.strip(), 'value': val.strip(), 'domain': '.huya.com', 'path': '/'})
            self.driver.refresh()
            self.wait.until(EC.presence_of_element_located((By.ID, cfg.LOGIN["huya_num"])))
            print("[SUCCESS] 登录成功")
            return True
        except: return False

    def get_hl_count(self):
        print("[SEARCH] 正在查询虎粮数量...")
        try:
            self.driver.get(cfg.URLS["pay_index"])
            time.sleep(5)
            btn = self.wait.until(EC.presence_of_element_located((By.ID, cfg.PAY_PAGE["pack_tab"])))
            self.driver.execute_script("arguments[0].click();", btn)
            time.sleep(3)
            n = self.driver.execute_script('''
                const items = document.querySelectorAll('li[data-num]');
                for (let item of items) {
                    if ((item.title || item.innerText).includes('虎粮')) return item.getAttribute('data-num');
                }
                return 0;
            ''')
            count = int(n) if n else 0
            print(f"[COUNT] 识别到虎粮: {count}")
            return count
        except: return 0

    def send_to_room_in_situ(self, count):
        """优化后的送礼：JS 强制显式化流程"""
        if count <= 0: return "无粮跳过"
        try:
            # 1. 点击包裹
            pack_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "player-package-btn")))
            self.driver.execute_script("arguments[0].click();", pack_btn)
            time.sleep(2)

            # 2. 选中虎粮 (通过 JS 点击，确保选中状态)
            hl_item = self.wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'm-gift-item')]//p[text()='虎粮']/..")))
            self.driver.execute_script("arguments[0].click();", hl_item)
            time.sleep(1)

            # 3. 使用 JS 强制填入数量
            # 逻辑：强行寻找输入框，即使它被隐藏了也直接修改其 value
            success = self.driver.execute_script(f'''
                var input = document.querySelector("input.z-cur[placeholder='自定义']");
                if (input) {{
                    input.value = "{count}";
                    // 触发 input 事件让页面感知到数值变化
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return true;
                }}
                return false;
            ''')
            
            if success:
                print(f"  [DEBUG] JS 已成功填入数量: {count}")
            else:
                print("  [DEBUG] JS 未能定位到输入框")

            # 4. 点击赠送
            send_btn = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "c-send")))
            self.driver.execute_script("arguments[0].click();", send_btn)
            time.sleep(2)
            
            return f"🚀 送出 {count} 个"
        except Exception as e:
            print(f"  [DEBUG] 送礼过程异常: {str(e)[:50]}")
            return "❌ 送礼失败"

    def daily_check_in(self):
        try:
            badge = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "FanClubHd--UAIAw8vo8FGSKqVwLp7A")))
            self.driver.execute_script("var e=document.createEvent('MouseEvents');e.initMouseEvent('mouseover',true,false,window,0,0,0,0,0,false,false,false,false,0,null);arguments[0].dispatchEvent(e);", badge)
            time.sleep(2)
            btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'Btn--giEMQ9MN7LbLqKHP79BQ') and contains(text(), '打卡')]")))
            self.driver.execute_script("arguments[0].click();", btn)
            return "✅ 打卡成功"
        except: return "ℹ️ 已打卡"

    def run(self):
        try:
            if not self.login(): return
            total_hl = self.get_hl_count()
            
            for i, rid in enumerate(self.rooms):
                n = len(self.rooms)
                num = (total_hl // n + (1 if i < (total_hl % n) else 0)) if total_hl > 0 else 0
                print(f"\n>>> 房间: {rid} (分配: {num})")
                
                try:
                    self.driver.get(cfg.URLS["room_base"].format(rid))
                    time.sleep(10) 
                    
                    g_res = self.send_to_room_in_situ(num)
                    c_res = self.daily_check_in()
                    
                    msg = f"{g_res}； {c_res} (房间 {rid})"
                    print(f"结果: {msg}")
                    self.msg_logs.append(msg)
                except:
                    self.msg_logs.append(f"❌ 房间 {rid} 异常")
        finally:
            if hasattr(self, 'driver'): self.driver.quit()

if __name__ == '__main__':
    HuYaAuto().run()
