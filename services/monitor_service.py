"""
状态监测服务模块
============================================
业务服务层 - 负责系统状态监测和数据采集
实现ADC数据滤波、电能统计、风扇PID温控
调用drivers层硬件接口，提供结构化监测数据
"""

import time
from utils.err_codes import *
from utils.logger import get_logger
from utils.filter import CompositeFilter
from utils.pid import PIDController
from config.config import FAN_PID_CONFIG, ENERGY_CONFIG

# 日志记录器
_log = get_logger("MON_SVC")


class MonitorService:
    """
    状态监测服务类
    负责数据采集、滤波处理、电能统计、风扇控制
    """

    def __init__(self, adc_driver, fan_driver, nvs_driver):
        """
        初始化监测服务
        参数:
            adc_driver: ADC驱动实例
            fan_driver: 风扇驱动实例
            nvs_driver: NVS驱动实例
        """
        self._adc_drv = adc_driver
        self._fan_drv = fan_driver
        self._nvs_drv = nvs_driver

        self._initialized = False

        # 电压电流温度滤波器
        self._voltage_filters = []
        self._current_filters = []
        self._temp_filters = []

        # 滤波后的数据
        self._voltages = []
        self._currents = []
        self._temperatures = []
        self._powers = []  # 各电源域功率

        # 系统总功率
        self._total_power = 0.0
        self._peak_power = 0.0

        # 电能统计
        self._total_energy = 0.0  # 总电能(kWh)
        self._today_energy = 0.0  # 今日电能
        self._last_energy_time = 0

        # 风扇PID控制
        self._fan_pid = PIDController()
        self._fan_enabled = True
        self._last_fan_update = 0

        # 通道数量
        self._v_count = 0
        self._c_count = 0
        self._t_count = 0

    def init(self):
        """
        初始化监测服务
        返回:
            int: 错误码
        """
        if self._initialized:
            return ERR_ALREADY_INIT

        try:
            self._v_count = self._adc_drv.get_voltage_count()
            self._c_count = self._adc_drv.get_current_count()
            self._t_count = self._adc_drv.get_temp_count()

            # 初始化滤波器
            for i in range(self._v_count):
                self._voltage_filters.append(CompositeFilter())
                self._voltages.append(0.0)

            for i in range(self._c_count):
                self._current_filters.append(CompositeFilter())
                self._currents.append(0.0)
                self._powers.append(0.0)

            for i in range(self._t_count):
                self._temp_filters.append(CompositeFilter())
                self._temperatures.append(0.0)

            # 初始化风扇PID
            self._fan_pid.set_setpoint(FAN_PID_CONFIG["target_temp"])

            # 读取历史电能数据
            self._load_energy_data()

            self._last_energy_time = time.ticks_ms()
            self._initialized = True
            _log.info("状态监测服务初始化完成")
            return ERR_OK

        except Exception as e:
            _log.error(f"状态监测服务初始化失败: {e}")
            return ERR_SYS_EXCEPTION

    def update(self):
        """
        更新监测数据
        需要在主循环中周期性调用
        返回:
            int: 错误码
        """
        if not self._initialized:
            return ERR_NOT_INITIALIZED

        try:
            # 采集并滤波电压
            err, raw_voltages = self._adc_drv.read_all_voltages()
            if err == ERR_OK:
                for i in range(self._v_count):
                    self._voltages[i] = self._voltage_filters[i].update(raw_voltages[i])

            # 采集并滤波电流
            err, raw_currents = self._adc_drv.read_all_currents()
            if err == ERR_OK:
                for i in range(self._c_count):
                    self._currents[i] = self._current_filters[i].update(raw_currents[i])

            # 采集并滤波温度
            err, raw_temps = self._adc_drv.read_all_temperatures()
            if err == ERR_OK:
                for i in range(self._t_count):
                    self._temperatures[i] = self._temp_filters[i].update(raw_temps[i])

            # 计算功率
            self._calculate_power()

            # 电能统计
            self._update_energy()

            # 风扇温控
            self._update_fan_control()

            return ERR_OK

        except Exception as e:
            _log.error(f"监测数据更新失败: {e}")
            return ERR_MON_DATA_ABNORMAL

    def _calculate_power(self):
        """计算各电源域功率和总功率"""
        total = 0.0
        count = min(self._v_count, self._c_count)

        for i in range(count):
            power = self._voltages[i] * self._currents[i]
            self._powers[i] = power
            total += power

        self._total_power = total

        # 更新峰值功率
        if total > self._peak_power:
            self._peak_power = total

    def _update_energy(self):
        """更新电能统计"""
        now = time.ticks_ms()
        dt_ms = time.ticks_diff(now, self._last_energy_time)

        if dt_ms >= 1000:  # 每秒统计一次
            dt_hours = dt_ms / 3600000.0
            energy_kwh = (self._total_power / 1000.0) * dt_hours

            self._total_energy += energy_kwh
            self._today_energy += energy_kwh
            self._last_energy_time = now

            # 定期保存到NVS
            stat_period = ENERGY_CONFIG.get("stat_period", 60)
            if int(now / 1000) % (stat_period * 60) == 0:
                self._save_energy_data()

    def _update_fan_control(self):
        """更新风扇PID控制"""
        if not self._fan_enabled:
            return

        now = time.ticks_ms()
        sample_period = int(FAN_PID_CONFIG.get("sample_period", 0.5) * 1000)

        if time.ticks_diff(now, self._last_fan_update) >= sample_period:
            # 取最高温度作为控制目标
            max_temp = max(self._temperatures) if self._temperatures else 25.0

            # 温度上下限处理
            temp_min = FAN_PID_CONFIG["temp_min"]
            temp_max = FAN_PID_CONFIG["temp_max"]

            if max_temp <= temp_min:
                # 温度低于下限，停转
                self._fan_drv.set_duty(0)
            elif max_temp >= temp_max:
                # 温度高于上限，全速
                self._fan_drv.set_duty(100)
            else:
                # PID控制
                duty = self._fan_pid.compute(max_temp, sample_period / 1000.0)
                self._fan_drv.set_duty(duty)

            self._last_fan_update = now

    def get_voltages(self):
        """获取滤波后的电压列表(V)"""
        return self._voltages.copy()

    def get_currents(self):
        """获取滤波后的电流列表(A)"""
        return self._currents.copy()

    def get_temperatures(self):
        """获取滤波后的温度列表(℃)"""
        return self._temperatures.copy()

    def get_powers(self):
        """获取各电源域功率列表(W)"""
        return self._powers.copy()

    def get_total_power(self):
        """获取系统总功率(W)"""
        return self._total_power

    def get_peak_power(self):
        """获取峰值功率(W)"""
        return self._peak_power

    def get_total_energy(self):
        """获取总电能(kWh)"""
        return self._total_energy

    def get_today_energy(self):
        """获取今日电能(kWh)"""
        return self._today_energy

    def get_fan_speed(self):
        """获取风扇转速(RPM)"""
        err, rpm = self._fan_drv.read_rpm()
        return rpm

    def get_fan_duty(self):
        """获取风扇占空比(%)"""
        return self._fan_drv.get_duty()

    def set_fan_enabled(self, enabled):
        """设置风扇是否启用"""
        self._fan_enabled = enabled
        if not enabled:
            self._fan_drv.fan_stop()

    def set_fan_target_temp(self, temp):
        """设置风扇目标温度"""
        self._fan_pid.set_setpoint(temp)

    def _load_energy_data(self):
        """从NVS加载电能统计数据"""
        try:
            from config.config import NVS_KEYS
            err, total = self._nvs_drv.read_float(NVS_KEYS["energy"]["total_kwh"], 0.0)
            if err == ERR_OK:
                self._total_energy = total

            err, peak = self._nvs_drv.read_float(NVS_KEYS["energy"]["peak_power"], 0.0)
            if err == ERR_OK:
                self._peak_power = peak

        except Exception as e:
            _log.warning(f"加载电能数据失败: {e}")

    def _save_energy_data(self):
        """保存电能统计数据到NVS"""
        try:
            from config.config import NVS_KEYS
            self._nvs_drv.write_float(NVS_KEYS["energy"]["total_kwh"], self._total_energy)
            self._nvs_drv.write_float(NVS_KEYS["energy"]["peak_power"], self._peak_power)
        except Exception as e:
            _log.warning(f"保存电能数据失败: {e}")

    def reset_peak_power(self):
        """重置峰值功率"""
        self._peak_power = self._total_power

    def reset_today_energy(self):
        """重置今日电能统计"""
        self._today_energy = 0.0

    def deinit(self):
        """反初始化服务"""
        if self._initialized:
            self._save_energy_data()
            self._initialized = False
            _log.info("状态监测服务已释放")
