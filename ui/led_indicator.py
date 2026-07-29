"""
LED状态指示模块
============================================
UI层 - 负责系统状态的LED可视化指示
根据系统状态自动控制各LED的亮灭闪烁模式
调用drivers层的LED驱动，不直接操作硬件
"""

from utils.err_codes import *
from utils.logger import get_logger
from drivers.led_driver import LED_ON, LED_OFF, LED_BLINK
from config.config import LED_PIN_CONFIG

# 日志记录器
_log = get_logger("LED_UI")

# LED索引定义
LED_POWER = 0   # 电源指示灯
LED_RUN = 1     # 运行指示灯
LED_ALARM = 2   # 告警指示灯
LED_NET = 3     # 网络指示灯


class LedIndicator:
    """
    LED状态指示类
    根据系统状态自动管理各LED显示模式
    """

    def __init__(self, led_driver):
        """
        初始化LED指示器
        参数:
            led_driver: LED驱动实例
        """
        self._led_drv = led_driver
        self._initialized = False

        # 当前系统状态
        self._system_state = 0  # 0=关机, 1=正常, 2=告警, 3=降额, 4=故障
        self._net_connected = False

    def init(self):
        """
        初始化LED指示
        返回:
            int: 错误码
        """
        if self._initialized:
            return ERR_ALREADY_INIT

        try:
            # 初始状态：所有灯灭
            self._led_drv.all_off()

            self._initialized = True
            _log.info("LED状态指示初始化完成")
            return ERR_OK

        except Exception as e:
            _log.error(f"LED指示初始化失败: {e}")
            return ERR_UI_INIT_FAIL

    def update_system_state(self, state):
        """
        更新系统状态，同步更新LED显示
        参数:
            state: 系统电源状态 (0-4)
        """
        if not self._initialized:
            return

        self._system_state = state

        # 电源灯
        if state == 0:
            # 关机：电源灯慢闪
            self._led_drv.set_blink(LED_POWER, 1000, 1000)
        else:
            # 开机：电源灯常亮
            self._led_drv.turn_on(LED_POWER)

        # 运行灯
        if state == 1:
            # 正常运行：慢闪
            blink_cfg = LED_PIN_CONFIG["blink_run"]
            self._led_drv.set_blink(LED_RUN, blink_cfg[0], blink_cfg[1])
        elif state == 2 or state == 3:
            # 告警/降额：快闪
            self._led_drv.set_blink(LED_RUN, 200, 200)
        else:
            # 关机/故障：灭
            self._led_drv.turn_off(LED_RUN)

        # 告警灯
        if state == 4:
            # 故障：快闪
            blink_cfg = LED_PIN_CONFIG["blink_alarm"]
            self._led_drv.set_blink(LED_ALARM, blink_cfg[0], blink_cfg[1])
        elif state == 2 or state == 3:
            # 告警/降额：常亮
            self._led_drv.turn_on(LED_ALARM)
        else:
            # 正常：灭
            self._led_drv.turn_off(LED_ALARM)

    def update_network_state(self, connected):
        """
        更新网络连接状态
        参数:
            connected: True=已连接
        """
        if not self._initialized:
            return

        self._net_connected = connected

        if connected:
            # 已连接：常亮
            self._led_drv.turn_on(LED_NET)
        else:
            # 未连接：慢闪
            blink_cfg = LED_PIN_CONFIG["blink_net"]
            self._led_drv.set_blink(LED_NET, blink_cfg[0], blink_cfg[1])

    def indicate_power_on(self):
        """指示上电成功"""
        if self._initialized:
            self._led_drv.turn_on(LED_POWER)

    def indicate_fault(self):
        """指示故障状态"""
        if self._initialized:
            blink_cfg = LED_PIN_CONFIG["blink_alarm"]
            self._led_drv.set_blink(LED_ALARM, blink_cfg[0], blink_cfg[1])

    def clear_fault(self):
        """清除故障指示"""
        if self._initialized:
            self._led_drv.turn_off(LED_ALARM)

    def update(self):
        """
        更新LED闪烁状态
        需要在主循环中调用
        """
        if self._initialized:
            self._led_drv.update()

    def deinit(self):
        """反初始化"""
        if self._initialized:
            self._led_drv.all_off()
            self._initialized = False
            _log.info("LED状态指示已释放")
