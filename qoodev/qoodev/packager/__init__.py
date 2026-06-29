"""Packager — 技能打包与分发系统。

.qooskills 格式：Python/C++ 技能、模型、资源的统一打包格式。
支持依赖管理、代码签名、版本锁定。
"""

from .package_format import (
    PackageManifest,
    PackageBuilder,
    PackageReader,
    PackageValidator,
    SkillCategory,
    SkillRuntime,
    SkillPlatform,
    create_default_manifest,
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
try:
    from .cli_integration import register_packager_commands
except ImportError:
    register_packager_commands = None  # typer not installed

__all__ = [
    # 包格式
    "PackageManifest",
    "PackageBuilder",
    "PackageReader",
    "PackageValidator",
    "SkillCategory",
    "SkillRuntime",
    "SkillPlatform",
    "create_default_manifest",
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
