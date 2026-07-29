"""
风扇控制驱动模块
============================================
硬件驱动层 - 负责PWM风扇调速和转速检测
只提供基础的PWM控制和转速读取，不包含控制逻辑
PID温控等业务逻辑由services层实现
"""

from machine import Pin, PWM
import time
from utils.err_codes import *
from utils.logger import get_logger
from config.config import FAN_PIN_CONFIG

# 日志记录器
_log = get_logger("FAN_DRV")


class FanDriver:
    """
    PWM风扇驱动类
    支持PWM调速和转速检测
    """

    def __init__(self):
        """
        初始化风扇驱动
        """
        self._pwm_pin = FAN_PIN_CONFIG["pwm_pin"]
        self._tach_pin = FAN_PIN_CONFIG["tach_pin"]
        self._pwm_freq = FAN_PIN_CONFIG["pwm_freq"]
        self._max_rpm = FAN_PIN_CONFIG["max_rpm"]
        self._min_rpm = FAN_PIN_CONFIG["min_rpm"]
        self._pulses_per_rev = FAN_PIN_CONFIG["pulses_per_rev"]

        self._pwm = None
        self._tach = None
        self._initialized = False

        # 当前占空比 (0-100%)
        self._current_duty = 0

        # 转速检测相关
        self._pulse_count = 0
        self._last_count_time = 0
        self._current_rpm = 0

    def init(self):
        """
        初始化风扇PWM和转速检测
        返回:
            int: 错误码
        """
        if self._initialized:
            return ERR_ALREADY_INIT

        try:
            # 初始化PWM
            self._pwm = PWM(Pin(self._pwm_pin))
            self._pwm.freq(self._pwm_freq)
            self._pwm.duty(0)  # 默认停止

            # 初始化转速检测引脚（外部中断）
            self._tach = Pin(self._tach_pin, Pin.IN, Pin.PULL_UP)
            self._tach.irq(trigger=Pin.IRQ_FALLING, handler=self._tach_isr)

            self._last_count_time = time.ticks_ms()
            self._initialized = True
            _log.info("风扇驱动初始化完成")
            return ERR_OK

        except Exception as e:
            _log.error(f"风扇驱动初始化失败: {e}")
            return ERR_PWM_INIT_FAIL

    def _tach_isr(self, pin):
        """
        转速检测中断服务函数
        下降沿触发计数
        """
        self._pulse_count += 1

    def set_duty(self, duty_percent):
        """
        设置风扇占空比
        参数:
            duty_percent: 占空比百分比 (0-100)
        返回:
            int: 错误码
        """
        if not self._initialized:
            return ERR_NOT_INITIALIZED

        if duty_percent < 0 or duty_percent > 100:
            return ERR_PWM_INVALID_DUTY

        try:
            # 转换为0-1023的duty值
            duty_val = int(duty_percent * 1023 / 100)
            self._pwm.duty(duty_val)
            self._current_duty = duty_percent
            return ERR_OK

        except Exception as e:
            _log.error(f"设置风扇占空比失败: {e}")
            return ERR_PWM_SET_FAIL

    def get_duty(self):
        """
        获取当前占空比
        返回:
            float: 占空比百分比
        """
        return self._current_duty

    def read_rpm(self):
        """
        读取风扇转速(RPM)
        通过计算单位时间内的脉冲数得到转速
        返回:
            tuple: (错误码, 转速RPM)
        """
        if not self._initialized:
            return (ERR_NOT_INITIALIZED, 0)

        try:
            now = time.ticks_ms()
            dt_ms = time.ticks_diff(now, self._last_count_time)

            if dt_ms >= 1000:  # 每秒计算一次
                # 计算转速: RPM = (脉冲数 / 每转脉冲数) * (60000 / 时间ms)
                rpm = (self._pulse_count / self._pulses_per_rev) * (60000 / dt_ms)
                self._current_rpm = int(rpm)

                # 重置计数器
                self._pulse_count = 0
                self._last_count_time = now

            return (ERR_OK, self._current_rpm)

        except Exception as e:
            _log.error(f"读取风扇转速失败: {e}")
            return (ERR_SENSOR_NO_DATA, 0)

    def fan_start(self):
        """启动风扇（默认50%转速）"""
        return self.set_duty(50)

    def fan_stop(self):
        """停止风扇"""
        return self.set_duty(0)

    def fan_full_speed(self):
        """风扇全速运转"""
        return self.set_duty(100)

    def is_stall(self):
        """
        检测风扇是否堵转
        返回:
            bool: True=堵转, False=正常
        """
        err, rpm = self.read_rpm()
        if err != ERR_OK:
            return True
        # 有占空比但转速为0，认为堵转
        if self._current_duty > 10 and rpm < 100:
            return True
        return False

    def deinit(self):
        """
        反初始化风扇驱动
        释放PWM和中断资源
        """
        if self._initialized:
            if self._pwm:
                self._pwm.duty(0)
                self._pwm.deinit()
            if self._tach:
                self._tach.irq(handler=None)
            self._initialized = False
            _log.info("风扇驱动已释放")
