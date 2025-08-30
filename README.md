# Cityline 自动购票系统

一个高效的 Cityline 购票自动化脚本，支持智能按钮检测、模糊票价匹配和自动提交订单。

## 功能特点

- 🎯 **智能按钮检测** - 自动识别"前往购票"、"继续"、"登入"等按钮
- 🔄 **持续搜索机制** - 不断重复搜索按钮，解决页面加载慢的问题
- 🎫 **模糊票价匹配** - 智能匹配票价区域，支持部分关键词匹配
- 🚀 **自动提交订单** - 完成票务选择后自动点击确定按钮
- 🏃 **高速运行** - 优化等待时间，提升整体运行速度
- 🇭🇰 **繁体中文优先** - 优先匹配繁体中文按钮文本
- 🛡️ **智能登录检测** - 自动处理登录重定向和状态检测

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置活动信息

编辑 `enhanced_config.json` 文件：

```json
{
  "target_event": {
    "url": "https://shows.cityline.com/tc/2025/your-event.html"
  },
  "ticket_preferences": {
    "quantity": 1,
    "preferred_zones": ["C/$348"]
  },
  "purchase_settings": {
    "auto_purchase": true,
    "max_wait_time": 300
  },
  "browser_config": {
    "headless": false,
    "page_timeout": 30
  }
}
```

### 3. 运行脚本

```bash
python3 enhanced_ticket_purchaser.py
```

## 配置说明

### target_event
- `url`: Cityline 活动页面URL

### ticket_preferences
- `quantity`: 购票数量
- `preferred_zones`: 偏好票价区域（支持模糊匹配）
  - 示例: `["C/$348"]` 会匹配 "Zone C HK$348"
  - 示例: `["VIP"]` 会匹配包含 "VIP" 的票价
  - 示例: `["A", "B"]` 会依次尝试匹配 A 区和 B 区

### purchase_settings
- `auto_purchase`: 是否自动提交订单
- `max_wait_time`: 最大等待时间（秒）

### browser_config
- `headless`: 是否无头模式运行
- `page_timeout`: 页面超时时间

## 使用流程

1. **自动访问活动页面**
2. **处理登录重定向** - 等待用户手动登录
3. **智能按钮检测** - 自动寻找"前往购票"按钮
4. **venue页面处理** - 自动点击"继续"和"登入"按钮
5. **智能票务选择** - 根据配置自动选择票价和数量
6. **自动提交订单** - 点击确定按钮完成购票

## 核心特性

### 持续搜索机制
脚本使用持续搜索而非固定等待，能够：
- 立即响应页面变化
- 解决页面加载慢的问题
- 大幅提升运行速度

### 模糊票价匹配
支持灵活的票价配置：
```json
"preferred_zones": ["C/$348", "VIP", "A区"]
```
会自动匹配：
- "Zone C HK$348" ✅
- "VIP A (企位) HK$1,580" ✅  
- "A区座位 HK$880" ✅

### 智能按钮识别
自动识别多种按钮类型：
- 繁体中文: 前往購票、登入、繼續
- 简体中文: 前往购票、登录、继续
- 英文: Buy Ticket、Login、Continue

## 故障排除

### 常见问题

1. **浏览器启动失败**
   - 检查 Chrome 浏览器安装
   - 更新 undetected-chromedriver

2. **找不到按钮**
   - 脚本会显示调试信息
   - 检查页面结构是否发生变化

3. **登录问题**
   - 脚本会等待手动登录
   - 支持 Facebook、Google 等第三方登录

4. **票价匹配失败**
   - 检查 preferred_zones 配置
   - 使用更通用的关键词

## 技术架构

- **Selenium WebDriver** - 浏览器自动化
- **undetected-chromedriver** - 绕过检测
- **智能等待机制** - WebDriverWait + 持续搜索
- **JavaScript 点击** - 避免元素被遮挡
- **配置驱动** - 灵活的 JSON 配置

## 安全说明

本脚本仅用于合法的个人购票用途，请遵守 Cityline 的使用条款。

## 文件结构

```
cityline_ticket-main/
├── enhanced_ticket_purchaser.py  # 主要脚本
├── enhanced_config.json          # 配置文件
├── requirements.txt               # Python 依赖
└── README.md                      # 说明文档
```