"""
监测详情页模块
============================================
显示各电源域详细监测数据
包含6路电压、6路电流、各电源域功率、3路温度
"""

from ui.pages.base_page import BasePage
from utils.logger import get_logger
from config.config import POWER_PIN_CONFIG

# 日志记录器
_log = get_logger("MON_PAGE")


class MonitorPage(BasePage):
    """
    监测详情页类
    分页显示各电源域详细数据
    """

    def __init__(self, ui_manager):
        super().__init__(ui_manager, "Monitor")
        self._view_mode = 0  # 0=电压, 1=电流, 2=功率, 3=温度
        self._mode_count = 4
        self._last_update = 0
        self._update_interval = 1000
        self._domain_names = POWER_PIN_CONFIG["domain_names"]

    def init(self):
        """初始化监测页"""
        super().init()
        self._item_count = self._mode_count
        _log.info("监测详情页初始化完成")
        return 0

    def draw(self):
        """绘制监测详情页"""
        if not self._is_active:
            return

        mon = self._ui_mgr.monitor_service
        mode_names = ["电压(V)", "电流(A)", "功率(W)", "温度(℃)"]

        _log.debug(f"[监测页] 当前显示: {mode_names[self._view_mode]}")

        if self._view_mode == 0:
            # 电压
            voltages = mon.get_voltages()
            for i, v in enumerate(voltages):
                name = self._domain_names[i] if i < len(self._domain_names) else f"CH{i}"
                _log.debug(f"  {name}: {v:.3f}V")

        elif self._view_mode == 1:
            # 电流
            currents = mon.get_currents()
            for i, c in enumerate(currents):
                name = self._domain_names[i] if i < len(self._domain_names) else f"CH{i}"
                _log.debug(f"  {name}: {c:.3f}A")

        elif self._view_mode == 2:
            # 功率
            powers = mon.get_powers()
            total = mon.get_total_power()
            peak = mon.get_peak_power()
            for i, p in enumerate(powers):
                name = self._domain_names[i] if i < len(self._domain_names) else f"CH{i}"
                _log.debug(f"  {name}: {p:.2f}W")
            _log.debug(f"  总功率: {total:.2f}W | 峰值: {peak:.2f}W")

        elif self._view_mode == 3:
            # 温度
            temps = mon.get_temperatures()
            temp_names = ["FPGA", "GPU", "BOARD"]
            for i, t in enumerate(temps):
                name = temp_names[i] if i < len(temp_names) else f"T{i}"
                _log.debug(f"  {name}: {t:.1f}℃")

    def update(self):
        """周期性更新监测数据"""
        import time
        now = time.ticks_ms()
        if time.ticks_diff(now, self._last_update) >= self._update_interval:
            self.draw()
            self._last_update = now

    def handle_key(self, key_index, event_type):
        """处理按键事件"""
        from drivers.key_driver import KEY_SHORT_PRESS

        if event_type == KEY_SHORT_PRESS:
            if key_index == 1:  # OK键 - 切换显示模式
                self._view_mode = (self._view_mode + 1) % self._mode_count
                self._selected_index = self._view_mode
                self._ui_mgr.buzzer_alarm.play_click()
                self.draw()
                return

        super().handle_key(key_index, event_type)

    def _on_ok_press(self):
        """OK键 - 已在handle_key中处理"""
        pass
