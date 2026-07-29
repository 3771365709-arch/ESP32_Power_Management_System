"""
UI页面模块
============================================
各功能页面实现
- base_page: 页面基类
- home_page: 主页（状态概览）
- monitor_page: 监测详情页
- control_page: 控制页面
- setting_page: 设置页面
- fault_page: 故障信息页
"""

from ui.pages.base_page import BasePage
from ui.pages.home_page import HomePage
from ui.pages.monitor_page import MonitorPage
from ui.pages.control_page import ControlPage
from ui.pages.setting_page import SettingPage
from ui.pages.fault_page import FaultPage

__all__ = [
    "BasePage",
    "HomePage",
    "MonitorPage",
    "ControlPage",
    "SettingPage",
    "FaultPage",
]
