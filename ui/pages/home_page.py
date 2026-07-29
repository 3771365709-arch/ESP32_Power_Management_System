"""
主页模块
============================================
系统主页 - 显示关键状态概览
包含系统状态、总功率、温度、风扇转速等核心信息
"""

from ui.pages.base_page import BasePage
from utils.logger import get_logger
from services.power_service import SYS_POWER_OFF, SYS_POWER_ON, SYS_POWER_WARNING, SYS_POWER_DERATE, SYS_POWER_FAULT

# 日志记录器
_log = get_logger("HOME_PAGE")

# 状态文本映射
STATE_TEXT = {
    SYS_POWER_OFF: "待机",
    SYS_POWER_ON: "运行中",
    SYS_POWER_WARNING: "告警",
    SYS_POWER_DERATE: "降额",
    SYS_POWER_FAULT: "故障",
}


class HomePage(BasePage):
    """
    主页类
    显示系统关键状态概览
    """

    def __init__(self, ui_manager):
        super().__init__(ui_manager, "Home")
        self._last_update = 0
        self._update_interval = 500  # 刷新间隔ms

    def init(self):
        """初始化主页"""
        super().init()
        _log.info("主页初始化完成")
        return 0

    def draw(self):
        """
        绘制主页
        布局：
        顶部：标题 + 系统状态
        中部：总功率、总电能
        下部：最高温度、风扇转速、网络状态
        """
        if not self._is_active:
            return

        # 实际LVGL实现中这里会创建/更新控件
        # 这里用日志模拟界面结构
        svc = self._ui_mgr.power_service
        mon = self._ui_mgr.monitor_service
        mqtt = self._ui_mgr.mqtt_service

        sys_state = svc.get_system_state()
        state_str = STATE_TEXT.get(sys_state, "未知")

        total_power = mon.get_total_power()
        total_energy = mon.get_total_energy()
        temps = mon.get_temperatures()
        max_temp = max(temps) if temps else 0
        fan_speed = mon.get_fan_speed()
        fan_duty = mon.get_fan_duty()
        net_connected = mqtt.is_connected()

        # 界面结构描述（实际项目中替换为LVGL控件操作）
        _log.debug(
            f"[主页] 状态:{state_str} | 功率:{total_power:.1f}W | "
            f"电能:{total_energy:.3f}kWh | 温度:{max_temp:.1f}℃ | "
            f"风扇:{fan_speed}RPM({fan_duty:.0f}%) | 网络:{'已连' if net_connected else '断开'}"
        )

    def update(self):
        """周期性更新主页数据"""
        import time
        now = time.ticks_ms()
        if time.ticks_diff(now, self._last_update) >= self._update_interval:
            self.draw()
            self._last_update = now

    def _on_ok_press(self):
        """OK键短按 - 快速开关电源"""
        svc = self._ui_mgr.power_service
        state = svc.get_system_state()

        if state == SYS_POWER_OFF:
            # 关机状态 -> 上电
            err = svc.power_on_sequence()
            if err == 0:
                self._ui_mgr.buzzer_alarm.play_success()
            else:
                self._ui_mgr.buzzer_alarm.play_error()
        elif state == SYS_POWER_ON:
            # 运行状态 -> 下电
            err = svc.power_off_sequence()
            if err == 0:
                self._ui_mgr.buzzer_alarm.play_success()
        elif state == SYS_POWER_FAULT:
            # 故障状态 -> 复位故障
            svc.reset_fault()
            self._ui_mgr.buzzer_alarm.play_success()

        self.draw()

    def _on_ok_long_press(self):
        """OK键长按 - 紧急断电"""
        svc = self._ui_mgr.power_service
        svc.emergency_shutdown()
        self._ui_mgr.buzzer_alarm.play_error()
        self.draw()
