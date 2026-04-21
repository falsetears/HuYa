#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虎牙虎粮自动发放 - 增强稳定推送版
"""

import os
import sys
import time
import requests  # 用于发送推送通知

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
# 引入显式等待
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

import config as cfg


class HuYaAuto:
    """精简稳定版虎牙虎粮自动发放"""

    def __init__(self):
        self.debug = ""
        self.msg_logs = []  # 用于存储需要推送的消息行

        # 获取配置
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

        # 获取推送 Key
        self.send_key = os.getenv('SEND_KEY', '').strip()

        if not self.cookie:
            print("[ERROR] 未设置 HUYA_COOKIE")
            sys.exit(1)

        if not self.rooms:
            print("[WARN] 未设置房间号，使用默认房间")
            self.rooms = [518512, 518511]

        self.driver = self._init_browser()
        self.wait = WebDriverWait(self.driver, 10)  # 增加全局默认等待时间

    def _parse_rooms(self, rooms_str):
        rooms = []
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
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--mute-audio')
        chrome_options.add_argument('--blink-settings=imagesEnabled=false')
        chrome_options.add_argument('--disable-webrtc')
        chrome_options.page_load_strategy = 'eager'
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--window-size=1280,720')

        print("[START] 启动浏览器")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        driver.set_page_load_timeout(60)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver

    def send_notification(self):
        """发送 Server 酱推送"""
        if not self.send_key:
            print("[PUSH] 未设置 SEND_KEY，跳过通知")
            return
        if not self.msg_logs:
            print("[PUSH] 无有效发放记录，跳过通知")
            return

        title = "虎牙虎粮发放汇总"
        content = "\n\n".join(self.msg_logs)
        push_url = f'https://sctapi.ftqq.com/{self.send_key}.send'
        
        try:
            res = requests.post(push_url, data={'text': title, 'desp': content}, timeout=10)
            if res.status_code == 200:
                print("✅ 推送通知发送成功")
            else:
                print(f"❌ 推送失败: {res.text}")
        except Exception as e:
            print(f"❌ 推送发生异常: {e}")

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
                self.driver.add_cookie({
                    'name': name.strip(), 'value': val.strip(),
                    'domain': '.huya.com', 'path': '/'
                })
                cnt += 1
            except Exception: continue

        print(f"[COOKIE] 已添加 {cnt} 个Cookie")
        self.driver.refresh()
        time.sleep(cfg.TIMING["page_load_wait"])

        try:
            elem = self.wait.until(EC.presence_of_element_located((By.ID, cfg.LOGIN["huya_num"])))
            print(f"[SUCCESS] 登录成功: {elem.text.strip()}")
            return True
        except Exception:
            print("[ERROR] 登录失败")
            return False

    def get_hl_count(self):
        print("[SEARCH] 查询虎粮数量")
        self.driver.get(cfg.URLS["pay_index"])
        time.sleep(3)

        try:
            pack_tab = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.ID, cfg.PAY_PAGE["pack_tab"]))
            )
            pack_tab.click()
            time.sleep(2)
        except Exception:
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
            return (async () => {
                while(maxWait-- > 0) {
                    let res = findHuliang();
                    if(res) return res;
                    await new Promise(r => setTimeout(r, 200));
                }
                return 0;
            })();
        ''')
        hl = int(n) if n and str(n).isdigit() else 0
        print(f"[COUNT] 虎粮数量: {hl}")
        return hl

    def send_to_room(self, room_id, count):
        msg = f"[GIFT] 房间 {room_id} 发送 {count} 个"
        print(msg)
        self.msg_logs.append(msg) # 收集发放记录

        if count <= 0: return 0

        try:
            self.driver.get(cfg.URLS["room_base"].format(room_id))
            # --- 稳定性修复点：进入房间后强制多等 3 秒 ---
            time.sleep(cfg.TIMING["room_enter_wait"] + 3)

            lp = self.driver.execute_script('return document.body.getAttribute("data-lp")')
            gid = self.driver.execute_script('return document.body.getAttribute("data-gid")')

            if not lp or not gid:
                print("[ERROR] 获取房间参数失败")
                return 0

            self.driver.get(cfg.URLS["gift_tab"].format(lp=lp, gid=gid))
            time.sleep(cfg.TIMING["page_load_wait"])

            # 显式等待元素出现
            items = self.wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, cfg.GIFT["item_class"])))
            
            hu_liang = next((i for i in items if "虎粮" in i.text), None)
            if not hu_liang:
                print("[ERROR] 未找到虎粮")
                return 0

            ActionChains(self.driver).move_to_element(hu_liang).pause(1.5).perform()
            
            inp = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, cfg.GIFT["input_css"])))
            inp.click()
            inp.clear()
            inp.send_keys(str(count))

            self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, cfg.GIFT["send_class"]))).click()
            time.sleep(1)
            self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, cfg.GIFT["confirm_class"]))).click()
            
            print(f"[SUCCESS] 赠送成功: {count} 个")
            return count

        except Exception as e:
            print(f"[CRASH] 赠送失败: {e}")
            return 0

    def run(self):
        success = False
        try:
            print("=" * 40)
            print("[HUYA] 虎牙虎粮自动发放")
            print("=" * 40)

            if not self.login(): return False

            total = self.get_hl_count()
            if total <= 0:
                print("❌ 暂无虎粮")
                return False

            n = len(self.rooms)
            per, rem = total // n, total % n
            plan = [(self.rooms[i], per + (1 if i < rem else 0)) for i in range(n)]

            print("\n[SEND] 开始执行发送方案...")
            sent = 0
            for rid, c in plan:
                sent += self.send_to_room(rid, c)

            done_msg = f"[DONE] 完成！已发送 {sent}/{total}"
            print(done_msg)
            self.msg_logs.append(done_msg) # 收集最终结果
            
            success = sent > 0
            return success

        except Exception as e:
            print(f"\n[CRASH] 程序异常: {e}")
            return False
        finally:
            if hasattr(self, 'driver'):
                self.driver.quit()
                print("[EXIT] 浏览器已关闭")
            # 无论成功失败，最后统一尝试推送
            self.send_notification()

def main():
    huya = HuYaAuto()
    res = huya.run()
    sys.exit(0 if res else 1)

if __name__ == '__main__':
    main()
