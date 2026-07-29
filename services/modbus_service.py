"""
Modbus-RTU通信服务模块
============================================
业务服务层 - 负责Modbus-RTU工业总线通信
实现寄存器映射、命令解析、数据响应
调用串口驱动，提供标准Modbus从机功能
"""

import time
from utils.err_codes import *
from utils.logger import get_logger
from utils.crc16 import verify_crc, append_crc
from config.config import MODBUS_CONFIG

# 日志记录器
_log = get_logger("MB_SVC")

try:
    from machine import UART
except ImportError:
    UART = None

# Modbus功能码
FUNC_READ_HOLDING = 0x03    # 读保持寄存器
FUNC_READ_INPUT = 0x04      # 读输入寄存器
FUNC_WRITE_SINGLE = 0x06    # 写单个寄存器
FUNC_WRITE_MULTIPLE = 0x10  # 写多个寄存器

# 异常码
EXC_ILLEGAL_FUNC = 0x01     # 非法功能码
EXC_ILLEGAL_ADDR = 0x02     # 非法地址
EXC_ILLEGAL_VAL = 0x03      # 非法数据值
EXC_SLAVE_FAIL = 0x04       # 从机设备故障


class ModbusService:
    """
    Modbus-RTU从机服务类
    实现标准Modbus-RTU协议，支持寄存器读写
    """

    def __init__(self, power_service, monitor_service):
        """
        初始化Modbus服务
        参数:
            power_service: 电源管理服务实例
            monitor_service: 状态监测服务实例
        """
        self._power_svc = power_service
        self._monitor_svc = monitor_service

        self._initialized = False
        self._uart = None
        self._slave_addr = MODBUS_CONFIG["slave_addr"]

        # 寄存器映射
        self._input_regs = {}   # 输入寄存器（只读）
        self._holding_regs = {} # 保持寄存器（可读写）

        # 接收缓冲区
        self._rx_buffer = bytearray()
        self._last_rx_time = 0

    def init(self):
        """
        初始化Modbus服务
        返回:
            int: 错误码
        """
        if self._initialized:
            return ERR_ALREADY_INIT

        try:
            if UART is not None:
                # 初始化串口
                self._uart = UART(
                    MODBUS_CONFIG["uart_id"],
                    baudrate=MODBUS_CONFIG["baudrate"],
                    bits=MODBUS_CONFIG["bits"],
                    parity=MODBUS_CONFIG["parity"],
                    stop=MODBUS_CONFIG["stop"],
                    tx=MODBUS_CONFIG["tx_pin"],
                    rx=MODBUS_CONFIG["rx_pin"],
                    timeout=MODBUS_CONFIG["rx_timeout"],
                )
            else:
                _log.warning("非ESP32环境，Modbus服务模拟运行")

            # 初始化寄存器映射
            self._init_registers()

            self._initialized = True
            _log.info("Modbus-RTU服务初始化完成")
            return ERR_OK

        except Exception as e:
            _log.error(f"Modbus服务初始化失败: {e}")
            return ERR_UART_INIT_FAIL

    def _init_registers(self):
        """初始化寄存器映射表"""
        # 输入寄存器（只读，实时数据）
        # 0x0000-0x0005: 6路电压 (单位: 0.01V)
        # 0x0006-0x000B: 6路电流 (单位: 0.01A)
        # 0x000C-0x000E: 3路温度 (单位: 0.1℃)
        # 0x000F: 系统总功率 (单位: 0.1W)
        # 0x0010: 系统状态
        # 0x0011: 故障码
        # 0x0012: 风扇转速 (RPM)
        # 0x0013: 风扇占空比 (%)

        # 保持寄存器（可读写，配置参数）
        # 0x0000: 从机地址
        # 0x0001: 风扇目标温度 (0.1℃)
        # 0x0002: 保护等级 (0=禁用, 1=告警, 2=降额, 3=切断)
        # 0x0003: 控制命令 (1=上电, 2=下电, 3=复位故障)

        # 初始化保持寄存器默认值
        self._holding_regs[0x0000] = self._slave_addr
        self._holding_regs[0x0001] = 550  # 55.0℃
        self._holding_regs[0x0002] = 3    # 全部保护启用
        self._holding_regs[0x0003] = 0    # 无命令

    def _update_input_registers(self):
        """更新输入寄存器（实时数据）"""
        try:
            voltages = self._monitor_svc.get_voltages()
            for i, v in enumerate(voltages):
                if i < 6:
                    self._input_regs[0x0000 + i] = int(v * 100) & 0xFFFF

            currents = self._monitor_svc.get_currents()
            for i, c in enumerate(currents):
                if i < 6:
                    self._input_regs[0x0006 + i] = int(c * 100) & 0xFFFF

            temps = self._monitor_svc.get_temperatures()
            for i, t in enumerate(temps):
                if i < 3:
                    self._input_regs[0x000C + i] = int(t * 10) & 0xFFFF

            # 总功率
            self._input_regs[0x000F] = int(self._monitor_svc.get_total_power() * 10) & 0xFFFF

            # 系统状态
            self._input_regs[0x0010] = self._power_svc.get_system_state()

            # 故障码（取第一个）
            faults = self._power_svc.get_fault_codes()
            self._input_regs[0x0011] = faults[0] if faults else 0

            # 风扇状态
            self._input_regs[0x0012] = self._monitor_svc.get_fan_speed() & 0xFFFF
            self._input_regs[0x0013] = int(self._monitor_svc.get_fan_duty()) & 0xFFFF

        except Exception as e:
            _log.error(f"更新输入寄存器失败: {e}")

    def _read_registers(self, start_addr, count, is_input):
        """
        读取寄存器
        参数:
            start_addr: 起始地址
            count: 寄存器数量
            is_input: True=输入寄存器, False=保持寄存器
        返回:
            tuple: (异常码, 寄存器值列表)
        """
        regs = self._input_regs if is_input else self._holding_regs
        values = []

        for i in range(count):
            addr = start_addr + i
            if addr in regs:
                values.append(regs[addr])
            else:
                # 未定义的寄存器返回0
                if is_input:
                    return (EXC_ILLEGAL_ADDR, [])
                values.append(0)

        return (0, values)

    def _write_register(self, addr, value):
        """
        写单个保持寄存器
        参数:
            addr: 寄存器地址
            value: 写入值
        返回:
            int: 异常码 (0=成功)
        """
        # 检查地址范围
        if addr > 0x0010:
            return EXC_ILLEGAL_ADDR

        # 特殊处理控制命令寄存器
        if addr == 0x0003:
            self._handle_control_command(value)

        self._holding_regs[addr] = value & 0xFFFF
        return 0

    def _write_multiple_registers(self, start_addr, values):
        """
        写多个保持寄存器
        参数:
            start_addr: 起始地址
            values: 值列表
        返回:
            int: 异常码 (0=成功)
        """
        for i, val in enumerate(values):
            exc = self._write_register(start_addr + i, val)
            if exc != 0:
                return exc
        return 0

    def _handle_control_command(self, cmd):
        """处理控制命令"""
        try:
            if cmd == 1:
                self._power_svc.power_on_sequence()
            elif cmd == 2:
                self._power_svc.power_off_sequence()
            elif cmd == 3:
                self._power_svc.reset_fault()
        except Exception as e:
            _log.error(f"执行控制命令失败: {e}")

    def _build_response(self, func_code, data):
        """
        构建响应帧
        参数:
            func_code: 功能码
            data: 数据部分(bytes)
        返回:
            bytes: 完整响应帧
        """
        frame = bytearray()
        frame.append(self._slave_addr)
        frame.append(func_code)
        frame.extend(data)
        return append_crc(bytes(frame))

    def _build_exception(self, func_code, exc_code):
        """
        构建异常响应帧
        参数:
            func_code: 功能码
            exc_code: 异常码
        返回:
            bytes: 异常响应帧
        """
        func_with_exc = func_code | 0x80
        return self._build_response(func_with_exc, bytes([exc_code]))

    def _parse_request(self, frame):
        """
        解析Modbus请求帧
        参数:
            frame: 完整帧数据
        返回:
            tuple: (从机地址, 功能码, 数据) 或 None
        """
        if len(frame) < 5:
            return None

        # CRC校验
        if not verify_crc(frame):
            _log.debug("Modbus CRC校验失败")
            return None

        slave_addr = frame[0]
        func_code = frame[1]
        data = frame[2:-2]

        return (slave_addr, func_code, data)

    def _handle_request(self, frame):
        """
        处理Modbus请求
        参数:
            frame: 请求帧
        返回:
            bytes: 响应帧，或None（非本机地址）
        """
        parsed = self._parse_request(frame)
        if not parsed:
            return None

        slave_addr, func_code, data = parsed

        # 检查地址
        if slave_addr != self._slave_addr:
            return None

        _log.debug(f"Modbus请求: 功能码=0x{func_code:02X}")

        try:
            if func_code == FUNC_READ_HOLDING:
                # 读保持寄存器
                start_addr = (data[0] << 8) | data[1]
                count = (data[2] << 8) | data[3]
                exc, values = self._read_registers(start_addr, count, False)

                if exc != 0:
                    return self._build_exception(func_code, exc)

                # 构建响应
                resp_data = bytearray()
                resp_data.append(count * 2)  # 字节数
                for val in values:
                    resp_data.append((val >> 8) & 0xFF)
                    resp_data.append(val & 0xFF)
                return self._build_response(func_code, resp_data)

            elif func_code == FUNC_READ_INPUT:
                # 读输入寄存器
                start_addr = (data[0] << 8) | data[1]
                count = (data[2] << 8) | data[3]

                # 先更新实时数据
                self._update_input_registers()

                exc, values = self._read_registers(start_addr, count, True)
                if exc != 0:
                    return self._build_exception(func_code, exc)

                resp_data = bytearray()
                resp_data.append(count * 2)
                for val in values:
                    resp_data.append((val >> 8) & 0xFF)
                    resp_data.append(val & 0xFF)
                return self._build_response(func_code, resp_data)

            elif func_code == FUNC_WRITE_SINGLE:
                # 写单个寄存器
                addr = (data[0] << 8) | data[1]
                value = (data[2] << 8) | data[3]

                exc = self._write_register(addr, value)
                if exc != 0:
                    return self._build_exception(func_code, exc)

                # 回显
                return self._build_response(func_code, data)

            elif func_code == FUNC_WRITE_MULTIPLE:
                # 写多个寄存器
                start_addr = (data[0] << 8) | data[1]
                count = (data[2] << 8) | data[3]
                byte_count = data[4]

                values = []
                for i in range(count):
                    val = (data[5 + i * 2] << 8) | data[6 + i * 2]
                    values.append(val)

                exc = self._write_multiple_registers(start_addr, values)
                if exc != 0:
                    return self._build_exception(func_code, exc)

                # 回显地址和数量
                return self._build_response(func_code, data[:4])

            else:
                # 不支持的功能码
                return self._build_exception(func_code, EXC_ILLEGAL_FUNC)

        except Exception as e:
            _log.error(f"处理Modbus请求异常: {e}")
            return self._build_exception(func_code, EXC_SLAVE_FAIL)

    def update(self):
        """
        更新Modbus通信
        需要在主循环中周期性调用
        返回:
            int: 错误码
        """
        if not self._initialized:
            return ERR_NOT_INITIALIZED

        if self._uart is None:
            return ERR_OK

        try:
            # 读取接收数据
            if self._uart.any():
                data = self._uart.read()
                if data:
                    self._rx_buffer.extend(data)
                    self._last_rx_time = time.ticks_ms()

            # 帧间隔检测（3.5字符时间）
            if len(self._rx_buffer) > 0:
                now = time.ticks_ms()
                # 9600波特率下约4ms
                if time.ticks_diff(now, self._last_rx_time) > 5:
                    # 处理完整帧
                    response = self._handle_request(bytes(self._rx_buffer))
                    if response:
                        self._uart.write(response)

                    # 清空缓冲区
                    self._rx_buffer = bytearray()

            return ERR_OK

        except Exception as e:
            _log.error(f"Modbus更新失败: {e}")
            return ERR_MODBUS_INVALID_FRAME

    def get_slave_address(self):
        """获取从机地址"""
        return self._slave_addr

    def deinit(self):
        """反初始化服务"""
        if self._initialized:
            if self._uart:
                self._uart.deinit()
            self._initialized = False
            _log.info("Modbus-RTU服务已释放")
