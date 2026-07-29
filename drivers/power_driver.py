"""
电源控制驱动模块
============================================
硬件驱动层 - 负责6路电源域的GPIO控制
只提供基础的开关控制和状态查询，不包含业务逻辑
业务逻辑由services层的power_service实现
"""

from machine import Pin
import time
from utils.err_codes import *
from utils.logger import get_logger
from config.config import POWER_PIN_CONFIG

# 日志记录器
_log = get_logger("PWR_DRV")


class PowerDriver:
    """
    6路电源域驱动类
    封装GPIO操作，提供统一的电源控制接口
    支持独立控制、批量控制、紧急断电等功能
    """

    def __init__(self):
        """
        初始化电源驱动
        配置所有电源域的GPIO引脚为输出模式，默认关闭
        """
        self._enable_pins = []
        self._domain_count = len(POWER_PIN_CONFIG["enable_pins"])
        self._domain_names = POWER_PIN_CONFIG["domain_names"]
        self._initialized = False

        # 电源状态缓存，避免频繁读取GPIO
        self._power_states = [False] * self._domain_count

    def init(self):
        """
        初始化电源控制引脚
        返回:
            int: 错误码，ERR_OK表示成功
        """
        if self._initialized:
            return ERR_ALREADY_INIT

        try:
            # 初始化每一路电源的使能引脚
            for pin_num in POWER_PIN_CONFIG["enable_pins"]:
                pin = Pin(pin_num, Pin.OUT, value=0)  # 默认关闭
                self._enable_pins.append(pin)

            self._initialized = True
            _log.info(f"电源驱动初始化完成，共{self._domain_count}路电源域")
            return ERR_OK

        except Exception as e:
            _log.error(f"电源驱动初始化失败: {e}")
            return ERR_GPIO_CONFIG_FAIL

    def power_on(self, domain_id):
        """
        开启指定电源域
        参数:
            domain_id: 电源域编号 (0-5)
        返回:
            int: 错误码
        """
        if not self._initialized:
            return ERR_NOT_INITIALIZED

        if domain_id < 0 or domain_id >= self._domain_count:
            return ERR_PWR_INVALID_DOMAIN

        if self._power_states[domain_id]:
            return ERR_PWR_ALREADY_ON

        try:
            self._enable_pins[domain_id].value(1)
            self._power_states[domain_id] = True
            _log.debug(f"电源域{self._domain_names[domain_id]}已开启")
            return ERR_OK

        except Exception as e:
            _log.error(f"开启电源域{domain_id}失败: {e}")
            return ERR_PWR_SEQUENCE_FAIL

    def power_off(self, domain_id):
        """
        关闭指定电源域
        参数:
            domain_id: 电源域编号 (0-5)
        返回:
            int: 错误码
        """
        if not self._initialized:
            return ERR_NOT_INITIALIZED

        if domain_id < 0 or domain_id >= self._domain_count:
            return ERR_PWR_INVALID_DOMAIN

        if not self._power_states[domain_id]:
            return ERR_PWR_ALREADY_OFF

        try:
            self._enable_pins[domain_id].value(0)
            self._power_states[domain_id] = False
            _log.debug(f"电源域{self._domain_names[domain_id]}已关闭")
            return ERR_OK

        except Exception as e:
            _log.error(f"关闭电源域{domain_id}失败: {e}")
            return ERR_PWR_SEQUENCE_FAIL

    def power_all_on(self):
        """
        按顺序开启所有电源域（不包含延时，时序由上层控制）
        返回:
            int: 错误码
        """
        err = ERR_OK
        for i in range(self._domain_count):
            ret = self.power_on(i)
            if ret != ERR_OK and ret != ERR_PWR_ALREADY_ON:
                err = ret
                break
        return err

    def power_all_off(self):
        """
        按逆序关闭所有电源域（不包含延时，时序由上层控制）
        返回:
            int: 错误码
        """
        err = ERR_OK
        for i in range(self._domain_count - 1, -1, -1):
            ret = self.power_off(i)
            if ret != ERR_OK and ret != ERR_PWR_ALREADY_OFF:
                err = ret
                break
        return err

    def get_state(self, domain_id):
        """
        获取指定电源域状态
        参数:
            domain_id: 电源域编号
        返回:
            tuple: (错误码, 状态bool)
        """
        if not self._initialized:
            return (ERR_NOT_INITIALIZED, False)

        if domain_id < 0 or domain_id >= self._domain_count:
            return (ERR_PWR_INVALID_DOMAIN, False)

        return (ERR_OK, self._power_states[domain_id])

    def get_all_states(self):
        """
        获取所有电源域状态
        返回:
            list: bool列表，对应每路电源状态
        """
        return self._power_states.copy()

    def get_domain_count(self):
        """获取电源域数量"""
        return self._domain_count

    def get_domain_name(self, domain_id):
        """获取电源域名称"""
        if 0 <= domain_id < self._domain_count:
            return self._domain_names[domain_id]
        return "UNKNOWN"

    def emergency_shutdown(self):
        """
        紧急断电 - 立即关闭所有电源
        用于故障保护，不做任何延时
        直接操作硬件寄存器，最快速度切断
        返回:
            int: 错误码
        """
        try:
            for pin in self._enable_pins:
                pin.value(0)
            self._power_states = [False] * self._domain_count
            _log.warning("执行紧急断电，所有电源域已关闭")
            return ERR_OK

        except Exception as e:
            _log.critical(f"紧急断电失败: {e}")
            return ERR_PWR_SEQUENCE_FAIL

    def deinit(self):
        """
        反初始化电源驱动
        释放所有GPIO资源
        """
        if self._initialized:
            for pin in self._enable_pins:
                pin.value(0)
            self._enable_pins.clear()
            self._power_states = [False] * self._domain_count
            self._initialized = False
            _log.info("电源驱动已释放")
