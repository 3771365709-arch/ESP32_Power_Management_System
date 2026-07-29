"""
看门狗驱动模块
============================================
硬件驱动层 - 负责看门狗定时器操作
提供系统级可靠性保障，防止程序跑飞
只提供基础看门狗操作，喂狗逻辑由上层实现
"""

try:
    from machine import WDT
except ImportError:
    # 非ESP32环境下的模拟实现
    WDT = None

from utils.err_codes import *
from utils.logger import get_logger
from config.config import SYS_CONFIG

# 日志记录器
_log = get_logger("WDT_DRV")


class WatchdogDriver:
    """
    看门狗驱动类
    封装ESP32硬件看门狗，提供系统监控功能
    """

    def __init__(self):
        """
        初始化看门狗驱动
        """
        self._timeout = SYS_CONFIG.get("wdt_timeout", 30)
        self._wdt = None
        self._initialized = False
        self._enabled = False

    def init(self, timeout=None):
        """
        初始化并启动看门狗
        参数:
            timeout: 超时时间(秒)，默认使用配置值
        返回:
            int: 错误码
        """
        if self._initialized:
            return ERR_ALREADY_INIT

        if timeout is not None:
            self._timeout = timeout

        try:
            if WDT is not None:
                # ESP32硬件看门狗
                self._wdt = WDT(timeout=int(self._timeout * 1000))
                self._enabled = True
                _log.info(f"硬件看门狗已启动，超时: {self._timeout}秒")
            else:
                _log.warning("非ESP32环境，看门狗模拟运行")

            self._initialized = True
            return ERR_OK

        except Exception as e:
            _log.error(f"看门狗初始化失败: {e}")
            return ERR_WDT_INIT_FAIL

    def feed(self):
        """
        喂狗（重置看门狗计数器）
        需要在主循环中定期调用
        返回:
            int: 错误码
        """
        if not self._initialized:
            return ERR_NOT_INITIALIZED

        if not self._enabled:
            return ERR_OK

        try:
            if self._wdt is not None:
                self._wdt.feed()
            return ERR_OK

        except Exception as e:
            _log.error(f"看门狗喂狗失败: {e}")
            return ERR_WDT_FEED_FAIL

    def enable(self):
        """
        启用看门狗
        返回:
            int: 错误码
        """
        if not self._initialized:
            return ERR_NOT_INITIALIZED

        self._enabled = True
        _log.info("看门狗已启用")
        return ERR_OK

    def disable(self):
        """
        禁用看门狗（注意：ESP32硬件看门狗一旦启动无法禁用）
        返回:
            int: 错误码
        """
        if not self._initialized:
            return ERR_NOT_INITIALIZED

        # ESP32硬件看门狗启动后不能禁用，这里只是标记
        self._enabled = False
        _log.warning("看门狗已标记禁用（硬件可能仍在运行）")
        return ERR_OK

    def is_enabled(self):
        """检测看门狗是否启用"""
        return self._enabled

    def get_timeout(self):
        """获取看门狗超时时间(秒)"""
        return self._timeout

    def deinit(self):
        """
        反初始化看门狗
        注意：ESP32硬件看门狗一旦启动无法停止
        """
        if self._initialized:
            self._enabled = False
            self._initialized = False
            _log.info("看门狗驱动已释放（硬件可能仍在运行）")
