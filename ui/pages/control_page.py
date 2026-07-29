"""
控制页面模块
============================================
系统控制页面
提供电源开关、风扇控制、故障复位等操作入口
"""

from ui.pages.base_page import BasePage
from utils.logger import get_logger

# 日志记录器
_log = get_logger("CTRL_PAGE")

# 菜单项
MENU_ITEMS = [
    "系统上电",
    "系统下电",
    "风扇控制",
    "复位故障",
    "紧急断电",
]


class ControlPage(BasePage):
    """
    控制页面类
    提供系统控制功能菜单
    """

    def __init__(self, ui_manager):
        super().__init__(ui_manager, "Control")
        self._item_count = len(MENU_ITEMS)
        self._selected_index = 0

    def init(self):
        """初始化控制页"""
        super().init()
        _log.info("控制页面初始化完成")
        return 0

    def draw(self):
        """绘制控制菜单"""
        if not self._is_active:
            return

        _log.debug("[控制页] 系统控制菜单:")
        for i, item in enumerate(MENU_ITEMS):
            marker = ">" if i == self._selected_index else " "
            _log.debug(f"  {marker} {item}")

    def handle_key(self, key_index, event_type):
        """处理按键事件"""
        from drivers.key_driver import KEY_SHORT_PRESS

        if event_type == KEY_SHORT_PRESS:
            if key_index == 1:  # OK键 - 执行选中项
                self._execute_item(self._selected_index)
                return

        super().handle_key(key_index, event_type)

    def _move_selection(self, direction):
        """移动选中项"""
        super()._move_selection(direction)
        self.draw()

    def _execute_item(self, index):
        """执行选中的菜单项"""
        svc = self._ui_mgr.power_service
        mon = self._ui_mgr.monitor_service
        buzzer = self._ui_mgr.buzzer_alarm

        if index == 0:
            # 系统上电
            err = svc.power_on_sequence()
            if err == 0:
                buzzer.play_success()
            else:
                buzzer.play_error()

        elif index == 1:
            # 系统下电
            err = svc.power_off_sequence()
            if err == 0:
                buzzer.play_success()

        elif index == 2:
            # 风扇控制 - 切换开关
            fan_enabled = not mon.get_fan_duty() > 0
            mon.set_fan_enabled(fan_enabled)
            buzzer.play_click()
            _log.info(f"风扇已{'开启' if fan_enabled else '关闭'}")

        elif index == 3:
            # 复位故障
            err = svc.reset_fault()
            if err == 0:
                buzzer.play_success()
                _log.info("故障已复位")
            else:
                buzzer.play_error()

        elif index == 4:
            # 紧急断电
            svc.emergency_shutdown()
            buzzer.play_error()
            _log.warning("执行紧急断电")

        self.draw()

    def _on_ok_press(self):
        """OK键 - 已在handle_key中处理"""
        pass
