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
        self.debug = False
        self.msg_logs = []
        
        # 1. 按照要求，默认关闭推送开关
        self.enable_push = False  
        
        # 环境变量获取
        self.cookie = os.getenv('HUYA_COOKIE', '').strip()
        self.rooms = self._parse_rooms(os.getenv('HUYA_ROOMS', ''))
        self.send_key = os.getenv('SEND_KEY', '').strip()

        if not self.cookie:
            print("[ERROR] 未设置 HUYA_COOKIE"); sys.exit(1)
        
        if not self.rooms:
            print("[WARN] 未设置房间号，使用默认房间")
            self.rooms = [518512, 518511]

        self.driver = self._init_browser()
        self.wait = WebDriverWait(self.driver, 15)

    def _parse_rooms(self, rooms_str):
        if not rooms_str: return []
        rooms = []
        for s in rooms_str.split(','):
            s = s.strip()
            if s.isdigit():
                rooms.append(int(s))
        return rooms

    def _init_browser(self):
        chrome_options = Options()
        if not self.debug:
            chrome_options.add_argument('--headless=new')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--mute-audio')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        print("[START] 启动浏览器")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.set_page_load_timeout(50)
        # 防检测注入
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver

    def send_notification(self):
        """推送逻辑"""
        # 严格遵守开关状态
        if not self.enable_push or not self.send_key:
            return
            
        if not self.msg_logs:
            return

        try:
            content = "\n\n".join(self.msg_logs)
            url = f'https://sctapi.ftqq.com/{self.send_key}.send'
            requests.post(url, data={'text': '虎牙任务报告', 'desp': content}, timeout=10)
            print("[PUSH] 通知已发送")
        except:
            pass

    def login(self):
        print("[LOGIN] 正在登录...")
        try:
            self.driver.get(cfg.URLS["user_index"])
            time.sleep(2)
            for line in self.cookie.split(';'):
                if '=' not in line: continue
                name, val = line.split('=', 1)
                self.driver.add_cookie({
                    'name': name.strip(), 
                    'value': val.strip(), 
                    'domain': '.huya.com', 
                    'path': '/'
                })
            self.driver.refresh()
            self.wait.until(EC.presence_of_element_located((By.ID, cfg.LOGIN["huya_num"])))
            print("[SUCCESS] 登录成功")
            return True
        except: 
            print("[ERROR] 登录验证失败")
            return False

    def get_hl_count(self):
        """原脚本优秀的异步轮询查找逻辑"""
        print("[SEARCH] 正在查询虎粮数量...")
        self.driver.get(cfg.URLS["pay_index"])
        time.sleep(3)
        try:
            pack_tab = self.wait.until(EC.element_to_be_clickable((By.ID, cfg.PAY_PAGE["pack_tab"])))
            self.driver.execute_script("arguments[0].click();", pack_tab)
        except:
            return 0

        n = self.driver.execute_script('''
            let maxWait = 20;
            async function findHuliang() {
                const items = document.querySelectorAll('li[data-num]');
                for (let item of items) {
                    let title = item.title || item.innerText || '';
                    if (title.includes('虎粮')) return item.getAttribute('data-num');
                }
                return null;
            }
            return (async () => {
                while(maxWait-- > 0) {
                    let res = await findHuliang();
                    if(res) return res;
                    await new Promise(r => setTimeout(r, 250));
                }
                return 0;
            })();
        ''')
        count = int(n) if n and str(n).isdigit() else 0
        print(f"[COUNT] 识别到虎粮: {count}")
        return count

    def send_to_room_in_situ(self, count):
        """结合 JS 填入，解决 Headless 模式下的悬停难题"""
        if count <= 0: return "无粮跳过"
        try:
            # 1. 点击包裹
            pack_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "player-package-btn")))
            self.driver.execute_script("arguments[0].click();", pack_btn)
            time.sleep(2)

            # 2. 选中虎粮
            hl_xpath = "//div[contains(@class, 'm-gift-item')]//p[text()='虎粮']/.."
            hl_item = self.wait.until(EC.presence_of_element_located((By.XPATH, hl_xpath)))
            self.driver.execute_script("arguments[0].click();", hl_item)
            time.sleep(1)

            # 3. JS 强制赋值数量并触发事件
            self.driver.execute_script(f'''
                var input = document.querySelector("input.z-cur[placeholder='自定义']");
                if (input) {{
                    input.value = "{count}";
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            ''')
            
            # 4. 点击赠送按钮
            send_btn = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "c-send")))
            self.driver.execute_script("arguments[0].click();", send_btn)
            time.sleep(2)
            
            return f"🚀 送出 {count} 个"
        except Exception:
            return "❌ 送礼失败"

    def daily_check_in(self):
        """现脚本打卡逻辑"""
        try:
            badge = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "FanClubHd--UAIAw8vo8FGSKqVwLp7A")))
            # JS 模拟悬停，防止无头模式失效
            self.driver.execute_script("var e=document.createEvent('MouseEvents');e.initMouseEvent('mouseover',true,false,window,0,0,0,0,0,false,false,false,false,0,null);arguments[0].dispatchEvent(e);", badge)
            time.sleep(2.5)
            btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'Btn--giEMQ9MN7LbLqKHP79BQ') and contains(text(), '打卡')]")))
            self.driver.execute_script("arguments[0].click();", btn)
            return "✅ 打卡成功"
        except:
            return "ℹ️ 已打卡"

    def run(self):
        print("=" * 40)
        print("[HUYA] 虎牙虎粮任务启动")
        print("=" * 40)
        
        try:
            if not self.login(): return False
            
            total_hl = self.get_hl_count()
            n_rooms = len(self.rooms)
            
            for i, rid in enumerate(self.rooms):
                num = (total_hl // n_rooms + (1 if i < (total_hl % n_rooms) else 0)) if total_hl > 0 else 0
                print(f"\n>>> 房间: {rid} (分配: {num})")
                
                try:
                    self.driver.get(cfg.URLS["room_base"].format(rid))
                    time.sleep(10) 
                    
                    g_res = self.send_to_room_in_situ(num)
                    c_res = self.daily_check_in()
                    
                    res_msg = f"{g_res}； {c_res} (房间 {rid})"
                    print(f"结果: {res_msg}")
                    self.msg_logs.append(res_msg)
                except Exception:
                    self.msg_logs.append(f"❌ 房间 {rid} 异常")
                
                time.sleep(2)
                
            print(f"\n[DONE] 流程结束")
            return True

        finally:
            if hasattr(self, 'driver'):
                self.driver.quit()
                print("[EXIT] 浏览器已关闭")
            # 只有开关为 True 时才会推送
            self.send_notification()

if __name__ == '__main__':
    HuYaAuto().run()
