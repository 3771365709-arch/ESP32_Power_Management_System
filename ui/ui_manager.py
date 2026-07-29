"""
UI管理器模块
============================================
UI层 - 负责整体界面管理和页面切换
管理页面栈、按键事件分发、显示刷新
调用各页面模块，协调显示逻辑
"""

from utils.err_codes import *
from utils.logger import get_logger
from drivers.key_driver import KEY_SHORT_PRESS, KEY_LONG_PRESS

# 日志记录器
_log = get_logger("UI_MGR")

# 页面ID定义
PAGE_HOME = 0        # 主页
PAGE_MONITOR = 1     # 监测详情
PAGE_CONTROL = 2     # 控制页面
PAGE_SETTING = 3     # 设置页面
PAGE_FAULT = 4       # 故障信息
PAGE_MAX = 5         # 页面数量


class UIManager:
    """
    UI管理器类
    负责页面切换、按键分发、界面刷新
    """

    def __init__(self, power_service, monitor_service, mqtt_service, ota_service,
                 led_indicator, buzzer_alarm, key_driver):
        """
        初始化UI管理器
        参数:
            power_service: 电源管理服务
            monitor_service: 状态监测服务
            mqtt_service: MQTT服务
            ota_service: OTA服务
            led_indicator: LED指示器
            buzzer_alarm: 蜂鸣器告警
            key_driver: 按键驱动
        """
        self._power_svc = power_service
        self._monitor_svc = monitor_service
        self._mqtt_svc = mqtt_service
        self._ota_svc = ota_service
        self._led_ind = led_indicator
        self._buzzer_alarm = buzzer_alarm
        self._key_drv = key_driver

        self._initialized = False
        self._current_page = PAGE_HOME
        self._pages = {}

        # 页面上下文数据
        self._context = {}

    def init(self):
        """
        初始化UI系统
        返回:
            int: 错误码
        """
        if self._initialized:
            return ERR_ALREADY_INIT

        try:
            # 初始化所有页面
            self._init_pages()

            # 显示主页
            self._switch_page(PAGE_HOME)

            self._initialized = True
            _log.info("UI管理器初始化完成")
            return ERR_OK

        except Exception as e:
            _log.error(f"UI管理器初始化失败: {e}")
            return ERR_UI_INIT_FAIL

    def _init_pages(self):
        """初始化所有页面"""
        # 导入页面类
        from ui.pages.home_page import HomePage
        from ui.pages.monitor_page import MonitorPage
        from ui.pages.control_page import ControlPage
        from ui.pages.setting_page import SettingPage
        from ui.pages.fault_page import FaultPage

        # 创建页面对象
        self._pages[PAGE_HOME] = HomePage(self)
        self._pages[PAGE_MONITOR] = MonitorPage(self)
        self._pages[PAGE_CONTROL] = ControlPage(self)
        self._pages[PAGE_SETTING] = SettingPage(self)
        self._pages[PAGE_FAULT] = FaultPage(self)

        # 初始化各页面
        for page in self._pages.values():
            page.init()

    def _switch_page(self, page_id):
        """
        切换到指定页面
        参数:
            page_id: 页面ID
        """
        if page_id < 0 or page_id >= PAGE_MAX:
            return

        # 旧页面退出
        if self._current_page in self._pages:
            self._pages[self._current_page].on_exit()

        # 切换
        self._current_page = page_id

        # 新页面进入
        if self._current_page in self._pages:
            self._pages[self._current_page].on_enter()

        _log.debug(f"切换页面: {page_id}")

    def next_page(self):
        """切换到下一页（MENU键）"""
        next_id = (self._current_page + 1) % PAGE_MAX
        self._switch_page(next_id)
        self._buzzer_alarm.play_click()

    def prev_page(self):
        """切换到上一页"""
        prev_id = (self._current_page - 1) % PAGE_MAX
        self._switch_page(prev_id)
        self._buzzer_alarm.play_click()

    def handle_key_event(self, key_index, event_type):
        """
        处理按键事件
        参数:
            key_index: 按键索引 (0=MENU, 1=OK, 2=BACK)
            event_type: 事件类型 (短按/长按)
        """
        if not self._initialized:
            return

        # 全局按键处理
        if event_type == KEY_SHORT_PRESS:
            if key_index == 0:  # MENU键 - 翻页
                self.next_page()
                return
            elif key_index == 2:  # BACK键 - 返回主页
                if self._current_page != PAGE_HOME:
                    self._switch_page(PAGE_HOME)
                    self._buzzer_alarm.play_click()
                    return

        # 分发到当前页面
        if self._current_page in self._pages:
            self._pages[self._current_page].handle_key(key_index, event_type)

    def update(self):
        """
        更新UI显示
        需要在主循环中周期性调用
        """
        if not self._initialized:
            return

        # 更新当前页面
        if self._current_page in self._pages:
            self._pages[self._current_page].update()

    def refresh(self):
        """强制刷新当前页面"""
        if self._current_page in self._pages:
            self._pages[self._current_page].draw()

    def get_current_page(self):
        """获取当前页面ID"""
        return self._current_page

    def get_page(self, page_id):
        """获取指定页面对象"""
        return self._pages.get(page_id)

    # 服务访问接口，供页面调用
    @property
    def power_service(self):
        return self._power_svc

    @property
    def monitor_service(self):
        return self._monitor_svc

    @property
    def mqtt_service(self):
        return self._mqtt_svc

    @property
    def ota_service(self):
        return self._ota_svc

    @property
    def led_indicator(self):
        return self._led_ind

    @property
    def buzzer_alarm(self):
        return self._buzzer_alarm

    def deinit(self):
        """反初始化UI"""
        if self._initialized:
            for page in self._pages.values():
                page.deinit()
            self._pages.clear()
            self._initialized = False
            _log.info("UI管理器已释放")
