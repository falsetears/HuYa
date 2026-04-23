# 虎牙虎粮自动发放、直播间打卡
轻量、开箱即用的 **虎牙虎粮自动批量赠送、直播间打卡工具**，支持 GitHub Actions，并通过 [Server 酱](https://sct.ftqq.com/)推送赠送虎粮、打卡结果至微信。

---

## ✨ 特性
- 🔐 **安全配置**：Cookie / 房间号通过 GitHub Secrets 管理，不泄露
- 🤖 **全自动运行**：支持定时执行 + 手动触发
- 📦 **无冗余依赖**：仅需 Selenium 环境，超轻量
- 🎯 **精准分配**：自动读取背包虎粮，批量分配到多个房间
- 🚀 **云原生**：直接在 GitHub Actions 运行，无需服务器
- 📲 **Server 酱** 实时推送赠送虎粮、打卡结果至微信

---

## 📁 项目结构
```
.github/workflows/auto.yml  # GitHub Actions 自动化配置
requirements.txt            # 依赖清单
main.py                     # 主程序（核心逻辑）
config.py                   # 页面选择器（唯一配置文件）
```

---

## 🚀 快速部署
### 1. 准备工作
1. 登录 [虎牙网页版](https://i.huya.com/)
2. F12 打开开发者工具 -> 网络 -> F5
3. 找到 "index.php?m=Msg&do=getMsgC" 项
4. 在标头中找到并复制整个 Cookie 字符串


### 2. 获取 SendKey（Server 酱）
1. 打开 [Server 酱官网](https://sct.ftqq.com/)
2. 注册并登录后，进入「发送通道」页面
3. 创建通知通道并获取 `SendKey`

### 3. GitHub 部署
1. Fork 本仓库
2. 进入仓库 **Settings → Secrets and variables → Actions**
3. 添加 **2 个必需密钥**、**1个非必需密钥**（缺少任意一个将直接停止运行）：
   - `HUYA_COOKIE`：你的虎牙登录 Cookie；--必须
   - `HUYA_ROOMS`：房间号列表，英文逗号分隔（例：`518512,1964,294636272`）；--必须
   - `SEND_KEY`：步骤2中获取的`SendKey`,用于推送送礼物和打卡结果；--非必须
4. 进入 **Actions** → 启用工作流
5. 完成！每天 **北京时间 0:30** 自动运行

---

## 🎮 手动运行
### 方式 1：GitHub 在线运行
1. 进入仓库 Actions
2. 选择 `虎牙虎粮自动发放`
3. 点击 `Run workflow`
4. 可自定义输入房间号（覆盖密钥配置）

### 方式 2：本地运行
```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export HUYA_COOKIE="你的Cookie"
export HUYA_ROOMS="518512,1964"
export SEND_KEY="你的sendkey"

# 启动
python main.py
```

---

## ⚙️ 配置说明
| 名称 | 说明 |
|------|------|
| HUYA_COOKIE | 登录凭证（必须） |
| HUYA_ROOMS | 目标房间号列表（必须） |
| SEND_KEY | Server 酱sendkey（非必须）|

---

## 📅 定时任务
默认：**每天 北京时间 0:01** 执行
修改定时：编辑 `.github/workflows/auto.yml`
```yaml
on:
  schedule:
    # 每天 北京时间 00:01 运行
    - cron: '1 16 * * *'
```

---

## 📌 运行流程
1. 验证 Cookie / 房间号（缺少直接退出）
2. 打开背包页面，读取虎粮数量
3. 自动分配数量到所有房间
4. 依次进入房间 → 悬停虎粮 → 自定义数量 → 赠送
5. 房间打卡
6. 输出执行结果
7. 推送执行结果到微信：🚀 房间 XXX 送出虎粮 X 个； 打卡结果（✅ 打卡成功 or ℹ️ 已打卡）

---

## ✉️ 推送结果
<img width="1439" height="697" alt="image" src="https://github.com/user-attachments/assets/6ab4b08b-6553-4b49-9998-386fbf7c94ad" />

---

## ⚠️ 重要提醒
- 请勿分享 Cookie，避免账号被盗
- Cookie 过期后重新获取更新即可
- 房间必须**正常开播**才能赠送礼物
- 本项目仅用于学习交流，遵守平台规则

---

## 🐛 常见问题
- **登录失败**：Cookie 过期或格式错误，重新获取
- **赠送失败**：房间未开播、礼物面板未加载
- **Action 报错**：检查 Secrets 是否正确配置

---

## 📄 许可证
MIT License
