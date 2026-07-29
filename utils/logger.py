"""
日志记录模块
============================================
提供统一的日志输出接口
支持多等级日志、颜色输出、模块标识
"""

import time
from config.config import LOG_CONFIG

# 日志等级定义
LOG_LEVELS = {
    "DEBUG": 0,
    "INFO": 1,
    "WARNING": 2,
    "ERROR": 3,
    "CRITICAL": 4,
}

# ANSI颜色代码
COLORS = {
    "RESET": "\033[0m",
    "DEBUG": "\033[36m",      # 青色
    "INFO": "\033[32m",       # 绿色
    "WARNING": "\033[33m",    # 黄色
    "ERROR": "\033[31m",      # 红色
    "CRITICAL": "\033[35m",   # 紫色
}

# 全局日志等级
_global_level = LOG_LEVELS.get(LOG_CONFIG.get("level", "INFO"), 1)
_color_enable = LOG_CONFIG.get("color_output", True)


class Logger:
    """
    日志记录器类
    每个模块创建一个实例，带模块名标识
    """

    def __init__(self, module_name):
        """
        初始化日志记录器
        参数:
            module_name: 模块名称，用于日志标识
        """
        self._module = module_name
        self._level = _global_level

    def _format_msg(self, level, msg):
        """
        格式化日志消息
        参数:
            level: 日志等级字符串
            msg: 日志内容
        返回:
            str: 格式化后的日志字符串
        """
        parts = []

        # 时间戳
        if LOG_CONFIG.get("show_timestamp", True):
            try:
                t = time.localtime()
                timestamp = f"{t[3]:02d}:{t[4]:02d}:{t[5]:02d}"
            except Exception:
                timestamp = "??:??:??"
            parts.append(timestamp)

        # 日志等级
        if LOG_CONFIG.get("show_level", True):
            level_str = f"[{level:<7}]"
            if _color_enable and level in COLORS:
                level_str = f"{COLORS[level]}{level_str}{COLORS['RESET']}"
            parts.append(level_str)

        # 模块名
        if LOG_CONFIG.get("show_module", True):
            parts.append(f"[{self._module:<10}]")

        # 消息内容
        parts.append(str(msg))

        return " ".join(parts)

    def _output(self, level, msg):
        """
        输出日志
        参数:
            level: 日志等级
            msg: 日志内容
        """
        if LOG_LEVELS.get(level, 0) < self._level:
            return

        formatted = self._format_msg(level, msg)

        # 串口输出
        if LOG_CONFIG.get("enable_uart", True):
            print(formatted)

        # 文件输出（预留接口）
        if LOG_CONFIG.get("enable_file", False):
            # TODO: 文件日志实现
            pass

    def debug(self, msg):
        """输出DEBUG级日志"""
        self._output("DEBUG", msg)

    def info(self, msg):
        """输出INFO级日志"""
        self._output("INFO", msg)

    def warning(self, msg):
        """输出WARNING级日志"""
        self._output("WARNING", msg)

    def error(self, msg):
        """输出ERROR级日志"""
        self._output("ERROR", msg)

    def critical(self, msg):
        """输出CRITICAL级日志"""
        self._output("CRITICAL", msg)

    def set_level(self, level):
        """
        设置当前日志记录器的等级
        参数:
            level: 日志等级字符串
        """
        if level in LOG_LEVELS:
            self._level = LOG_LEVELS[level]


def get_logger(module_name):
    """
    获取指定模块的日志记录器
    参数:
        module_name: 模块名称
    返回:
        Logger实例
    """
    return Logger(module_name)


def set_global_level(level):
    """
    设置全局日志等级
    参数:
        level: 日志等级字符串
    """
    global _global_level
    if level in LOG_LEVELS:
        _global_level = LOG_LEVELS[level]
