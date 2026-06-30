"""单位转换工具"""

from __future__ import annotations

import math


def rad_to_deg(rad: float) -> float:
    """弧度 → 角度"""
    return rad * 180.0 / math.pi


def deg_to_rad(deg: float) -> float:
    """角度 → 弧度"""
    return deg * math.pi / 180.0


def celsius_to_fahrenheit(c: float) -> float:
    """摄氏度 → 华氏度"""
    return c * 9.0 / 5.0 + 32.0


def fahrenheit_to_celsius(f: float) -> float:
    """华氏度 → 摄氏度"""
    return (f - 32.0) * 5.0 / 9.0


def watts_to_hp(w: float) -> float:
    """瓦特 → 马力"""
    return w / 745.7


def hp_to_watts(hp: float) -> float:
    """马力 → 瓦特"""
    return hp * 745.7


def nm_to_kgf_cm(nm: float) -> float:
    """牛米 → 千克力厘米"""
    return nm * 10.1972


def bytes_to_human(size_bytes: int) -> str:
    """字节 → 人类可读格式"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    for unit in ("KB", "MB", "GB", "TB"):
        size_bytes /= 1024.0
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
    return f"{size_bytes:.1f} PB"


def seconds_to_human(total_seconds: float) -> str:
    """秒 → 人类可读时间"""
    if total_seconds < 0:
        return "0s"
    days = int(total_seconds // 86400)
    hours = int((total_seconds % 86400) // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
    return "".join(parts)
