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
        self.debug = False
        self.msg_logs = []
        self.enable_push = False 
        
        self.cookie = os.getenv('HUYA_COOKIE', '').strip()
        self.rooms = self._parse_rooms(os.getenv('HUYA_ROOMS', ''))
        self.send_key = os.getenv('SEND_KEY', '').strip()

        if not self.cookie:
            print("[ERROR] 未设置 HUYA_COOKIE"); sys.exit(1)
        
        if not self.rooms:
            self.rooms = [518512, 518511]

        self.driver = self._init_browser()
        self.wait = WebDriverWait(self.driver, 15)

    def _parse_rooms(self, rooms_str):
        if not rooms_str: return []
        return [int(s.strip()) for s in rooms_str.split(',') if s.strip().isdigit()]

    def _init_browser(self):
        chrome_options = Options()
        if not self.debug: chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--mute-audio')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver

    def send_notification(self):
        if not self.enable_push or not self.send_key: return
        try:
            content = "\n\n".join(self.msg_logs)
            requests.post(f'https://sctapi.ftqq.com/{self.send_key}.send', data={'text': '虎牙任务报告', 'desp': content}, timeout=10)
        except: pass

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
        self.driver.get(cfg.URLS["pay_index"])
        time.sleep(5)
        try:
            pack_tab = self.wait.until(EC.element_to_be_clickable((By.ID, cfg.PAY_PAGE["pack_tab"])))
            self.driver.execute_script("arguments[0].click();", pack_tab)
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

    def send_to_room_in_situ(self, rid, count):
        """终极修复版：双重点击锁死 + 异步请求保护"""
        if count <= 0: return "无粮跳过"
        try:
            # 1. 抓取参数
            self.driver.get(cfg.URLS["room_base"].format(rid))
            time.sleep(6)
            lp = self.driver.execute_script('return document.body.getAttribute("data-lp")')
            gid = self.driver.execute_script('return document.body.getAttribute("data-gid")')
            if not lp or not gid: return "❌ 参数缺失"

            # 2. 进入专用接口
            self.driver.get(cfg.URLS["gift_tab"].format(lp=lp, gid=gid))
            time.sleep(5)

            # 3. 寻找虎粮并第一次点击（激活输入框）
            items = self.wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, cfg.GIFT["item_class"])))
            hu_liang = next((i for i in items if "虎粮" in i.text), None)
            if not hu_liang: return "❌ 接口无虎粮"
            
            self.driver.execute_script("arguments[0].scrollIntoView();", hu_liang)
            self.driver.execute_script("arguments[0].click();", hu_liang)
            time.sleep(1)

            # 4. 填入数量并强制触发页面响应
            inp = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, cfg.GIFT["input_css"])))
            self.driver.execute_script("arguments[0].value = '';", inp)
            inp.send_keys(str(count))
            time.sleep(0.5)
            inp.send_keys(Keys.TAB) # 换焦点触发 React/Vue 的变更监听
            
            # 5. 第二次点击虎粮（再次确认选中状态）
            self.driver.execute_script("arguments[0].click();", hu_liang)
            time.sleep(1)

            # 6. 点击赠送并处理二次确认
            send_btn = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, cfg.GIFT["send_class"])))
            self.driver.execute_script("arguments[0].click();", send_btn)
            
            time.sleep(2)
            # 处理可能的弹窗（使用 JS 捕获隐藏或延迟弹出的确认框）
            self.driver.execute_script(f'''
                let confirm = document.querySelector(".{cfg.GIFT['confirm_class']}");
                if (confirm && confirm.offsetParent !== null) confirm.click();
            ''')

            # 7. 关键：原地等待网络请求完成，不立即跳转
            print(f"  [WAIT] 等待房间 {rid} 请求结算...")
            time.sleep(7) 
            
            return f"🚀 送出 {count} 个"
        except Exception as e:
            return f"❌ 过程异常"

    def daily_check_in(self, rid):
        try:
            self.driver.get(cfg.URLS["room_base"].format(rid))
            time.sleep(7)
            badge = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "FanClubHd--UAIAw8vo8FGSKqVwLp7A")))
            self.driver.execute_script("var e=document.createEvent('MouseEvents');e.initMouseEvent('mouseover',true,false,window,0,0,0,0,0,false,false,false,false,0,null);arguments[0].dispatchEvent(e);", badge)
            time.sleep(4)
            btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'Btn--giEMQ9MN7LbLqKHP79BQ') and contains(text(), '打卡')]")))
            self.driver.execute_script("arguments[0].click();", btn)
            time.sleep(2)
            return "✅ 打卡成功"
        except: return "ℹ️ 已打卡"

    def run(self):
        print("=" * 40 + "\n[HUYA] 虎牙自动任务启动\n" + "=" * 40)
        try:
            if not self.login(): return
            total = self.get_hl_count()
            if total <= 0:
                print("[DONE] 暂无虎粮")
                return
                
            for i, rid in enumerate(self.rooms):
                num = (total // len(self.rooms) + (1 if i < (total % len(self.rooms)) else 0))
                print(f"\n>>> 房间: {rid} (目标: {num})")
                
                # 改动点：送礼之后增加足够的停顿
                g_res = self.send_to_room_in_situ(rid, num)
                c_res = self.daily_check_in(rid)
                
                msg = f"{g_res}； {c_res} (房间 {rid})"
                print(f"结果: {msg}")
                self.msg_logs.append(msg)
                time.sleep(5) # 房间间歇
                
        finally:
            if hasattr(self, 'driver'): self.driver.quit()
            self.send_notification()

if __name__ == '__main__':
    HuYaAuto().run()
