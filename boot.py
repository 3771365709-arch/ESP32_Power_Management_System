"""
boot.py - 系统启动引导文件
============================================
MicroPython启动时首先执行此文件
负责基础硬件初始化、系统时钟配置、启动计数等
注意：此文件应尽量精简，避免复杂逻辑
"""

import machine
import sys
import os

# 启动标志
_BOOT_OK = False


def boot_init():
    """
    启动初始化
    执行最基础的硬件配置
    """
    global _BOOT_OK

    try:
        # 禁用REPL调试输出（可选）
        # import esp
        # esp.osdebug(None)

        # 配置系统频率（ESP32-S3默认240MHz）
        # machine.freq(240000000)

        # 初始化随机数种子
        import urandom
        urandom.seed(machine.unique_id())

        # 添加库路径
        sys.path.insert(0, '/')
        sys.path.insert(0, '/lib')

        # 垃圾回收
        import gc
        gc.enable()
        gc.collect()

        _BOOT_OK = True
        print("[BOOT] 系统引导完成")
        return True

    except Exception as e:
        print(f"[BOOT] 引导失败: {e}")
        return False


def check_boot_mode():
    """
    检测启动模式
    返回:
        str: 'normal'=正常启动, 'safe'=安全模式, 'update'=升级模式
    """
    # 这里可以通过检测GPIO电平判断启动模式
    # 简化处理：默认正常启动
    return "normal"


# 执行启动初始化
if __name__ == "__main__":
    boot_ok = boot_init()
    boot_mode = check_boot_mode()

    if not boot_ok:
        # 引导失败，进入安全模式
        print("[BOOT] 引导失败，进入安全模式")
        # 此处可启动最小系统
    else:
        print(f"[BOOT] 启动模式: {boot_mode}")
