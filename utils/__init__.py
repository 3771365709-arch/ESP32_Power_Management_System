"""
工具类模块
============================================
提供通用工具函数和类
- err_codes: 统一错误码定义
- logger: 日志记录器
- crc16: CRC16校验算法
- filter: 数字滤波算法
- pid: PID控制器
"""

from utils.err_codes import *
from utils.logger import get_logger, set_global_level
from utils.crc16 import crc16_modbus, crc16_bytes, verify_crc, append_crc
from utils.filter import (
    MovingAverageFilter,
    LimitFilter,
    MedianFilter,
    DebounceFilter,
    CompositeFilter,
)
from utils.pid import PIDController

__all__ = [
    # 错误码
    "ERR_OK",
    "ERR_UNKNOWN",
    "ERR_INVALID_PARAM",
    "get_error_desc",
    "is_success",
    "is_error",
    # 日志
    "get_logger",
    "set_global_level",
    # CRC
    "crc16_modbus",
    "crc16_bytes",
    "verify_crc",
    "append_crc",
    # 滤波
    "MovingAverageFilter",
    "LimitFilter",
    "MedianFilter",
    "DebounceFilter",
    "CompositeFilter",
    # PID
    "PIDController",
]
