"""
数字滤波模块
============================================
提供多种数字滤波算法
用于ADC采样数据的平滑处理
包含：滑动平均滤波、限幅滤波、中值滤波、消抖滤波
"""

from config.config import FILTER_CONFIG


class MovingAverageFilter:
    """
    滑动平均滤波器
    对连续N个采样值取平均，有效抑制随机噪声
    """

    def __init__(self, window_size=None):
        """
        初始化滑动平均滤波器
        参数:
            window_size: 窗口大小，默认使用配置值
        """
        if window_size is None:
            window_size = FILTER_CONFIG.get("moving_avg_window", 8)
        self._window_size = window_size
        self._buffer = []
        self._sum = 0.0

    def update(self, value):
        """
        更新滤波器，输入新采样值
        参数:
            value: 新采样值
        返回:
            float: 滤波后的值
        """
        self._buffer.append(value)
        self._sum += value

        # 窗口满时移除最旧的值
        if len(self._buffer) > self._window_size:
            self._sum -= self._buffer.pop(0)

        return self._sum / len(self._buffer)

    def reset(self):
        """重置滤波器"""
        self._buffer.clear()
        self._sum = 0.0

    def get_value(self):
        """获取当前滤波值"""
        if not self._buffer:
            return 0.0
        return self._sum / len(self._buffer)


class LimitFilter:
    """
    限幅滤波器
    限制两次采样值的最大变化率，剔除突变干扰
    """

    def __init__(self, max_change_rate=None):
        """
        初始化限幅滤波器
        参数:
            max_change_rate: 最大变化率（相对于上一值的比例）
        """
        if max_change_rate is None:
            max_change_rate = FILTER_CONFIG.get("limit_rate", 0.2)
        self._max_rate = max_change_rate
        self._last_value = None

    def update(self, value):
        """
        更新滤波器
        参数:
            value: 新采样值
        返回:
            float: 滤波后的值
        """
        if self._last_value is None:
            self._last_value = value
            return value

        # 计算最大允许变化量
        max_delta = abs(self._last_value) * self._max_rate
        delta = value - self._last_value

        if abs(delta) > max_delta:
            # 超过限幅，按最大步长变化
            if delta > 0:
                self._last_value += max_delta
            else:
                self._last_value -= max_delta
        else:
            self._last_value = value

        return self._last_value

    def reset(self):
        """重置滤波器"""
        self._last_value = None

    def get_value(self):
        """获取当前滤波值"""
        return self._last_value if self._last_value is not None else 0.0


class MedianFilter:
    """
    中值滤波器
    对连续N个采样值取中值，有效抑制脉冲干扰
    """

    def __init__(self, window_size=None):
        """
        初始化中值滤波器
        参数:
            window_size: 窗口大小，默认使用配置值
        """
        if window_size is None:
            window_size = FILTER_CONFIG.get("median_window", 5)
        self._window_size = window_size
        self._buffer = []

    def update(self, value):
        """
        更新滤波器
        参数:
            value: 新采样值
        返回:
            float: 滤波后的值
        """
        self._buffer.append(value)

        if len(self._buffer) > self._window_size:
            self._buffer.pop(0)

        # 计算中值
        sorted_buf = sorted(self._buffer)
        mid = len(sorted_buf) // 2
        return sorted_buf[mid]

    def reset(self):
        """重置滤波器"""
        self._buffer.clear()

    def get_value(self):
        """获取当前滤波值"""
        if not self._buffer:
            return 0.0
        sorted_buf = sorted(self._buffer)
        mid = len(sorted_buf) // 2
        return sorted_buf[mid]


class DebounceFilter:
    """
    消抖滤波器
    连续N次采样值稳定才认为有效，用于状态判定
    """

    def __init__(self, debounce_count=None):
        """
        初始消抖滤波器
        参数:
            debounce_count: 消抖计数，默认使用配置值
        """
        if debounce_count is None:
            debounce_count = FILTER_CONFIG.get("debounce_count", 3)
        self._debounce_count = debounce_count
        self._current_state = False
        self._counter = 0
        self._last_raw_state = False

    def update(self, state):
        """
        更新消抖状态
        参数:
            state: 原始状态(bool)
        返回:
            bool: 消抖后的稳定状态
        """
        if state == self._last_raw_state:
            self._counter += 1
        else:
            self._counter = 1
            self._last_raw_state = state

        # 连续N次相同才更新状态
        if self._counter >= self._debounce_count:
            self._current_state = state

        return self._current_state

    def reset(self):
        """重置滤波器"""
        self._current_state = False
        self._counter = 0
        self._last_raw_state = False

    def get_state(self):
        """获取当前稳定状态"""
        return self._current_state


class CompositeFilter:
    """
    复合滤波器
    组合限幅+滑动平均，达到最佳滤波效果
    """

    def __init__(self, window_size=8, max_change_rate=0.2):
        """
        初始化复合滤波器
        参数:
            window_size: 滑动平均窗口大小
            max_change_rate: 限幅最大变化率
        """
        self._limit_filter = LimitFilter(max_change_rate)
        self._avg_filter = MovingAverageFilter(window_size)

    def update(self, value):
        """
        更新滤波器
        参数:
            value: 新采样值
        返回:
            float: 滤波后的值
        """
        # 先限幅，再滑动平均
        limited = self._limit_filter.update(value)
        return self._avg_filter.update(limited)

    def reset(self):
        """重置滤波器"""
        self._limit_filter.reset()
        self._avg_filter.reset()

    def get_value(self):
        """获取当前滤波值"""
        return self._avg_filter.get_value()
