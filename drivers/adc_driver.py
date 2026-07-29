"""
ADC采集驱动模块
============================================
硬件驱动层 - 负责电压、电流、温度的ADC采样
只提供原始数据采集和基本换算，不包含业务逻辑
数据滤波和业务处理由services层实现
"""

from machine import ADC
import math
from utils.err_codes import *
from utils.logger import get_logger
from config.config import ADC_PIN_CONFIG

# 日志记录器
_log = get_logger("ADC_DRV")


class ADCDriver:
    """
    ADC采集驱动类
    支持多通道电压、电流、温度采集
    提供原始ADC值和工程值转换
    """

    def __init__(self):
        """
        初始化ADC驱动
        """
        self._voltage_channels = ADC_PIN_CONFIG["voltage_channels"]
        self._current_channels = ADC_PIN_CONFIG["current_channels"]
        self._temp_channels = ADC_PIN_CONFIG["temp_channels"]
        self._temp_names = ADC_PIN_CONFIG["temp_names"]

        self._vref_mv = ADC_PIN_CONFIG["vref_mv"]
        self._resolution = ADC_PIN_CONFIG["resolution"]
        self._max_adc = (1 << self._resolution) - 1

        self._voltage_divider = ADC_PIN_CONFIG["voltage_divider"]
        self._current_shunt = ADC_PIN_CONFIG["current_shunt_ohm"]
        self._opamp_gain = ADC_PIN_CONFIG["opamp_gain"]

        self._ntc_beta = ADC_PIN_CONFIG["ntc_beta"]
        self._ntc_r25 = ADC_PIN_CONFIG["ntc_r25"]
        self._sample_times = ADC_PIN_CONFIG["sample_times"]

        self._adc_objs = {}
        self._initialized = False

    def init(self):
        """
        初始化所有ADC通道
        返回:
            int: 错误码
        """
        if self._initialized:
            return ERR_ALREADY_INIT

        try:
            # 初始化电压采集通道
            for ch in self._voltage_channels:
                adc = ADC(Pin(ch))
                adc.atten(ADC.ATTN_11DB)  # 满量程3.3V
                adc.width(ADC.WIDTH_12BIT)
                self._adc_objs[ch] = adc

            # 初始化电流采集通道
            for ch in self._current_channels:
                adc = ADC(Pin(ch))
                adc.atten(ADC.ATTN_11DB)
                adc.width(ADC.WIDTH_12BIT)
                self._adc_objs[ch] = adc

            # 初始化温度采集通道
            for ch in self._temp_channels:
                adc = ADC(Pin(ch))
                adc.atten(ADC.ATTN_11DB)
                adc.width(ADC.WIDTH_12BIT)
                self._adc_objs[ch] = adc

            self._initialized = True
            total_ch = len(self._voltage_channels) + len(self._current_channels) + len(self._temp_channels)
            _log.info(f"ADC驱动初始化完成，共{total_ch}个通道")
            return ERR_OK

        except Exception as e:
            _log.error(f"ADC驱动初始化失败: {e}")
            return ERR_ADC_CALIBRATION

    def _read_raw(self, channel):
        """
        读取ADC原始值（多次采样取平均）
        参数:
            channel: ADC通道号
        返回:
            int: 平均后的原始ADC值
        """
        if channel not in self._adc_objs:
            return 0

        adc = self._adc_objs[channel]
        total = 0
        for _ in range(self._sample_times):
            total += adc.read()
        return total // self._sample_times

    def _adc_to_voltage(self, raw_adc):
        """
        ADC原始值转换为引脚电压(mV)
        参数:
            raw_adc: 原始ADC值
        返回:
            float: 电压值(mV)
        """
        return (raw_adc / self._max_adc) * self._vref_mv

    def read_voltage_raw(self, index):
        """
        读取指定电压通道的原始ADC值
        参数:
            index: 电压通道索引(0-5)
        返回:
            tuple: (错误码, 原始ADC值)
        """
        if not self._initialized:
            return (ERR_NOT_INITIALIZED, 0)

        if index < 0 or index >= len(self._voltage_channels):
            return (ERR_ADC_INVALID_CH, 0)

        try:
            ch = self._voltage_channels[index]
            raw = self._read_raw(ch)
            return (ERR_OK, raw)
        except Exception as e:
            _log.error(f"读取电压通道{index}失败: {e}")
            return (ERR_ADC_READ_FAIL, 0)

    def read_voltage(self, index):
        """
        读取指定通道的实际电压值(V)
        经过分压比换算
        参数:
            index: 电压通道索引(0-5)
        返回:
            tuple: (错误码, 电压值V)
        """
        err, raw = self.read_voltage_raw(index)
        if err != ERR_OK:
            return (err, 0.0)

        pin_mv = self._adc_to_voltage(raw)
        actual_v = (pin_mv / 1000.0) * self._voltage_divider[index]
        return (ERR_OK, actual_v)

    def read_current_raw(self, index):
        """
        读取指定电流通道的原始ADC值
        参数:
            index: 电流通道索引(0-5)
        返回:
            tuple: (错误码, 原始ADC值)
        """
        if not self._initialized:
            return (ERR_NOT_INITIALIZED, 0)

        if index < 0 or index >= len(self._current_channels):
            return (ERR_ADC_INVALID_CH, 0)

        try:
            ch = self._current_channels[index]
            raw = self._read_raw(ch)
            return (ERR_OK, raw)
        except Exception as e:
            _log.error(f"读取电流通道{index}失败: {e}")
            return (ERR_ADC_READ_FAIL, 0)

    def read_current(self, index):
        """
        读取指定通道的实际电流值(A)
        经过采样电阻和运放增益换算
        参数:
            index: 电流通道索引(0-5)
        返回:
            tuple: (错误码, 电流值A)
        """
        err, raw = self.read_current_raw(index)
        if err != ERR_OK:
            return (err, 0.0)

        pin_mv = self._adc_to_voltage(raw)
        # 运放输出电压 = 引脚电压
        # 采样电阻电压 = 运放输出 / 增益
        # 电流 = 采样电阻电压 / 采样电阻(毫欧转欧)
        shunt_mv = pin_mv / self._opamp_gain
        current_a = shunt_mv / (self._current_shunt[index] / 1000.0) / 1000.0
        return (ERR_OK, current_a)

    def read_temp_raw(self, index):
        """
        读取指定温度通道的原始ADC值
        参数:
            index: 温度通道索引(0-2)
        返回:
            tuple: (错误码, 原始ADC值)
        """
        if not self._initialized:
            return (ERR_NOT_INITIALIZED, 0)

        if index < 0 or index >= len(self._temp_channels):
            return (ERR_ADC_INVALID_CH, 0)

        try:
            ch = self._temp_channels[index]
            raw = self._read_raw(ch)
            return (ERR_OK, raw)
        except Exception as e:
            _log.error(f"读取温度通道{index}失败: {e}")
            return (ERR_ADC_READ_FAIL, 0)

    def read_temperature(self, index):
        """
        读取指定通道的温度值(摄氏度)
        使用NTC热敏电阻Beta公式计算
        参数:
            index: 温度通道索引(0-2)
        返回:
            tuple: (错误码, 温度值℃)
        """
        err, raw = self.read_temp_raw(index)
        if err != ERR_OK:
            return (err, 0.0)

        pin_mv = self._adc_to_voltage(raw)
        vcc_mv = self._vref_mv

        # 计算NTC电阻值（假设上拉电阻10K，接VCC）
        if raw == 0 or raw >= self._max_adc:
            return (ERR_SENSOR_OUT_OF_RANGE, 0.0)

        ntc_r = self._ntc_r25 * (pin_mv / (vcc_mv - pin_mv))

        # Beta公式计算温度
        # 1/T = 1/T25 + (1/Beta) * ln(R/R25)
        t25_kelvin = 25.0 + 273.15
        inv_t = 1.0 / t25_kelvin + (1.0 / self._ntc_beta) * math.log(ntc_r / self._ntc_r25)
        temp_c = 1.0 / inv_t - 273.15

        return (ERR_OK, temp_c)

    def read_all_voltages(self):
        """
        读取所有电压通道
        返回:
            tuple: (错误码, 电压值列表)
        """
        voltages = []
        for i in range(len(self._voltage_channels)):
            err, v = self.read_voltage(i)
            if err != ERR_OK:
                return (err, [])
            voltages.append(v)
        return (ERR_OK, voltages)

    def read_all_currents(self):
        """
        读取所有电流通道
        返回:
            tuple: (错误码, 电流值列表)
        """
        currents = []
        for i in range(len(self._current_channels)):
            err, c = self.read_current(i)
            if err != ERR_OK:
                return (err, [])
            currents.append(c)
        return (ERR_OK, currents)

    def read_all_temperatures(self):
        """
        读取所有温度通道
        返回:
            tuple: (错误码, 温度值列表)
        """
        temps = []
        for i in range(len(self._temp_channels)):
            err, t = self.read_temperature(i)
            if err != ERR_OK:
                return (err, [])
            temps.append(t)
        return (ERR_OK, temps)

    def get_voltage_count(self):
        """获取电压通道数量"""
        return len(self._voltage_channels)

    def get_current_count(self):
        """获取电流通道数量"""
        return len(self._current_channels)

    def get_temp_count(self):
        """获取温度通道数量"""
        return len(self._temp_channels)

    def get_temp_name(self, index):
        """获取温度传感器名称"""
        if 0 <= index < len(self._temp_names):
            return self._temp_names[index]
        return "UNKNOWN"

    def deinit(self):
        """
        反初始化ADC驱动
        释放资源
        """
        if self._initialized:
            self._adc_objs.clear()
            self._initialized = False
            _log.info("ADC驱动已释放")
