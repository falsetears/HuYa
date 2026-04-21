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
        
        # 按照要求，默认关闭推送开关
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
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver

    def send_notification(self):
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
        """强制 UI 唤醒补强版：使用 JS 驱动点击并增加错误原因打印"""
        if count <= 0: return "无粮跳过"
        try:
            # 1. 唤醒包裹面板 (JS 强制点击)
            try:
                self.driver.execute_script("document.querySelector('#player-package-btn').click();")
                time.sleep(2.5)
            except Exception as e:
                print(f"  [DEBUG] 唤醒包裹失败: {str(e)[:50]}")
                return "❌ 唤醒包裹失败"

            # 2. 选中虎粮 (JS 遍历点击)
            hl_found = self.driver.execute_script('''
                var items = document.querySelectorAll(".m-gift-item, .gift-item");
                for (let item of items) {
                    if (item.innerText.includes("虎粮")) {
                        item.click();
                        return true;
                    }
                }
                return false;
            ''')
            if not hl_found:
                print("  [DEBUG] 面板中未定位到虎粮元素")
                return "❌ 未找到虎粮"
            time.sleep(1)

            # 3. 注入数量 (强制 Focus 后赋值)
            set_success = self.driver.execute_script(f'''
                var inp = document.querySelector("input.z-cur[placeholder*='自定义']");
                if (inp) {{
                    inp.focus();
                    inp.value = "{count}";
                    inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return true;
                }}
                return false;
            ''')
            if not set_success:
                print("  [DEBUG] 未定位到自定义数量输入框")
            time.sleep(1)

            # 4. 赠送 (JS 强制点击)
            did_click_send = self.driver.execute_script('''
                var btn = document.querySelector(".c-send, .btn-send");
                if (btn) {
                    btn.click();
                    return true;
                }
                return false;
            ''')
            
            if not did_click_send:
                print("  [DEBUG] 未定位到赠送按钮")
                return "❌ 赠送按钮失效"

            time.sleep(2)
            return f"🚀 送出 {count} 个"
        except Exception as e:
            print(f"  [DEBUG] 运行异常: {str(e)[:100]}")
            return "❌ 送礼失败"

    def daily_check_in(self):
        try:
            badge = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "FanClubHd--UAIAw8vo8FGSKqVwLp7A")))
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
            self.send_notification()

if __name__ == '__main__':
    HuYaAuto().run()
