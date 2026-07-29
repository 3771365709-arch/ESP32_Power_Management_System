"""
统一错误码定义模块
============================================
所有模块的返回值统一使用本文件定义的错误码
便于错误追踪、日志记录和上层统一处理

错误码规则：
- 0 = 成功 (ERR_OK)
- 1-99 = 通用错误
- 100-199 = 硬件驱动层错误
- 200-299 = 业务服务层错误
- 300-399 = 通信层错误
- 400-499 = 存储/文件错误
- 500-599 = 系统级错误
"""

# ============================================================
# 通用错误码 (0-99)
# ============================================================
ERR_OK = 0                  # 操作成功
ERR_UNKNOWN = 1             # 未知错误
ERR_INVALID_PARAM = 2       # 参数无效
ERR_NOT_INITIALIZED = 3     # 模块未初始化
ERR_ALREADY_INIT = 4        # 已初始化
ERR_TIMEOUT = 5             # 操作超时
ERR_BUSY = 6                # 设备忙
ERR_NOT_SUPPORTED = 7       # 不支持的功能
ERR_OUT_OF_RANGE = 8        # 数值超出范围
ERR_NULL_POINTER = 9        # 空指针/空对象
ERR_PERMISSION_DENIED = 10  # 权限不足
ERR_BUFFER_OVERFLOW = 11    # 缓冲区溢出
ERR_CHECKSUM_FAIL = 12      # 校验失败

# ============================================================
# 硬件驱动层错误码 (100-199)
# ============================================================
# GPIO相关
ERR_GPIO_BASE = 100
ERR_GPIO_INVALID_PIN = 101      # 无效引脚号
ERR_GPIO_CONFIG_FAIL = 102      # GPIO配置失败

# ADC相关
ERR_ADC_BASE = 110
ERR_ADC_INVALID_CH = 111        # 无效ADC通道
ERR_ADC_READ_FAIL = 112         # ADC读取失败
ERR_ADC_CALIBRATION = 113       # ADC校准失败
ERR_ADC_OVERFLOW = 114          # ADC溢出

# PWM相关
ERR_PWM_BASE = 120
ERR_PWM_INIT_FAIL = 121         # PWM初始化失败
ERR_PWM_SET_FAIL = 122          # PWM设置失败
ERR_PWM_INVALID_DUTY = 123      # 无效占空比

# 电源相关
ERR_PWR_BASE = 130
ERR_PWR_INVALID_DOMAIN = 131    # 无效电源域
ERR_PWR_SEQUENCE_FAIL = 132     # 电源时序失败
ERR_PWR_PROTECTION_TRIG = 133   # 保护触发
ERR_PWR_ALREADY_ON = 134        # 电源已开启
ERR_PWR_ALREADY_OFF = 135       # 电源已关闭
ERR_PWR_RAMP_FAIL = 136         # 电源软启动失败

# 传感器相关
ERR_SENSOR_BASE = 140
ERR_SENSOR_NO_DATA = 141        # 无有效数据
ERR_SENSOR_COMM_FAIL = 142      # 传感器通信失败
ERR_SENSOR_OUT_OF_RANGE = 143   # 传感器超量程
ERR_SENSOR_CALIBRATION = 144    # 传感器校准失败

# 存储相关
ERR_NVS_BASE = 150
ERR_NVS_READ_FAIL = 151         # NVS读取失败
ERR_NVS_WRITE_FAIL = 152        # NVS写入失败
ERR_NVS_ERASE_FAIL = 153        # NVS擦除失败
ERR_NVS_KEY_NOT_FOUND = 154     # 键不存在
ERR_NVS_FULL = 155              # NVS空间满

# 看门狗相关
ERR_WDT_BASE = 160
ERR_WDT_INIT_FAIL = 161         # 看门狗初始化失败
ERR_WDT_FEED_FAIL = 162         # 看门狗喂狗失败

# ============================================================
# 业务服务层错误码 (200-299)
# ============================================================
# 电源管理服务
ERR_PM_BASE = 200
ERR_PM_OVP_TRIGGERED = 201      # 过压保护触发
ERR_PM_UVP_TRIGGERED = 202      # 欠压保护触发
ERR_PM_OCP_TRIGGERED = 203      # 过流保护触发
ERR_PM_OTP_TRIGGERED = 204      # 过温保护触发
ERR_PM_POWER_LOSS = 205         # 掉电检测触发
ERR_PM_FAULT_LATCHED = 206      # 故障锁存
ERR_PM_SEQUENCE_TIMEOUT = 207   # 电源时序超时
ERR_PM_DERATE_ACTIVE = 208      # 降额模式激活

