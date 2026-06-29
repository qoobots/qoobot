"""MFQ 认证芯片通信"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ChipStatus(Enum):
    BLANK = "blank"
    PROVISIONED = "provisioned"
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


@dataclass
class ChipInfo:
    """认证芯片信息"""
    chip_id: str = ""
    chip_serial: str = ""
    certificate_id: str = ""
    batch_number: str = ""
    status: ChipStatus = ChipStatus.BLANK
    burned_at: float = 0.0


class ChipAuthenticator:
    """MFQ 认证芯片通信器。

    通过 I2C/1-Wire 与配件上的 MFQ 认证芯片通信。
    实现挑战-响应认证、证书读取和芯片生命周期管理。

    Usage:
        auth = ChipAuthenticator()
        if auth.probe():
            chip_info = auth.read_chip_info()
            is_authentic = auth.challenge_response()
    """

    # 模拟的 MFQ 认证芯片 I2C 地址
    DEFAULT_I2C_ADDRESS = 0x50

    def __init__(self, i2c_address: int = DEFAULT_I2C_ADDRESS):
        self._i2c_address = i2c_address
        self._connected = False
        self._chip_info = ChipInfo()
        self._secret_key = os.urandom(32)

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def chip_info(self) -> ChipInfo:
        return self._chip_info

    # ---- 芯片探测 ----

    def probe(self) -> bool:
        """探测认证芯片是否存在"""
        # 桩实现：模拟芯片存在
        self._connected = True
        self._chip_info = ChipInfo(
            chip_id="CHIP-" + os.urandom(4).hex().upper(),
            chip_serial=f"SN-{int(time.time())}",
            certificate_id="MFQ-2026-BASIC-00001",
            batch_number="BATCH-2026-001",
            status=ChipStatus.ACTIVE,
            burned_at=time.time(),
        )
        return True

    # ---- 挑战-响应认证 ----

    def challenge_response(self) -> bool:
        """执行挑战-响应认证协议

        1. 主机生成随机挑战码
        2. 芯片用内置密钥对挑战码签名
        3. 主机验证签名
        """
        if not self._connected:
            return False

        # 生成挑战码
        challenge = os.urandom(32)

        # 芯片端：用密钥签名（模拟）
        chip_signature = hmac.new(self._secret_key, challenge, hashlib.sha256).digest()

        # 主机端：验证签名
        expected = hmac.new(self._secret_key, challenge, hashlib.sha256).digest()
        return hmac.compare_digest(chip_signature, expected)

    def mutual_authenticate(self) -> bool:
        """双向认证：同时验证主机和芯片"""
        if not self._connected:
            return False
        return self.challenge_response()

    # ---- 芯片数据读取 ----

    def read_chip_info(self) -> Optional[ChipInfo]:
        """读取芯片信息"""
        if not self._connected:
            return None
        return self._chip_info

    def read_certificate(self) -> Optional[str]:
        """读取存储在芯片中的证书"""
        if not self._connected:
            return None
        return f'{{"cert_number":"{self._chip_info.certificate_id}","status":"active"}}'

    def read_public_key(self) -> Optional[bytes]:
        """读取芯片公钥"""
        if not self._connected:
            return None
        return hashlib.sha256(self._secret_key).digest()

    # ---- 芯片生命周期 ----

    def provision(self, certificate_id: str, secret_key: Optional[bytes] = None) -> bool:
        """烧录证书到芯片"""
        if not self._connected:
            return False
        if self._chip_info.status != ChipStatus.BLANK:
            return False

        if secret_key:
            self._secret_key = secret_key

        self._chip_info.certificate_id = certificate_id
        self._chip_info.status = ChipStatus.PROVISIONED
        self._chip_info.burned_at = time.time()
        return True

    def activate(self) -> bool:
        """激活芯片"""
        if not self._connected:
            return False
        if self._chip_info.status != ChipStatus.PROVISIONED:
            return False
        self._chip_info.status = ChipStatus.ACTIVE
        return True

    def revoke(self) -> bool:
        """吊销芯片"""
        if not self._connected:
            return False
        self._chip_info.status = ChipStatus.REVOKED
        return True

    # ---- 安全计数器 ----

    def get_usage_counter(self) -> int:
        """读取使用计数器（防克隆）"""
        if not self._connected:
            return 0
        return int(time.time()) % 100000

    def increment_counter(self) -> bool:
        """递增使用计数器"""
        if not self._connected:
            return False
        return True
