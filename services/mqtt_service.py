"""
MQTT通信服务模块
============================================
业务服务层 - 负责MQTT云端通信
实现数据上报、命令接收、遗嘱消息等功能
调用系统WiFi和MQTT库，不直接操作硬件
"""

import json
import time
from utils.err_codes import *
from utils.logger import get_logger
from config.config import MQTT_CONFIG, WIFI_CONFIG, SYS_CONFIG

# 日志记录器
_log = get_logger("MQTT_SVC")

try:
    import network
    from umqtt.simple import MQTTClient
except ImportError:
    # 非ESP32环境模拟
    network = None
    MQTTClient = None


class MQTTService:
    """
    MQTT通信服务类
    负责WiFi连接、MQTT通信、数据上报和命令接收
    """

    def __init__(self, power_service, monitor_service):
        """
        初始化MQTT服务
        参数:
            power_service: 电源管理服务实例
            monitor_service: 状态监测服务实例
        """
        self._power_svc = power_service
        self._monitor_svc = monitor_service

        self._initialized = False
        self._connected = False
        self._wifi_connected = False

        self._client = None
        self._wlan = None

        self._last_report_time = 0
        self._report_interval = MQTT_CONFIG["report_interval"]

        # 主题
        self._topic_prefix = MQTT_CONFIG["topic_prefix"] + SYS_CONFIG["device_id"] + "/"
        self._cmd_topic = self._topic_prefix + "cmd"
        self._data_topic = self._topic_prefix + "data"
        self._status_topic = self._topic_prefix + "status"

        # 命令回调
        self._cmd_callback = None

    def init(self):
        """
        初始化MQTT服务
        返回:
            int: 错误码
        """
        if self._initialized:
            return ERR_ALREADY_INIT

        try:
            if network is None:
                _log.warning("非ESP32环境，MQTT服务模拟运行")
                self._initialized = True
                return ERR_OK

            # 初始化WiFi
            self._wlan = network.WLAN(network.STA_IF)
            self._wlan.active(True)

            self._initialized = True
            _log.info("MQTT服务初始化完成")
            return ERR_OK

        except Exception as e:
            _log.error(f"MQTT服务初始化失败: {e}")
            return ERR_MQTT_INIT_FAIL

    def connect_wifi(self):
        """
        连接WiFi
        返回:
            int: 错误码
        """
        if not self._initialized:
            return ERR_NOT_INITIALIZED

        if self._wifi_connected:
            return ERR_OK

        if network is None:
            self._wifi_connected = True
            return ERR_OK

        try:
            ssid = WIFI_CONFIG["ssid"]
            password = WIFI_CONFIG["password"]

            _log.info(f"连接WiFi: {ssid}")
            self._wlan.connect(ssid, password)

            # 等待连接
            timeout = WIFI_CONFIG["connect_timeout"]
            start = time.ticks_ms()

            while not self._wlan.isconnected():
                if time.ticks_diff(time.ticks_ms(), start) > timeout:
                    _log.error("WiFi连接超时")
                    return ERR_WIFI_CONNECT_FAIL
                time.sleep_ms(100)

            self._wifi_connected = True
            _log.info(f"WiFi连接成功，IP: {self._wlan.ifconfig()[0]}")
            return ERR_OK

        except Exception as e:
            _log.error(f"WiFi连接失败: {e}")
            return ERR_WIFI_CONNECT_FAIL

    def connect_mqtt(self):
        """
        连接MQTT服务器
        返回:
            int: 错误码
        """
        if not self._wifi_connected:
            return ERR_WIFI_NOT_CONNECTED

        if self._connected:
            return ERR_OK

        if MQTTClient is None:
            self._connected = True
            return ERR_OK

        try:
            client_id = SYS_CONFIG["device_id"]
            host = MQTT_CONFIG["host"]
            port = MQTT_CONFIG["port"]
            username = MQTT_CONFIG["username"]
            password = MQTT_CONFIG["password"]
            keepalive = MQTT_CONFIG["keepalive"]

            # 遗嘱消息
            will_topic = self._topic_prefix + MQTT_CONFIG["will_topic"]
            will_payload = MQTT_CONFIG["will_payload"]

            self._client = MQTTClient(
                client_id,
                host,
                port=port,
                user=username,
                password=password,
                keepalive=keepalive,
            )

            # 设置遗嘱
            self._client.set_last_will(
                will_topic,
                will_payload.encode(),
                retain=MQTT_CONFIG["will_retain"],
                qos=MQTT_CONFIG["qos"],
            )

            # 设置回调
            self._client.set_callback(self._on_message)

            # 连接
            self._client.connect()

            # 订阅命令主题
            self._client.subscribe(self._cmd_topic, qos=MQTT_CONFIG["qos"])

            # 上线通知
            self._client.publish(self._status_topic, b"online", retain=True)

            self._connected = True
            _log.info("MQTT连接成功")
            return ERR_OK

        except Exception as e:
            _log.error(f"MQTT连接失败: {e}")
            return ERR_MQTT_CONNECT_FAIL

    def disconnect(self):
        """断开MQTT连接"""
        if self._client and self._connected:
            try:
                self._client.publish(self._status_topic, b"offline", retain=True)
                self._client.disconnect()
            except Exception:
                pass
        self._connected = False

    def _on_message(self, topic, msg):
        """
        MQTT消息接收回调
        参数:
            topic: 主题
            msg: 消息内容
        """
        try:
            topic_str = topic.decode()
            msg_str = msg.decode()
            _log.debug(f"收到MQTT消息: {topic_str} -> {msg_str}")

            if topic_str == self._cmd_topic:
                self._handle_command(msg_str)

        except Exception as e:
            _log.error(f"处理MQTT消息失败: {e}")

    def _handle_command(self, cmd_str):
        """
        处理控制命令
        参数:
            cmd_str: 命令JSON字符串
        """
        try:
            cmd = json.loads(cmd_str)
            cmd_type = cmd.get("type", "")

            if cmd_type == "power_on":
                self._power_svc.power_on_sequence()
            elif cmd_type == "power_off":
                self._power_svc.power_off_sequence()
            elif cmd_type == "reset_fault":
                self._power_svc.reset_fault()
            elif cmd_type == "set_fan_temp":
                temp = cmd.get("temp", 55)
                self._monitor_svc.set_fan_target_temp(temp)
            elif cmd_type == "emergency_shutdown":
                self._power_svc.emergency_shutdown()

            # 调用外部回调
            if self._cmd_callback:
                self._cmd_callback(cmd)

        except Exception as e:
            _log.error(f"处理命令失败: {e}")

    def report_data(self):
        """
        上报监测数据
        返回:
            int: 错误码
        """
        if not self._connected:
            return ERR_MQTT_NOT_CONNECTED

        if MQTTClient is None:
            return ERR_OK

        try:
            data = {
                "device_id": SYS_CONFIG["device_id"],
                "timestamp": time.time(),
                "system_state": self._power_svc.get_system_state(),
                "fault_latched": self._power_svc.is_fault_latched(),
                "derate_active": self._power_svc.is_derate_active(),
                "voltages": self._monitor_svc.get_voltages(),
                "currents": self._monitor_svc.get_currents(),
                "temperatures": self._monitor_svc.get_temperatures(),
                "total_power": round(self._monitor_svc.get_total_power(), 2),
                "peak_power": round(self._monitor_svc.get_peak_power(), 2),
                "total_energy": round(self._monitor_svc.get_total_energy(), 4),
                "fan_speed": self._monitor_svc.get_fan_speed(),
                "fan_duty": self._monitor_svc.get_fan_duty(),
                "fault_codes": self._power_svc.get_fault_codes(),
            }

            payload = json.dumps(data).encode()
            self._client.publish(self._data_topic, payload, qos=MQTT_CONFIG["qos"])
            return ERR_OK

        except Exception as e:
            _log.error(f"上报数据失败: {e}")
            return ERR_MQTT_PUBLISH_FAIL

    def update(self):
        """
        更新MQTT状态
        需要在主循环中周期性调用
        返回:
            int: 错误码
        """
        if not self._initialized:
            return ERR_NOT_INITIALIZED

        try:
            # 检查WiFi连接
            if not self._wifi_connected:
                self.connect_wifi()
                return ERR_OK

            # 检查MQTT连接
            if not self._connected:
                self.connect_mqtt()
                return ERR_OK

            # 处理MQTT消息
            if self._client:
                self._client.check_msg()

            # 定时上报数据
            now = time.ticks_ms()
            if time.ticks_diff(now, self._last_report_time) >= self._report_interval:
                self.report_data()
                self._last_report_time = now

            return ERR_OK

        except Exception as e:
            _log.error(f"MQTT更新失败: {e}")
            self._connected = False
            return ERR_MQTT_DISCONNECTED

    def is_connected(self):
        """检测MQTT是否连接"""
        return self._connected

    def is_wifi_connected(self):
        """检测WiFi是否连接"""
        return self._wifi_connected

    def set_command_callback(self, callback):
        """设置命令接收回调"""
        self._cmd_callback = callback

    def deinit(self):
        """反初始化服务"""
        if self._initialized:
            self.disconnect()
            if self._wlan:
                self._wlan.active(False)
            self._initialized = False
            _log.info("MQTT服务已释放")
