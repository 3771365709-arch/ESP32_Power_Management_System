"""
电源管理服务模块
============================================
业务服务层 - 负责电源时序控制和保护逻辑
实现上电/下电时序控制、三级保护机制（告警-降额-切断）
调用drivers层的硬件接口，不直接操作硬件
"""

import time
from utils.err_codes import *
from utils.logger import get_logger
from utils.filter import DebounceFilter
from config.config import POWER_PIN_CONFIG, PROTECTION_CONFIG, POWER_LOSS_CONFIG

# 日志记录器
_log = get_logger("PWR_SVC")

# 系统状态定义
SYS_POWER_OFF = 0      # 系统关闭
SYS_POWER_ON = 1       # 系统正常运行
SYS_POWER_WARNING = 2  # 告警状态
SYS_POWER_DERATE = 3   # 降额运行
SYS_POWER_FAULT = 4    # 故障切断


class PowerService:
    """
    电源管理服务类
    实现完整的电源时序控制和三级保护机制
    """

    def __init__(self, power_driver, adc_driver, nvs_driver):
        """
        初始化电源管理服务
        参数:
            power_driver: 电源驱动实例
            adc_driver: ADC驱动实例
            nvs_driver: NVS驱动实例
        """
        self._power_drv = power_driver
        self._adc_drv = adc_driver
        self._nvs_drv = nvs_driver

        self._initialized = False
        self._system_state = SYS_POWER_OFF

        # 三级保护配置
        self._warning_cfg = PROTECTION_CONFIG["warning"]
        self._derate_cfg = PROTECTION_CONFIG["derate"]
        self._cutoff_cfg = PROTECTION_CONFIG["cutoff"]

        # 保护消抖滤波器
        self._warning_filters = []
        self._derate_filters = []
        self._cutoff_filters = []

        # 故障状态
        self._fault_codes = []
        self._fault_latched = False
        self._derate_active = False
        self._derate_recovery_time = 0

        # 掉电检测
        self._power_loss_filter = DebounceFilter(POWER_LOSS_CONFIG["debounce_count"])
        self._power_loss_detected = False

        # 额定参数
        self._rated_voltage = POWER_PIN_CONFIG["rated_voltage"]
        self._rated_current = POWER_PIN_CONFIG["rated_current"]
        self._domain_count = len(self._rated_voltage)

    def init(self):
        """
        初始化电源管理服务
        返回:
            int: 错误码
        """
        if self._initialized:
            return ERR_ALREADY_INIT

        try:
            # 初始化保护消抖滤波器
            for i in range(self._domain_count):
                # 每路电源3种保护，每种2个检测（电压+电流）
                self._warning_filters.append(DebounceFilter())
                self._derate_filters.append(DebounceFilter())
                self._cutoff_filters.append(DebounceFilter())

            self._initialized = True
            _log.info("电源管理服务初始化完成")
            return ERR_OK

        except Exception as e:
            _log.error(f"电源管理服务初始化失败: {e}")
            return ERR_SYS_EXCEPTION

    def power_on_sequence(self):
        """
        执行上电时序
        按配置的延迟依次开启各电源域
        返回:
            int: 错误码
        """
        if not self._initialized:
            return ERR_NOT_INITIALIZED

        if self._system_state != SYS_POWER_OFF:
            return ERR_PWR_ALREADY_ON

        if self._fault_latched:
            _log.error("故障已锁存，无法上电，请先复位故障")
            return ERR_PM_FAULT_LATCHED

        _log.info("开始执行上电时序")

        try:
            delays = POWER_PIN_CONFIG["power_on_delays"]

            for i in range(self._domain_count):
                # 延时
                if delays[i] > 0:
                    time.sleep_ms(delays[i])

                # 开启电源域
                err = self._power_drv.power_on(i)
                if err != ERR_OK and err != ERR_PWR_ALREADY_ON:
                    _log.error(f"上电时序失败，电源域{i}开启失败")
                    # 回滚：关闭已开启的电源
                    self.power_off_sequence()
                    return err

            self._system_state = SYS_POWER_ON
            _log.info("上电时序完成，系统正常运行")
            return ERR_OK

        except Exception as e:
            _log.error(f"上电时序异常: {e}")
            self.power_off_sequence()
            return ERR_PWR_SEQUENCE_FAIL

    def power_off_sequence(self):
        """
        执行下电时序
        按逆序依次关闭各电源域
        返回:
            int: 错误码
        """
        if not self._initialized:
            return ERR_NOT_INITIALIZED

        _log.info("开始执行下电时序")

        try:
            delays = POWER_PIN_CONFIG["power_off_delays"]

            for i in range(self._domain_count - 1, -1, -1):
                # 关闭电源域
                self._power_drv.power_off(i)

                # 延时
                if delays[i] > 0:
                    time.sleep_ms(delays[i])

            self._system_state = SYS_POWER_OFF
            self._derate_active = False
            _log.info("下电时序完成")
            return ERR_OK

        except Exception as e:
            _log.error(f"下电时序异常: {e}")
            return ERR_PWR_SEQUENCE_FAIL

    def check_protections(self, voltages, currents, temperatures):
        """
        检查所有保护条件
        需要在主循环中周期性调用
        参数:
            voltages: 电压列表
            currents: 电流列表
            temperatures: 温度列表
        返回:
            int: 最高优先级的错误码
        """
        if not self._initialized:
            return ERR_NOT_INITIALIZED

        if self._system_state == SYS_POWER_OFF:
            return ERR_OK

        max_err = ERR_OK
        any_warning = False
        any_derate = False
        any_cutoff = False

        # 检查每路电源的电压和电流保护
        for i in range(self._domain_count):
            v = voltages[i] if i < len(voltages) else 0
            c = currents[i] if i < len(currents) else 0
            rated_v = self._rated_voltage[i]
            rated_c = self._rated_current[i]

            # 电压偏差率
            v_deviation = abs(v - rated_v) / rated_v if rated_v > 0 else 0
            # 电流比率
            c_ratio = c / rated_c if rated_c > 0 else 0

            # 切断级保护（最高优先级）
            cutoff_trigger = (
                v_deviation >= self._cutoff_cfg["voltage_deviation"] or
                c_ratio >= self._cutoff_cfg["current_ratio"]
            )
            # 温度保护
            for temp in temperatures:
                if temp >= self._cutoff_cfg["temp_threshold"]:
                    cutoff_trigger = True

            cutoff_stable = self._cutoff_filters[i].update(cutoff_trigger)
            if cutoff_stable:
                any_cutoff = True
                if v_deviation >= self._cutoff_cfg["voltage_deviation"]:
                    self._record_fault(ERR_PM_OVP_TRIGGERED if v > rated_v else ERR_PM_UVP_TRIGGERED)
                if c_ratio >= self._cutoff_cfg["current_ratio"]:
                    self._record_fault(ERR_PM_OCP_TRIGGERED)

            # 降额级保护
            derate_trigger = (
                v_deviation >= self._derate_cfg["voltage_deviation"] or
                c_ratio >= self._derate_cfg["current_ratio"]
            )
            for temp in temperatures:
                if temp >= self._derate_cfg["temp_threshold"]:
                    derate_trigger = True

            derate_stable = self._derate_filters[i].update(derate_trigger)
            if derate_stable and not cutoff_stable:
                any_derate = True

            # 告警级保护
            warning_trigger = (
                v_deviation >= self._warning_cfg["voltage_deviation"] or
                c_ratio >= self._warning_cfg["current_ratio"]
            )
            for temp in temperatures:
                if temp >= self._warning_cfg["temp_threshold"]:
                    warning_trigger = True

            warning_stable = self._warning_filters[i].update(warning_trigger)
            if warning_stable and not derate_stable and not cutoff_stable:
                any_warning = True

        # 过温保护检查
        for temp in temperatures:
            if temp >= self._cutoff_cfg["temp_threshold"]:
                self._record_fault(ERR_PM_OTP_TRIGGERED)

        # 执行保护动作
        if any_cutoff:
            self._execute_cutoff()
            max_err = ERR_PWR_PROTECTION_TRIG
        elif any_derate:
            self._execute_derate()
            max_err = ERR_PM_DERATE_ACTIVE
        elif any_warning:
            self._system_state = SYS_POWER_WARNING
            max_err = ERR_OK  # 告警不返回错误
        else:
            # 正常状态，检查是否需要从降额恢复
            if self._derate_active and self._derate_cfg["auto_recovery"]:
                now = time.ticks_ms()
                if time.ticks_diff(now, self._derate_recovery_time) >= self._derate_cfg["recovery_delay_ms"]:
                    self._recover_from_derate()
            self._system_state = SYS_POWER_ON

        return max_err

    def _execute_cutoff(self):
        """执行切断级保护"""
        if self._system_state == SYS_POWER_FAULT:
            return

        _log.critical("切断级保护触发，紧急断电！")
        self._power_drv.emergency_shutdown()
        self._system_state = SYS_POWER_FAULT

        if self._cutoff_cfg["latch"]:
            self._fault_latched = True
            _log.warning("故障已锁存，需手动复位")

        # 保存故障记录
        self._save_fault_record()

    def _execute_derate(self):
        """执行降额级保护"""
        if self._derate_active:
            return

        _log.warning("降额级保护触发，进入降额运行模式")
        self._derate_active = True
        self._system_state = SYS_POWER_DERATE
        self._derate_recovery_time = time.ticks_ms()

        # 关闭非必要电源域（最后两路）
        for i in range(self._domain_count - 2, self._domain_count):
            self._power_drv.power_off(i)

    def _recover_from_derate(self):
        """从降额模式恢复"""
        if not self._derate_active:
            return

        _log.info("从降额模式恢复")
        self._derate_active = False

        # 重新开启被关闭的电源域
        for i in range(self._domain_count - 2, self._domain_count):
            self._power_drv.power_on(i)
            time.sleep_ms(50)

        self._system_state = SYS_POWER_ON

    def check_power_loss(self, input_voltage):
        """
        检查交流掉电
        参数:
            input_voltage: 输入电压值
        返回:
            bool: True=检测到掉电
        """
        threshold = POWER_LOSS_CONFIG["threshold_volt"]
        is_loss = input_voltage < threshold
        stable_loss = self._power_loss_filter.update(is_loss)

        if stable_loss and not self._power_loss_detected:
            self._power_loss_detected = True
            _log.warning("检测到交流掉电，执行紧急保存")
            self._handle_power_loss()

        return stable_loss

    def _handle_power_loss(self):
        """处理掉电事件"""
        # 保存关键数据
        self._save_runtime_data()
        # 执行安全下电
        self.power_off_sequence()

    def _record_fault(self, fault_code):
        """记录故障码"""
        if fault_code not in self._fault_codes:
            self._fault_codes.append(fault_code)
            _log.error(f"故障触发: {get_error_desc(fault_code)} (0x{fault_code:04X})")

    def _save_fault_record(self):
        """保存故障记录到NVS"""
        try:
            from config.config import NVS_KEYS
            # 保存最新故障码
            if self._fault_codes:
                latest = self._fault_codes[-1]
                self._nvs_drv.write_int(NVS_KEYS["sys"]["last_fault_code"], latest)

            # 故障计数
            err, count = self._nvs_drv.read_int(NVS_KEYS["fault"]["count"], 0)
            self._nvs_drv.write_int(NVS_KEYS["fault"]["count"], count + 1)

        except Exception as e:
            _log.error(f"保存故障记录失败: {e}")

    def _save_runtime_data(self):
        """保存运行时数据（掉电时调用）"""
        try:
            from config.config import NVS_KEYS
            # 增加启动计数
            err, count = self._nvs_drv.read_int(NVS_KEYS["sys"]["boot_count"], 0)
            # 这里不增加，只是保存当前状态
        except Exception as e:
            _log.error(f"保存运行数据失败: {e}")

    def reset_fault(self):
        """
        复位故障锁存
        返回:
            int: 错误码
        """
        if not self._fault_latched:
            return ERR_OK

        self._fault_latched = False
        self._fault_codes.clear()
        self._system_state = SYS_POWER_OFF
        _log.info("故障已复位")
        return ERR_OK

    def get_system_state(self):
        """获取系统电源状态"""
        return self._system_state

    def is_fault_latched(self):
        """检测是否故障锁存"""
        return self._fault_latched

    def is_derate_active(self):
        """检测是否降额运行"""
        return self._derate_active

    def get_fault_codes(self):
        """获取当前故障码列表"""
        return self._fault_codes.copy()

    def emergency_shutdown(self):
        """紧急断电"""
        _log.warning("执行紧急断电命令")
        self._power_drv.emergency_shutdown()
        self._system_state = SYS_POWER_OFF
        self._derate_active = False
        return ERR_OK

    def deinit(self):
        """反初始化服务"""
        if self._initialized:
            self.power_off_sequence()
            self._initialized = False
            _log.info("电源管理服务已释放")
