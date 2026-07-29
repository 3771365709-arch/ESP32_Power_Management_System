"""
按键驱动模块
============================================
硬件驱动层 - 负责按键输入检测
支持消抖、长按、短按检测
只提供原始按键状态，按键事件处理由上层实现
"""

from machine import Pin
import time
from utils.err_codes import *
from utils.logger import get_logger
from config.config import KEY_PIN_CONFIG

# 日志记录器
_log = get_logger("KEY_DRV")

# 按键状态定义
KEY_RELEASED = 0      # 释放
KEY_PRESSED = 1       # 按下
KEY_SHORT_PRESS = 2   # 短按事件
KEY_LONG_PRESS = 3    # 长按事件


class KeyDriver:
    """
    按键驱动类
    支持多按键、消抖、长按检测
    """

    def __init__(self):
        """
        初始化按键驱动
        """
        self._key_pins = KEY_PIN_CONFIG["key_pins"]
        self._key_names = KEY_PIN_CONFIG["key_names"]
        self._key_count = len(self._key_pins)

        self._debounce_ms = KEY_PIN_CONFIG["debounce_ms"]
        self._long_press_ms = KEY_PIN_CONFIG["long_press_ms"]
        self._active_level = KEY_PIN_CONFIG["active_level"]
        self._pull_up = KEY_PIN_CONFIG["pull_up"]

        self._pin_objs = []
        self._initialized = False

        # 按键状态
        self._states = [KEY_RELEASED] * self._key_count
        self._last_raw_states = [False] * self._key_count
        self._press_start_time = [0] * self._key_count
        self._debounce_counter = [0] * self._key_count
        self._long_press_triggered = [False] * self._key_count

    def init(self):
        """
        初始化所有按键引脚
        返回:
            int: 错误码
        """
        if self._initialized:
            return ERR_ALREADY_INIT

        try:
            for pin_num in self._key_pins:
                if self._pull_up:
                    pin = Pin(pin_num, Pin.IN, Pin.PULL_UP)
                else:
                    pin = Pin(pin_num, Pin.IN, Pin.PULL_DOWN)
                self._pin_objs.append(pin)

            self._initialized = True
            _log.info(f"按键驱动初始化完成，共{self._key_count}个按键")
            return ERR_OK

        except Exception as e:
            _log.error(f"按键驱动初始化失败: {e}")
            return ERR_GPIO_CONFIG_FAIL

    def _read_raw(self, index):
        """
        读取按键原始电平
        参数:
            index: 按键索引
        返回:
            bool: True=按下, False=释放
        """
        if index < 0 or index >= self._key_count:
            return False

        pin_val = self._pin_objs[index].value()
        # 转换为按下状态
        pressed = (pin_val == self._active_level)
        return pressed

    def scan(self):
        """
        扫描所有按键状态
        需要在主循环中周期性调用
        返回:
            list: 每个按键的当前事件状态
        """
        if not self._initialized:
            return [KEY_RELEASED] * self._key_count

        events = [KEY_RELEASED] * self._key_count
        now = time.ticks_ms()

        for i in range(self._key_count):
            raw_pressed = self._read_raw(i)

            # 消抖处理
            if raw_pressed == self._last_raw_states[i]:
                self._debounce_counter[i] += 1
            else:
                self._debounce_counter[i] = 0
                self._last_raw_states[i] = raw_pressed

            # 消抖稳定后才判定状态变化
            if self._debounce_counter[i] >= 2:
                if raw_pressed:
                    # 按下状态
                    if self._states[i] == KEY_RELEASED:
                        # 刚按下
                        self._press_start_time[i] = now
                        self._long_press_triggered[i] = False
                        self._states[i] = KEY_PRESSED

                    elif self._states[i] == KEY_PRESSED:
                        # 持续按下，检测长按
                        press_duration = time.ticks_diff(now, self._press_start_time[i])
                        if press_duration >= self._long_press_ms and not self._long_press_triggered[i]:
                            self._long_press_triggered[i] = True
                            events[i] = KEY_LONG_PRESS
                else:
                    # 释放状态
                    if self._states[i] == KEY_PRESSED:
                        # 刚释放
                        press_duration = time.ticks_diff(now, self._press_start_time[i])
                        if press_duration < self._long_press_ms:
                            # 短按事件
                            events[i] = KEY_SHORT_PRESS
                        self._states[i] = KEY_RELEASED
                        self._long_press_triggered[i] = False

        return events

    def get_state(self, index):
        """
        获取指定按键的当前状态
        参数:
            index: 按键索引
        返回:
            int: 按键状态
        """
        if 0 <= index < self._key_count:
            return self._states[index]
        return KEY_RELEASED

    def is_pressed(self, index):
        """
        检测按键是否按下
        参数:
            index: 按键索引
        返回:
            bool: True=按下
        """
        return self.get_state(index) == KEY_PRESSED

    def get_key_count(self):
        """获取按键数量"""
        return self._key_count

    def get_key_name(self, index):
        """获取按键名称"""
        if 0 <= index < self._key_count:
            return self._key_names[index]
        return "UNKNOWN"

    def deinit(self):
        """
        反初始化按键驱动
        """
        if self._initialized:
            self._pin_objs.clear()
            self._initialized = False
            _log.info("按键驱动已释放")
