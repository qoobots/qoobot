"""应用初始化 — QApplication 配置与全局设置"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QLocale
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication


def setup_logging(level: int = logging.INFO) -> None:
    """配置日志系统"""
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def create_application(argv: list[str] | None = None) -> QApplication:
    """创建并配置 QApplication 实例

    设置应用元信息、字体、高DPI支持。
    """
    if argv is None:
        argv = sys.argv

    # 高 DPI 支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(argv)
    app.setApplicationName("qooremote")
    app.setApplicationDisplayName("QooRemote")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("QooBot")
    app.setOrganizationDomain("qoobot.dev")

    # 设置默认字体
    font = QFont("Segoe UI", 10)
    font.setFamilies(["Segoe UI", "Microsoft YaHei", "Noto Sans CJK SC", "sans-serif"])
    app.setFont(font)

    # 中文 locale
    locale = QLocale(QLocale.Language.Chinese, QLocale.Country.China)
    QLocale.setDefault(locale)

    return app
