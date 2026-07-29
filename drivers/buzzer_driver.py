"""
蜂鸣器驱动模块
============================================
硬件驱动层 - 负责蜂鸣器PWM控制
支持多种告警音模式
只提供基础蜂鸣器控制，告警逻辑由上层实现
"""

from machine import Pin, PWM
import time
from utils.err_codes import *
from utils.logger import get_logger
from config.config import BUZZER_PIN_CONFIG

# 日志记录器
_log = get_logger("BUZ_DRV")


class BuzzerDriver:
    """
    蜂鸣器驱动类
    支持PWM调频、多种告警模式
    """

    def __init__(self):
        """
        初始化蜂鸣器驱动
        """
        self._pwm_pin = BUZZER_PIN_CONFIG["pwm_pin"]
        self._default_freq = BUZZER_PIN_CONFIG["default_freq"]
        self._patterns = BUZZER_PIN_CONFIG["patterns"]

        self._pwm = None
        self._initialized = False

        # 播放状态
        self._playing = False
        self._current_pattern = None
        self._pattern_index = 0
        self._note_start_time = 0
        self._current_note = None
        self._repeat = False

    def init(self):
        """
        初始化蜂鸣器PWM
        返回:
            int: 错误码
        """
        if self._initialized:
            return ERR_ALREADY_INIT

        try:
            self._pwm = PWM(Pin(self._pwm_pin))
            self._pwm.freq(self._default_freq)
            self._pwm.duty(0)  # 默认静音

            self._initialized = True
            _log.info("蜂鸣器驱动初始化完成")
            return ERR_OK

        except Exception as e:
            _log.error(f"蜂鸣器驱动初始化失败: {e}")
            return ERR_PWM_INIT_FAIL

    def _start_tone(self, freq):
        """
        开始发声
        参数:
            freq: 频率(Hz)
        """
        if self._pwm:
            self._pwm.freq(freq)
            self._pwm.duty(512)  # 50%占空比

    def _stop_tone(self):
        """停止发声"""
        if self._pwm:
            self._pwm.duty(0)

    def play_pattern(self, pattern_name, repeat=False):
        """
        播放指定的音效模式
        参数:
            pattern_name: 模式名称 (click/success/error/alarm)
            repeat: 是否循环播放
        返回:
            int: 错误码
        """
        if not self._initialized:
            return ERR_NOT_INITIALIZED

        if pattern_name not in self._patterns:
            return ERR_INVALID_PARAM

        self._current_pattern = self._patterns[pattern_name]
        self._pattern_index = 0
        self._repeat = repeat
        self._playing = True
        self._note_start_time = time.ticks_ms()
        self._current_note = self._current_pattern[0]

        # 播放第一个音符
        self._start_tone(self._current_note[0])

        _log.debug(f"播放蜂鸣器模式: {pattern_name}")
        return ERR_OK

    def stop(self):
        """停止播放"""
        self._playing = False
        self._stop_tone()
        self._current_pattern = None

    def beep(self, freq=None, duration_ms=100):
        """
        简单的单音蜂鸣
        参数:
            freq: 频率(Hz)，默认使用默认频率
            duration_ms: 持续时间(ms)
        返回:
            int: 错误码
        """
        if not self._initialized:
            return ERR_NOT_INITIALIZED

        if freq is None:
            freq = self._default_freq

        self._start_tone(freq)
        time.sleep_ms(duration_ms)
        self._stop_tone()
        return ERR_OK

    def update(self):
        """
        更新蜂鸣器播放状态
        需要在主循环中周期性调用
        """
        if not self._playing or not self._current_pattern:
            return

        now = time.ticks_ms()
        freq, duration_ms, interval_ms = self._current_note

        # 检查当前音符是否播放完毕
        if time.ticks_diff(now, self._note_start_time) >= duration_ms:
            # 停止发声，进入间隔
            self._stop_tone()

            # 检查间隔是否结束
            if time.ticks_diff(now, self._note_start_time) >= duration_ms + interval_ms:
                # 下一个音符
                self._pattern_index += 1

                if self._pattern_index >= len(self._current_pattern):
                    # 模式播放完毕
                    if self._repeat:
                        # 循环播放
                        self._pattern_index = 0
                    else:
                        # 结束
                        self._playing = False
                        return

                # 播放新音符
                self._current_note = self._current_pattern[self._pattern_index]
                self._note_start_time = now
                self._start_tone(self._current_note[0])

    def is_playing(self):
        """检测是否正在播放"""
        return self._playing

    def play_click(self):
        """播放按键点击音"""
        return self.play_pattern("click")

    def play_success(self):
        """播放操作成功音"""
        return self.play_pattern("success")

    def play_error(self):
        """播放操作失败音"""
        return self.play_pattern("error")

    def play_alarm(self, repeat=True):
        """播放故障告警音"""
        return self.play_pattern("alarm", repeat=repeat)

    def deinit(self):
        """
        反初始化蜂鸣器驱动
        """
        if self._initialized:
            self.stop()
            if self._pwm:
                self._pwm.deinit()
            self._initialized = False
            _log.info("蜂鸣器驱动已释放")
