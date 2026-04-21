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
        self.debug = ""
        self.msg_logs = []
        self.enable_push = True 

        self.cookie = os.getenv('HUYA_COOKIE', '').strip()
        self.rooms = self._parse_rooms(os.getenv('HUYA_ROOMS', ''))
        self.send_key = os.getenv('SEND_KEY', '').strip()

        if not self.cookie:
            print("[ERROR] 未设置 HUYA_COOKIE"); sys.exit(1)
        if not self.rooms:
            self.rooms = [518512, 518511]

        self.driver = self._init_browser()
        self.wait = WebDriverWait(self.driver, 25) # 稍微增加等待上限

    def _parse_rooms(self, rooms_str):
        return [int(s.strip()) for s in rooms_str.split(',') if s.strip().isdigit()]

    def _init_browser(self):
        chrome_options = Options()
        if not self.debug: chrome_options.add_argument('--headless=new')
        
        chrome_options.page_load_strategy = 'none'
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--mute-audio')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.set_page_load_timeout(120)
        return driver

    def send_notification(self):
        if not self.enable_push or not self.send_key or not self.msg_logs: return
        try:
            content = "\n\n".join([line for line in self.msg_logs if line.strip()])
            requests.post(f'https://sctapi.ftqq.com/{self.send_key}.send', 
                          data={'text': '虎牙任务汇总报告', 'desp': content}, timeout=10)
            print("✅ 微信推送完成")
        except: pass

    def login(self):
        print("[LOGIN] 注入登录凭证...")
        self.driver.get(cfg.URLS["user_index"])
        time.sleep(5)
        for line in self.cookie.split(';'):
            if '=' not in line: continue
            name, val = line.split('=', 1)
            try: self.driver.add_cookie({'name': name.strip(), 'value': val.strip(), 'domain': '.huya.com', 'path': '/'})
            except: continue
        self.driver.refresh()
        try:
            self.wait.until(EC.presence_of_element_located((By.ID, cfg.LOGIN["huya_num"])))
            print("[SUCCESS] 登录成功")
            return True
        except:
            print("[ERROR] 登录超时"); return False

    def get_hl_count(self):
        """适配 'player-package-btn' 的查询逻辑"""
        print("[SEARCH] 正在通过“包裹”面板查询虎粮...")
        self.driver.get("https://pay.huya.com/index.html")
        time.sleep(10) 
        
        try:
            # 1. 精准点击“包裹”按钮
            try:
                # 优先使用你提供的 ID
                tab = self.wait.until(EC.element_to_be_clickable((By.ID, "player-package-btn")))
                self.driver.execute_script("arguments[0].click();", tab)
            except:
                # 备用方案：通过文本“包裹”
                tab = self.driver.find_element(By.XPATH, "//p[contains(text(), '包裹')]/..")
                self.driver.execute_script("arguments[0].click();", tab)
            
            print("[INFO] 已展开包裹面板，等待数据渲染...")
            time.sleep(5)

            # 2. 增强版 JS 穿透提取
            n = self.driver.execute_script("""
                const items = document.querySelectorAll('li');
                for (let x of items) {
                    let fullText = (x.title || x.innerText || '').trim();
                    if (fullText.includes('虎粮')) {
                        // 1. 尝试 data-num 属性
                        let dNum = x.getAttribute('data-num');
                        if (dNum && !isNaN(dNum)) return dNum;
                        
                        // 2. 尝试从文本中匹配数字
                        let match = fullText.match(/\\d+/);
                        if (match) return match[0];
                    }
                }
                return 0;
            """)
            
            count = int(n) if n and str(n).isdigit() else 0
            print(f"[COUNT] 最终识别结果: {count}")
            return count
        except Exception as e:
            print(f"[WARN] 查询异常: {e}"); return 0

    def daily_check_in(self, room_id):
        try:
            badge = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "FanClubHd--UAIAw8vo8FGSKqVwLp7A")))
            self.driver.execute_script("var e=document.createEvent('MouseEvents');e.initMouseEvent('mouseover',true,false,window,0,0,0,0,0,false,false,false,false,0,null);arguments[0].dispatchEvent(e);", badge)
            time.sleep(3)
            # 点击打卡按钮 (包含文本“打卡”)
            checkin_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'Btn--giEMQ9MN7LbLqKHP79BQ') and contains(text(), '打卡')]")))
            self.driver.execute_script("arguments[0].click();", checkin_btn)
            return "✅ 打卡成功"
        except: 
            return "ℹ️ 已打卡或无需打卡"

    def _execute_send_gift(self, room_id, count):
        if count <= 0: return "无粮跳过"
        try:
            lp = self.driver.execute_script('return document.body.getAttribute("data-lp")')
            gid = self.driver.execute_script('return document.body.getAttribute("data-gid")')
            if not lp or not gid: return "❌ 参数缺失"

            self.driver.get(cfg.URLS["gift_tab"].format(lp=lp, gid=gid))
            time.sleep(5)
            items = self.wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, cfg.GIFT["item_class"])))
            hl_icon = next((i for i in items if "虎粮" in i.text), None)
            
            if hl_icon:
                ActionChains(self.driver).move_to_element(hl_icon).perform()
                inp = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, cfg.GIFT["input_css"])))
                # 注入数值并触发 Event
                self.driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', {bubbles:true}));", inp, str(count))
                time.sleep(1)
                
                send_btn = self.driver.find_element(By.CLASS_NAME, cfg.GIFT["send_class"])
                self.driver.execute_script("arguments[0].click();", send_btn)
                time.sleep(1.5)
                confirm = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, cfg.GIFT["confirm_class"])))
                self.driver.execute_script("arguments[0].click();", confirm)
                return f"🚀 送出 {count} 个"
            return "❌ 没找到虎粮"
        except Exception as e: return f"❌ 送礼异常: {str(e)[:15]}"

    def run(self):
        try:
            if not self.login(): return False
            total_hl = self.get_hl_count()
            
            # 如果依然为 0，且不是因为真的没粮，脚本会按 0 粮逻辑运行（仅打卡）
            n = len(self.rooms)
            for i, rid in enumerate(self.rooms):
                print(f"\n>>> 房间 {rid}")
                count = (total_hl // n + (1 if i < (total_hl % n) else 0)) if total_hl > 0 else 0
                
                self.driver.get(cfg.URLS["room_base"].format(rid))
                time.sleep(8)
                
                # 执行送礼逻辑
                gift_res = self._execute_send_gift(rid, count)
                
                # 执行打卡逻辑
                self.driver.get(cfg.URLS["room_base"].format(rid))
                time.sleep(6)
                checkin_res = self.daily_check_in(rid)
                
                res_str = f"房间 {rid}: {gift_res} | {checkin_res}"
                print(res_str)
                self.msg_logs.append(res_str)

            return True
        finally:
            if hasattr(self, 'driver'): self.driver.quit()
            self.send_notification()

if __name__ == '__main__':
    HuYaAuto().run()
