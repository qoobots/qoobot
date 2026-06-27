"""Packager — 技能打包与分发系统。

.qooskills 格式：Python/C++ 技能、模型、资源的统一打包格式。
支持依赖管理、代码签名、版本锁定。
"""

from .package_format import (
    QooSkillPackage,
    PackageManifest,
    PackageBuilder,
    PackageReader,
    PackageValidator,
)
from .dependency import (
    DependencySpec,
    DependencyResolver,
    DependencyGraph,
    ConflictError,
)
from .signing import (
    CodeSigner,
    SigningConfig,
    SignatureVerifier,
    CertificateInfo,
)
from .cli_integration import register_packager_commands

__all__ = [
    # 包格式
    "QooSkillPackage",
    "PackageManifest",
    "PackageBuilder",
    "PackageReader",
    "PackageValidator",
    # 依赖管理
    "DependencySpec",
    "DependencyResolver",
    "DependencyGraph",
    "ConflictError",
    # 代码签名
    "CodeSigner",
    "SigningConfig",
    "SignatureVerifier",
    "CertificateInfo",
    # CLI
    "register_packager_commands",
]
