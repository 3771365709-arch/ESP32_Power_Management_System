"""
main.py - 主程序入口
============================================
ESP32异构算力板卡智能电源与状态管控系统
三层架构：driver(驱动层) → service(服务层) → ui(UI层)
负责系统初始化、主循环调度、异常处理
"""

import time
import gc
import sys

# 导入工具类
from utils.err_codes import ERR_OK, get_error_desc
from utils.logger import get_logger, set_log_level, LOG_INFO

# 设置日志级别
set_log_level(LOG_INFO)
_log = get_logger("MAIN")

# 全局系统对象
_system = None


class PowerManagementSystem:
    """
    电源管理系统主类
    整合所有模块，提供统一的初始化和主循环
    """

    def __init__(self):
        """初始化系统对象"""
        self._running = False
        self._start_time = 0
        self._loop_count = 0

        # 驱动层对象
        self._power_drv = None
        self._adc_drv = None
        self._fan_drv = None
        self._key_drv = None
        self._led_drv = None
        self._buzzer_drv = None
        self._nvs_drv = None
        self._wdt_drv = None

        # 服务层对象
        self._power_svc = None
        self._monitor_svc = None
        self._mqtt_svc = None
        self._modbus_svc = None
        self._ota_svc = None

        # UI层对象
        self._led_ind = None
        self._buzzer_alarm = None
        self._ui_mgr = None

    def init(self):
        """
        系统初始化
        按依赖顺序初始化各层模块
        返回:
            bool: True=成功
        """
        _log.info("=" * 50)
        _log.info("ESP32异构算力板卡智能电源管理系统启动")
        _log.info("=" * 50)

        try:
            # ========== 1. 驱动层初始化 ==========
            _log.info("--- 初始化驱动层 ---")
            self._init_drivers()

            # ========== 2. 服务层初始化 ==========
            _log.info("--- 初始化服务层 ---")
            self._init_services()

            # ========== 3. UI层初始化 ==========
            _log.info("--- 初始化UI层 ---")
            self._init_ui()

            # ========== 4. 看门狗启动 ==========
            _log.info("--- 启动系统看门狗 ---")
            self._start_watchdog()

            # ========== 5. 启动计数 ==========
            self._record_boot()

            self._start_time = time.ticks_ms()
            _log.info("系统初始化完成，进入主循环")
            return True

        except Exception as e:
            _log.critical(f"系统初始化失败: {e}")
            import sys
            sys.print_exception(e)
            return False

    def _init_drivers(self):
        """初始化所有驱动模块"""
        from drivers import (
            PowerDriver, ADCDriver, FanDriver, KeyDriver,
            LedDriver, BuzzerDriver, NVSDriver, WatchdogDriver
        )

        # NVS存储（最先初始化，其他模块可能依赖）
        self._nvs_drv = NVSDriver()
        err = self._nvs_drv.init()
        if err != ERR_OK:
            _log.warning(f"NVS初始化失败: {get_error_desc(err)}")

        # 电源驱动
        self._power_drv = PowerDriver()
        self._power_drv.init()

        # ADC驱动
        self._adc_drv = ADCDriver()
        self._adc_drv.init()

        # 风扇驱动
        self._fan_drv = FanDriver()
        self._fan_drv.init()

        # 按键驱动
        self._key_drv = KeyDriver()
        self._key_drv.init()

        # LED驱动
        self._led_drv = LedDriver()
        self._led_drv.init()

        # 蜂鸣器驱动
        self._buzzer_drv = BuzzerDriver()
        self._buzzer_drv.init()

        # 看门狗驱动（先创建，最后启动）
        self._wdt_drv = WatchdogDriver()

        _log.info("驱动层初始化完成")

    def _init_services(self):
        """初始化所有服务模块"""
        from services import (
            PowerService, MonitorService, MQTTService, ModbusService, OTAService
        )

        # 电源管理服务
        self._power_svc = PowerService(self._power_drv, self._adc_drv, self._nvs_drv)
        self._power_svc.init()

        # 状态监测服务
        self._monitor_svc = MonitorService(self._adc_drv, self._fan_drv, self._nvs_drv)
        self._monitor_svc.init()

        # MQTT通信服务
        self._mqtt_svc = MQTTService(self._power_svc, self._monitor_svc)
        self._mqtt_svc.init()

        # Modbus-RTU服务
        self._modbus_svc = ModbusService(self._power_svc, self._monitor_svc)
        self._modbus_svc.init()

        # OTA升级服务
        self._ota_svc = OTAService(self._nvs_drv)
        self._ota_svc.init()

        _log.info("服务层初始化完成")

    def _init_ui(self):
        """初始化UI层模块"""
        from ui import LedIndicator, BuzzerAlarm, UIManager

        # LED状态指示
        self._led_ind = LedIndicator(self._led_drv)
        self._led_ind.init()

        # 蜂鸣器告警
        self._buzzer_alarm = BuzzerAlarm(self._buzzer_drv)
        self._buzzer_alarm.init()

        # UI管理器
        self._ui_mgr = UIManager(
            self._power_svc,
            self._monitor_svc,
            self._mqtt_svc,
            self._ota_svc,
            self._led_ind,
            self._buzzer_alarm,
            self._key_drv,
        )
        self._ui_mgr.init()

        _log.info("UI层初始化完成")

    def _start_watchdog(self):
        """启动看门狗"""
        from config.config import SYS_CONFIG
        if SYS_CONFIG.get("wdt_enable", True):
            self._wdt_drv.init()
            _log.info("看门狗已启动")
        else:
            _log.info("看门狗已禁用（配置）")

    def _record_boot(self):
        """记录启动次数"""
        try:
            from config.config import NVS_KEYS
            err, count = self._nvs_drv.read_int(NVS_KEYS["sys"]["boot_count"], 0)
            self._nvs_drv.write_int(NVS_KEYS["sys"]["boot_count"], count + 1)
            _log.info(f"这是第 {count + 1} 次启动")
        except Exception as e:
            _log.warning(f"记录启动次数失败: {e}")

    def run(self):
        """
        主循环
        周期性调度各模块更新
        """
        self._running = True
        _log.info("主循环开始运行")

        # 任务调度计时器
        last_fast_task = time.ticks_ms()   # 快速任务（10ms）
        last_medium_task = time.ticks_ms() # 中速任务（100ms）
        last_slow_task = time.ticks_ms()   # 慢速任务（1000ms）

        try:
            while self._running:
                now = time.ticks_ms()

                # ========== 快速任务 (10ms) ==========
                if time.ticks_diff(now, last_fast_task) >= 10:
                    self._fast_tasks()
                    last_fast_task = now

                # ========== 中速任务 (100ms) ==========
                if time.ticks_diff(now, last_medium_task) >= 100:
                    self._medium_tasks()
                    last_medium_task = now

                # ========== 慢速任务 (1000ms) ==========
                if time.ticks_diff(now, last_slow_task) >= 1000:
                    self._slow_tasks()
                    last_slow_task = now

                # 喂狗
                self._wdt_drv.feed()

                # 让出CPU（避免忙等）
                time.sleep_ms(1)

                self._loop_count += 1

        except KeyboardInterrupt:
            _log.info("收到中断信号，退出主循环")
        except Exception as e:
            _log.critical(f"主循环异常: {e}")
            import sys
            sys.print_exception(e)
            # 异常时尝试安全下电
            self._emergency_shutdown()
        finally:
            self._shutdown()

    def _fast_tasks(self):
        """快速任务（10ms周期）- 按键、LED、蜂鸣器"""
        # 按键扫描
        key_events = self._key_drv.scan()
        for i, event in enumerate(key_events):
            if event != 0:  # 有事件
                self._ui_mgr.handle_key_event(i, event)

        # LED更新
        self._led_ind.update()

        # 蜂鸣器更新
        self._buzzer_alarm.update()

    def _medium_tasks(self):
        """中速任务（100ms周期）- 监测、保护、UI"""
        # 监测数据更新
        self._monitor_svc.update()

        # 保护检查
        voltages = self._monitor_svc.get_voltages()
        currents = self._monitor_svc.get_currents()
        temps = self._monitor_svc.get_temperatures()
        self._power_svc.check_protections(voltages, currents, temps)

        # 掉电检测（第一路电压作为输入）
        if voltages:
            self._power_svc.check_power_loss(voltages[0])

        # UI更新
        self._ui_mgr.update()

        # Modbus通信
        self._modbus_svc.update()

        # 更新LED系统状态
        sys_state = self._power_svc.get_system_state()
        self._led_ind.update_system_state(sys_state)

        # 更新蜂鸣器告警级别
        self._update_alarm_level(sys_state)

    def _slow_tasks(self):
        """慢速任务（1s周期）- MQTT、OTA、内存管理"""
        # MQTT通信
        self._mqtt_svc.update()

        # 更新网络状态LED
        self._led_ind.update_network_state(self._mqtt_svc.is_connected())

        # OTA试运行超时检查
        self._ota_svc.check_trial_timeout()

        # 垃圾回收
        gc.collect()

        # 内存监控（调试用）
        # mem_free = gc.mem_free()
        # _log.debug(f"空闲内存: {mem_free} bytes")

    def _update_alarm_level(self, sys_state):
        """根据系统状态更新告警级别"""
        from services.power_service import (
            SYS_POWER_OFF, SYS_POWER_ON, SYS_POWER_WARNING,
            SYS_POWER_DERATE, SYS_POWER_FAULT
        )
        from ui.buzzer_alarm import ALARM_NONE, ALARM_WARNING, ALARM_DERATE, ALARM_CRITICAL

        if sys_state == SYS_POWER_FAULT:
            level = ALARM_CRITICAL
        elif sys_state == SYS_POWER_DERATE:
            level = ALARM_DERATE
        elif sys_state == SYS_POWER_WARNING:
            level = ALARM_WARNING
        else:
            level = ALARM_NONE

        self._buzzer_alarm.set_alarm_level(level)

    def _emergency_shutdown(self):
        """紧急停机处理"""
        _log.warning("执行紧急停机流程")
        try:
            if self._power_svc:
                self._power_svc.emergency_shutdown()
        except Exception:
            pass

    def _shutdown(self):
        """系统正常关闭"""
        _log.info("系统关闭中...")
        self._running = False

        # 反初始化各层（逆序）
        try:
            if self._ui_mgr:
                self._ui_mgr.deinit()
            if self._buzzer_alarm:
                self._buzzer_alarm.deinit()
            if self._led_ind:
                self._led_ind.deinit()

            if self._ota_svc:
                self._ota_svc.deinit()
            if self._modbus_svc:
                self._modbus_svc.deinit()
            if self._mqtt_svc:
                self._mqtt_svc.deinit()
            if self._monitor_svc:
                self._monitor_svc.deinit()
            if self._power_svc:
                self._power_svc.deinit()

            if self._wdt_drv:
                self._wdt_drv.deinit()
            if self._buzzer_drv:
                self._buzzer_drv.deinit()
            if self._led_drv:
                self._led_drv.deinit()
            if self._key_drv:
                self._key_drv.deinit()
            if self._fan_drv:
                self._fan_drv.deinit()
            if self._adc_drv:
                self._adc_drv.deinit()
            if self._power_drv:
                self._power_drv.deinit()
            if self._nvs_drv:
                self._nvs_drv.deinit()
        except Exception as e:
            _log.error(f"关闭过程异常: {e}")

        run_time = time.ticks_diff(time.ticks_ms(), self._start_time) / 1000
        _log.info(f"系统已关闭，运行时长: {run_time:.1f}秒，循环次数: {self._loop_count}")

    def stop(self):
        """停止主循环"""
        self._running = False


def main():
    """主函数"""
    global _system

    print("\n")
    print("╔══════════════════════════════════════════╗")
    print("║  ESP32 异构算力板卡智能电源管理系统     ║")
    print("║  版本: v1.0.0                            ║")
    print("╚══════════════════════════════════════════╝")
    print()

    # 创建系统对象
    _system = PowerManagementSystem()

    # 初始化
    if not _system.init():
        print("系统初始化失败，程序退出")
        return

    # 运行主循环
    _system.run()


# 程序入口
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"程序崩溃: {e}")
        import sys
        sys.print_exception(e)
        # 崩溃后延迟重启（如果有看门狗会自动重启）
        time.sleep(5)
        machine.reset()
