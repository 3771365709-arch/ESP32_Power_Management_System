"""
配置集中管理模块
============================================
所有硬件引脚、功能参数、网络配置均在此统一管理
修改本文件即可适配不同硬件版本，无需修改业务代码

技术栈：ESP32-S3 + MicroPython + LVGL + MQTT + Modbus-RTU
"""

# ============================================================
# 系统基础配置
# ============================================================
SYS_CONFIG = {
    # 设备唯一标识，用于MQTT等通信
    "device_id": "HET-PWR-MGMT-001",
    # 设备型号
    "device_model": "ESP32-S3-HET-PWR",
    # 固件版本号
    "fw_version": "v2.0.0",
    # 硬件版本号
    "hw_version": "v2.1",
    # 主循环周期(ms)
    "main_loop_period": 50,
    # 看门狗超时时间(秒)
    "wdt_timeout": 30,
    # 系统启动延时(ms)，等待电源稳定
    "boot_delay": 500,
}

# ============================================================
# 引脚配置 - 电源控制（6路异构算力电源域）
# ============================================================
POWER_PIN_CONFIG = {
    # 6路电源域使能引脚 (GPIO编号)
    "enable_pins": [1, 2, 3, 4, 5, 6],
    # 电源域名称，对应异构算力各模块
    "domain_names": ["VCC_CORE", "VCC_MEM", "VCC_IO", "VCC_AFE", "VCC_CLK", "VCC_AUX"],
    # 上电时序延迟(ms)，按顺序依次上电（严格时序要求）
    "power_on_delays": [0, 10, 20, 50, 100, 200],
    # 下电时序延迟(ms)，按逆序依次下电
    "power_off_delays": [200, 100, 50, 20, 10, 0],
    # 每路电源额定电压(V)
    "rated_voltage": [1.0, 1.8, 3.3, 2.5, 1.2, 5.0],
    # 每路电源额定电流(A)
    "rated_current": [5.0, 3.0, 2.0, 1.5, 2.0, 1.0],
    # 过压保护阈值(额定电压百分比)
    "ovp_threshold": 1.10,  # 110%
    # 欠压保护阈值(额定电压百分比)
    "uvp_threshold": 0.90,  # 90%
    # 过流保护阈值(额定电流百分比)
    "ocp_threshold": 1.20,  # 120%
}

# ============================================================
# 引脚配置 - ADC采集（电压电流温度监测）
# ============================================================
ADC_PIN_CONFIG = {
    # 6路电压采集通道 (ADC1通道)
    "voltage_channels": [0, 1, 2, 3, 4, 5],
    # 6路电流采集通道 (ADC1通道)
    "current_channels": [6, 7, 8, 9, 10, 11],
    # 3路温度采集通道
    "temp_channels": [12, 13, 14],
    # 温度传感器名称
    "temp_names": ["FPGA_TEMP", "GPU_TEMP", "BOARD_TEMP"],
    # ADC参考电压(mV)
    "vref_mv": 2500,
    # ADC分辨率(位)
    "resolution": 12,
    # 电压分压比 (实际电压 = ADC电压 * 分压比)
    "voltage_divider": [11.0, 11.0, 4.3, 5.5, 9.1, 2.5],
    # 电流采样电阻(毫欧)
    "current_shunt_ohm": [10, 10, 20, 20, 10, 50],
    # 运放增益
    "opamp_gain": 50,
    # NTC参数
    "ntc_beta": 3950,
    "ntc_r25": 10000,  # 25度时电阻值
    # ADC采样次数（多次采样取平均）
    "sample_times": 8,
}

# ============================================================
# 引脚配置 - 智能风扇控制
# ============================================================
FAN_PIN_CONFIG = {
    # PWM控制引脚
    "pwm_pin": 7,
    # 转速检测引脚
    "tach_pin": 8,
    # PWM频率(Hz)
    "pwm_freq": 25000,
    # 最大转速(RPM)
    "max_rpm": 6000,
    # 最小转速(RPM)
    "min_rpm": 800,
    # 转速检测脉冲数/转
    "pulses_per_rev": 2,
}

# ============================================================
# PID风扇控制参数
# ============================================================
FAN_PID_CONFIG = {
    # PID参数
    "kp": 2.0,
    "ki": 0.1,
    "kd": 0.5,
    # 目标温度(摄氏度)
    "target_temp": 55.0,
    # 温度上限(超过则全速)
    "temp_max": 80.0,
    # 温度下限(低于则停转)
    "temp_min": 35.0,
    # 输出限幅(0-100%)
    "output_min": 0,
    "output_max": 100,
    # 积分限幅
    "integral_min": -50,
    "integral_max": 50,
    # 采样周期(秒)
    "sample_period": 0.5,
}

