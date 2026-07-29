"""
LED指示灯驱动模块
============================================
硬件驱动层 - 负责LED状态指示
支持常亮、熄灭、闪烁等模式
只提供基础LED控制，业务含义由上层定义
"""

from machine import Pin
import time
from utils.err_codes import *
from utils.logger import get_logger
from config.config import LED_PIN_CONFIG

# 日志记录器
_log = get_logger("LED_DRV")

# LED模式定义
LED_OFF = 0       # 熄灭
LED_ON = 1        # 常亮
LED_BLINK = 2     # 闪烁


class LedDriver:
    """
    LED指示灯驱动类
    支持多LED独立控制、闪烁模式
    """

    def __init__(self):
        """
        初始化LED驱动
        """
        self._led_pins = LED_PIN_CONFIG["led_pins"]
        self._led_names = LED_PIN_CONFIG["led_names"]
        self._led_count = len(self._led_pins)
        self._active_level = LED_PIN_CONFIG["active_level"]

        self._pin_objs = []
        self._initialized = False

        # LED状态
        self._modes = [LED_OFF] * self._led_count
        self._blink_on_ms = [500] * self._led_count
        self._blink_off_ms = [500] * self._led_count
        self._last_toggle_time = [0] * self._led_count
        self._current_state = [False] * self._led_count

    def init(self):
        """
        初始化所有LED引脚
        返回:
            int: 错误码
        """
        if self._initialized:
            return ERR_ALREADY_INIT

        try:
            for pin_num in self._led_pins:
                pin = Pin(pin_num, Pin.OUT, value=0 if self._active_level else 1)
                self._pin_objs.append(pin)

            self._initialized = True
            _log.info(f"LED驱动初始化完成，共{self._led_count}个LED")
            return ERR_OK

        except Exception as e:
            _log.error(f"LED驱动初始化失败: {e}")
            return ERR_GPIO_CONFIG_FAIL

    def _set_led(self, index, on):
        """
        设置LED亮灭
        参数:
            index: LED索引
            on: True=亮, False=灭
        """
        if 0 <= index < self._led_count:
            val = self._active_level if on else (1 - self._active_level)
            self._pin_objs[index].value(val)
            self._current_state[index] = on

    def turn_on(self, index):
        """
        点亮指定LED（常亮模式）
        参数:
            index: LED索引
        返回:
            int: 错误码
        """
        if not self._initialized:
            return ERR_NOT_INITIALIZED

        if index < 0 or index >= self._led_count:
            return ERR_INVALID_PARAM

        self._modes[index] = LED_ON
        self._set_led(index, True)
        return ERR_OK

    def turn_off(self, index):
        """
        熄灭指定LED
        参数:
            index: LED索引
        返回:
            int: 错误码
        """
        if not self._initialized:
            return ERR_NOT_INITIALIZED

        if index < 0 or index >= self._led_count:
            return ERR_INVALID_PARAM

        self._modes[index] = LED_OFF
        self._set_led(index, False)
        return ERR_OK

    def set_blink(self, index, on_ms=500, off_ms=500):
        """
        设置LED为闪烁模式
        参数:
            index: LED索引
            on_ms: 亮的时长(ms)
            off_ms: 灭的时长(ms)
        返回:
            int: 错误码
        """
        if not self._initialized:
            return ERR_NOT_INITIALIZED

        if index < 0 or index >= self._led_count:
            return ERR_INVALID_PARAM

        self._modes[index] = LED_BLINK
        self._blink_on_ms[index] = on_ms
        self._blink_off_ms[index] = off_ms
        self._last_toggle_time[index] = time.ticks_ms()
        self._set_led(index, True)
        return ERR_OK

    def update(self):
        """
        更新LED闪烁状态
        需要在主循环中周期性调用
        """
        if not self._initialized:
            return

        now = time.ticks_ms()

        for i in range(self._led_count):
            if self._modes[i] != LED_BLINK:
                continue

            if self._current_state[i]:
                # 当前亮，检查是否该灭
                if time.ticks_diff(now, self._last_toggle_time[i]) >= self._blink_on_ms[i]:
                    self._set_led(i, False)
                    self._last_toggle_time[i] = now
            else:
                # 当前灭，检查是否该亮
                if time.ticks_diff(now, self._last_toggle_time[i]) >= self._blink_off_ms[i]:
                    self._set_led(i, True)
                    self._last_toggle_time[i] = now

    def get_mode(self, index):
        """获取LED当前模式"""
        if 0 <= index < self._led_count:
            return self._modes[index]
        return LED_OFF

    def is_on(self, index):
        """检测LED是否点亮"""
        if 0 <= index < self._led_count:
            return self._current_state[index]
        return False

    def get_led_count(self):
        """获取LED数量"""
        return self._led_count

    def get_led_name(self, index):
        """获取LED名称"""
        if 0 <= index < self._led_count:
            return self._led_names[index]
        return "UNKNOWN"

    def all_off(self):
        """熄灭所有LED"""
        for i in range(self._led_count):
            self.turn_off(i)

    def all_on(self):
        """点亮所有LED"""
        for i in range(self._led_count):
            self.turn_on(i)

    def deinit(self):
        """
        反初始化LED驱动
        """
        if self._initialized:
            self.all_off()
            self._pin_objs.clear()
            self._initialized = False
            _log.info("LED驱动已释放")
