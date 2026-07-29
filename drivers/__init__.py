"""
硬件驱动层模块
============================================
提供底层硬件驱动接口
- power_driver: 6路电源域控制
- adc_driver: ADC电压电流温度采集
- fan_driver: PWM风扇控制
- key_driver: 按键输入检测
- led_driver: LED状态指示
- buzzer_driver: 蜂鸣器告警
- nvs_driver: NVS非易失性存储
- wdt_driver: 看门狗定时器
"""

from drivers.power_driver import PowerDriver
from drivers.adc_driver import ADCDriver
from drivers.fan_driver import FanDriver
from drivers.key_driver import KeyDriver, KEY_RELEASED, KEY_PRESSED, KEY_SHORT_PRESS, KEY_LONG_PRESS
from drivers.led_driver import LedDriver, LED_OFF, LED_ON, LED_BLINK
from drivers.buzzer_driver import BuzzerDriver
from drivers.nvs_driver import NVSDriver
from drivers.wdt_driver import WatchdogDriver

__all__ = [
    "PowerDriver",
    "ADCDriver",
    "FanDriver",
    "KeyDriver",
    "KEY_RELEASED",
    "KEY_PRESSED",
    "KEY_SHORT_PRESS",
    "KEY_LONG_PRESS",
    "LedDriver",
    "LED_OFF",
    "LED_ON",
    "LED_BLINK",
    "BuzzerDriver",
    "NVSDriver",
    "WatchdogDriver",
]