# ============================================================
# 引脚配置 - 按键输入
# ============================================================
KEY_PIN_CONFIG = {
    # 3个按键引脚
    "key_pins": [9, 10, 11],
    # 按键名称
    "key_names": ["MENU", "OK", "BACK"],
    # 消抖时间(ms)
    "debounce_ms": 20,
    # 长按判定时间(ms)
    "long_press_ms": 1000,
    # 按下电平 (0=低电平有效, 1=高电平有效)
    "active_level": 0,
    # 是否启用内部上拉
    "pull_up": True,
}

# ============================================================
# 引脚配置 - LED状态指示
# ============================================================
LED_PIN_CONFIG = {
    # 4个状态LED
    "led_pins": [12, 13, 14, 15],
    # LED名称
    "led_names": ["POWER", "RUN", "ALARM", "NET"],
    # 点亮电平
    "active_level": 1,
    # 闪烁周期(ms) - [亮时长, 灭时长]
    "blink_power": [1000, 0],      # 常亮
    "blink_run": [500, 500],       # 慢闪
    "blink_alarm": [200, 200],     # 快闪
    "blink_net": [1000, 1000],     # 慢闪
}

# ============================================================
# 引脚配置 - 蜂鸣器告警
# ============================================================
BUZZER_PIN_CONFIG = {
    # PWM引脚
    "pwm_pin": 16,
    # 默认频率(Hz)
    "default_freq": 2000,
    # 告警模式定义: [(频率, 持续ms, 间隔ms), ...]
    "patterns": {
        # 短响 - 按键反馈
        "click": [(2000, 50, 0)],
        # 双响 - 操作成功
        "success": [(2000, 80, 100), (2000, 80, 0)],
        # 长响 - 操作失败
        "error": [(1500, 500, 0)],
        # 连续告警 - 故障
        "alarm": [(2500, 200, 200), (2500, 200, 200), (2500, 200, 1000)],
    }
}

# ============================================================
# 掉电检测配置（交流掉电预警）
# ============================================================
POWER_LOSS_CONFIG = {
    # 掉电检测ADC通道
    "detect_channel": 15,
    # 掉电阈值电压(V)
    "threshold_volt": 10.0,
    # 防抖次数
    "debounce_count": 3,
    # 紧急保存超时时间(ms)
    "save_timeout": 500,
    # 储能电容维持时间(ms)
    "hold_up_time": 200,
}

# ============================================================
# 三级保护参数配置（告警-降额-切断）
# ============================================================
PROTECTION_CONFIG = {
    # 告警级：仅记录日志+指示灯，不动作
    "warning": {
        "voltage_deviation": 0.05,    # 电压偏差5%
        "current_ratio": 0.90,        # 电流达90%额定
        "temp_threshold": 70,         # 温度70度
        "debounce_ms": 1000,          # 持续1秒触发
    },
    # 降功率级：降低负载/关闭非必要电源域
    "derate": {
        "voltage_deviation": 0.08,    # 电压偏差8%
        "current_ratio": 1.05,        # 电流达105%额定
        "temp_threshold": 80,         # 温度80度
        "debounce_ms": 500,           # 持续0.5秒触发
        "auto_recovery": True,        # 自动恢复
        "recovery_delay_ms": 5000,    # 恢复延迟
    },
    # 切断级：立即切断电源，保护硬件
    "cutoff": {
        "voltage_deviation": 0.15,    # 电压偏差15%
        "current_ratio": 1.20,        # 电流达120%额定
        "temp_threshold": 90,         # 温度90度
        "debounce_ms": 10,            # 持续10ms触发
        "auto_recovery": False,       # 需手动复位
        "latch": True,                # 锁存故障
    },
}

# ============================================================
# WiFi配置
# ============================================================
WIFI_CONFIG = {
    "ssid": "Heterogeneous_Network",
    "password": "P@ssw0rd2024",
    # 连接超时(ms)
    "connect_timeout": 10000,
    # 自动重连间隔(ms)
    "reconnect_interval": 5000,
    # 最大重连次数
    "max_retry": 10,
}

