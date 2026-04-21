#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虎牙虎粮自动发放 + 粉丝团自动打卡 - 最终增强版
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
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

import config as cfg

class HuYaAuto:
    """精简稳定版虎牙虎粮自动发放及打卡"""

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

        # 获取推送 Key (确保与 YAML 中的 SEND_KEY 对应)
        self.send_key = os.getenv('SEND_KEY', '').strip()

        if not self.cookie:
            print("[ERROR] 未设置 HUYA_COOKIE")
            sys.exit(1)

        if not self.rooms:
            print("[WARN] 未设置房间号，使用默认房间")
            self.rooms = [518512, 518511]

        self.driver = self._init_browser()
        self.wait = WebDriverWait(self.driver, 15)  # 增加等待时间提高稳定性

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
        chrome_options.add_argument('--window-size=1920,1080') # 窗口加大，防止侧边栏折叠
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

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
            print("[PUSH] 无有效记录，跳过通知")
            return

        title = "虎牙虎粮发放及打卡汇总"
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
            pack_tab = self.wait.until(EC.element_to_be_clickable((By.ID, cfg.PAY_PAGE["pack_tab"])))
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

    def daily_check_in(self, room_id):
        """精准悬停打卡逻辑"""
        try:
            print(f"[CHECKIN] 尝试房间 {room_id} 打卡...")
            # 使用你提供的精确类名
            FANS_BADGE_CSS = ".FanClubHd--UAIAw8vo8FGSKqVwLp7A"
            CHECKIN_BTN_CSS = ".Btn--giEMQ9MN7LbLqKHP79BQ"

            # 1. 悬停触发弹窗
            badge = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, FANS_BADGE_CSS)))
            actions = ActionChains(self.driver)
            actions.move_to_element(badge).pause(2.0).perform()

            # 2. 点击打卡按钮
            checkin_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, CHECKIN_BTN_CLASS_CSS)))
            # 兼容处理，有时类名前面带点，有时不带，这里直接通过 By.CSS_SELECTOR 配合变量使用
            checkin_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, CHECKIN_BTN_CSS)))
            checkin_btn.click()
            
            msg = f"✅ 房间 {room_id} 粉丝团打卡成功"
            print(msg)
            self.msg_logs.append(msg)
        except Exception:
            print(f"[INFO] 房间 {room_id} 无需打卡或未发现入口")
        finally:
            try:
                # 鼠标移开，防止悬停层遮挡
                ActionChains(self.driver).move_by_offset(-200, 0).perform()
            except: pass

    def send_to_room(self, room_id, count):
        try:
            # 进入房间
            self.driver.get(cfg.URLS["room_base"].format(room_id))
            time.sleep(cfg.TIMING["room_enter_wait"] + 3)

            # A. 先执行送礼
            if count > 0:
                print(f"[GIFT] 房间 {room_id} 准备发送 {count} 个")
                lp = self.driver.execute_script('return document.body.getAttribute("data-lp")')
                gid = self.driver.execute_script('return document.body.getAttribute("data-gid")')

                if lp and gid:
                    self.driver.get(cfg.URLS["gift_tab"].format(lp=lp, gid=gid))
                    time.sleep(cfg.TIMING["page_load_wait"])
                    items = self.wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, cfg.GIFT["item_class"])))
                    hu_liang = next((i for i in items if "虎粮" in i.text), None)
                    
                    if hu_liang:
                        ActionChains(self.driver).move_to_element(hu_liang).pause(1.5).perform()
                        inp = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, cfg.GIFT["input_css"])))
                        inp.click()
                        inp.clear()
                        inp.send_keys(str(count))
                        self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, cfg.GIFT["send_class"]))).click()
                        time.sleep(1)
                        self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, cfg.GIFT["confirm_class"]))).click()
                        
                        done_msg = f"🚀 房间 {room_id} 虎粮赠送成功: {count} 个"
                        print(done_msg)
                        self.msg_logs.append(done_msg)
                    else:
                        print("[ERROR] 房间内未发现虎粮图标")
                else:
                    print("[ERROR] 获取房间参数失败，跳过送礼")

            # B. 回到主直播间页面执行打卡 (防止刚才切换了 URL)
            self.driver.get(cfg.URLS["room_base"].format(room_id))
            time.sleep(2)
            self.daily_check_in(room_id)

            return count
        except Exception as e:
            print(f"[CRASH] 房间 {room_id} 异常: {e}")
            return 0

    def run(self):
        try:
            print("=" * 40)
            print("[HUYA] 虎牙自动助手启动")
            print("=" * 40)

            if not self.login(): return False

            total = self.get_hl_count()
            if total <= 0:
                msg = "⚠️ 今日查询结果：账号内暂无虎粮。"
                print(msg)
                self.msg_logs.append(msg)
                # 即便没粮，也会在最后执行推送，确认脚本跑过
            else:
                n = len(self.rooms)
                per, rem = total // n, total % n
                plan = [(self.rooms[i], per + (1 if i < rem else 0)) for i in range(n)]

                print("\n[SEND] 开始执行发送与打卡方案...")
                for rid, c in plan:
                    self.send_to_room(rid, c)

            return True
        except Exception as e:
            print(f"\n[CRASH] 程序主进程异常: {e}")
            self.msg_logs.append(f"❌ 程序运行异常: {str(e)[:50]}")
            return False
        finally:
            if hasattr(self, 'driver'):
                self.driver.quit()
                print("[EXIT] 浏览器已关闭")
            self.send_notification()

def main():
    huya = HuYaAuto()
    res = huya.run()
    sys.exit(0 if res else 1)

if __name__ == '__main__':
    main()
