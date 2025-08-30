#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版独立购票脚本
完全配置驱动，包含完整的选座和购票流程
基于成功验证的Cloudflare绕过方法
"""

import sys
import os
import json
import time
import random
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from loguru import logger


@dataclass
class TicketSelectionResult:
    """选票结果数据类"""
    success: bool
    selected_tickets: List[Dict] = None
    total_price: float = 0.0
    message: str = ""
    performance_id: str = ""


@dataclass
class PurchaseResult:
    """购票结果数据类"""
    success: bool
    order_id: str = ""
    total_amount: float = 0.0
    payment_status: str = ""
    message: str = ""


class ConfigDrivenTicketPurchaser:
    """配置驱动的独立购票系统"""
    
    def __init__(self, config_path="enhanced_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.driver = None
        self.current_event = None
        
        # 预编译高频使用的选择器
        self.fast_selectors = {
            'continue_btns': '.continue-btn, #continueBtn, button[onclick*="continue"], a[onclick*="continue"]',
            'login_btns': '.login-btn, #loginBtn, button[onclick*="login"], a[onclick*="login"]',
            'purchase_btns': '.load-button, #buyTicketBtn, .btn_cta, .purchase-btn',
            'go_buttons': 'button[onclick*="go()"], a[onclick*="go()"]'
        }
    
    def _fast_find_button(self, button_type: str, text_keywords: list = None, max_wait: int = 10) -> object:
        """持续快速查找按钮（不怕页面加载慢）"""
        try:
            check_interval = 0.5
            total_rounds = int(max_wait / check_interval)
            
            for round_num in range(total_rounds):
                # 首先使用预编译的CSS选择器
                if button_type in self.fast_selectors:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, self.fast_selectors[button_type])
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            if not text_keywords:  # 如果不需要文本匹配
                                return element
                            
                            # 快速文本匹配
                            text = element.text.strip()
                            if text and any(keyword in text for keyword in text_keywords):
                                return element
                
                # 备用：使用XPath查找（仅在必要时）
                if text_keywords:
                    keyword_conditions = " or ".join([f"contains(text(), '{kw}')" for kw in text_keywords])
                    xpath = f"//button[{keyword_conditions}] | //a[{keyword_conditions}]"
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            return element
                
                # 如果这轮没找到，短暂等待后继续
                if round_num < total_rounds - 1:  # 不是最后一轮
                    time.sleep(check_interval)
            
            return None
        except Exception as e:
            return None
        
    def _load_config(self) -> Dict:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"✅ 成功加载配置文件: {self.config_path}")
            return config
        except FileNotFoundError:
            print(f"❌ 配置文件不存在: {self.config_path}")
            self._create_default_config()
            return self._load_config()
        except Exception as e:
            print(f"❌ 配置文件加载失败: {e}")
            sys.exit(1)
    
    def _create_default_config(self):
        """创建默认配置文件（简化版）"""
        default_config = {
            "target_event": {
                "url": "https://shows.cityline.com/sc/2025/example.html"
            },
            "ticket_preferences": {
                "quantity": 2,
                "preferred_zones": ["VIP", "A区", "B区"]
            },
            "purchase_settings": {
                "auto_purchase": False,
                "max_wait_time": 300
            },
            "browser_config": {
                "headless": False,
                "page_timeout": 30
            },
            "notifications": {
                "success_message": "🎉 购票成功！门票已预订"
            }
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        print(f"✅ 已创建默认配置文件: {self.config_path}")
    
    def create_browser(self) -> bool:
        """创建浏览器实例（使用验证成功的兼容配置）"""
        try:
            print("🚀 正在启动浏览器...")
            print("💡 使用兼容性优化的配置")
            
            options = uc.ChromeOptions()
            browser_config = self.config.get('browser_config', {})
            
            # 基础配置（兼容性优先）
            window_size = browser_config.get('window_size', [1920, 1080])
            options.add_argument(f"--window-size={window_size[0]},{window_size[1]}")
            
            # 优化的反检测设置（仅使用兼容参数）
            if browser_config.get('stealth_mode', True):
                # 只使用确定兼容的参数
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--no-sandbox")
                # 移除所有experimental_option，避免兼容性问题
            
            # 使用验证成功的核心参数
            self.driver = uc.Chrome(
                options=options,
                headless=browser_config.get('headless', False),
                use_subprocess=False  # 关键成功参数
            )
            
            # 设置超时
            page_timeout = browser_config.get('page_timeout', 30)
            self.driver.set_page_load_timeout(page_timeout)
            
            print("✅ 浏览器启动成功（兼容性优化版本）")
            return True
            
        except Exception as e:
            print(f"❌ 浏览器启动失败: {e}")
            print("💡 建议检查Chrome浏览器安装和undetected-chromedriver版本")
            return False
    
    def handle_cloudflare_verification(self, url: str) -> bool:
        """处理Cloudflare验证（基于成功验证的方法）"""
        try:
            print("🛡️ 检查Cloudflare验证...")
            
            # 检测Cloudflare
            has_cloudflare = self._detect_cloudflare()
            
            if not has_cloudflare:
                print("✅ 未检测到Cloudflare验证")
                return True
            
            print("🔒 检测到Cloudflare验证")
            print("💡 请手动完成验证...")
            
            # 高亮验证区域
            self._highlight_verification_areas()
            
            print("👤 请手动完成Cloudflare验证：")
            print("   1. 点击验证复选框")
            print("   2. 等待绿色对勾出现")
            print("   3. 完成任何图像验证")
            
            # 智能等待验证完成
            return self._wait_for_verification_complete()
            
        except Exception as e:
            print(f"❌ Cloudflare处理异常: {e}")
            return False
    
    def _detect_cloudflare(self) -> bool:
        """检测是否存在Cloudflare验证（智能检测）"""
        try:
            # 等待页面稳定
            time.sleep(2)
            
            page_source = self.driver.page_source.lower()
            page_title = self.driver.title.lower()
            current_url = self.driver.current_url.lower()
            
            # 强指示器（确实有Cloudflare）
            strong_indicators = [
                "checking your browser" in page_source,
                "just a moment" in page_source,
                "please wait" in page_title,
                "cloudflare" in page_title,
                len(self.driver.find_elements(By.CSS_SELECTOR, ".cf-turnstile")) > 0,
                len(self.driver.find_elements(By.CSS_SELECTOR, "[data-sitekey]")) > 0,
                len(self.driver.find_elements(By.CSS_SELECTOR, "#cf-challenge")) > 0
            ]
            
            # 弱指示器（可能只是引用）
            weak_indicators = [
                "cloudflare" in page_source,
                "ray id" in page_source
            ]
            
            # 排除指示器（明确不是Cloudflare页面）
            exclude_indicators = [
                len(page_source) > 50000,  # 完整页面通常很长
                "cityline" in current_url and len(page_source) > 10000,  # Cityline正常页面
                "login" in current_url and "username" in page_source,  # 登录页面
                "shows.cityline.com" in current_url and len(page_source) > 5000  # 活动页面
            ]
            
            # 如果有强指示器，确认为Cloudflare
            if any(strong_indicators):
                print("🔍 检测到明确的Cloudflare验证页面")
                return True
            
            # 如果有排除指示器，确认不是Cloudflare
            if any(exclude_indicators):
                print("🔍 页面似乎已正常加载，无需Cloudflare验证")
                return False
            
            # 如果只有弱指示器，进一步检查
            if any(weak_indicators):
                print("🔍 检测到可能的Cloudflare元素，等待确认...")
                time.sleep(3)  # 等待可能的重定向
                
                # 重新检查
                new_page_source = self.driver.page_source.lower()
                if any(indicator in new_page_source for indicator in ["checking your browser", "just a moment"]):
                    return True
                
                print("🔍 确认为正常页面，跳过Cloudflare处理")
                return False
            
            return False
            
        except Exception as e:
            print(f"⚠️ Cloudflare检测异常: {e}")
            return False
    
    def _highlight_verification_areas(self):
        """高亮显示验证区域"""
        try:
            highlight_script = """
                var selectors = ['.cf-turnstile', '[data-sitekey]', '#cf-challenge'];
                selectors.forEach(function(selector) {
                    var elements = document.querySelectorAll(selector);
                    elements.forEach(function(el) {
                        if (el && el.offsetHeight > 0) {
                            el.style.border = '3px solid #ff6b6b';
                            el.style.borderRadius = '5px';
                            el.style.backgroundColor = 'rgba(255, 107, 107, 0.1)';
                            el.scrollIntoView({behavior: 'smooth', block: 'center'});
                        }
                    });
                });
            """
            self.driver.execute_script(highlight_script)
            print("✨ 已高亮显示验证区域")
            
        except Exception as e:
            print(f"⚠️ 高亮显示异常: {e}")
    
    def _wait_for_verification_complete(self) -> bool:
        """等待验证完成"""
        print("⏳ 等待验证完成...")
        
        max_wait = 60
        check_interval = 2
        
        for i in range(0, max_wait, check_interval):
            time.sleep(check_interval)
            
            try:
                completion_indicators = [
                    lambda: len(self.driver.find_elements(By.CSS_SELECTOR, ".cf-turnstile.cf-success")) > 0,
                    lambda: len(self.driver.find_elements(By.CSS_SELECTOR, "[data-cf-turnstile-success='true']")) > 0,
                    lambda: "checking your browser" not in self.driver.page_source.lower(),
                    lambda: len(self.driver.find_elements(By.CSS_SELECTOR, ".cf-turnstile")) == 0
                ]
                
                if any(indicator() for indicator in completion_indicators):
                    print("✅ 验证完成！")
                    self._remove_highlights()
                    return True
                
                remaining = max_wait - i - check_interval
                if remaining > 0 and remaining % 10 == 0:
                    print(f"⏱️ 剩余等待时间: {remaining}秒")
                    
            except:
                continue
        
        print("⏰ 验证等待超时")
        return False
    
    def _remove_highlights(self):
        """移除高亮效果"""
        try:
            remove_script = """
                var elements = document.querySelectorAll('[style*="rgb(255, 107, 107)"]');
                elements.forEach(function(el) {
                    el.style.border = '';
                    el.style.backgroundColor = '';
                    el.style.boxShadow = '';
                });
            """
            self.driver.execute_script(remove_script)
        except:
            pass
    
    def _check_login_status(self) -> bool:
        """检查当前登录状态（简化版）"""
        try:
            # 简化获取页面信息，避免连接错误
            try:
                current_url = self.driver.current_url.lower()
                page_source = self.driver.page_source.lower()
                page_title = self.driver.title.lower()
            except:
                # 如果获取页面信息失败，返回未登录
                print("🔍 检查登录状态: 浏览器连接异常，默认未登录")
                return False
            
            print(f"🔍 检查登录状态:")
            print(f"   当前URL: {current_url}")
            print(f"   页面标题: {page_title}")
            
            # 1. 明确的未登录指示器（优先级最高）
            not_logged_in_indicators = [
                "login.html" in current_url,  # 在登录页面
                "login" in current_url and "targeturl" in current_url,  # 带重定向的登录页面
                "/login" in current_url,  # 登录路径
                "www.cityline.com/login" in current_url,  # Cityline登录页面
                "请登录" in page_source,
                "please login" in page_source,
                "sign in" in page_title,
                "登录" in page_title and "会员" not in page_source,
                # 特别检查Cityline登录页面特征
                "會員登入" in page_title,  # Cityline登录页面标题特征
                "cityline" in current_url and "login" in current_url
            ]
            
            # 2. 明确的已登录指示器
            logged_in_indicators = [
                "會員" in page_source, "会员" in page_source, "member" in page_source,
                "登出" in page_source, "logout" in page_source, "sign out" in page_source,
                "我的账户" in page_source, "个人中心" in page_source,
                "用户名" in page_source, "username" in page_source
            ]
            
            # 3. 页面内容指示器（活动页面）
            activity_page_indicators = [
                "shows.cityline.com" in current_url and "login" not in current_url,
                "演唱会" in page_source, "concert" in page_source,
                "购票" in page_source, "ticket" in page_source,
                len(page_source) > 10000  # 完整页面通常较长
            ]
            
            # 统计各种指示器
            not_logged_score = sum(not_logged_in_indicators)
            login_score = sum(logged_in_indicators)
            activity_score = sum(activity_page_indicators)
            
            print(f"   📊 未登录指示器得分: {not_logged_score}")
            print(f"   📊 已登录指示器得分: {login_score}")
            print(f"   📊 活动页面指示器得分: {activity_score}")
            
            # 1. 最高优先级：检查明确的未登录状态
            if not_logged_score >= 1:
                print("   🔐 状态: 未登录（检测到登录页面特征）")
                return False
            
            # 2. 第二优先级：检查明确的已登录状态
            if login_score >= 1 and not_logged_score == 0:
                print("   ✅ 状态: 已登录（检测到登录指示器）")
                return True
            
            # 3. 第三优先级：检查是否在活动页面
            if activity_score >= 2 and not_logged_score == 0 and "login" not in current_url:
                print("   ✅ 状态: 已登录（在活动页面）")
                return True
            
            # 4. 默认：状态不明确，倾向于未登录
            print("   ⚠️ 状态: 登录状态不明确，默认为未登录")
            return False
                
        except Exception as e:
            print(f"   ❌ 登录状态检查异常: {e}")
            return False
    
    def _wait_for_login_completion(self, max_wait_time: int = 300) -> bool:
        """智能等待登录完成"""
        try:
            print(f"⏳ 等待用户完成登录（最多等待{max_wait_time}秒）...")
            print("💡 请在浏览器中:")
            print("   1. 选择登录方式（Facebook、Google等）")
            print("   2. 完成登录验证")
            print("   3. 系统检测到登录成功后自动继续")
            print()
            
            check_interval = 5  # 每5秒检查一次
            waited_time = 0
            
            while waited_time < max_wait_time:
                # 检查登录状态
                if self._check_login_status():
                    print("🎉 检测到登录成功！")
                    return True
                
                # 检查是否已跳转到活动页面
                current_url = self.driver.current_url
                if ("shows.cityline.com" in current_url and 
                    "login" not in current_url.lower()):
                    print("🎉 检测到已跳转到活动页面！")
                    return True
                
                # 显示等待状态
                remaining = max_wait_time - waited_time
                if waited_time % 30 == 0 and waited_time > 0:  # 每30秒提示一次
                    print(f"⏱️ 继续等待登录... 剩余{remaining}秒")
                    print(f"   当前页面: {current_url}")
                
                time.sleep(check_interval)
                waited_time += check_interval
            
            print("⏰ 等待登录超时")
            print("💡 您可以:")
            print("   1. 继续手动完成登录")
            print("   2. 重新运行脚本")
            
            return False
            
        except Exception as e:
            print(f"❌ 等待登录过程异常: {e}")
            return False
    
    def login_member(self) -> bool:
        """会员登录（智能检测和跳过机制）"""
        try:
            member_config = self.config.get('member_info', {})
            
            if not member_config.get('auto_login', False):
                print("⚠️ 自动登录已禁用，跳过登录")
                return True
            
            username = member_config.get('username', '')
            password = member_config.get('password', '')
            
            if not username or not password:
                print("⚠️ 未配置登录信息，跳过自动登录")
                return True
            
            # 先检查当前登录状态
            current_status = self._check_login_status()
            if current_status:
                print("✅ 检测到已登录状态，跳过登录")
                return True
            
            # 如果在登录页面，等待用户完成登录
            current_url = self.driver.current_url.lower()
            if "login.html" in current_url or ("login" in current_url and "targeturl" in current_url):
                print("🔐 检测到正在登录页面，等待用户完成登录...")
                return self._wait_for_login_completion()
            
            print("🔐 开始会员登录...")
            
            # 访问登录页面
            try:
                self.driver.get("https://www.cityline.com/member/login")
                time.sleep(random.uniform(2, 4))
            except Exception as e:
                print(f"⚠️ 访问登录页面失败: {e}")
                print("💡 跳过登录，直接尝试购票")
                return True
            
            # 处理可能的Cloudflare
            if not self.handle_cloudflare_verification(self.driver.current_url):
                print("❌ 登录页面Cloudflare处理失败，跳过登录")
                return True
            
            # 登录操作
            wait = WebDriverWait(self.driver, 10)
            
            try:
                # 尝试多种可能的用户名输入框定位方式
                username_selectors = [
                    (By.NAME, "username"),
                    (By.NAME, "loginName"),
                    (By.ID, "username"),
                    (By.ID, "loginName"),
                    (By.CSS_SELECTOR, "input[type='text']"),
                    (By.CSS_SELECTOR, "input[placeholder*='用户名']"),
                    (By.CSS_SELECTOR, "input[placeholder*='电话']")
                ]
                
                username_field = None
                for selector in username_selectors:
                    try:
                        username_field = wait.until(EC.presence_of_element_located(selector))
                        if username_field.is_displayed():
                            break
                    except:
                        continue
                
                if not username_field:
                    print("⚠️ 未找到用户名输入框，可能需要手动登录")
                    return False
                
                username_field.clear()
                username_field.send_keys(username)
                
                time.sleep(random.uniform(1, 2))
                
                password_field = self.driver.find_element(By.NAME, "password")
                password_field.clear()
                password_field.send_keys(password)
                
                time.sleep(random.uniform(1, 2))
                
                # 提交登录
                login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
                login_button.click()
                
                time.sleep(1)  # 减少登录等待
                
                # 验证登录状态
                if "login" not in self.driver.current_url.lower():
                    print("✅ 登录成功！")
                    return True
                else:
                    print("⚠️ 登录状态不确定，请检查")
                    return False
                    
            except Exception as e:
                print(f"⚠️ 登录操作异常: {e}")
                return False
                
        except Exception as e:
            print(f"❌ 登录过程异常: {e}")
            return False
    
    def access_event_page(self) -> bool:
        """访问活动页面（增强连接稳定性）"""
        try:
            event_config = self.config.get('target_event', {})
            event_url = event_config.get('url', '')
            
            if not event_url:
                print("❌ 未配置活动URL")
                return False
            
            print(f"🎯 访问活动页面: {event_url}")
            
            # 重试机制
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.driver.get(event_url)
                    time.sleep(random.uniform(3, 5))
                    
                    # 验证页面加载成功
                    if len(self.driver.page_source) < 1000:
                        print(f"⚠️ 页面加载异常，第{attempt+1}次重试...")
                        time.sleep(2)
                        continue
                    
                    
                    # 检查是否被重定向到登录页面
                    current_url = self.driver.current_url.lower()
                    if ("login.html" in current_url or 
                        ("login" in current_url and "targeturl" in current_url)):
                        print("🔐 检测到被重定向到登录页面")
                        print("💡 需要用户手动登录后才能访问活动页面")
                        
                        # 等待用户完成登录
                        if self._wait_for_login_completion():
                            print("✅ 登录完成，继续访问活动页面")
                            # 登录完成后不直接返回，而是继续执行点击购票按钮的流程
                            print("✅ 成功访问活动页面（登录后直接跳转）")
                            # 继续后续流程，不要直接返回
                        else:
                            print("❌ 登录等待失败或超时")
                            return False
                    
                    print("✅ 成功访问活动页面")
                    # 继续执行点击"前往购票"的流程
                    return self._execute_purchase_button_flow()
                    
                except Exception as e:
                    print(f"⚠️ 第{attempt+1}次访问失败: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(3)
                        continue
                    else:
                        raise e
            
            return False
            
        except Exception as e:
            print(f"❌ 访问活动页面失败: {e}")
            print("💡 建议检查网络连接和活动URL有效性")
            return False
    
    def _execute_purchase_button_flow(self) -> bool:
        """执行点击'前往购票'按钮和后续流程"""
        try:
            print("🎯 开始执行购票按钮流程...")
            time.sleep(1)  # 减少等待时间
            
            # 直接寻找并点击"前往购票"按钮
            print("🔍 直接寻找'前往购票'按钮...")
            
            target_button = None
            original_url = self.driver.current_url
            original_windows = self.driver.window_handles
            
            # 方法1：使用持续快速查找（预编译选择器）
            print("🔄 持续搜索go按钮...")
            target_button = self._fast_find_button('go_buttons', max_wait=8)
            
            if not target_button:
                # 方法2：使用文本匹配查找购票按钮（持续搜索）
                print("🔄 持续搜索购票按钮...")
                target_button = self._fast_find_button('purchase_btns', ['前往購票', '前往购票', '立即購買', '立即购买', '快速購票', '快速购票'], max_wait=8)
            
            if not target_button:
                # 方法3：传统选择器查找（备用）
                button_selectors = [
                    "button[onclick*='goevent'], button[onclick*='goEvent'], a[onclick*='goevent'], a[onclick*='goEvent']",
                    "button, a[role='button']"
                ]
                
                for selector in button_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                text = element.text.strip()
                            
                            # 检查是否是"前往购票"相关按钮
                            if text:  # 如果有文本
                                # 检查是否包含购票关键词（支持简体和繁体）
                                if ('前' in text and '往' in text and ('购' in text or '購' in text) and '票' in text) or \
                                   '前往購票' in text or '前往购票' in text or \
                                   '立即購買' in text or '立即购买' in text or \
                                   '馬上購買' in text or '马上购买' in text or \
                                   '快速購票' in text or '快速购票' in text or \
                                   'buy ticket' in text.lower() or \
                                   'purchase' in text.lower():
                                    
                                    # 排除第三方登录按钮
                                    if not any(exclude in text.lower() for exclude in ['facebook', 'google', 'login', '登录', '微信', 'wechat']):
                                        target_button = element
                                        print(f"✅ 找到目标按钮: '{text}' (选择器: {selector})")
                                        break
                            elif selector in ["#buyTicketBtn", ".load-button", "button[onclick*='go()']"]:
                                # 对于特定的选择器，即使没有文本也接受
                                target_button = element
                                print(f"✅ 找到目标按钮 (选择器: {selector})")
                                break
                        
                        if target_button:
                            break
                            
                    except Exception as e:
                        continue
            
            if not target_button:
                print("❌ 未找到'前往购票'按钮，显示调试信息...")
                self._show_debug_buttons()
                return False
            
            # 高亮并点击按钮
            self.driver.execute_script("""
                arguments[0].style.border = '3px solid #00ff00';
                arguments[0].style.backgroundColor = 'rgba(0,255,0,0.2)';
                arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});
            """, target_button)
            
            time.sleep(1)
            print("🖱️ 点击'前往购票'按钮...")
            target_button.click()
            time.sleep(2)
            
            # 检查是否有新窗口
            new_windows = self.driver.window_handles
            if len(new_windows) > len(original_windows):
                print("🔄 检测到新窗口，切换中...")
                self.driver.switch_to.window(new_windows[-1])
                time.sleep(1)
                
            new_url = self.driver.current_url
            print(f"🌐 当前URL: {new_url}")
            
            # 处理venue页面的继续流程
            if "venue.cityline.com" in new_url:
                print("🏟️ 进入venue页面，开始处理继续流程...")
                return self._handle_venue_continue_flow()
            else:
                print("✅ 购票按钮点击成功")
                return True
                
        except Exception as e:
            print(f"❌ 购票按钮流程异常: {e}")
            return False
    

    

    
    def _is_seat_selection_page(self) -> bool:
        """判断是否为选座页面"""
        try:
            seat_indicators = [
                ".seat", ".座位", "seat-map", "选座",
                "venue.cityline.com" in self.driver.current_url,
                "座位图" in self.driver.page_source
            ]
            
            return any([
                self.driver.find_elements(By.CSS_SELECTOR, ".seat"),
                "选座" in self.driver.page_source,
                "seat" in self.driver.page_source.lower(),
                "venue.cityline.com" in self.driver.current_url
            ])
            
        except:
            return False
    
    def handle_seat_selection(self) -> bool:
        """处理选座流程"""
        try:
            print("💺 开始选座流程...")
            
            # 等待选座页面加载
            time.sleep(5)
            
            # 检查是否在venue页面
            if "venue.cityline.com" in self.driver.current_url:
                print("🏟️ 检测到venue页面，等待加载...")
                
                # 处理可能的Cloudflare
                if not self.handle_cloudflare_verification(self.driver.current_url):
                    print("❌ venue页面Cloudflare处理失败")
                    return False
                
                # 等待并寻找继续按钮
                return self._handle_venue_page()
            
            # 如果不是venue页面，寻找其他选座元素
            print("🔍 寻找选座选项...")
            
            return True
            
        except Exception as e:
            print(f"❌ 选座流程异常: {e}")
            return False
    
    def _handle_venue_continue_flow(self) -> bool:
        """处理venue页面的继续流程（参考项目风格）"""
        try:
            print("🏟️ 处理venue页面继续流程...")
            
            # 等待页面完全加载
            time.sleep(2)
            
            # venue页面不需要Cloudflare验证，直接处理按钮
            
            # 参考项目的继续按钮策略（更精确）
            continue_strategies = [
                # 策略1: onclick事件（最优先）
                {"selector": "button[onclick*='goEvent']", "method": "onclick_goEvent", "priority": 100},
                {"selector": "button[onclick*='goevent']", "method": "onclick_goevent", "priority": 95},
                {"selector": "a[onclick*='goEvent']", "method": "link_goEvent", "priority": 90},
                
                # 策略2: 特定class（参考项目常用）
                {"selector": ".btn_cta", "method": "btn_cta_class", "priority": 85},
                {"selector": ".queue-button", "method": "queue_button_class", "priority": 80},
                {"selector": ".continue-btn", "method": "continue_btn_class", "priority": 75},
                
                # 策略3: 文本匹配（优先繁体中文）
                {"selector": "//button[contains(text(), '繼續')]", "method": "xpath_continue_tc", "priority": 85},      # 繁体继续 - 最高
                {"selector": "//button[contains(text(), '登入')]", "method": "xpath_login_universal", "priority": 82},  # 通用登入
                {"selector": "//button[contains(text(), '登錄')]", "method": "xpath_login_tc", "priority": 80},         # 繁体登录
                {"selector": "//a[contains(text(), '繼續')]", "method": "xpath_link_continue_tc", "priority": 78},      # 繁体继续链接
                {"selector": "//a[contains(text(), '登入')]", "method": "xpath_login_link", "priority": 75},            # 通用登入链接
                {"selector": "//button[contains(text(), '继续')]", "method": "xpath_continue_zh", "priority": 70},      # 简体继续
                {"selector": "//button[contains(text(), '登录')]", "method": "xpath_login_zh", "priority": 68},         # 简体登录
                {"selector": "//button[contains(text(), 'Continue')]", "method": "xpath_continue_en", "priority": 65}, # 英文继续
                {"selector": "//button[contains(text(), '排隊')]", "method": "xpath_queue_tc", "priority": 62},         # 繁体排队
                {"selector": "//button[contains(text(), '排队')]", "method": "xpath_queue", "priority": 60},            # 简体排队
                {"selector": "//a[contains(text(), '继续')]", "method": "xpath_link_continue", "priority": 55},         # 简体继续链接
                {"selector": "//button[contains(text(), 'Login')]", "method": "xpath_login_en", "priority": 50}        # 英文登录
            ]
            
            # 按优先级排序
            continue_strategies.sort(key=lambda x: x["priority"], reverse=True)
            
            found_buttons = []
            
            # 直接使用已知有效的按钮选择器
            
            # 收集所有可能的继续按钮
            for strategy in continue_strategies:
                try:
                    selector = strategy["selector"]
                    method = strategy["method"]
                    priority = strategy["priority"]
                    
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            text = element.text.strip()
                            found_buttons.append({
                                'element': element,
                                'text': text,
                                'method': method,
                                'priority': priority,
                                'selector': selector
                            })
                            
                except Exception as e:
                    print(f"   策略 {method} 失败: {e}")
                    continue
            
            if found_buttons:
                # 按优先级排序
                found_buttons.sort(key=lambda x: x["priority"], reverse=True)
                
                # 选择最高优先级的按钮
                selected_button = found_buttons[0]
                element = selected_button['element']
                
                print(f"✅ 找到继续按钮: '{selected_button['text']}'")
                
                # 使用JavaScript点击，避免被遮挡
                try:
                    # 先滚动到按钮位置
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                    time.sleep(0.5)
                    
                    # 使用JavaScript点击
                    self.driver.execute_script("arguments[0].click();", element)
                    time.sleep(1)
                    print("✅ 继续按钮点击完成 (JavaScript点击)")
                    
                    # 等待并寻找登入按钮（智能等待）
                    print("🔍 寻找登入按钮...")
                    login_found = self._smart_wait_for_login_button()
                    
                    if not login_found:
                        print("⚠️ 未找到登入按钮，检查是否已自动跳转...")
                        # 等待可能的自动跳转
                        time.sleep(2)
                        current_url = self.driver.current_url
                        print(f"🌐 检查跳转后URL: {current_url}")
                        
                        # 检查多种可能的页面状态
                        if "performance" in current_url:
                            print("🎯 检测到购票页面，开始自动购票...")
                            purchase_result = self.complete_purchase_flow()
                            if purchase_result.success:
                                print(f"🎉 {purchase_result.message}")
                            else:
                                print(f"⚠️ {purchase_result.message}")
                        elif "eventDetail" in current_url:
                            print("🔍 仍在活动详情页面，尝试寻找更多按钮...")
                            # 扩展搜索范围，寻找任何可能的按钮
                            self._find_and_click_any_purchase_button()
                        else:
                            print(f"⚠️ 未识别的页面类型: {current_url}")
                            print("💡 可能需要手动操作或检查页面状态")
                    
                    return True
                    
                except Exception as e:
                    print(f"❌ 点击继续按钮失败: {e}")
                    return False
            else:
                print("❌ 未找到继续按钮，显示调试信息...")
                # 只有找不到按钮时才显示调试信息
                self._show_debug_buttons()
                return False
            
        except Exception as e:
            print(f"❌ venue继续流程异常: {e}")
            return False
    
    def _show_debug_buttons(self):
        """显示调试信息：页面上所有按钮"""
        try:
            print("🔍 调试：扫描页面上所有按钮...")
            all_buttons = []
            
            button_selectors = [
                "button", "a", "input[type='button']", "input[type='submit']", 
                ".btn", "[role='button']", "[onclick]"
            ]
            
            for selector in button_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            text = element.text.strip()
                            onclick = element.get_attribute('onclick') or ''
                            class_name = element.get_attribute('class') or ''
                            
                            if text or onclick:
                                all_buttons.append({
                                    'text': text,
                                    'onclick': onclick,
                                    'class': class_name
                                })
                                
                except Exception as e:
                    continue
            
            print(f"📊 发现 {len(all_buttons)} 个按钮:")
            for i, btn in enumerate(all_buttons[:10], 1):  # 只显示前10个
                text_preview = btn['text'][:50] + "..." if len(btn['text']) > 50 else btn['text']
                print(f"   {i}. 文本: '{text_preview}'")
                if btn['onclick']:
                    onclick_preview = btn['onclick'][:50] + "..." if len(btn['onclick']) > 50 else btn['onclick']
                    print(f"      onclick: {onclick_preview}")
                if btn['class']:
                    print(f"      class: {btn['class'][:50]}")
                print()
                
        except Exception as e:
            print(f"⚠️ 调试信息获取失败: {e}")
    
    def _wait_for_cloudflare_and_login_button(self) -> bool:
        """等待Cloudflare验证完成并点击登入按钮"""
        try:
            print("⏳ 等待Cloudflare验证和登入按钮...")
            max_wait = 60
            check_interval = 3
            
            for i in range(0, max_wait, check_interval):
                time.sleep(check_interval)
                
                # 检查是否有Cloudflare验证
                try:
                    page_source = self.driver.page_source.lower()
                    
                    # 检查是否有welcome窗口或验证完成
                    if "welcome" in page_source or "cloudflare" in page_source:
                        print(f"🔍 检测到验证页面，继续等待... ({i+check_interval}秒)")
                        
                        # 处理Cloudflare验证
                        if not self.handle_cloudflare_verification(self.driver.current_url):
                            print("⚠️ Cloudflare处理失败，继续尝试...")
                        
                        continue
                    
                    # 寻找登入按钮（优先繁体中文）
                    login_button_selectors = [
                        "//button[contains(text(), '登入')]",        # 通用登入
                        "//button[contains(text(), '登錄')]",        # 繁体登录
                        "//button[contains(text(), '登录')]",        # 简体登录
                        "//a[contains(text(), '登入')]",            # 通用登入链接
                        "//a[contains(text(), '登錄')]",            # 繁体登录链接
                        "//a[contains(text(), '登录')]",            # 简体登录链接
                        "//button[contains(text(), 'Login')]",       # 英文登录
                        "//input[@value='登入']",                   # 登入输入框
                        "//input[@value='登錄']",                   # 繁体登录输入框
                        "//input[@value='登录']",                   # 简体登录输入框
                        ".login-btn",
                        "#loginBtn"
                    ]
                    
                    login_button_found = False
                    for selector in login_button_selectors:
                        try:
                            if selector.startswith("//"):
                                elements = self.driver.find_elements(By.XPATH, selector)
                            else:
                                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            
                            for element in elements:
                                if element.is_displayed() and element.is_enabled():
                                    button_text = element.text.strip()
                                    print(f"✅ 找到登入按钮: '{button_text}'")
                                    
                                    # 高亮并点击登入按钮
                                    self.driver.execute_script("""
                                        arguments[0].style.border = '3px solid #00ff00';
                                        arguments[0].style.backgroundColor = 'rgba(0,255,0,0.2)';
                                        arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});
                                    """, element)
                                    
                                    time.sleep(2)
                                    print(f"🖱️ 点击登入按钮: '{button_text}'")
                                    element.click()
                                    time.sleep(5)
                                    
                                    # 检查页面变化
                                    new_url = self.driver.current_url
                                    print(f"🌐 点击后URL: {new_url}")
                                    
                                    print("✅ 成功点击登入按钮！")
                                    print("🎉 应该已进入购票页面")
                                    
                                    login_button_found = True
                                    return True
                                    
                        except Exception as e:
                            continue
                    
                    if not login_button_found:
                        remaining = max_wait - i - check_interval
                        if remaining > 0:
                            print(f"🔍 未找到登入按钮，继续等待... (剩余 {remaining} 秒)")
                        else:
                            break
                    
                except Exception as e:
                    print(f"⚠️ 页面检查异常: {e}")
                    continue
            
            print("⚠️ 等待登入按钮超时")
            print("💡 请手动点击登入按钮进入购票页面")
            return False
            
        except Exception as e:
            print(f"❌ 等待Cloudflare和登入按钮异常: {e}")
            return False

    def _handle_additional_continue_button(self) -> bool:
        """处理登入后出现的额外继续按钮"""
        try:
            print("🔍 寻找登入后的继续按钮...")
            time.sleep(1)  # 等待页面加载新的按钮
            
            # 使用快速查找方法
            continue_button = self._fast_find_button('continue_btns', ['繼續', '继续', 'Continue'])
            
            if continue_button:
                text = continue_button.text.strip()
                print(f"✅ 找到继续按钮: '{text}'")
                
                # 高亮并使用JavaScript点击（避免被遮挡）
                self.driver.execute_script("""
                    arguments[0].style.border = '3px solid #00ff00';
                    arguments[0].style.backgroundColor = 'rgba(0,255,0,0.2)';
                    arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});
                """, continue_button)
                
                time.sleep(0.5)
                
                # 使用JavaScript点击，避免被footer等元素遮挡
                try:
                    self.driver.execute_script("arguments[0].click();", continue_button)
                    print(f"✅ 已点击继续按钮: '{text}' (JavaScript点击)")
                except Exception as e:
                    # 备用：尝试ActionChains点击
                    try:
                        from selenium.webdriver.common.action_chains import ActionChains
                        actions = ActionChains(self.driver)
                        actions.move_to_element(continue_button).click().perform()
                        print(f"✅ 已点击继续按钮: '{text}' (ActionChains点击)")
                    except Exception as e2:
                        print(f"❌ 继续按钮点击失败: JavaScript: {e}, ActionChains: {e2}")
                        return False
                
                # 等待页面跳转
                time.sleep(1.5)
                return True
            
            # 备用：传统方法
            continue_selectors = [
                "//button[contains(text(), '繼續') or contains(text(), '继续') or contains(text(), 'Continue')]",
                "//a[contains(text(), '繼續') or contains(text(), '继续')]"
            ]
            
            for selector in continue_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            text = element.text.strip()
                            print(f"✅ 找到继续按钮: '{text}'")
                            
                            # 高亮并点击
                            self.driver.execute_script("""
                                arguments[0].style.border = '3px solid #00ff00';
                                arguments[0].style.backgroundColor = 'rgba(0,255,0,0.2)';
                                arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});
                            """, element)
                            
                            time.sleep(0.5)
                            element.click()
                            print(f"✅ 已点击继续按钮: '{text}'")
                            
                            # 等待页面跳转
                            time.sleep(1.5)
                            return True
                            
                except Exception as e:
                    continue
            
            print("⚠️ 未找到继续按钮")
            return False
            
        except Exception as e:
            print(f"❌ 处理继续按钮异常: {e}")
            return False

    def _check_for_additional_buttons(self) -> bool:
        """检查页面中是否出现了新的需要处理的按钮"""
        try:
            time.sleep(2)  # 等待页面动态加载
            
            # 检查是否出现了新的按钮（优先繁体中文）
            additional_button_selectors = [
                "//button[contains(text(), '登入')]",    # 通用登入
                "//button[contains(text(), '登錄')]",    # 繁体登录
                "//button[contains(text(), '登录')]",    # 简体登录
                "//a[contains(text(), '登入')]",        # 通用登入链接
                "//a[contains(text(), '登錄')]",        # 繁体登录链接
                "//a[contains(text(), '登录')]",        # 简体登录链接
                "//button[contains(text(), '確認')]",    # 繁体确认
                "//button[contains(text(), '确认')]",    # 简体确认
                "//button[contains(text(), '下一步')]",  # 下一步
                "//button[contains(text(), 'Login')]",   # 英文登录
                "//button[contains(text(), 'Next')]",    # 英文下一步
                "//button[contains(text(), 'Confirm')]", # 英文确认
                ".login-btn",
                ".confirm-btn"
            ]
            
            for selector in additional_button_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            button_text = element.text.strip()
                            print(f"🔍 发现额外按钮: '{button_text}'")
                            
                            # 自动点击登入/确认类按钮（支持繁体中文）
                            if any(keyword in button_text for keyword in ['登入', '登錄', '登录', 'Login', '確認', '确认', '下一步', 'Next', 'Confirm']):
                                print(f"🎯 自动点击: '{button_text}'")
                                
                                # 高亮按钮
                                self.driver.execute_script("""
                                    arguments[0].style.border = '3px solid #00ff00';
                                    arguments[0].style.backgroundColor = 'rgba(0,255,0,0.2)';
                                """, element)
                                
                                time.sleep(1)
                                element.click()
                                time.sleep(3)
                                print(f"✅ 成功点击'{button_text}'按钮")
                                return True
                                
                except Exception as e:
                    continue
            
            return False
            
        except Exception as e:
            print(f"⚠️ 检查额外按钮异常: {e}")
            return False
    
    def _find_and_click_any_purchase_button(self) -> bool:
        """在活动详情页面持续寻找任何可能的购票相关按钮"""
        try:
            print("🔍 持续搜索购票相关按钮...")
            print("💡 将不断重复搜索直到找到按钮")
            
            max_search_time = 20  # 最多搜索20秒
            check_interval = 1    # 每1秒检查一次
            total_rounds = int(max_search_time / check_interval)
            
            # 更全面的按钮搜索策略
            purchase_button_strategies = [
                # 文本匹配（优先繁体中文）
                "//button[contains(text(), '購票') or contains(text(), '购票')]",
                "//a[contains(text(), '購票') or contains(text(), '购票')]",
                "//button[contains(text(), '購買') or contains(text(), '购买')]", 
                "//a[contains(text(), '購買') or contains(text(), '购买')]",
                "//button[contains(text(), '立即') and (contains(text(), '購') or contains(text(), '买'))]",
                "//button[contains(text(), '馬上') and (contains(text(), '購') or contains(text(), '买'))]",
                "//button[contains(text(), 'Buy') or contains(text(), 'Purchase')]",
                "//button[contains(text(), '登入')]",  # 添加登入按钮
                "//a[contains(text(), '登入')]",      # 添加登入链接
                "//button[contains(text(), '繼續')]", # 添加繼續按钮
                "//a[contains(text(), '繼續')]",      # 添加繼續链接
                
                # ID和class选择器
                "#buyTicketBtn", "#purchaseBtn", "#buyBtn", "#loginBtn",
                ".buy-button", ".purchase-button", ".ticket-button", ".btn-login",
                "button[class*='buy']", "button[class*='purchase']", "button[class*='ticket']", "button[class*='login']",
                
                # onclick事件
                "button[onclick*='buy']", "button[onclick*='purchase']", "button[onclick*='ticket']", "button[onclick*='login']",
                "a[onclick*='buy']", "a[onclick*='purchase']", "a[onclick*='ticket']", "a[onclick*='login']",
                
                # 通用按钮（最后尝试）
                "button", "a[role='button']"
            ]
            
            # 持续搜索循环
            for search_round in range(total_rounds):
                elapsed_time = search_round * check_interval
                
                # 每5秒显示一次进度
                if search_round % 5 == 0 and search_round > 0:
                    print(f"🔄 继续搜索购票按钮... 已搜索{elapsed_time}秒")
                
                    for strategy in purchase_button_strategies:
                        try:
                            if strategy.startswith("//"):
                                elements = self.driver.find_elements(By.XPATH, strategy)
                            else:
                                elements = self.driver.find_elements(By.CSS_SELECTOR, strategy)
                            
                            for element in elements:
                                if element.is_displayed() and element.is_enabled():
                                    text = element.text.strip()
                                    onclick = element.get_attribute('onclick') or ''
                                    
                                    # 检查是否是购票相关按钮
                                    purchase_keywords = ['購票', '购票', '購買', '购买', '立即', '馬上', 'buy', 'purchase', 'ticket', '登入', '繼續', '继续']
                                    exclude_keywords = ['facebook', 'google', 'wechat', '微信', 'share', '分享']
                                    
                                    if text:
                                        # 文本匹配
                                        has_purchase_keyword = any(keyword in text for keyword in purchase_keywords)
                                        has_exclude_keyword = any(keyword in text.lower() for keyword in exclude_keywords)
                                        
                                        if has_purchase_keyword and not has_exclude_keyword:
                                            print(f"✅ 找到目标按钮: '{text}' (第{search_round+1}轮搜索)")
                                            
                                            # 尝试点击
                                            try:
                                                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                                                time.sleep(0.3)
                                                self.driver.execute_script("arguments[0].click();", element)
                                                print(f"✅ 已点击按钮: '{text}'")
                                                
                                                # 等待页面反应
                                                time.sleep(2)
                                                new_url = self.driver.current_url
                                                print(f"🌐 点击后URL: {new_url}")
                                                
                                                # 检查是否成功跳转
                                                if "performance" in new_url:
                                                    print("🎯 检测到进入购票页面")
                                                    purchase_result = self.complete_purchase_flow()
                                                    if purchase_result.success:
                                                        print(f"🎉 {purchase_result.message}")
                                                    return True
                                                else:
                                                    print("🔄 点击后继续监控...")
                                                    break  # 跳出当前策略，进入下一轮搜索
                                                
                                            except Exception as e:
                                                print(f"❌ 点击按钮失败: {e}")
                                                continue
                                    
                                    # onclick事件匹配
                                    elif onclick and any(keyword in onclick.lower() for keyword in ['buy', 'purchase', 'ticket', 'go', 'login']):
                                        print(f"✅ 找到onclick按钮: onclick='{onclick[:50]}...' (第{search_round+1}轮搜索)")
                                        try:
                                            self.driver.execute_script("arguments[0].click();", element)
                                            print("✅ 已点击onclick按钮")
                                            time.sleep(2)
                                            
                                            # 检查跳转
                                            new_url = self.driver.current_url
                                            if "performance" in new_url:
                                                purchase_result = self.complete_purchase_flow()
                                                if purchase_result.success:
                                                    print(f"🎉 {purchase_result.message}")
                                                return True
                                            break  # 进入下一轮搜索
                                        except:
                                            continue
                                            
                        except Exception as e:
                            continue
                
                # 每轮搜索后检查页面状态
                current_url = self.driver.current_url
                if "performance" in current_url:
                    print(f"🎯 检测到页面已跳转到购票页面 (第{search_round+1}轮搜索)")
                    purchase_result = self.complete_purchase_flow()
                    if purchase_result.success:
                        print(f"🎉 {purchase_result.message}")
                    return True
                
                # 等待后进入下一轮搜索
                time.sleep(check_interval)
            
            print("⚠️ 未找到任何可点击的购票按钮")
            
            # 显示页面上所有可用按钮进行调试
            print("🔍 调试：显示页面上所有按钮...")
            self._show_all_buttons_debug()
            
            return False
            
        except Exception as e:
            print(f"❌ 扩展按钮搜索异常: {e}")
            return False
    
    def _show_all_buttons_debug(self):
        """显示页面上所有按钮的调试信息"""
        try:
            print("📊 调试信息：页面上所有按钮和链接")
            print("-" * 50)
            
            # 获取所有可能的按钮元素
            all_elements = []
            
            # 按钮元素
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                if btn.is_displayed():
                    text = btn.text.strip()
                    onclick = btn.get_attribute('onclick') or ''
                    class_name = btn.get_attribute('class') or ''
                    id_attr = btn.get_attribute('id') or ''
                    all_elements.append({
                        'type': 'button',
                        'text': text,
                        'onclick': onclick[:100] if onclick else '',
                        'class': class_name[:50] if class_name else '',
                        'id': id_attr
                    })
            
            # 链接元素
            links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                if link.is_displayed():
                    text = link.text.strip()
                    href = link.get_attribute('href') or ''
                    onclick = link.get_attribute('onclick') or ''
                    class_name = link.get_attribute('class') or ''
                    id_attr = link.get_attribute('id') or ''
                    if text or onclick or 'button' in class_name.lower():
                        all_elements.append({
                            'type': 'link',
                            'text': text,
                            'href': href[:100] if href else '',
                            'onclick': onclick[:100] if onclick else '',
                            'class': class_name[:50] if class_name else '',
                            'id': id_attr
                        })
            
            print(f"发现 {len(all_elements)} 个可交互元素:")
            for i, elem in enumerate(all_elements[:15], 1):  # 只显示前15个
                print(f"\n{i}. 类型: {elem['type']}")
                if elem['text']:
                    print(f"   文本: '{elem['text'][:80]}'")
                if elem['id']:
                    print(f"   ID: '{elem['id']}'")
                if elem['class']:
                    print(f"   Class: '{elem['class']}'")
                if elem.get('href'):
                    print(f"   Href: '{elem['href']}'")
                if elem['onclick']:
                    print(f"   Onclick: '{elem['onclick']}'")
            
            print("\n" + "-" * 50)
            
        except Exception as e:
            print(f"❌ 调试信息获取失败: {e}")
    
    def _smart_wait_for_login_button(self, max_wait_time: int = 30) -> bool:
        """持续重复寻找登入按钮直到找到为止（解决页面加载慢的问题）"""
        try:
            print("⏳ 持续寻找登入按钮...")
            print("💡 将不断重复搜索直到找到按钮或达到最大等待时间")
            
            login_selectors = [
                ".btn-login",
                "button[onclick*='submitLogin']", 
                "button[onclick*='login']",
                "//button[contains(text(), '登入')]",
                "//button[contains(text(), '登錄')]", 
                "//button[contains(text(), '登录')]",
                "//a[contains(text(), '登入')]",
                "//a[contains(text(), '登錄')]",
                "//a[contains(text(), '登录')]",
                "//button[contains(text(), 'Login')]",
                "//button[contains(text(), '繼續')]",  # 添加繼續按钮
                "//button[contains(text(), '继续')]",   # 添加继续按钮
                "//a[contains(text(), '繼續')]",       # 添加繼續链接
                "//a[contains(text(), '继续')]"        # 添加继续链接
            ]
            
            check_interval = 1  # 每1秒检查一次
            total_checks = int(max_wait_time / check_interval)
            
            for check_round in range(total_checks):
                elapsed_time = check_round * check_interval
                
                # 每5秒显示一次进度
                if check_round % 5 == 0 and check_round > 0:
                    print(f"🔄 继续搜索... 已等待{elapsed_time}秒，还会继续尝试{max_wait_time - elapsed_time}秒")
                
                # 循环尝试所有选择器
                for selector_round, selector in enumerate(login_selectors):
                    try:
                        if selector.startswith("//"):
                            elements = self.driver.find_elements(By.XPATH, selector)
                        else:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                text = element.text.strip()
                                print(f"✅ 找到目标按钮: '{text}' (第{check_round+1}轮搜索，选择器{selector_round+1})")
                                
                                # 立即点击
                                try:
                                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                                    time.sleep(0.3)
                                    self.driver.execute_script("arguments[0].click();", element)
                                    print("✅ 按钮点击完成 (持续搜索+JavaScript点击)")
                                    
                                    # 等待页面反应
                                    time.sleep(2)
                                    current_url = self.driver.current_url
                                    print(f"🌐 点击后URL: {current_url}")
                                    
                                    # 检查是否进入购票页面
                                    if "performance" in current_url:
                                        print("🎯 检测到购票页面，开始自动购票...")
                                        purchase_result = self.complete_purchase_flow()
                                        if purchase_result.success:
                                            print(f"🎉 {purchase_result.message}")
                                        else:
                                            print(f"⚠️ {purchase_result.message}")
                                        return True
                                    else:
                                        print("🔄 点击后继续监控页面变化...")
                                        # 继续下一轮搜索，页面可能还在加载
                                        break
                                    
                                except Exception as e:
                                    print(f"❌ 按钮点击失败: {e}")
                                    continue
                                    
                    except Exception as e:
                        continue
                
                # 每轮搜索后检查是否已经自动跳转
                current_url = self.driver.current_url
                if "performance" in current_url:
                    print(f"🎯 检测到页面已自动跳转到购票页面 (第{check_round+1}轮搜索)")
                    purchase_result = self.complete_purchase_flow()
                    if purchase_result.success:
                        print(f"🎉 {purchase_result.message}")
                    return True
                
                # 等待后继续下一轮搜索
                time.sleep(check_interval)
            
            print(f"⏰ 持续搜索{max_wait_time}秒后仍未找到目标按钮")
            print("💡 显示调试信息...")
            self._show_all_buttons_debug()
            return False
            
        except Exception as e:
            print(f"❌ 持续搜索按钮异常: {e}")
            return False
    
    def _analyze_page_structure(self):
        """分析购票页面结构"""
        try:
            current_url = self.driver.current_url
            page_title = self.driver.title
            print(f"📄 页面URL: {current_url}")
            print(f"📄 页面标题: {page_title}")
            
            # 分析表单结构
            forms = self.driver.find_elements(By.TAG_NAME, "form")
            print(f"📋 发现 {len(forms)} 个表单")
            
            # 分析所有select元素
            selects = self.driver.find_elements(By.TAG_NAME, "select")
            print(f"🔽 发现 {len(selects)} 个下拉选择框:")
            for i, select in enumerate(selects):
                try:
                    name = select.get_attribute('name') or '无名称'
                    id_attr = select.get_attribute('id') or '无ID'
                    options = select.find_elements(By.TAG_NAME, "option")
                    print(f"   选择框{i+1}: name='{name}', id='{id_attr}', {len(options)}个选项")
                    for j, option in enumerate(options[:5]):  # 只显示前5个选项
                        text = option.text.strip()
                        value = option.get_attribute('value')
                        print(f"     选项{j+1}: '{text}' (value='{value}')")
                except:
                    continue
            
            # 分析日期选择按钮
            date_elements = self.driver.find_elements(By.CSS_SELECTOR, ".date-box, [class*='date'], button[class*='date']")
            print(f"📅 发现 {len(date_elements)} 个日期相关元素:")
            for i, elem in enumerate(date_elements):
                try:
                    text = elem.text.strip()
                    class_attr = elem.get_attribute('class') or '无class'
                    print(f"   日期元素{i+1}: '{text}' (class='{class_attr}')")
                except:
                    continue
            
            # 分析票价按钮（寻找ticketPrice相关元素）
            print("🎟️ 分析票价按钮:")
            price_patterns = [
                "[id*='ticketPrice']",
                "[id*='price']", 
                "button[class*='price']",
                ".price-button",
                "[onclick*='price']"
            ]
            
            all_price_elements = []
            for pattern in price_patterns:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, pattern)
                    all_price_elements.extend(elements)
                except:
                    continue
            
            print(f"   发现 {len(all_price_elements)} 个票价相关元素:")
            for i, elem in enumerate(all_price_elements[:10]):  # 只显示前10个
                try:
                    id_attr = elem.get_attribute('id') or '无ID'
                    class_attr = elem.get_attribute('class') or '无class'
                    text = elem.text.strip()[:50]  # 限制文本长度
                    onclick = elem.get_attribute('onclick') or ''
                    onclick = onclick[:30] + '...' if len(onclick) > 30 else onclick
                    print(f"     票价{i+1}: id='{id_attr}', text='{text}', onclick='{onclick}'")
                except:
                    continue
            
            # 分析购买按钮
            buy_patterns = [
                "#expressPurchaseBtn",
                "button[class*='purchase']",
                "button[class*='buy']",
                "button[class*='express']",
                "[onclick*='purchase']"
            ]
            
            print("🛒 分析购买按钮:")
            for pattern in buy_patterns:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, pattern)
                    for i, elem in enumerate(elements):
                        id_attr = elem.get_attribute('id') or '无ID'
                        text = elem.text.strip()
                        print(f"   购买按钮: id='{id_attr}', text='{text}', selector='{pattern}'")
                except:
                    continue
            
            # 分析数量选择（包括ticketType类型）
            qty_elements = self.driver.find_elements(By.CSS_SELECTOR, "select[name*='qty'], input[name*='qty'], [name*='quantity'], select[name*='ticketType']")
            print(f"🔢 发现 {len(qty_elements)} 个数量选择元素:")
            for i, elem in enumerate(qty_elements):
                try:
                    name = elem.get_attribute('name') or '无名称'
                    tag = elem.tag_name
                    print(f"   数量元素{i+1}: {tag}, name='{name}'")
                except:
                    continue
                    
        except Exception as e:
            print(f"❌ 页面结构分析异常: {e}")
    
    def _handle_venue_page(self) -> bool:
        """处理venue页面（保持兼容性）"""
        return self._handle_venue_continue_flow()
    
    def _auto_select_ticket(self) -> bool:
        """自动选择票型和数量（参考项目实现）"""
        try:
            print("🎫 开始自动选票流程...")
            time.sleep(1)  # 减少等待时间，加快速度
            
            # 先获取配置信息
            ticket_prefs = self.config.get('ticket_preferences', {})
            preferred_zones = ticket_prefs.get('preferred_zones', ['VIP', 'A区', 'B区'])
            quantity = ticket_prefs.get('quantity', 2)
            
            # 跟踪数量选择是否已处理
            quantity_handled = False
            
            # 调试：分析页面结构（可选，注释掉以加快速度）
            # print("🔍 分析购票页面结构...")
            # self._analyze_page_structure()
            
            # 1. 分析ticketType0是票型还是数量
            try:
                dropdown_element = self.driver.find_element(By.NAME, "ticketType0")
                if dropdown_element:
                    select = Select(dropdown_element)
                    options = select.options
                    option_texts = [opt.text.strip() for opt in options]
                    option_values = [opt.get_attribute('value') for opt in options]
                    
                    print(f"📋 发现ticketType0下拉框")
                    print(f"   选项文本: {option_texts}")
                    print(f"   选项值: {option_values}")
                    
                    # 判断这是数量选择还是票型选择
                    # 如果所有选项都是数字且范围较大（如0-40），很可能是数量选择
                    all_numeric = all(val.isdigit() for val in option_values if val)
                    max_value = max(int(val) for val in option_values if val.isdigit()) if any(val.isdigit() for val in option_values) else 0
                    
                    if all_numeric and max_value >= 2:  # 如果是0-6这样的数字范围，肯定是数量选择
                        print("   判定: 这是数量选择框")
                        
                        # 直接使用数量作为索引（简化逻辑）
                        target_quantity = quantity
                        
                        # 确保数量在有效范围内
                        if target_quantity >= len(options):
                            target_quantity = len(options) - 1
                        elif target_quantity < 0:
                            target_quantity = 1
                        
                        try:
                            # 直接通过索引选择（数字就是索引）
                            select.select_by_index(target_quantity)
                            print(f"✅ 已设置购票数量: {target_quantity}")
                            quantity_handled = True
                        except Exception as e:
                            print(f"❌ 数量设置失败: {e}")
                            # 备用方案：选择索引1（1张票）
                            try:
                                select.select_by_index(1)
                                print(f"✅ 已设置购票数量: 1 (备用)")
                                quantity_handled = True
                            except:
                                print("❌ 备用数量设置也失败")
                    else:
                        print("   判定: 这是票型选择框")
                        # 选择第二个选项（跳过第一个可能是"请选择"）
                        if len(options) > 1:
                            select.select_by_index(1)
                            print(f"✅ 已选择票型: {option_texts[1]}")
                    
                    time.sleep(0.3)  # 减少等待时间
            except Exception as e:
                print(f"ℹ️ ticketType0处理异常: {e}")
            
            # 2. 选择日期（如果有多个场次）
            try:
                # 更精确的日期选择检测
                date_boxes = self.driver.find_elements(By.CLASS_NAME, "date-box")
                clickable_dates = []
                
                # 只检测真正可点击且包含日期内容的元素
                for date_box in date_boxes:
                    if date_box.is_displayed() and date_box.is_enabled():
                        text = date_box.text.strip()
                        # 检查是否包含日期相关内容（数字、月份等）
                        if text and (any(char.isdigit() for char in text) or 
                                   any(month in text for month in ['一月', '二月', '三月', '四月', '五月', '六月', 
                                                                 '七月', '八月', '九月', '十月', '十一月', '十二月',
                                                                 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                                                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])):
                            clickable_dates.append((date_box, text))
                
                if len(clickable_dates) > 1:
                    print(f"📅 发现 {len(clickable_dates)} 个可选场次日期")
                    # 选择第一个可用日期
                    date_box, text = clickable_dates[0]
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", date_box)
                    time.sleep(0.3)
                    date_box.click()
                    print(f"✅ 已选择日期: {text[:30]}...")
                elif len(clickable_dates) == 1:
                    print("ℹ️ 只有一个场次，无需选择日期")
                else:
                    print("ℹ️ 未发现需要选择的日期")
                    
                time.sleep(0.3)
            except:
                print("ℹ️ 日期选择检测异常，跳过")
            
            # 3. 选择票价区域
            print(f"🎯 寻找票价选项...")
            print(f"   偏好区域: {preferred_zones}")
            print(f"   购票数量: {quantity}")
            
            # 改进的票价选择逻辑 - 基于preferred_zones配置
            ticket_selected = False
            
            # 方法1：智能匹配preferred_zones配置
            print("   方法1: 根据配置匹配票价选项...")
            
            # 获取所有可能的票价元素
            all_price_elements = []
            for i in range(10):  # 检查ticketPrice0到ticketPrice9
                try:
                    price_element = self.driver.find_element(By.ID, f"ticketPrice{i}")
                    
                    # 获取该票价选项的文本信息
                    element_text = ""
                    try:
                        # 尝试获取相关的文本标签
                        parent = price_element.find_element(By.XPATH, "..")
                        element_text = parent.text.strip()
                        if not element_text:
                            # 尝试获取相邻的label元素
                            label_element = self.driver.find_element(By.CSS_SELECTOR, f"label[for='ticketPrice{i}']")
                            element_text = label_element.text.strip()
                    except:
                        # 如果无法获取文本，尝试其他方法
                        try:
                            # 查找包含该元素的行或区域
                            table_row = price_element.find_element(By.XPATH, "./ancestor::tr")
                            element_text = table_row.text.strip()
                        except:
                            element_text = f"票价选项{i}"
                    
                    all_price_elements.append({
                        'element': price_element,
                        'text': element_text,
                        'index': i
                    })
                    print(f"     票价{i}: '{element_text}'")
                    
                except:
                    continue
            
            # 根据preferred_zones模糊匹配最佳选项
            best_match = None
            best_score = 0
            
            for preferred in preferred_zones:
                # 将配置项拆分为多个关键词进行模糊匹配
                preferred_keywords = []
                
                # 提取字母、数字、价格等关键词
                import re
                
                # 提取所有可能的关键词
                words = re.findall(r'[A-Za-z]+|\d+|[$￥]\d+|[一-龟]+', preferred)
                for word in words:
                    if len(word) > 0:
                        preferred_keywords.append(word.upper())  # 转为大写进行匹配
                
                # 如果没有提取到关键词，按空格分割
                if not preferred_keywords:
                    preferred_keywords = [kw.strip().upper() for kw in preferred.split() if len(kw.strip()) > 0]
                
                print(f"   配置 '{preferred}' 的关键词: {preferred_keywords}")
                
                for price_info in all_price_elements:
                    price_text_upper = price_info['text'].upper()
                    
                    # 计算匹配得分
                    match_score = 0
                    matched_keywords = []
                    
                    for keyword in preferred_keywords:
                        if keyword in price_text_upper:
                            match_score += 1
                            matched_keywords.append(keyword)
                    
                    # 如果匹配得分更高，更新最佳匹配
                    if match_score > best_score:
                        best_score = match_score
                        best_match = price_info
                        print(f"   💯 更好匹配: '{price_info['text']}' (得分:{match_score}, 匹配:{matched_keywords})")
                    elif match_score > 0:
                        print(f"   ✓ 部分匹配: '{price_info['text']}' (得分:{match_score}, 匹配:{matched_keywords})")
            
            # 显示最终选择结果
            if best_match and best_score > 0:
                print(f"✅ 最佳匹配票价: '{best_match['text']}' (最终得分:{best_score})")
            
            # 如果找到匹配的选项，点击它
            if best_match and best_score > 0:
                try:
                    element = best_match['element']
                    self.driver.execute_script("arguments[0].click();", element)
                    print(f"✅ 已选择模糊匹配的票价选项 {best_match['index']}: '{best_match['text']}'")
                    ticket_selected = True
                except Exception as e:
                    print(f"❌ 点击匹配选项失败: {e}")
            
            # 如果没有找到匹配的，使用备用方法
            if not ticket_selected:
                print("   方法2: 备用选择（未找到匹配的preferred_zones）...")
                # 选择第一个可用的票价选项
                for price_info in all_price_elements:
                    try:
                        element = price_info['element']
                        self.driver.execute_script("arguments[0].click();", element)
                        print(f"✅ 已选择备用票价选项 {price_info['index']}: '{price_info['text']}'")
                        ticket_selected = True
                        break
                    except Exception as e:
                        continue
            
            # 方法3：如果仍然失败，尝试强制选择任何票价相关元素
            if not ticket_selected:
                print("   方法3: 强制尝试页面上任何票价相关元素...")
                
                # 尝试所有可能的票价相关选择器
                force_selectors = [
                    "[id^='ticketPrice']",  # 任何以ticketPrice开头的ID
                    "input[type='radio']",  # 单选按钮
                ]
                
                for selector in force_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        print(f"     尝试选择器 {selector}，找到 {len(elements)} 个元素")
                        
                        for i, elem in enumerate(elements):
                            try:
                                # 检查元素ID或名称是否包含price
                                elem_id = elem.get_attribute('id') or ''
                                elem_name = elem.get_attribute('name') or ''
                                elem_class = elem.get_attribute('class') or ''
                                
                                if 'price' in elem_id.lower() or 'price' in elem_name.lower() or 'price' in elem_class.lower():
                                    print(f"     找到票价相关元素: id='{elem_id}', name='{elem_name}'")
                                    
                                    # 强制点击
                                    self.driver.execute_script("arguments[0].click();", elem)
                                    print(f"✅ 已选择票价选项 (强制点击: {elem_id})")
                                    ticket_selected = True
                                    break
                                    
                            except Exception as e:
                                print(f"     元素 {i} 点击失败: {e}")
                                continue
                        
                        if ticket_selected:
                            break
                            
                    except Exception as e:
                        print(f"     选择器 {selector} 失败: {e}")
                        continue
            
            if not ticket_selected:
                print("❌ 无法选择票价")
                return False
            
            # 4. 设置购票数量（仅在未处理时执行）
            if not quantity_handled:
                print("🔢 寻找其他数量选择...")
            else:
                print("✅ 数量选择已完成，跳过额外搜索")
            
            if not quantity_handled:
                try:
                    # 扩展数量选择器，包括所有可能的select元素
                    qty_selectors = [
                        "select[name*='qty']",
                        "select[name*='quantity']", 
                        "select[name*='num']",
                        "select[name*='count']",
                        "select[id*='qty']",
                        "select[id*='quantity']"
                    ]
                    
                    quantity_found = False
                    for selector in qty_selectors:
                        try:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            for elem in elements:
                                if elem.is_displayed():
                                    select_obj = Select(elem)
                                    options = select_obj.options
                                    option_texts = [opt.text.strip() for opt in options if opt.text.strip()]
                                    print(f"     发现数量选择框，选项: {option_texts}")
                                    
                                    # 尝试选择指定数量（改进版）
                                    target_quantity = min(quantity, len(options) - 1)
                                    
                                    # 方法1：通过文本或value匹配
                                    for opt in options:
                                        opt_text = opt.text.strip()
                                        opt_value = opt.get_attribute('value')
                                        if opt_text == str(target_quantity) or opt_value == str(target_quantity):
                                            select_obj.select_by_value(opt_value)
                                            print(f"✅ 已设置购票数量: {target_quantity} (匹配: text='{opt_text}', value='{opt_value}')")
                                            quantity_found = True
                                            break
                                    
                                    # 方法2：通过索引直接选择
                                    if not quantity_found and target_quantity < len(options):
                                        try:
                                            select_obj.select_by_index(target_quantity)
                                            selected_option = options[target_quantity]
                                            print(f"✅ 已设置购票数量: {target_quantity} (索引选择: {selected_option.text})")
                                            quantity_found = True
                                        except Exception as e:
                                            print(f"     索引选择失败: {e}")
                                    
                                    # 方法3：备用选择
                                    if not quantity_found and len(options) > 1:
                                        select_obj.select_by_index(1)
                                        print(f"✅ 已设置购票数量: {options[1].text} (备用)")
                                        quantity_found = True
                                    
                                    if quantity_found:
                                        break
                        
                            if quantity_found:
                                break
                        except Exception as e:
                            print(f"     选择器 {selector} 异常: {e}")
                            continue
                
                    # 如果上面都没找到，检查所有select元素
                    if not quantity_found:
                        print("     检查所有select元素...")
                        all_selects = self.driver.find_elements(By.TAG_NAME, "select")
                        for i, elem in enumerate(all_selects):
                            try:
                                if elem.is_displayed():
                                    # 跳过已经处理过的ticketType0
                                    elem_name = elem.get_attribute('name') or ''
                                    if elem_name == 'ticketType0':
                                        print(f"     跳过已处理的ticketType0")
                                        continue
                                    
                                    select_obj = Select(elem)
                                    options = select_obj.options
                                    option_texts = [opt.text.strip() for opt in options if opt.text.strip()]
                                    
                                    # 如果选项看起来像数量选择（包含数字）
                                    if any(text.isdigit() and int(text) <= 10 for text in option_texts):
                                        print(f"     可能的数量选择框{i}: {option_texts}")
                                        
                                        # 尝试选择合适的数量
                                        target_quantity = min(quantity, len(options) - 1)  # 确保不超出范围
                                        
                                        # 方法1：通过value选择
                                        for opt in options:
                                            opt_text = opt.text.strip()
                                            opt_value = opt.get_attribute('value')
                                            if opt_text == str(target_quantity) or opt_value == str(target_quantity):
                                                select_obj.select_by_value(opt_value)
                                                print(f"✅ 已设置购票数量: {target_quantity} (通过value: {opt_value})")
                                                quantity_found = True
                                                break
                                        
                                        # 方法2：如果value方法失败，通过索引选择
                                        if not quantity_found and target_quantity < len(options):
                                            try:
                                                select_obj.select_by_index(target_quantity)
                                                selected_option = options[target_quantity]
                                                print(f"✅ 已设置购票数量: {target_quantity} (通过索引，选项: {selected_option.text})")
                                                quantity_found = True
                                            except Exception as idx_e:
                                                print(f"     通过索引选择失败: {idx_e}")
                                        
                                        # 方法3：如果还是失败，选择第二个选项（跳过第一个"0"）
                                        if not quantity_found and len(options) > 1:
                                            try:
                                                select_obj.select_by_index(1)
                                                print(f"✅ 已设置购票数量: {options[1].text} (备用选择)")
                                                quantity_found = True
                                            except:
                                                pass
                                        
                                        if quantity_found:
                                            break
                            except Exception as e:
                                continue
                
                    if not quantity_found:
                        print("ℹ️ 未发现额外的数量选择元素")
                    else:
                        quantity_handled = True
                        
                except Exception as e:
                    print(f"❌ 数量选择异常: {e}")
            
            time.sleep(0.5)
            
            print("✅ 票务选择完成")
            if quantity_handled:
                print(f"🎯 已成功设置购票数量: {quantity}")
            else:
                print("⚠️ 未能设置数量，可能使用页面默认值")
            
            # 自动提交订单
            if self._auto_submit_order():
                print("🎉 订单已自动提交！")
            else:
                print("⚠️ 自动提交失败，请手动完成")
            
            return True
            
        except Exception as e:
            print(f"❌ 自动选票异常: {e}")
            return False
    
    def _auto_submit_order(self) -> bool:
        """自动提交订单"""
        try:
            print("🚀 开始自动提交订单...")
            
            # 查找确定按钮（支持繁体中文）
            submit_selectors = [
                "#expressPurchaseBtn",  # 主要的购买按钮ID
                "button[onclick*='expressPurchase']",
                "//button[contains(text(), '確定')]",
                "//button[contains(text(), '确定')]",
                "//button[contains(text(), '提交')]",
                "//button[contains(text(), '購買')]",
                "//button[contains(text(), '购买')]",
                "button.btn-purchase",
                "button.btn-submit",
                "button[type='submit']"
            ]
            
            submit_button = None
            
            # 尝试各种选择器
            for selector in submit_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            text = element.text.strip()
                            # 检查按钮文本是否包含确定、提交等关键词
                            if any(keyword in text for keyword in ['確定', '确定', '提交', '購買', '购买', 'Submit', 'Confirm']):
                                submit_button = element
                                print(f"✅ 找到提交按钮: '{text}'")
                                break
                            # 对于ID选择器，即使没有文本也接受
                            elif selector == "#expressPurchaseBtn":
                                submit_button = element
                                print(f"✅ 找到提交按钮 (ID: expressPurchaseBtn)")
                                break
                    
                    if submit_button:
                        break
                        
                except Exception as e:
                    continue
            
            if not submit_button:
                print("❌ 未找到提交按钮")
                return False
            
            # 高亮并点击提交按钮
            try:
                self.driver.execute_script("""
                    arguments[0].style.border = '3px solid #ff0000';
                    arguments[0].style.backgroundColor = 'rgba(255,0,0,0.2)';
                    arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});
                """, submit_button)
                
                time.sleep(0.5)
                
                # 使用JavaScript点击，避免被遮挡
                self.driver.execute_script("arguments[0].click();", submit_button)
                print("✅ 已点击提交按钮！")
                
                # 等待页面响应
                time.sleep(2)
                
                # 检查是否成功提交
                current_url = self.driver.current_url
                if "payment" in current_url or "confirm" in current_url or "success" in current_url:
                    print("🎉 订单提交成功！已进入支付或确认页面")
                    return True
                else:
                    print("⚠️ 订单提交后页面状态待确认")
                    return True
                    
            except Exception as e:
                print(f"❌ 点击提交按钮失败: {e}")
                # 尝试常规点击
                try:
                    submit_button.click()
                    print("✅ 已使用常规方式点击提交按钮")
                    return True
                except:
                    return False
                    
        except Exception as e:
            print(f"❌ 自动提交订单异常: {e}")
            return False
    
    def _fill_purchase_form(self) -> bool:
        """填写购票表单（参考项目实现）"""
        try:
            print("📝 开始填写购票信息...")
            time.sleep(2)
            
            # 1. 勾选条款复选框
            try:
                checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
                for checkbox in checkboxes:
                    if not checkbox.is_selected() and checkbox.is_displayed():
                        self.driver.execute_script("arguments[0].click();", checkbox)
                        print("✅ 已勾选条款")
                        time.sleep(0.5)
            except:
                print("ℹ️ 未发现需要勾选的条款")
            
            # 2. 填写取票密码（如果需要）
            ticket_password = self.config.get('purchase_settings', {}).get('ticket_password', '123456')
            try:
                password_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='password'], input[name*='password']")
                for pwd_input in password_inputs:
                    if pwd_input.is_displayed():
                        pwd_input.clear()
                        pwd_input.send_keys(ticket_password)
                        print(f"✅ 已填写取票密码")
                        time.sleep(0.5)
            except:
                print("ℹ️ 未发现取票密码输入框")
            
            # 3. 选择支付方式
            payment_method = self.config.get('purchase_settings', {}).get('payment_method', 'visa')
            if payment_method == 'alipay':
                try:
                    alipay_button = self.driver.find_element(By.CSS_SELECTOR, "[data-payment-code='ALIPAY']")
                    alipay_button.click()
                    print("✅ 已选择支付宝付款")
                except:
                    print("⚠️ 未找到支付宝选项")
            else:
                # 默认使用信用卡
                try:
                    visa_button = self.driver.find_element(By.CSS_SELECTOR, "[data-payment-code='VISA']")
                    visa_button.click()
                    print("✅ 已选择信用卡付款")
                except:
                    print("ℹ️ 使用默认支付方式")
            
            time.sleep(1)
            return True
            
        except Exception as e:
            print(f"❌ 填写购票信息异常: {e}")
            return False
    
    def _submit_purchase(self) -> bool:
        """提交购票（参考项目实现）"""
        try:
            print("💳 准备提交购票...")
            
            # 查找并点击确认/提交按钮
            submit_selectors = [
                "#proceedDisplay button",
                "button[type='submit']",
                "//button[contains(text(), '确认')]",
                "//button[contains(text(), '提交')]",
                "//button[contains(text(), '去付款')]",
                "//button[contains(text(), 'Proceed')]",
                "//button[contains(text(), 'Confirm')]"
            ]
            
            for selector in submit_selectors:
                try:
                    if selector.startswith("//"):
                        submit_btn = self.driver.find_element(By.XPATH, selector)
                    else:
                        submit_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if submit_btn.is_displayed() and submit_btn.is_enabled():
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
                        time.sleep(1)
                        
                        # 最后确认
                        if self.config.get('purchase_settings', {}).get('auto_purchase', False):
                            print("🚀 自动提交购票...")
                            submit_btn.click()
                            print("✅ 已提交购票！")
                            
                            # 等待页面跳转
                            time.sleep(5)
                            
                            # 截图保存
                            timestamp = time.strftime("%Y%m%d-%H%M%S")
                            self.driver.save_screenshot(f"purchase_success_{timestamp}.png")
                            print(f"📸 已保存购票截图: purchase_success_{timestamp}.png")
                            
                            return True
                        else:
                            print("⚠️ 自动购票未启用，请手动点击提交按钮")
                            print("💡 如需启用自动购票，请在配置文件中设置 auto_purchase: true")
                            return False
                except:
                    continue
            
            print("❌ 未找到提交按钮")
            return False
            
        except Exception as e:
            print(f"❌ 提交购票异常: {e}")
            return False
    
    def complete_purchase_flow(self) -> PurchaseResult:
        """完成购票流程"""
        try:
            print("💳 开始完成购票流程...")
            
            # 检查当前页面
            current_url = self.driver.current_url
            print(f"📍 当前页面: {current_url}")
            
            # 判断是否在购票页面
            if "performance" in current_url and "venue.cityline.com" in current_url:
                print("✅ 已进入购票页面")
                
                # 只进行票务选择，不自动提交
                if self._auto_select_ticket():
                    return PurchaseResult(
                        success=True,
                        message="票务选择完成！请手动完成后续购票和支付"
                    )
                else:
                    return PurchaseResult(
                        success=False,
                        message="票务选择失败"
                    )
            else:
                print("⚠️ 未在购票页面，无法执行自动购票")
            
            purchase_settings = self.config.get('purchase_settings', {})
            
            if not purchase_settings.get('auto_purchase', False):
                print("⚠️ 自动购票已禁用，需要手动完成")
                print("💡 请手动完成以下步骤：")
                print("   1. 选择座位")
                print("   2. 确认购票数量")
                print("   3. 填写购票信息")
                print("   4. 选择支付方式")
                print("   5. 完成支付")
                
                # 等待用户手动操作
                try:
                    input("按Enter键继续（完成手动购票后）...")
                except (EOFError, KeyboardInterrupt):
                    print("\n⚠️ 输入被中断，继续流程...")
                
                return PurchaseResult(
                    success=True,
                    message="手动购票模式，等待用户完成操作"
                )
            
            # 如果启用自动购票，这里可以实现自动化逻辑
            print("🤖 自动购票功能开发中...")
            
            return PurchaseResult(
                success=False,
                message="自动购票功能尚未完全实现"
            )
            
        except Exception as e:
            return PurchaseResult(
                success=False,
                message=f"购票流程异常: {e}"
            )
    
    def run_complete_flow(self) -> bool:
        """运行完整的购票流程（参考项目风格的完整版）"""
        try:
            print("🎬 启动完整购票流程")
            print("=" * 50)
            print("💡 类似参考项目的自动化流程")
            print("🚀 增强功能：智能检测 + 优先级排序 + 多重验证")
            print()
            
            # 显示配置概览
            self._display_config_summary()
            
            # 1. 创建浏览器
            print("🔧 第1步：创建浏览器实例")
            if not self.create_browser():
                return False
            print("✅ 浏览器创建成功")
            
            choice = ""  # 初始化choice变量
            
            try:
                # 第2步：访问活动页面并处理登录
                print("🌐 第2步：访问活动页面")
                if not self.access_event_page():
                    return False
                
                # 检查是否已经在购票页面（可能在venue流程后直接跳转）
                current_url = self.driver.current_url
                if "performance" in current_url:
                    print("🎯 检测到购票页面，开始自动购票...")
                    purchase_result = self.complete_purchase_flow()
                    if purchase_result.success:
                        print(f"🎉 {purchase_result.message}")
                    else:
                        print(f"⚠️ {purchase_result.message}")
                else:
                    print("✅ 购票流程执行完成！")
                    print("💡 如果进入了购票页面，请手动完成选座和支付")
                
                # 保持浏览器开放
                try:
                    choice = input("\n按Enter关闭浏览器，或输入'keep'保持开放: ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    print("\n⚠️ 输入被中断，默认保持浏览器开放")
                    choice = 'keep'
                if choice == 'keep':
                    print("🔄 浏览器保持开放")
                    return True
                
                return True
                
            finally:
                if self.driver and choice != 'keep':
                    self.driver.quit()
                    print("🔚 浏览器已关闭")
                    
        except Exception as e:
            print(f"❌ 完整流程异常: {e}")
            return False
    
    def _display_config_summary(self):
        """显示配置概览（简化版）"""
        try:
            target_event = self.config.get('target_event', {})
            ticket_prefs = self.config.get('ticket_preferences', {})
            purchase_settings = self.config.get('purchase_settings', {})
            
            # 从URL中提取活动名称
            url = target_event.get('url', '未配置')
            activity_name = "未配置"
            if url and url != "未配置":
                # 从URL中提取活动名称
                if "nctdreamthefuturehk" in url:
                    activity_name = "NCT DREAM THE FUTURE 香港演唱会"
                elif "sekainoowariphoenix" in url:
                    activity_name = "SEKAI NO OWARI Phoenix演唱会"
                else:
                    activity_name = "Cityline演出"
            
            print("📋 当前配置概览：")
            print(f"   🎯 目标活动: {activity_name}")
            print(f"   🌐 活动URL: {url}")
            print(f"   🎫 购票数量: {ticket_prefs.get('quantity', 1)}")
            print(f"   💰 偏好区域: {ticket_prefs.get('preferred_zones', [])}")
            print(f"   🤖 自动购买: {'是' if purchase_settings.get('auto_purchase', False) else '否（需手动确认）'}")
            print(f"   ⏱️ 最大等待: {purchase_settings.get('max_wait_time', 300)}秒")
            print()
            
        except Exception as e:
            print(f"⚠️ 配置显示异常: {e}")
    
    def _send_success_notification(self):
        """发送成功通知"""
        try:
            notifications = self.config.get('notifications', {})
            
            if notifications.get('success_sound', False):
                # 播放系统提示音
                print("\a")  # 系统提示音
            
            success_msg = notifications.get('success_message', '🎉 购票成功！')
            print(f"\n{success_msg}")
            
        except Exception as e:
            print(f"⚠️ 通知发送异常: {e}")


def main():
    """主函数"""
    print("🎫 增强版独立购票系统")
    print("=" * 50)
    print("💡 最接近参考项目的完整实现")
    print("🚀 功能特点:")
    print("   ✅ 智能'前　往　购　票'按钮检测")
    print("   ✅ 优先级排序的选择策略")
    print("   ✅ 完善的venue页面继续流程")
    print("   ✅ 多重验证和错误恢复")
    print("   ✅ 配置驱动的灵活系统")
    print()
    
    # 创建购票器实例
    purchaser = ConfigDrivenTicketPurchaser()
    
    # 运行完整流程
    success = purchaser.run_complete_flow()
    
    if success:
        print("\n🎉 增强版购票系统运行完成！")
        print("💡 这是最接近参考项目的完整实现")
        print("🔧 如有问题可继续完善配置文件")
    else:
        print("\n❌ 购票流程失败")
        print("💡 建议检查:")
        print("   - 网络连接状态")
        print("   - enhanced_config.json 配置")
        print("   - 活动URL有效性")
        print("   - Chrome浏览器版本")


if __name__ == "__main__":
    main()