"""
设置页面模块
============================================
系统设置页面
提供风扇目标温度、告警静音、保护等级等参数设置
"""

from ui.pages.base_page import BasePage
from utils.logger import get_logger
from config.config import FAN_PID_CONFIG

# 日志记录器
_log = get_logger("SET_PAGE")

# 设置项
SETTING_ITEMS = [
    "风扇目标温度",
    "告警声音",
    "保护等级",
    "恢复默认",
    "系统信息",
]


class SettingPage(BasePage):
    """
    设置页面类
    提供系统参数配置功能
    """

    def __init__(self, ui_manager):
        super().__init__(ui_manager, "Setting")
        self._item_count = len(SETTING_ITEMS)
        self._selected_index = 0
        self._editing = False  # 是否正在编辑

        # 设置值缓存
        self._fan_target_temp = FAN_PID_CONFIG["target_temp"]
        self._buzzer_muted = False
        self._protection_level = 3  # 0=禁用, 1=告警, 2=降额, 3=全部

    def init(self):
        """初始化设置页"""
        super().init()
        _log.info("设置页面初始化完成")
        return 0

    def draw(self):
        """绘制设置菜单"""
        if not self._is_active:
            return

        _log.debug("[设置页] 系统设置:")
        for i, item in enumerate(SETTING_ITEMS):
            marker = ">" if i == self._selected_index else " "
            value = self._get_item_value(i)
            _log.debug(f"  {marker} {item}: {value}")

    def _get_item_value(self, index):
        """获取设置项当前值"""
        if index == 0:
            return f"{self._fan_target_temp:.1f}℃"
        elif index == 1:
            return "静音" if self._buzzer_muted else "开启"
        elif index == 2:
            levels = ["禁用", "告警级", "降额级", "全部"]
            return levels[self._protection_level] if self._protection_level < 4 else "全部"
        elif index == 3:
            return "执行"
        elif index == 4:
            return "查看"
        return ""

    def handle_key(self, key_index, event_type):
        """处理按键事件"""
        from drivers.key_driver import KEY_SHORT_PRESS, KEY_LONG_PRESS

        if event_type == KEY_SHORT_PRESS:
            if key_index == 1:  # OK键
                if self._editing:
                    # 确认编辑
                    self._apply_setting()
                    self._editing = False
                else:
                    # 进入编辑或执行
                    if self._selected_index in (0, 1, 2):
                        self._editing = True
                    else:
                        self._execute_item(self._selected_index)
                self._ui_mgr.buzzer_alarm.play_click()
                self.draw()
                return

        super().handle_key(key_index, event_type)

    def _move_selection(self, direction):
        """移动选中项或调整数值"""
        if self._editing:
            # 编辑模式：调整数值
            self._adjust_value(direction)
        else:
            # 浏览模式：移动光标
            super()._move_selection(direction)

        self.draw()

    def _adjust_value(self, direction):
        """调整当前编辑项的数值"""
        if self._selected_index == 0:
            # 风扇温度，步长1℃
            self._fan_target_temp += direction * 1.0
            self._fan_target_temp = max(30.0, min(80.0, self._fan_target_temp))

        elif self._selected_index == 1:
            # 告警声音，切换
            self._buzzer_muted = not self._buzzer_muted

        elif self._selected_index == 2:
            # 保护等级
            self._protection_level += direction
            self._protection_level = max(0, min(3, self._protection_level))

    def _apply_setting(self):
        """应用设置"""
        mon = self._ui_mgr.monitor_service
        buzzer = self._ui_mgr.buzzer_alarm

        if self._selected_index == 0:
            mon.set_fan_target_temp(self._fan_target_temp)
            _log.info(f"风扇目标温度设置为: {self._fan_target_temp}℃")

        elif self._selected_index == 1:
            buzzer.set_mute(self._buzzer_muted)
            _log.info(f"告警声音: {'静音' if self._buzzer_muted else '开启'}")

        elif self._selected_index == 2:
            _log.info(f"保护等级设置为: {self._protection_level}")

    def _execute_item(self, index):
        """执行特殊设置项"""
        if index == 3:
            # 恢复默认
            self._fan_target_temp = FAN_PID_CONFIG["target_temp"]
            self._buzzer_muted = False
            self._protection_level = 3
            self._ui_mgr.buzzer_alarm.play_success()
            _log.info("已恢复默认设置")

        elif index == 4:
            # 系统信息
            self._show_system_info()

        self.draw()

    def _show_system_info(self):
        """显示系统信息"""
        from config.config import SYS_CONFIG
        _log.info("=== 系统信息 ===")
        _log.info(f"设备ID: {SYS_CONFIG['device_id']}")
        _log.info(f"固件版本: {SYS_CONFIG['fw_version']}")
        _log.info(f"硬件版本: {SYS_CONFIG['hw_version']}")
        _log.info(f"生产序号: {SYS_CONFIG['serial']}")

    def _on_ok_press(self):
        """OK键 - 已在handle_key中处理"""
        pass
