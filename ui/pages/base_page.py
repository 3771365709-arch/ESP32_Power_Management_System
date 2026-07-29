"""
页面基类模块
============================================
所有页面的基类，定义统一接口
实际项目中可继承LVGL的页面控件
这里提供抽象接口，便于各页面实现
"""

from utils.err_codes import *
from utils.logger import get_logger
from drivers.key_driver import KEY_SHORT_PRESS, KEY_LONG_PRESS

# 日志记录器
_log = get_logger("PAGE_BASE")


class BasePage:
    """
    页面基类
    定义页面的生命周期和交互接口
    """

    def __init__(self, ui_manager, page_name="Base"):
        """
        初始化页面
        参数:
            ui_manager: UI管理器实例
            page_name: 页面名称
        """
        self._ui_mgr = ui_manager
        self._page_name = page_name
        self._initialized = False
        self._is_active = False

        # 选中项索引（用于列表/菜单页面）
        self._selected_index = 0
        self._item_count = 0

    def init(self):
        """
        初始化页面
        创建UI控件，设置初始状态
        返回:
            int: 错误码
        """
        if self._initialized:
            return ERR_ALREADY_INIT

        self._initialized = True
        _log.debug(f"页面初始化: {self._page_name}")
        return ERR_OK

    def on_enter(self):
        """页面进入时调用"""
        self._is_active = True
        self.draw()
        _log.debug(f"进入页面: {self._page_name}")

    def on_exit(self):
        """页面退出时调用"""
        self._is_active = False
        _log.debug(f"退出页面: {self._page_name}")

    def draw(self):
        """
        绘制页面内容
        子类重写此方法实现具体界面
        """
        pass

    def update(self):
        """
        周期性更新页面数据
        子类重写此方法实现动态刷新
        """
        pass

    def handle_key(self, key_index, event_type):
        """
        处理按键事件
        参数:
            key_index: 按键索引 (0=MENU, 1=OK, 2=BACK)
            event_type: 事件类型
        """
        if event_type == KEY_SHORT_PRESS:
            if key_index == 1:  # OK键
                self._on_ok_press()
        elif event_type == KEY_LONG_PRESS:
            if key_index == 1:  # OK长按
                self._on_ok_long_press()

    def _on_ok_press(self):
        """OK键短按处理，子类重写"""
        pass

    def _on_ok_long_press(self):
        """OK键长按处理，子类重写"""
        pass

    def _move_selection(self, direction):
        """
        移动选中项
        参数:
            direction: 1=向下, -1=向上
        """
        if self._item_count <= 0:
            return

        self._selected_index += direction
        if self._selected_index < 0:
            self._selected_index = self._item_count - 1
        elif self._selected_index >= self._item_count:
            self._selected_index = 0

    def is_active(self):
        """检测页面是否活跃"""
        return self._is_active

    def get_page_name(self):
        """获取页面名称"""
        return self._page_name

    def deinit(self):
        """反初始化页面"""
        if self._initialized:
            self._initialized = False
            _log.debug(f"页面释放: {self._page_name}")