# 状态监测服务
ERR_MON_BASE = 210
ERR_MON_SENSOR_FAULT = 211      # 传感器故障
ERR_MON_DATA_ABNORMAL = 212     # 数据异常
ERR_MON_CALC_FAIL = 213         # 数据计算失败

# 风扇控制服务
ERR_FAN_BASE = 220
ERR_FAN_STALL = 221             # 风扇堵转
ERR_FAN_SPEED_LOW = 222         # 风扇转速过低
ERR_FAN_SPEED_HIGH = 223        # 风扇转速过高
ERR_FAN_PID_FAIL = 224          # PID控制失败

# OTA升级服务
ERR_OTA_BASE = 230
ERR_OTA_DOWNLOAD_FAIL = 231     # 下载失败
ERR_OTA_VERIFY_FAIL = 232       # 校验失败
ERR_OTA_FLASH_FAIL = 233        # 烧录失败
ERR_OTA_ROLLBACK = 234          # 回滚中
ERR_OTA_NO_UPDATE = 235         # 无新版本
ERR_OTA_IN_PROGRESS = 236       # 升级进行中

# 电能统计服务
ERR_ENERGY_BASE = 240
ERR_ENERGY_CALC_FAIL = 241      # 电能计算失败
ERR_ENERGY_SAVE_FAIL = 242      # 电能保存失败

# ============================================================
# 通信层错误码 (300-399)
# ============================================================
# WiFi相关
ERR_WIFI_BASE = 300
ERR_WIFI_NOT_CONNECTED = 301    # WiFi未连接
ERR_WIFI_CONNECT_FAIL = 302     # WiFi连接失败
ERR_WIFI_DISCONNECTED = 303     # WiFi断开
ERR_WIFI_AUTH_FAIL = 304        # WiFi认证失败
ERR_WIFI_NO_SSID = 305          # 未找到SSID

# MQTT相关
ERR_MQTT_BASE = 310
ERR_MQTT_NOT_CONNECTED = 311    # MQTT未连接
ERR_MQTT_CONNECT_FAIL = 312     # MQTT连接失败
ERR_MQTT_PUBLISH_FAIL = 313     # 发布失败
ERR_MQTT_SUBSCRIBE_FAIL = 314   # 订阅失败
ERR_MQTT_DISCONNECTED = 315     # MQTT断开
ERR_MQTT_PING_FAIL = 316        # 心跳失败

# Modbus相关
ERR_MODBUS_BASE = 320
ERR_MODBUS_CRC_ERROR = 321      # CRC校验错误
ERR_MODBUS_INVALID_FRAME = 322  # 无效帧
ERR_MODBUS_TIMEOUT = 323        # 响应超时
ERR_MODBUS_EXCEPTION = 324      # 异常响应
ERR_MODBUS_INVALID_ADDR = 325   # 无效寄存器地址
ERR_MODBUS_INVALID_FUNC = 326   # 无效功能码
ERR_MODBUS_BUSY = 327           # Modbus忙

# 串口相关
ERR_UART_BASE = 330
ERR_UART_INIT_FAIL = 331        # 串口初始化失败
ERR_UART_SEND_FAIL = 332        # 发送失败
ERR_UART_RECV_FAIL = 333        # 接收失败
ERR_UART_OVERFLOW = 334         # 串口溢出

# ============================================================
# 存储/文件错误码 (400-499)
# ============================================================
ERR_FILE_BASE = 400
ERR_FILE_NOT_FOUND = 401        # 文件不存在
ERR_FILE_OPEN_FAIL = 402        # 文件打开失败
ERR_FILE_READ_FAIL = 403        # 文件读取失败
ERR_FILE_WRITE_FAIL = 404       # 文件写入失败
ERR_FILE_FULL = 405             # 存储空间满
ERR_FILE_DELETE_FAIL = 406      # 文件删除失败
ERR_FILE_FORMAT = 407           # 文件格式错误

# ============================================================
# 系统级错误码 (500-599)
# ============================================================
ERR_SYS_BASE = 500
ERR_SYS_OOM = 501               # 内存不足
ERR_SYS_ASSERT = 502            # 断言失败
ERR_SYS_EXCEPTION = 503         # 系统异常
ERR_SYS_WDT_RESET = 504         # 看门狗复位
ERR_SYS_INVALID_STATE = 505     # 无效状态
ERR_SYS_BOOT_FAIL = 506         # 系统启动失败
ERR_SYS_TASK_CREATE = 507       # 任务创建失败

