"""
蜂鸣器告警模块
============================================
UI层 - 负责系统告警的声音提示
根据告警级别播放不同的蜂鸣器模式
调用drivers层的蜂鸣器驱动，不直接操作硬件
"""

from utils.err_codes import *
from utils.logger import get_logger

# 日志记录器
_log = get_logger("BUZ_UI")

# 告警级别定义
ALARM_NONE = 0      # 无告警
ALARM_WARNING = 1   # 告警级
ALARM_DERATE = 2    # 降额级
ALARM_CRITICAL = 3  # 严重故障级


class BuzzerAlarm:
    """
    蜂鸣器告警类
    根据系统告警级别自动控制蜂鸣器
    """

    def __init__(self, buzzer_driver):
        """
        初始化蜂鸣器告警
        参数:
            buzzer_driver: 蜂鸣器驱动实例
        """
        self._buzzer_drv = buzzer_driver
        self._initialized = False

        self._alarm_level = ALARM_NONE
        self._muted = False  # 静音标志

    def init(self):
        """
        初始化蜂鸣器告警
        返回:
            int: 错误码
        """
        if self._initialized:
            return ERR_ALREADY_INIT

        try:
            self._initialized = True
            _log.info("蜂鸣器告警初始化完成")
            return ERR_OK

        except Exception as e:
            _log.error(f"蜂鸣器告警初始化失败: {e}")
            return ERR_UI_INIT_FAIL

    def set_alarm_level(self, level):
        """
        设置告警级别，自动播放对应音效
        参数:
            level: 告警级别 (0-3)
        """
        if not self._initialized:
            return

        if level == self._alarm_level:
            return

        self._alarm_level = level

        if self._muted:
            return

        # 停止当前播放
        self._buzzer_drv.stop()

        if level == ALARM_NONE:
            # 无告警，不发声
            pass
        elif level == ALARM_WARNING:
            # 告警级：偶尔提示
            self._buzzer_drv.play_pattern("success")
        elif level == ALARM_DERATE:
            # 降额级：间隔告警
            self._buzzer_drv.play_pattern("error")
        elif level == ALARM_CRITICAL:
            # 严重故障：连续告警
            self._buzzer_drv.play_alarm(repeat=True)

    def trigger_warning(self):
        """触发一次告警提示音"""
        if not self._initialized or self._muted:
            return
        self._buzzer_drv.play_pattern("success")

    def trigger_error(self):
        """触发一次错误提示音"""
        if not self._initialized or self._muted:
            return
        self._buzzer_drv.play_pattern("error")

    def play_click(self):
        """播放按键点击音"""
        if not self._initialized or self._muted:
            return
        self._buzzer_drv.play_click()

    def play_success(self):
        """播放操作成功音"""
        if not self._initialized or self._muted:
            return
        self._buzzer_drv.play_success()

    def play_error(self):
        """播放操作失败音"""
        if not self._initialized or self._muted:
            return
        self._buzzer_drv.play_error()

    def start_critical_alarm(self):
        """启动严重故障连续告警"""
        if not self._initialized or self._muted:
            return
        self._buzzer_drv.play_alarm(repeat=True)
        self._alarm_level = ALARM_CRITICAL

    def stop_alarm(self):
        """停止告警"""
        if self._initialized:
            self._buzzer_drv.stop()
            self._alarm_level = ALARM_NONE

    def set_mute(self, muted):
        """
        设置静音
        参数:
            muted: True=静音
        """
        self._muted = muted
        if muted:
            self._buzzer_drv.stop()

    def toggle_mute(self):
        """切换静音状态"""
        self.set_mute(not self._muted)
        return self._muted

    def is_muted(self):
        """检测是否静音"""
        return self._muted

    def get_alarm_level(self):
        """获取当前告警级别"""
        return self._alarm_level

    def update(self):
        """
        更新蜂鸣器播放状态
        需要在主循环中调用
        """
        if self._initialized:
            self._buzzer_drv.update()

    def deinit(self):
        """反初始化"""
        if self._initialized:
            self._buzzer_drv.stop()
            self._initialized = False
            _log.info("蜂鸣器告警已释放")
