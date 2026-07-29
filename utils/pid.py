"""
PID控制器模块
============================================
标准位置式PID控制算法
带积分限幅、输出限幅、死区设置
用于风扇温控等闭环控制场景
"""

from config.config import FAN_PID_CONFIG


class PIDController:
    """
    标准PID控制器
    位置式PID算法，支持积分分离、积分限幅、输出限幅
    """

    def __init__(self, kp=None, ki=None, kd=None, config=None):
        """
        初始化PID控制器
        参数:
            kp: 比例系数
            ki: 积分系数
            kd: 微分系数
            config: 配置字典，可包含所有参数
        """
        # 使用配置文件默认值
        if config is None:
            config = FAN_PID_CONFIG

        self._kp = kp if kp is not None else config.get("kp", 2.0)
        self._ki = ki if ki is not None else config.get("ki", 0.1)
        self._kd = kd if kd is not None else config.get("kd", 0.5)

        # 目标值
        self._setpoint = config.get("target_temp", 55.0)

        # 输出限幅
        self._output_min = config.get("output_min", 0)
        self._output_max = config.get("output_max", 100)

        # 积分限幅
        self._integral_min = config.get("integral_min", -50)
        self._integral_max = config.get("integral_max", 50)

        # 内部状态
        self._integral = 0.0       # 积分项累计
        self._last_error = 0.0     # 上一次误差
        self._last_output = 0.0    # 上一次输出
        self._first_run = True     # 首次运行标志

    def set_setpoint(self, setpoint):
        """
        设置目标值
        参数:
            setpoint: 目标设定值
        """
        self._setpoint = setpoint

    def set_params(self, kp=None, ki=None, kd=None):
        """
        设置PID参数
        参数:
            kp: 比例系数
            ki: 积分系数
            kd: 微分系数
        """
        if kp is not None:
            self._kp = kp
        if ki is not None:
            self._ki = ki
        if kd is not None:
            self._kd = kd

    def set_output_limit(self, min_val, max_val):
        """
        设置输出限幅
        参数:
            min_val: 输出最小值
            max_val: 输出最大值
        """
        self._output_min = min_val
        self._output_max = max_val

    def set_integral_limit(self, min_val, max_val):
        """
        设置积分限幅
        参数:
            min_val: 积分最小值
            max_val: 积分最大值
        """
        self._integral_min = min_val
        self._integral_max = max_val

    def compute(self, feedback, dt=1.0):
        """
        计算PID输出
        参数:
            feedback: 反馈值（当前测量值）
            dt: 采样周期(秒)
        返回:
            float: PID输出值
        """
        # 计算误差
        error = self._setpoint - feedback

        # 比例项
        p_term = self._kp * error

        # 积分项（梯形积分）
        if not self._first_run:
            self._integral += self._ki * (error + self._last_error) * 0.5 * dt
            # 积分限幅
            self._integral = max(self._integral_min, min(self._integral_max, self._integral))
        i_term = self._integral

        # 微分项
        if self._first_run:
            d_term = 0.0
            self._first_run = False
        else:
            d_term = self._kd * (error - self._last_error) / dt

        # 总输出
        output = p_term + i_term + d_term

        # 输出限幅
        output = max(self._output_min, min(self._output_max, output))

        # 保存状态
        self._last_error = error
        self._last_output = output

        return output

    def reset(self):
        """重置PID控制器状态"""
        self._integral = 0.0
        self._last_error = 0.0
        self._last_output = 0.0
        self._first_run = True

    def get_integral(self):
        """获取当前积分值"""
        return self._integral

    def get_last_error(self):
        """获取上一次误差"""
        return self._last_error

    def get_setpoint(self):
        """获取目标设定值"""
        return self._setpoint
