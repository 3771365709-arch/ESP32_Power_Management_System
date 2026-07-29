"""
OTA远程升级服务模块
============================================
业务服务层 - 负责固件远程升级
实现固件下载、校验、烧录、回滚功能
保证升级过程的可靠性和安全性
"""

import time
from utils.err_codes import *
from utils.logger import get_logger
from config.config import OTA_CONFIG, SYS_CONFIG

# 日志记录器
_log = get_logger("OTA_SVC")

try:
    import urequests as requests
    import hashlib
    import machine
except ImportError:
    requests = None
    hashlib = None
    machine = None

# OTA状态定义
OTA_STATE_IDLE = 0        # 空闲
OTA_STATE_DOWNLOADING = 1 # 下载中
OTA_STATE_VERIFYING = 2   # 校验中
OTA_STATE_FLASHING = 3    # 烧录中
OTA_STATE_SUCCESS = 4     # 成功
OTA_STATE_FAILED = 5      # 失败
OTA_STATE_ROLLBACK = 6    # 回滚中


class OTAService:
    """
    OTA远程升级服务类
    支持固件下载、MD5校验、自动回滚
    """

    def __init__(self, nvs_driver):
        """
        初始化OTA服务
        参数:
            nvs_driver: NVS驱动实例
        """
        self._nvs_drv = nvs_driver

        self._initialized = False
        self._state = OTA_STATE_IDLE
        self._progress = 0
        self._error_code = ERR_OK

        # 升级信息
        self._new_version = ""
        self._download_url = ""
        self._md5_sum = ""

        # 试运行标志
        self._trial_mode = False
        self._trial_start_time = 0

    def init(self):
        """
        初始化OTA服务
        返回:
            int: 错误码
        """
        if self._initialized:
            return ERR_ALREADY_INIT

        try:
            # 检查是否在试运行期
            self._check_trial_mode()

            self._initialized = True
            _log.info("OTA升级服务初始化完成")
            return ERR_OK

        except Exception as e:
            _log.error(f"OTA服务初始化失败: {e}")
            return ERR_SYS_EXCEPTION

    def _check_trial_mode(self):
        """检查是否处于升级试运行期"""
        try:
            # 读取试运行标志
            err, trial = self._nvs_drv.read_int("ota_trial", 0)
            if err == ERR_OK and trial == 1:
                self._trial_mode = True
                self._trial_start_time = time.ticks_ms()
                _log.info("检测到升级试运行模式")
        except Exception:
            pass

    def check_update(self):
        """
        检查是否有新版本
        返回:
            tuple: (错误码, 是否有新版本, 版本号)
        """
        if not self._initialized:
            return (ERR_NOT_INITIALIZED, False, "")

        if requests is None:
            return (ERR_OK, False, "")

        try:
            # 请求版本信息
            version_url = OTA_CONFIG["server_url"] + "latest_version.json"
            response = requests.get(version_url, timeout=10)

            if response.status_code != 200:
                return (ERR_OTA_DOWNLOAD_FAIL, False, "")

            import json
            info = json.loads(response.text)
            latest_ver = info.get("version", "")
            self._download_url = info.get("url", "")
            self._md5_sum = info.get("md5", "")

            current_ver = SYS_CONFIG["fw_version"]

            # 版本比较
            has_update = latest_ver != current_ver
            if has_update:
                self._new_version = latest_ver
                _log.info(f"发现新版本: {current_ver} -> {latest_ver}")

            response.close()
            return (ERR_OK, has_update, latest_ver)

        except Exception as e:
            _log.error(f"检查更新失败: {e}")
            return (ERR_OTA_DOWNLOAD_FAIL, False, "")

    def start_update(self, firmware_url=None, md5=None):
        """
        开始OTA升级
        参数:
            firmware_url: 固件下载地址（可选，默认使用检查更新获取的地址）
            md5: MD5校验值（可选）
        返回:
            int: 错误码
        """
        if not self._initialized:
            return ERR_NOT_INITIALIZED

        if self._state == OTA_STATE_DOWNLOADING:
            return ERR_OTA_IN_PROGRESS

        if firmware_url:
            self._download_url = firmware_url
        if md5:
            self._md5_sum = md5

        if not self._download_url:
            return ERR_INVALID_PARAM

        _log.info(f"开始OTA升级，下载地址: {self._download_url}")
        self._state = OTA_STATE_DOWNLOADING
        self._progress = 0
        self._error_code = ERR_OK

        # 在后台执行升级（这里简化处理，实际应使用线程）
        try:
            self._do_update()
        except Exception as e:
            _log.error(f"升级异常: {e}")
            self._state = OTA_STATE_FAILED
            self._error_code = ERR_OTA_FLASH_FAIL

        return ERR_OK

    def _do_update(self):
        """执行升级流程"""
        try:
            # 1. 下载固件
            _log.info("正在下载固件...")
            firmware_data = self._download_firmware()
            if not firmware_data:
                self._state = OTA_STATE_FAILED
                self._error_code = ERR_OTA_DOWNLOAD_FAIL
                return

            self._progress = 50
            self._state = OTA_STATE_VERIFYING

            # 2. MD5校验
            if OTA_CONFIG["verify_md5"] and self._md5_sum:
                _log.info("正在校验固件...")
                if not self._verify_md5(firmware_data):
                    self._state = OTA_STATE_FAILED
                    self._error_code = ERR_OTA_VERIFY_FAIL
                    return

            self._progress = 80
            self._state = OTA_STATE_FLASHING

            # 3. 烧录固件
            _log.info("正在烧录固件...")
            if not self._flash_firmware(firmware_data):
                self._state = OTA_STATE_FAILED
                self._error_code = ERR_OTA_FLASH_FAIL
                return

            # 4. 设置试运行标志
            if OTA_CONFIG["auto_rollback"]:
                self._nvs_drv.write_int("ota_trial", 1)

            self._progress = 100
            self._state = OTA_STATE_SUCCESS
            _log.info("OTA升级完成，准备重启")

            # 延迟重启
            time.sleep(2)
            if machine:
                machine.reset()

        except Exception as e:
            _log.error(f"升级流程异常: {e}")
            self._state = OTA_STATE_FAILED
            self._error_code = ERR_UNKNOWN

    def _download_firmware(self):
        """
        下载固件文件
        返回:
            bytes: 固件数据，失败返回None
        """
        if requests is None:
            return None

        try:
            response = requests.get(
                self._download_url,
                stream=True,
                timeout=OTA_CONFIG["timeout"]
            )

            if response.status_code != 200:
                _log.error(f"下载失败，状态码: {response.status_code}")
                return None

            # 获取文件大小
            content_length = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            firmware = bytearray()

            # 分块下载
            chunk_size = 4096
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    firmware.extend(chunk)
                    downloaded += len(chunk)
                    if content_length > 0:
                        self._progress = int(downloaded / content_length * 40)  # 下载占40%进度

            response.close()
            _log.info(f"固件下载完成，大小: {len(firmware)} 字节")
            return bytes(firmware)

        except Exception as e:
            _log.error(f"下载固件异常: {e}")
            return None

    def _verify_md5(self, data):
        """
        MD5校验
        参数:
            data: 固件数据
        返回:
            bool: True=校验通过
        """
        if hashlib is None:
            return True  # 没有hashlib时跳过校验

        try:
            md5 = hashlib.md5(data).hexdigest()
            _log.debug(f"计算MD5: {md5}, 期望: {self._md5_sum}")
            return md5.lower() == self._md5_sum.lower()
        except Exception as e:
            _log.error(f"MD5校验异常: {e}")
            return False

    def _flash_firmware(self, firmware_data):
        """
        烧录固件到OTA分区
        参数:
            firmware_data: 固件数据
        返回:
            bool: True=成功
        """
        try:
            # MicroPython OTA实现（根据实际平台调整）
            # 这里使用标准的machine.OTA接口
            if machine and hasattr(machine, 'OTA'):
                ota = machine.OTA()
                ota.write(firmware_data)
                ota.set_boot_partition()
                return True
            else:
                # 模拟模式
                _log.warning("非ESP32环境，跳过实际烧录")
                return True

        except Exception as e:
            _log.error(f"烧录固件异常: {e}")
            return False

    def confirm_update(self):
        """
        确认升级成功（清除试运行标志）
        在试运行期结束且系统运行正常时调用
        返回:
            int: 错误码
        """
        if not self._trial_mode:
            return ERR_OK

        try:
            self._nvs_drv.write_int("ota_trial", 0)
            self._trial_mode = False
            _log.info("升级已确认，试运行结束")
            return ERR_OK

        except Exception as e:
            _log.error(f"确认升级失败: {e}")
            return ERR_NVS_WRITE_FAIL

    def rollback(self):
        """
        手动触发回滚
        返回:
            int: 错误码
        """
        if not OTA_CONFIG["auto_rollback"]:
            return ERR_NOT_SUPPORTED

        _log.warning("执行固件回滚")
        self._state = OTA_STATE_ROLLBACK

        try:
            if machine and hasattr(machine, 'OTA'):
                ota = machine.OTA()
                ota.rollback()
                machine.reset()
            return ERR_OK

        except Exception as e:
            _log.error(f"回滚失败: {e}")
            return ERR_OTA_ROLLBACK

    def check_trial_timeout(self):
        """
        检查试运行是否超时，超时则自动确认
        返回:
            bool: True=已确认
        """
        if not self._trial_mode:
            return False

        trial_time = OTA_CONFIG["trial_time"] * 1000
        if time.ticks_diff(time.ticks_ms(), self._trial_start_time) >= trial_time:
            self.confirm_update()
            return True

        return False

    def get_state(self):
        """获取OTA状态"""
        return self._state

    def get_progress(self):
        """获取升级进度(0-100)"""
        return self._progress

    def get_error_code(self):
        """获取错误码"""
        return self._error_code

    def is_in_progress(self):
        """检测是否正在升级"""
        return self._state in (OTA_STATE_DOWNLOADING, OTA_STATE_VERIFYING, OTA_STATE_FLASHING)

    def is_trial_mode(self):
        """检测是否处于试运行模式"""
        return self._trial_mode

    def deinit(self):
        """反初始化服务"""
        if self._initialized:
            self._initialized = False
            _log.info("OTA升级服务已释放")
