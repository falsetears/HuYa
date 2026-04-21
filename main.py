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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

import config as cfg

class HuYaAuto:
    def __init__(self):
        # ============ 配置项 ============
        self.debug = False  # 开启调试
        self.enable_push = True  # 推送开关已开启
        # ================================
        
        self.msg_logs = []
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
        if not self.debug: 
            chrome_options.add_argument('--headless=new')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        return driver

    def send_notification(self):
        """新增：Server酱推送方法"""
        if not self.enable_push or not self.send_key:
            return
            
        print("[PUSH] 正在发送推送通知...")
        try:
            content = "\n\n".join(self.msg_logs)
            url = f"https://sctapi.ftqq.com/{self.send_key}.send"
            data = {
                "title": "虎牙自动任务报告",
                "desp": content
            }
            res = requests.post(url, data=data, timeout=10)
            if res.status_code == 200:
                print("[SUCCESS] 推送发送成功")
            else:
                print(f"[FAILED] 推送失败，状态码: {res.status_code}")
        except Exception as e:
            print(f"[ERROR] 推送异常: {e}")

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
        except Exception as e:
            print(f"[ERROR] 登录失败: {e}")
            return False

    def get_hl_count(self):
        print("[SEARCH] 正在查询虎粮数量...")
        self.driver.get(cfg.URLS["pay_index"])
        time.sleep(4)
        try:
            pack_tab = self.wait.until(EC.element_to_be_clickable((By.ID, cfg.PAY_PAGE["pack_tab"])))
            pack_tab.click()
            time.sleep(2)
            n = self.driver.execute_script('''
                const items = document.querySelectorAll('li[data-num]');
                for (let item of items) {
                    let title = item.title || item.innerText || '';
                    if (title.includes('虎粮')) return item.getAttribute('data-num');
                }
                return 0;
            ''')
            count = int(n) if n else 0
            print(f"[COUNT] 识别到虎粮: {count}")
            return count
        except: 
            print("[ERROR] 虎粮数量识别失败")
            return 0

    def send_to_room_in_situ(self, rid, count):
        if count <= 0: return "无粮跳过"
        try:
            self.driver.get(cfg.URLS["room_base"].format(rid))
            time.sleep(5)
            lp = self.driver.execute_script('return document.body.getAttribute("data-lp")')
            gid = self.driver.execute_script('return document.body.getAttribute("data-gid")')
            if not lp or not gid: return "❌ 获取参数失败"

            self.driver.get(cfg.URLS["gift_tab"].format(lp=lp, gid=gid))
            time.sleep(4)

            items = self.wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, cfg.GIFT["item_class"])))
            hu_liang = next((i for i in items if "虎粮" in i.text), None)
            if not hu_liang: return "❌ 未找到虎粮"

            ActionChains(self.driver).move_to_element(hu_liang).pause(1).click().perform()
            time.sleep(1)

            inp = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, cfg.GIFT["input_css"])))
            inp.click()
            inp.clear()
            inp.send_keys(str(count))
            time.sleep(1)

            send_btn = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, cfg.GIFT["send_class"])))
            send_btn.click()
            time.sleep(1)

            try:
                confirm = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, cfg.GIFT["confirm_class"])))
                confirm.click()
            except:
                pass

            print(f"  [WAIT] 正在结算房间 {rid}，原地等待 12 秒...")
            time.sleep(12) 
            return f"🚀 送出 {count} 个"
        except Exception as e:
            if self.debug: print(f"  [DEBUG] 送礼异常: {e}")
            return "❌ 过程异常"

    def daily_check_in(self, rid):
        try:
            self.driver.get(cfg.URLS["room_base"].format(rid))
            time.sleep(6)
            badge = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "FanClubHd--UAIAw8vo8FGSKqVwLp7A")))
            ActionChains(self.driver).move_to_element(badge).perform()
            time.sleep(3)
            btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '打卡')]")))
            btn.click()
            return "✅ 打卡成功"
        except: return "ℹ️ 已打卡"

    def run(self):
        print("=" * 40 + f"\n[HUYA] 虎牙自动任务启动 (Debug: {self.debug})\n" + "=" * 40)
        try:
            if not self.login(): 
                self.msg_logs.append("登录失败")
                return
            total = self.get_hl_count()
            self.msg_logs.append(f"今日虎粮总数: {total}")
            
            if total <= 0:
                print("[DONE] 暂无虎粮，结束运行")
                return
                
            for i, rid in enumerate(self.rooms):
                num = (total // len(self.rooms) + (1 if i < (total % len(self.rooms)) else 0))
                print(f"\n>>> 房间: {rid} (目标数量: {num})")
                
                g_res = self.send_to_room_in_situ(rid, num)
                c_res = self.daily_check_in(rid)
                
                msg = f"房间 {rid}: {g_res}； {c_res}"
                print(f"结果: {msg}")
                self.msg_logs.append(msg)
                time.sleep(2)
        finally:
            # 无论是否运行成功，最后都尝试推送并关闭浏览器
            if self.enable_push:
                self.send_notification()
            if hasattr(self, 'driver'): 
                self.driver.quit()

if __name__ == '__main__':
    HuYaAuto().run()