# ============================================================
# MQTT配置（云端数据上报）
# ============================================================
MQTT_CONFIG = {
    "host": "mqtt.het-cloud.com",
    "port": 1883,
    "username": "device_admin",
    "password": "admin_het123",
    # 心跳间隔(秒)
    "keepalive": 60,
    # 数据上报周期(ms)
    "report_interval": 5000,
    # 主题前缀
    "topic_prefix": "het/device/power/",
    # QoS等级
    "qos": 1,
    # 遗嘱消息
    "will_topic": "status",
    "will_payload": "offline",
    # 遗嘱保留消息
    "will_retain": True,
}

# ============================================================
# Modbus-RTU配置（工业现场总线）
# ============================================================
MODBUS_CONFIG = {
    # 串口号
    "uart_id": 2,
    # 波特率
    "baudrate": 9600,
    # 数据位
    "bits": 8,
    # 校验位
    "parity": None,
    # 停止位
    "stop": 1,
    # TX引脚
    "tx_pin": 17,
    # RX引脚
    "rx_pin": 18,
    # 从机地址
    "slave_addr": 1,
    # 接收超时(ms)
    "rx_timeout": 100,
    # 字符间超时(ms)
    "char_timeout": 5,
    # 寄存器起始地址
    "reg_base_addr": 0x0000,
    # 最大寄存器数量
    "max_registers": 64,
}

# ============================================================
# OTA远程升级配置
# ============================================================
OTA_CONFIG = {
    # 升级服务器地址
    "server_url": "https://ota.het-cloud.com/firmware/",
    # 升级超时(秒)
    "timeout": 300,
    # 升级包MD5校验
    "verify_md5": True,
    # 自动回滚使能
    "auto_rollback": True,
    # 试运行时间(秒) - 升级后运行多久判定成功
    "trial_time": 120,
    # 升级包缓存分区
    "cache_partition": "ota_0",
}

# ============================================================
# 日志配置
# ============================================================
LOG_CONFIG = {
    # 日志等级: DEBUG, INFO, WARNING, ERROR, CRITICAL
    "level": "INFO",
    # 是否输出到串口
    "enable_uart": True,
    # 是否保存到文件
    "enable_file": False,
    # 日志文件最大行数
    "max_lines": 500,
    # 时间戳格式
    "show_timestamp": True,
    # 显示日志等级
    "show_level": True,
    # 显示模块名
    "show_module": True,
    # 日志颜色输出
    "color_output": True,
}

# ============================================================
# NVS存储键名定义
# ============================================================
NVS_KEYS = {
    # 系统参数
    "sys": {
        "boot_count": "sys_boot_cnt",
        "total_runtime": "sys_total_run",
        "last_fault_code": "sys_last_fault",
        "last_fault_time": "sys_last_fault_t",
    },
    # 配置参数
    "cfg": {
        "fan_target_temp": "cfg_fan_temp",
        "protection_level": "cfg_prot_level",
        "mqtt_enable": "cfg_mqtt_en",
        "modbus_enable": "cfg_modbus_en",
    },
    # 故障记录
    "fault": {
        "history": "fault_history",
        "count": "fault_count",
        "latest": "fault_latest",
    },
    # 电能统计
    "energy": {
        "total_kwh": "energy_total",
        "today_kwh": "energy_today",
        "peak_power": "energy_peak",
    },
}

# ============================================================
# 滤波参数配置
# ============================================================
FILTER_CONFIG = {
    # 滑动平均窗口大小
    "moving_avg_window": 8,
    # 限幅滤波阈值(相对于上一值的最大变化率)
    "limit_rate": 0.2,
    # 消抖计数
    "debounce_count": 3,
    # 中值滤波窗口
    "median_window": 5,
}

# ============================================================
# LVGL显示配置（人机交互界面）
# ============================================================
LVGL_CONFIG = {
    # 屏幕分辨率
    "width": 320,
    "height": 240,
    # SPI引脚
    "spi_id": 1,
    "sck_pin": 36,
    "mosi_pin": 35,
    "miso_pin": 37,
    "cs_pin": 34,
    "dc_pin": 33,
    "rst_pin": 32,
    "bl_pin": 31,
    # 驱动芯片
    "driver": "ST7789",
    # 像素格式
    "pixel_format": "RGB565",
    # 刷新率(Hz)
    "refresh_rate": 30,
    # 背光亮度(0-100)
    "backlight": 80,
    # 触摸芯片（如有）
    "touch_driver": "FT6236",
    "touch_sda": 38,
    "touch_scl": 39,
}

# ============================================================
# 电能统计配置
# ============================================================
ENERGY_CONFIG = {
    # 统计周期(秒)
    "stat_period": 60,
    # 保存间隔(分钟)
    "save_interval": 5,
    # 历史数据保留天数
    "history_days": 30,
}
