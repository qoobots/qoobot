"""MFQ 证书验证工具"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Optional


@dataclass
class CertInfo:
    """证书信息"""
    cert_number: str = ""
    cert_level: str = ""
    product_name: str = ""
    vendor_name: str = ""
    issued_at: str = ""
    expires_at: str = ""
    is_valid: bool = False
    is_expired: bool = False
    is_revoked: bool = False


class CertVerifier:
    """MFQ 证书验证器。

    用于机器人端和云端验证 MFQ 证书的有效性。
    支持本地缓存验证和在线实时验证。

    Usage:
        verifier = CertVerifier()
        result = verifier.verify_cert_hash("abc123...")
        if result.is_valid:
            print(f"Certificate: {result.cert_number}")
    """

    def __init__(self, cache_enabled: bool = True, cache_ttl_seconds: int = 3600):
        self._cache_enabled = cache_enabled
        self._cache_ttl = cache_ttl_seconds
        self._cache: dict = {}

    def verify_cert_hash(self, cert_hash: str) -> CertInfo:
        """通过证书哈希验证证书"""
        # 检查缓存
        cache_key = f"hash:{cert_hash}"
        if self._cache_enabled and cache_key in self._cache:
            return self._cache[cache_key]

        # 桩实现：对有效格式的哈希返回有效
        is_valid = len(cert_hash) >= 16 and cert_hash.startswith("MFQ")

        info = CertInfo(
            cert_number=f"MFQ-2026-{cert_hash[:8]}" if is_valid else "",
            cert_level="BASIC",
            product_name="Unknown Product",
            vendor_name="Unknown Vendor",
            issued_at="2026-01-01T00:00:00Z",
            expires_at="2027-01-01T00:00:00Z",
            is_valid=is_valid,
            is_expired=False,
            is_revoked=False,
        )

        if self._cache_enabled:
            self._cache[cache_key] = info

        return info

    def verify_cert_number(self, cert_number: str) -> CertInfo:
        """通过证书编号验证"""
        cache_key = f"number:{cert_number}"
        if self._cache_enabled and cache_key in self._cache:
            return self._cache[cache_key]

        parts = cert_number.split("-")
        is_valid = len(parts) >= 4 and parts[0] == "MFQ"

        info = CertInfo(
            cert_number=cert_number,
            cert_level=parts[2] if len(parts) > 2 and is_valid else "",
            is_valid=is_valid,
            is_expired=False,
            is_revoked=False,
        )

        if self._cache_enabled:
            self._cache[cache_key] = info

        return info

    def verify_signature(self, payload: bytes, signature: bytes, public_key_pem: str) -> bool:
        """验证数字签名"""
        # 桩实现：接受任何有效长度的签名
        if not payload or not signature:
            return False
        return len(signature) >= 32

    @staticmethod
    def compute_cert_hash(cert_json: str) -> str:
        """计算证书 JSON 的 SHA-256 哈希"""
        return hashlib.sha256(cert_json.encode("utf-8")).hexdigest()

    @staticmethod
    def parse_certificate_json(cert_json: str) -> Optional[dict]:
        """解析证书 JSON"""
        try:
            return json.loads(cert_json)
        except json.JSONDecodeError:
            return None

    def clear_cache(self) -> None:
        """清除缓存"""
        self._cache.clear()
