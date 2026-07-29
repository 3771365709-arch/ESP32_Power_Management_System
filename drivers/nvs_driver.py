"""
NVS存储驱动模块
============================================
硬件驱动层 - 负责非易失性存储(NVS)操作
提供键值对存储接口，用于保存配置和运行数据
只提供基础存储操作，业务数据结构由上层定义
"""

try:
    from esp32 import NVS
except ImportError:
    # 非ESP32环境下的模拟实现，用于开发调试
    NVS = None

import json
from utils.err_codes import *
from utils.logger import get_logger

# 日志记录器
_log = get_logger("NVS_DRV")

# 默认命名空间
DEFAULT_NAMESPACE = "pwr_mgmt"


class NVSDriver:
    """
    NVS存储驱动类
    封装ESP32 NVS操作，提供统一的键值存储接口
    """

    def __init__(self, namespace=DEFAULT_NAMESPACE):
        """
        初始化NVS驱动
        参数:
            namespace: NVS命名空间
        """
        self._namespace = namespace
        self._nvs = None
        self._initialized = False

        # 非ESP32环境下的内存模拟存储
        self._sim_storage = {}

    def init(self):
        """
        初始化NVS
        返回:
            int: 错误码
        """
        if self._initialized:
            return ERR_ALREADY_INIT

        try:
            if NVS is not None:
                self._nvs = NVS(self._namespace)
            else:
                _log.warning("非ESP32环境，使用内存模拟NVS")

            self._initialized = True
            _log.info(f"NVS驱动初始化完成，命名空间: {self._namespace}")
            return ERR_OK

        except Exception as e:
            _log.error(f"NVS驱动初始化失败: {e}")
            return ERR_NVS_READ_FAIL

    def write_int(self, key, value):
        """
        写入整数值
        参数:
            key: 键名
            value: 整数值
        返回:
            int: 错误码
        """
        if not self._initialized:
            return ERR_NOT_INITIALIZED

        try:
            if self._nvs is not None:
                self._nvs.set_i32(key, value)
                self._nvs.commit()
            else:
                self._sim_storage[key] = value
            return ERR_OK

        except Exception as e:
            _log.error(f"NVS写入整数失败 {key}: {e}")
            return ERR_NVS_WRITE_FAIL

    def read_int(self, key, default=0):
        """
        读取整数值
        参数:
            key: 键名
            default: 默认值
        返回:
            tuple: (错误码, 值)
        """
        if not self._initialized:
            return (ERR_NOT_INITIALIZED, default)

        try:
            if self._nvs is not None:
                value = self._nvs.get_i32(key)
            else:
                value = self._sim_storage.get(key, default)
            return (ERR_OK, value)

        except Exception as e:
            _log.warning(f"NVS读取整数失败 {key}: {e}")
            return (ERR_NVS_KEY_NOT_FOUND, default)

    def write_float(self, key, value):
        """
        写入浮点值（通过字符串存储）
        参数:
            key: 键名
            value: 浮点值
        返回:
            int: 错误码
        """
        return self.write_str(key, str(value))

    def read_float(self, key, default=0.0):
        """
        读取浮点值
        参数:
            key: 键名
            default: 默认值
        返回:
            tuple: (错误码, 值)
        """
        err, str_val = self.read_str(key, "")
        if err != ERR_OK:
            return (err, default)
        try:
            return (ERR_OK, float(str_val))
        except ValueError:
            return (ERR_FILE_FORMAT, default)

    def write_str(self, key, value):
        """
        写入字符串
        参数:
            key: 键名
            value: 字符串值
        返回:
            int: 错误码
        """
        if not self._initialized:
            return ERR_NOT_INITIALIZED

        try:
            if self._nvs is not None:
                self._nvs.set_str(key, value)
                self._nvs.commit()
            else:
                self._sim_storage[key] = value
            return ERR_OK

        except Exception as e:
            _log.error(f"NVS写入字符串失败 {key}: {e}")
            return ERR_NVS_WRITE_FAIL

    def read_str(self, key, default=""):
        """
        读取字符串
        参数:
            key: 键名
            default: 默认值
        返回:
            tuple: (错误码, 值)
        """
        if not self._initialized:
            return (ERR_NOT_INITIALIZED, default)

        try:
            if self._nvs is not None:
                value = self._nvs.get_str(key)
            else:
                value = self._sim_storage.get(key, default)
            return (ERR_OK, value)

        except Exception as e:
            _log.warning(f"NVS读取字符串失败 {key}: {e}")
            return (ERR_NVS_KEY_NOT_FOUND, default)

    def write_blob(self, key, data):
        """
        写入二进制数据
        参数:
            key: 键名
            data: bytes数据
        返回:
            int: 错误码
        """
        if not self._initialized:
            return ERR_NOT_INITIALIZED

        try:
            if self._nvs is not None:
                self._nvs.set_blob(key, data)
                self._nvs.commit()
            else:
                self._sim_storage[key] = data
            return ERR_OK

        except Exception as e:
            _log.error(f"NVS写入二进制失败 {key}: {e}")
            return ERR_NVS_WRITE_FAIL

    def read_blob(self, key, default=b""):
        """
        读取二进制数据
        参数:
            key: 键名
            default: 默认值
        返回:
            tuple: (错误码, 值)
        """
        if not self._initialized:
            return (ERR_NOT_INITIALIZED, default)

        try:
            if self._nvs is not None:
                buf = bytearray(256)
                length = self._nvs.get_blob(key, buf)
                value = bytes(buf[:length])
            else:
                value = self._sim_storage.get(key, default)
            return (ERR_OK, value)

        except Exception as e:
            _log.warning(f"NVS读取二进制失败 {key}: {e}")
            return (ERR_NVS_KEY_NOT_FOUND, default)

    def write_json(self, key, obj):
        """
        写入JSON对象
        参数:
            key: 键名
            obj: 可序列化的Python对象
        返回:
            int: 错误码
        """
        try:
            json_str = json.dumps(obj)
            return self.write_str(key, json_str)
        except Exception as e:
            _log.error(f"JSON序列化失败 {key}: {e}")
            return ERR_FILE_FORMAT

    def read_json(self, key, default=None):
        """
        读取JSON对象
        参数:
            key: 键名
            default: 默认值
        返回:
            tuple: (错误码, 对象)
        """
        err, json_str = self.read_str(key, "")
        if err != ERR_OK:
            return (err, default)
        try:
            obj = json.loads(json_str)
            return (ERR_OK, obj)
        except Exception as e:
            _log.error(f"JSON解析失败 {key}: {e}")
            return (ERR_FILE_FORMAT, default)

    def erase_key(self, key):
        """
        删除指定键
        参数:
            key: 键名
        返回:
            int: 错误码
        """
        if not self._initialized:
            return ERR_NOT_INITIALIZED

        try:
            if self._nvs is not None:
                self._nvs.erase_key(key)
                self._nvs.commit()
            else:
                if key in self._sim_storage:
                    del self._sim_storage[key]
            return ERR_OK

        except Exception as e:
            _log.error(f"NVS删除键失败 {key}: {e}")
            return ERR_NVS_ERASE_FAIL

    def erase_all(self):
        """
        擦除所有数据
        返回:
            int: 错误码
        """
        if not self._initialized:
            return ERR_NOT_INITIALIZED

        try:
            if self._nvs is not None:
                self._nvs.erase_all()
                self._nvs.commit()
            else:
                self._sim_storage.clear()
            _log.warning("NVS所有数据已擦除")
            return ERR_OK

        except Exception as e:
            _log.error(f"NVS擦除失败: {e}")
            return ERR_NVS_ERASE_FAIL

    def deinit(self):
        """
        反初始化NVS驱动
        """
        if self._initialized:
            self._nvs = None
            self._initialized = False
            _log.info("NVS驱动已释放")
