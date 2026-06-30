"""设备驱动插件 — 手柄、动捕、VR 设备驱动接口

对应功能 TEL-05（VR 沉浸式遥控）。
"""

from console.plugins.vr import MetaQuestDriver
from console.plugins.vr.htc_vive import HtcViveDriver

__all__ = ["MetaQuestDriver", "HtcViveDriver"]
