"""
UI层模块
============================================
用户界面与交互层
- ui_manager: UI管理器（页面切换、按键分发）
- led_indicator: LED状态指示
- buzzer_alarm: 蜂鸣器告警
- pages: 各功能页面
"""

from ui.ui_manager import UIManager, PAGE_HOME, PAGE_MONITOR, PAGE_CONTROL, PAGE_SETTING, PAGE_FAULT
from ui.led_indicator import LedIndicator
from ui.buzzer_alarm import BuzzerAlarm, ALARM_NONE, ALARM_WARNING, ALARM_DERATE, ALARM_CRITICAL

__all__ = [
    "UIManager",
    "PAGE_HOME",
    "PAGE_MONITOR",
    "PAGE_CONTROL",
    "PAGE_SETTING",
    "PAGE_FAULT",
    "LedIndicator",
    "BuzzerAlarm",
    "ALARM_NONE",
    "ALARM_WARNING",
    "ALARM_DERATE",
    "ALARM_CRITICAL",
]
