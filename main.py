#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虎牙虎粮自动发放 - 精简稳定版（含打卡与推送开关）
"""

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
    """精简稳定版虎牙虎粮自动发放"""

    def __init__(self):
        self.debug = ""
        self.msg_logs = []
        # --- 推送控制开关 ---
        self.enable_push = False 
        self.send_key = os.getenv('SEND_KEY', '').strip()

        if self.debug:
            print("从文件获取 HUYA_COOKIE")
            try:
                with open("cookie", "r", encoding="utf-8") as f:
                    self.cookie = f.read().strip()
            except FileNotFoundError:
                self.cookie = ""
            self.rooms = ["998"]
        else:
            print("从环境变量获取 HUYA_COOKIE")
            self.cookie = os.getenv('HUYA_COOKIE', '').strip()
            self.rooms = self._parse_rooms(os.getenv('HUYA_ROOMS', ''))

        if not self.cookie:
            print("[ERROR] 未设置 HUYA_COOKIE")
            sys.exit(1)

        if not self.rooms:
            print("[WARN] 未设置房间号，使用默认房间")
            self.rooms = [518512, 518511]

        self.driver = self._init_browser()
        self.wait = WebDriverWait(self.driver, 5)

    def _parse_rooms(self, rooms_str):
        rooms = []
        if not rooms_str: return rooms
        for s in rooms_str.split(','):
            s = s.strip()
            if s:
                try:
                    rooms.append(int(s))
                except ValueError:
                    print(f"[WARN] 跳过无效房间号: {s}")
        return rooms

    def _init_browser(self):
        chrome_options = Options()
        if not self.debug:
            chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-images')
        chrome_options.add_argument('--disable-javascript=false')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--window-size=1920,1080')

        print("[START] 启动浏览器")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver

    def send_notification(self):
        """推送逻辑"""
        if not self.enable_push or not self.send_key or not self.msg_logs:
            return
        try:
            content = "\n\n".join(self.msg_logs)
            requests.post(f'https://sctapi.ftqq.com/{self.send_key}.send', 
                          data={'text': '虎牙任务报告', 'desp': content}, timeout=10)
            print("✅ 微信推送完成")
        except:
            pass

    def daily_check_in(self, room_id):
        """新增：在直播间页面打卡"""
        try:
            # 悬停勋章
            badge = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "FanClubHd--UAIAw8vo8FGSKqVwLp7A"))
            )
            self.driver.execute_script("var e=document.createEvent('MouseEvents');e.initMouseEvent('mouseover',true,false,window,0,0,0,0,0,false,false,false,false,0,null);arguments[0].dispatchEvent(e);", badge)
            time.sleep(2)
            # 点击打卡按钮
            btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'Btn--giEMQ9MN7LbLqKHP79BQ') and contains(text(), '打卡')]"))
            )
            self.driver.execute_script("arguments[0].click();", btn)
            return "✅ 打卡成功"
        except:
            return "ℹ️ 已打卡"

    def login(self):
        print("[LOGIN] 登录中")
        self.driver.get(cfg.URLS["user_index"])
        time.sleep(cfg.TIMING["implicit_wait"])
        cnt = 0
        for line in self.cookie.split(';'):
            line = line.strip()
            if '=' not in line: continue
            name, val = line.split('=', 1)
            try:
                self.driver.add_cookie({'name': name.strip(), 'value': val.strip(), 'domain': '.huya.com', 'path': '/'})
                cnt += 1
            except: continue

        print(f"[COOKIE] 已添加 {cnt} 个Cookie")
        self.driver.refresh()
        time.sleep(cfg.TIMING["page_load_wait"])
        try:
            elem = self.wait.until(EC.presence_of_element_located((By.ID, cfg.LOGIN["huya_num"])))
            print(f"[SUCCESS] 登录成功: {elem.text.strip()}")
            return True
        except:
            print("[ERROR] 登录失败")
            return False

    def get_hl_count(self):
        print("[SEARCH] 查询虎粮数量")
        self.driver.get(cfg.URLS["pay_index"])
        time.sleep(3)
        try:
            pack_tab = WebDriverWait(self.driver, 15).until(EC.element_to_be_clickable((By.ID, cfg.PAY_PAGE["pack_tab"])))
            pack_tab.click()
            time.sleep(1.5)
        except:
            print("[WARN] 点击背包标签失败")
            return 0

        n = self.driver.execute_script('''
            let maxWait = 20;
            function findHuliang() {
                const items = document.querySelectorAll('li[data-num]');
                for (let item of items) {
                    let title = item.title || item.innerText || '';
                    if (title.includes('虎粮')) return item.getAttribute('data-num');
                }
                return null;
            }
            return findHuliang() || 0;
        ''')
        hl = int(n) if n and str(n).isdigit() else 0
        print(f"[COUNT] 虎粮数量: {hl}")
        return hl

    def send_to_room(self, room_id, count):
        print(f"[GIFT] 房间 {room_id} 发送 {count} 个")
        if count <= 0: return "跳过"

        try:
            self.driver.get(cfg.URLS["room_base"].format(room_id))
            time.sleep(cfg.TIMING["room_enter_wait"])

            # 记录初始结果
            gift_status = "❌ 失败"
            
            lp = self.driver.execute_script('return document.body.getAttribute("data-lp")')
            gid = self.driver.execute_script('return document.body.getAttribute("data-gid")')

            if lp and gid:
                self.driver.get(cfg.URLS["gift_tab"].format(lp=lp, gid=gid))
                time.sleep(cfg.TIMING["page_load_wait"])
                items = self.wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, cfg.GIFT["item_class"])))
                hu_liang = next((i for i in items if "虎粮" in i.text), None)
                
                if hu_liang:
                    ActionChains(self.driver).move_to_element(hu_liang).pause(1).perform()
                    time.sleep(1)
                    inp = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, cfg.GIFT["input_css"])))
                    inp.click()
                    inp.clear()
                    inp.send_keys(str(count))
                    self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, cfg.GIFT["send_class"]))).click()
                    time.sleep(1)
                    self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, cfg.GIFT["confirm_class"]))).click()
                    gift_status = f"🚀 送出 {count}个"
                    print(f"[SUCCESS] {gift_status}")
            
            # 无论送礼是否因参数失败，都回到房间尝试打卡
            self.driver.get(cfg.URLS["room_base"].format(room_id))
            time.sleep(4)
            checkin_status = self.daily_check_in(room_id)
            
            self.msg_logs.append(f"{gift_status}；{checkin_status} (房间 {room_id})")
            return count if "🚀" in gift_status else 0

        except Exception as e:
            print(f"[CRASH] 房间 {room_id} 异常: {e}")
            self.msg_logs.append(f"❌ 房间 {room_id} 异常")
            return 0

    def run(self):
        success = False
        try:
            if not self.login(): return False
            total = self.get_hl_count()
            if total <= 0:
                print("❌ 暂无虎粮")
                return False

            n = len(self.rooms)
            sent = 0
            for i, rid in enumerate(self.rooms):
                c = (total // n + (1 if i < (total % n) else 0))
                sent += self.send_to_room(rid, c)

            print(f"\n[DONE] 已发送 {sent}/{total}")
            success = sent > 0
            return success
        finally:
            if hasattr(self, 'driver'): self.driver.quit()
            self.send_notification()
            return success

if __name__ == '__main__':
    HuYaAuto().run()
