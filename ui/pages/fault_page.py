"""
故障信息页模块
============================================
显示当前故障信息和历史故障记录
包含故障码、故障描述、发生时间等信息
"""

from ui.pages.base_page import BasePage
from utils.logger import get_logger
from utils.err_codes import get_error_desc

# 日志记录器
_log = get_logger("FAULT_PAGE")


class FaultPage(BasePage):
    """
    故障信息页面类
    显示当前故障和历史记录
    """

    def __init__(self, ui_manager):
        super().__init__(ui_manager, "Fault")
        self._view_mode = 0  # 0=当前故障, 1=历史记录
        self._last_update = 0
        self._update_interval = 2000

    def init(self):
        """初始化故障页"""
        super().init()
        self._item_count = 2
        _log.info("故障信息页初始化完成")
        return 0

    def draw(self):
        """绘制故障信息页"""
        if not self._is_active:
            return

        svc = self._ui_mgr.power_service
        fault_codes = svc.get_fault_codes()
        fault_latched = svc.is_fault_latched()
        derate_active = svc.is_derate_active()

        _log.debug("[故障页] 故障信息:")
        _log.debug(f"  故障锁存: {'是' if fault_latched else '否'}")
        _log.debug(f"  降额运行: {'是' if derate_active else '否'}")

        if fault_codes:
            _log.debug(f"  当前故障数: {len(fault_codes)}")
            for i, code in enumerate(fault_codes):
                desc = get_error_desc(code)
                _log.debug(f"    [{i}] 0x{code:04X} - {desc}")
        else:
            _log.debug("  当前无故障")

    def update(self):
        """周期性更新故障信息"""
        import time
        now = time.ticks_ms()
        if time.ticks_diff(now, self._last_update) >= self._update_interval:
            self.draw()
            self._last_update = now

    def handle_key(self, key_index, event_type):
        """处理按键事件"""
        from drivers.key_driver import KEY_SHORT_PRESS

        if event_type == KEY_SHORT_PRESS:
            if key_index == 1:  # OK键 - 复位故障
                svc = self._ui_mgr.power_service
                if svc.is_fault_latched():
                    svc.reset_fault()
                    self._ui_mgr.buzzer_alarm.play_success()
                    _log.info("故障已复位")
                else:
                    self._ui_mgr.buzzer_alarm.play_click()
                self.draw()
                return

        super().handle_key(key_index, event_type)

    def _on_ok_press(self):
        """OK键 - 已在handle_key中处理"""
        pass

    def _on_ok_long_press(self):
        """OK键长按 - 清除所有故障记录"""
        svc = self._ui_mgr.power_service
        svc.reset_fault()
        self._ui_mgr.buzzer_alarm.play_success()
        _log.info("所有故障已清除")
        self.draw()
