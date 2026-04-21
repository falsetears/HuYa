#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import requests

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
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
        self.enable_push = False #True 

        self.cookie = os.getenv('HUYA_COOKIE', '').strip()
        self.rooms = self._parse_rooms(os.getenv('HUYA_ROOMS', ''))
        self.send_key = os.getenv('SEND_KEY', '').strip()

        if not self.cookie:
            print("[ERROR] 未设置 HUYA_COOKIE"); sys.exit(1)
        if not self.rooms:
            self.rooms = [518512, 518511]

        self.driver = self._init_browser()
        self.wait = WebDriverWait(self.driver, 20)

    def _parse_rooms(self, rooms_str):
        return [int(s.strip()) for s in rooms_str.split(',') if s.strip().isdigit()]

    def _init_browser(self):
        chrome_options = Options()
        if not self.debug:
            chrome_options.add_argument('--headless=new')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--mute-audio')
        
        # 仅禁用图片，保留CSS以确保元素定位准确
        prefs = {"profile.managed_default_content_settings.images": 2}
        chrome_options.add_experimental_option("prefs", prefs)
        
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_argument('--window-size=1920,1080')
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.set_page_load_timeout(45)
        return driver

    def send_notification(self):
        if not self.enable_push or not self.send_key or not self.msg_logs: return
        try:
            content = "\n\n".join(self.msg_logs)
            requests.post(f'https://sctapi.ftqq.com/{self.send_key}.send', 
                          data={'text': '虎牙任务报告', 'desp': content}, timeout=15)
            print("✅ 微信推送完成")
        except: pass

    def login(self):
        print("[LOGIN] 登录中...")
        try:
            self.driver.get(cfg.URLS["user_index"])
            time.sleep(3)
            for line in self.cookie.split(';'):
                if '=' not in line: continue
                name, val = line.split('=', 1)
                self.driver.add_cookie({'name': name.strip(), 'value': val.strip(), 'domain': '.huya.com', 'path': '/'})
            self.driver.refresh()
            elem = self.wait.until(EC.presence_of_element_located((By.ID, cfg.LOGIN["huya_num"])))
            print(f"[SUCCESS] 登录成功: {elem.text}")
            return True
        except: return False

    def get_hl_count(self):
        print("[SEARCH] 查询虎粮数量...")
        try:
            self.driver.get(cfg.URLS["pay_index"])
            time.sleep(5)
            pack_tab = self.wait.until(EC.element_to_be_clickable((By.ID, cfg.PAY_PAGE["pack_tab"])))
            self.driver.execute_script("arguments[0].click();", pack_tab)
            time.sleep(2)
            n = self.driver.execute_script('''
                const items = document.querySelectorAll('li[data-num]');
                for (let item of items) {
                    let title = item.title || item.innerText || '';
                    if (title.includes('虎粮')) return item.getAttribute('data-num');
                }
                return 0;
            ''')
            count = int(n) if n and str(n).isdigit() else 0
            print(f"[COUNT] 虎粮数量: {count}")
            return count
        except: return 0

    def daily_check_in(self):
        try:
            badge = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "FanClubHd--UAIAw8vo8FGSKqVwLp7A")))
            self.driver.execute_script("var e=document.createEvent('MouseEvents');e.initMouseEvent('mouseover',true,false,window,0,0,0,0,0,false,false,false,false,0,null);arguments[0].dispatchEvent(e);", badge)
            time.sleep(2)
            checkin_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'Btn--giEMQ9MN7LbLqKHP79BQ') and contains(text(), '打卡')]")))
            self.driver.execute_script("arguments[0].click();", checkin_btn)
            return "✅ 打卡成功"
        except: return "ℹ️ 已打卡"

    def send_to_room(self, room_id, count):
        if count <= 0: return "无粮跳过"
        try:
            lp = self.driver.execute_script('return document.body.getAttribute("data-lp")')
            gid = self.driver.execute_script('return document.body.getAttribute("data-gid")')
            if not lp or not gid: return "❌ 参数缺失"

            self.driver.get(cfg.URLS["gift_tab"].format(lp=lp, gid=gid))
            time.sleep(4)
            items = self.wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, cfg.GIFT["item_class"])))
            hl_item = next((i for i in items if "虎粮" in i.text), None)
            
            if hl_item:
                ActionChains(self.driver).move_to_element(hl_item).perform()
                inp = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, cfg.GIFT["input_css"])))
                
                # --- 强化输入逻辑 ---
                inp.click()
                # 1. 物理清空
                inp.send_keys(Keys.CONTROL + "a")
                inp.send_keys(Keys.BACKSPACE)
                # 2. JS 强制注入数值并触发 input 事件
                self.driver.execute_script("""
                    arguments[0].value = arguments[1];
                    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                """, inp, str(count))
                # 3. 补位操作：输入一个空格再删掉，强制触发生命周期钩子
                inp.send_keys(" ")
                inp.send_keys(Keys.BACKSPACE)
                time.sleep(1)
                
                # 验证数值
                current_val = inp.get_attribute("value")
                print(f"[DEBUG] 准备赠送数量: {current_val}")

                self.driver.find_element(By.CLASS_NAME, cfg.GIFT["send_class"]).click()
                time.sleep(1.5)
                self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, cfg.GIFT["confirm_class"]))).click()
                return f"🚀 送出 {count} 个"
            return "❌ 没粮"
        except Exception as e:
            return f"❌ 异常"

    def run(self):
        try:
            if not self.login(): return False
            total = self.get_hl_count()
            n = len(self.rooms)
            
            for i, rid in enumerate(self.rooms):
                print(f"\n>>> 处理房间: {rid}")
                count = (total // n + (1 if i < (total % n) else 0)) if total > 0 else 0
                
                try:
                    self.driver.get(cfg.URLS["room_base"].format(rid))
                    time.sleep(8) # 增加直播间加载等待
                    
                    gift_res = self.send_to_room(rid, count)
                    checkin_res = self.daily_check_in()
                    
                    log = f"{gift_res}； {checkin_res} (房间 {rid})"
                    print(log)
                    self.msg_logs.append(log)
                except:
                    print(f"[ERR] 房间 {rid} 失败")
                    self.msg_logs.append(f"❌ 房间 {rid} 执行异常")
            return True
        finally:
            if hasattr(self, 'driver'): self.driver.quit()
            self.send_notification()

if __name__ == '__main__':
    HuYaAuto().run()