# ============================================================
# UI层错误码 (600-699)
# ============================================================
ERR_UI_BASE = 600
ERR_UI_INIT_FAIL = 601          # UI初始化失败
ERR_UI_PAGE_NOT_FOUND = 602     # 页面不存在
ERR_UI_RENDER_FAIL = 603        # 渲染失败
ERR_UI_TOUCH_FAIL = 604         # 触摸失败

# ============================================================
# 错误码描述映射表
# 用于日志输出和调试
# ============================================================
ERR_DESC = {
    # 通用
    ERR_OK: "成功",
    ERR_UNKNOWN: "未知错误",
    ERR_INVALID_PARAM: "参数无效",
    ERR_NOT_INITIALIZED: "模块未初始化",
    ERR_ALREADY_INIT: "模块已初始化",
    ERR_TIMEOUT: "操作超时",
    ERR_BUSY: "设备忙",
    ERR_NOT_SUPPORTED: "不支持的功能",
    ERR_OUT_OF_RANGE: "数值超出范围",
    ERR_NULL_POINTER: "空指针",
    ERR_PERMISSION_DENIED: "权限不足",
    ERR_BUFFER_OVERFLOW: "缓冲区溢出",
    ERR_CHECKSUM_FAIL: "校验失败",

    # GPIO
    ERR_GPIO_INVALID_PIN: "无效引脚号",
    ERR_GPIO_CONFIG_FAIL: "GPIO配置失败",

    # ADC
    ERR_ADC_INVALID_CH: "无效ADC通道",
    ERR_ADC_READ_FAIL: "ADC读取失败",
    ERR_ADC_CALIBRATION: "ADC校准失败",
    ERR_ADC_OVERFLOW: "ADC溢出",

    # PWM
    ERR_PWM_INIT_FAIL: "PWM初始化失败",
    ERR_PWM_SET_FAIL: "PWM设置失败",
    ERR_PWM_INVALID_DUTY: "无效占空比",

    # 电源驱动
    ERR_PWR_INVALID_DOMAIN: "无效电源域",
    ERR_PWR_SEQUENCE_FAIL: "电源时序失败",
    ERR_PWR_PROTECTION_TRIG: "保护已触发",
    ERR_PWR_ALREADY_ON: "电源已开启",
    ERR_PWR_ALREADY_OFF: "电源已关闭",
    ERR_PWR_RAMP_FAIL: "电源软启动失败",

    # 传感器
    ERR_SENSOR_NO_DATA: "无有效数据",
    ERR_SENSOR_COMM_FAIL: "传感器通信失败",
    ERR_SENSOR_OUT_OF_RANGE: "传感器超量程",
    ERR_SENSOR_CALIBRATION: "传感器校准失败",

    # NVS
    ERR_NVS_READ_FAIL: "NVS读取失败",
    ERR_NVS_WRITE_FAIL: "NVS写入失败",
    ERR_NVS_ERASE_FAIL: "NVS擦除失败",
    ERR_NVS_KEY_NOT_FOUND: "NVS键不存在",
    ERR_NVS_FULL: "NVS空间满",

    # 看门狗
    ERR_WDT_INIT_FAIL: "看门狗初始化失败",
    ERR_WDT_FEED_FAIL: "看门狗喂狗失败",

    # 电源管理服务
    ERR_PM_OVP_TRIGGERED: "过压保护触发",
    ERR_PM_UVP_TRIGGERED: "欠压保护触发",
    ERR_PM_OCP_TRIGGERED: "过流保护触发",
    ERR_PM_OTP_TRIGGERED: "过温保护触发",
    ERR_PM_POWER_LOSS: "掉电检测触发",
    ERR_PM_FAULT_LATCHED: "故障已锁存",
    ERR_PM_SEQUENCE_TIMEOUT: "电源时序超时",
    ERR_PM_DERATE_ACTIVE: "降额模式激活",

    # 状态监测
    ERR_MON_SENSOR_FAULT: "传感器故障",
    ERR_MON_DATA_ABNORMAL: "数据异常",
    ERR_MON_CALC_FAIL: "数据计算失败",

    # 风扇
    ERR_FAN_STALL: "风扇堵转",
    ERR_FAN_SPEED_LOW: "风扇转速过低",
    ERR_FAN_SPEED_HIGH: "风扇转速过高",
    ERR_FAN_PID_FAIL: "PID控制失败",

    # OTA
    ERR_OTA_DOWNLOAD_FAIL: "OTA下载失败",
    ERR_OTA_VERIFY_FAIL: "OTA校验失败",
    ERR_OTA_FLASH_FAIL: "OTA烧录失败",
    ERR_OTA_ROLLBACK: "OTA回滚中",
    ERR_OTA_NO_UPDATE: "无新版本",
    ERR_OTA_IN_PROGRESS: "升级进行中",

    # 电能统计
    ERR_ENERGY_CALC_FAIL: "电能计算失败",
    ERR_ENERGY_SAVE_FAIL: "电能保存失败",

    # WiFi
    ERR_WIFI_NOT_CONNECTED: "WiFi未连接",
    ERR_WIFI_CONNECT_FAIL: "WiFi连接失败",
    ERR_WIFI_DISCONNECTED: "WiFi已断开",
    ERR_WIFI_AUTH_FAIL: "WiFi认证失败",
    ERR_WIFI_NO_SSID: "未找到SSID",

    # MQTT
    ERR_MQTT_NOT_CONNECTED: "MQTT未连接",
    ERR_MQTT_CONNECT_FAIL: "MQTT连接失败",
    ERR_MQTT_PUBLISH_FAIL: "MQTT发布失败",
    ERR_MQTT_SUBSCRIBE_FAIL: "MQTT订阅失败",
    ERR_MQTT_DISCONNECTED: "MQTT已断开",
    ERR_MQTT_PING_FAIL: "MQTT心跳失败",

    # Modbus
    ERR_MODBUS_CRC_ERROR: "Modbus CRC错误",
    ERR_MODBUS_INVALID_FRAME: "Modbus无效帧",
    ERR_MODBUS_TIMEOUT: "Modbus响应超时",
    ERR_MODBUS_EXCEPTION: "Modbus异常响应",
    ERR_MODBUS_INVALID_ADDR: "Modbus无效地址",
    ERR_MODBUS_INVALID_FUNC: "Modbus无效功能码",
    ERR_MODBUS_BUSY: "Modbus忙",

    # 串口
    ERR_UART_INIT_FAIL: "串口初始化失败",
    ERR_UART_SEND_FAIL: "串口发送失败",
    ERR_UART_RECV_FAIL: "串口接收失败",
    ERR_UART_OVERFLOW: "串口溢出",

    # 文件
    ERR_FILE_NOT_FOUND: "文件不存在",
    ERR_FILE_OPEN_FAIL: "文件打开失败",
    ERR_FILE_READ_FAIL: "文件读取失败",
    ERR_FILE_WRITE_FAIL: "文件写入失败",
    ERR_FILE_FULL: "存储空间满",
    ERR_FILE_DELETE_FAIL: "文件删除失败",
    ERR_FILE_FORMAT: "文件格式错误",

    # 系统
    ERR_SYS_OOM: "内存不足",
    ERR_SYS_ASSERT: "断言失败",
    ERR_SYS_EXCEPTION: "系统异常",
    ERR_SYS_WDT_RESET: "看门狗复位",
    ERR_SYS_INVALID_STATE: "无效系统状态",
    ERR_SYS_BOOT_FAIL: "系统启动失败",
    ERR_SYS_TASK_CREATE: "任务创建失败",

    # UI
    ERR_UI_INIT_FAIL: "UI初始化失败",
    ERR_UI_PAGE_NOT_FOUND: "页面不存在",
    ERR_UI_RENDER_FAIL: "渲染失败",
    ERR_UI_TOUCH_FAIL: "触摸失败",
}


def get_error_desc(err_code):
    """
    获取错误码对应的描述文本
    参数:
        err_code: 错误码整数
    返回:
        str: 错误描述字符串
    """
    return ERR_DESC.get(err_code, f"未知错误码({err_code})")


def is_success(err_code):
    """
    判断错误码是否表示成功
    参数:
        err_code: 错误码整数
    返回:
        bool: True=成功, False=失败
    """
    return err_code == ERR_OK


def is_error(err_code):
    """
    判断错误码是否表示失败
    参数:
        err_code: 错误码整数
    返回:
        bool: True=失败, False=成功
    """
    return err_code != ERR_OK
