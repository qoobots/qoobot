""".qooskills 包格式定义 — 构建、读取、校验。

包结构:
  skill.qooskills  (ZIP 容器)
  ├── manifest.json       # 元数据 + 依赖声明
  ├── signature.sig       # 代码签名 (可选)
  ├── python/             # Python 技能代码
  ├── cpp/                # C++ 技能代码 (可选)
  ├── models/             # 编译后模型文件 (可选)
  ├── resources/          # 3D 模型、纹理、音频等
  └── docs/               # 技能文档
"""

import json
import os
import shutil
import tempfile
import zipfile
import hashlib
import io
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class SkillCategory(str, Enum):
    PERCEPTION = "perception"       # 感知技能
    PLANNING = "planning"           # 规划技能
    CONTROL = "control"             # 控制技能
    NAVIGATION = "navigation"       # 导航技能
    MANIPULATION = "manipulation"   # 操作技能
    INTERACTION = "interaction"     # 人机交互
    UTILITY = "utility"             # 工具/服务
    COMPOSITE = "composite"         # 复合技能


class SkillRuntime(str, Enum):
    PYTHON = "python"
    CPP = "cpp"
    HYBRID = "hybrid"              # Python + C++ 混合


class SkillPlatform(str, Enum):
    LINUX_X86 = "linux-x86_64"
    LINUX_ARM = "linux-aarch64"
    WINDOWS = "windows-x86_64"
    MACOS = "macos-arm64"
    QOOBOT = "qoobot"              # 端侧部署
    SIM = "sim"                    # 仿真环境


@dataclass
class PackageManifest:
    """技能包清单文件"""
    # 基础信息
    name: str                           # 技能唯一标识 (com.example.my_skill)
    version: str                        # 语义化版本
    display_name: str = ""              # 显示名称
    description: str = ""               # 描述
    category: SkillCategory = SkillCategory.UTILITY
    runtime: SkillRuntime = SkillRuntime.PYTHON

    # 作者信息
    author: str = ""
    author_email: str = ""
    license: str = "MIT"
    homepage: str = ""

    # 依赖
    dependencies: List[Dict[str, str]] = field(default_factory=list)
    # [{"name": "qoobot-sdk", "version": ">=1.0.0"}, ...]
    python_dependencies: List[str] = field(default_factory=list)
    # ["numpy>=1.21", "torch>=2.0"]

    # 入口点
    entry_point: str = ""               # "module:function" 或 "skill_class"
    main_module: str = ""               # 主模块路径

    # 平台兼容
    platforms: List[str] = field(default_factory=lambda: ["linux-x86_64", "qoobot"])
    min_qoobot_version: str = "0.1.0"

    # 隐私与权限
    permissions: List[str] = field(default_factory=list)
    # ["camera", "microphone", "location", "network"]
    privacy_labels: Dict[str, str] = field(default_factory=dict)

    # 元数据
    tags: List[str] = field(default_factory=list)
    icon: str = ""                      # 图标路径 (相对于 resources/)
    screenshots: List[str] = field(default_factory=list)

    # 构建信息
    build_timestamp: str = ""
    build_tool_version: str = "0.7.0"
    package_format_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["category"] = self.category.value
        result["runtime"] = self.runtime.value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PackageManifest":
        # 处理枚举
        data = dict(data)
        data["category"] = SkillCategory(data.get("category", "utility"))
        data["runtime"] = SkillRuntime(data.get("runtime", "python"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_json(cls, path: Path) -> "PackageManifest":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


# ---------------------------------------------------------------------------
# 包构建器
# ---------------------------------------------------------------------------

class PackageBuilder:
    """构建 .qooskills 包"""

    # 必须存在的文件/目录
    REQUIRED_ENTRIES = ["manifest.json", "python/__init__.py"]

    def __init__(self, project_root: Path, output_dir: Optional[Path] = None):
        self.project_root = Path(project_root)
        self.output_dir = Path(output_dir) if output_dir else self.project_root / "dist"
        self._manifest: Optional[PackageManifest] = None

    def load_manifest(self, manifest_path: Optional[Path] = None) -> PackageManifest:
        """从 qooskills.toml 或 manifest.json 加载清单"""
        if manifest_path is None:
            # 尝试自动发现
            for candidate in [
                self.project_root / "qooskills.toml",
                self.project_root / "manifest.json",
                self.project_root / "skill.toml",
            ]:
                if candidate.exists():
                    manifest_path = candidate
                    break

        if manifest_path is None:
            raise FileNotFoundError("No manifest found (qooskills.toml / manifest.json)")

        if manifest_path.suffix == ".json":
            self._manifest = PackageManifest.from_json(manifest_path)
        elif manifest_path.suffix == ".toml":
            self._manifest = self._parse_toml_manifest(manifest_path)
        else:
            raise ValueError(f"Unsupported manifest format: {manifest_path.suffix}")

        # 设置构建时间
        self._manifest.build_timestamp = datetime.utcnow().isoformat()
        return self._manifest

    def _parse_toml_manifest(self, path: Path) -> PackageManifest:
        """从 TOML 解析清单 (简单实现，无第三方依赖)"""
        import re
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        def get_str(key: str, default: str = "") -> str:
            m = re.search(rf'^{key}\s*=\s*"([^"]*)"', content, re.MULTILINE)
            if m:
                return m.group(1)
            m = re.search(rf"^{key}\s*=\s*'([^']*)'", content, re.MULTILINE)
            return m.group(1) if m else default

        def get_list(key: str) -> List[str]:
            m = re.search(rf'^{key}\s*=\s*\[(.*?)\]', content, re.MULTILINE | re.DOTALL)
            if m:
                items = re.findall(r'"([^"]*)"', m.group(1))
                return items
            return []

        return PackageManifest(
            name=get_str("name"),
            version=get_str("version", "0.1.0"),
            display_name=get_str("display_name", get_str("name")),
            description=get_str("description"),
            category=SkillCategory(get_str("category", "utility")),
            runtime=SkillRuntime(get_str("runtime", "python")),
            author=get_str("author"),
            author_email=get_str("author_email"),
            license=get_str("license", "MIT"),
            entry_point=get_str("entry_point"),
            main_module=get_str("main_module", get_str("name").replace("-", "_")),
            dependencies=self._parse_toml_deps(content),
            python_dependencies=get_list("python_dependencies"),
            platforms=get_list("platforms") or ["linux-x86_64", "qoobot"],
            permissions=get_list("permissions"),
            tags=get_list("tags"),
        )

    def _parse_toml_deps(self, content: str) -> List[Dict[str, str]]:
        """解析 [dependencies] 段"""
        import re
        deps = []
        in_section = False
        for line in content.split("\n"):
            line = line.strip()
            if line == "[dependencies]":
                in_section = True
                continue
            if in_section:
                if line.startswith("[") and line.endswith("]"):
                    break
                m = re.match(r'(\S+)\s*=\s*"([^"]*)"', line)
                if m:
                    deps.append({"name": m.group(1), "version": m.group(2)})
        return deps

    def build(
        self,
        include_cpp: bool = False,
        include_models: bool = False,
        include_resources: bool = True,
        compression: int = zipfile.ZIP_DEFLATED,
    ) -> Path:
        """构建 .qooskills 包"""
        if self._manifest is None:
            self.load_manifest()

        manifest = self._manifest
        self.output_dir.mkdir(parents=True, exist_ok=True)

        pkg_name = f"{manifest.name}-{manifest.version}.qooskills"
        output_path = self.output_dir / pkg_name

        with zipfile.ZipFile(output_path, "w", compression=compression) as zf:
            # 写入 manifest
            zf.writestr("manifest.json", json.dumps(manifest.to_dict(), indent=2))

            # 写入 Python 代码
            python_dir = self.project_root / "python"
            if python_dir.exists():
                self._add_directory(zf, python_dir, "python/")
            else:
                # 从项目根目录收集 Python 文件
                for py_file in self.project_root.rglob("*.py"):
                    if "node_modules" in str(py_file) or "__pycache__" in str(py_file):
                        continue
                    if ".qoodev" in str(py_file) or "dist" in str(py_file):
                        continue
                    arcname = "python/" + str(py_file.relative_to(self.project_root))
                    zf.write(py_file, arcname)

            # 写入 C++ 代码 (可选)
            if include_cpp:
                cpp_dir = self.project_root / "cpp"
                if cpp_dir.exists():
                    self._add_directory(zf, cpp_dir, "cpp/")

            # 写入模型 (可选)
            if include_models:
                models_dir = self.project_root / "models"
                if models_dir.exists():
                    self._add_directory(zf, models_dir, "models/")

            # 写入资源
            if include_resources:
                resources_dir = self.project_root / "resources"
                if resources_dir.exists():
                    self._add_directory(zf, resources_dir, "resources/")

            # 写入文档
            docs_dir = self.project_root / "docs"
            if docs_dir.exists():
                self._add_directory(zf, docs_dir, "docs/")

            # 生成并写入校验和
            checksums = self._compute_checksums(output_path)
            zf.writestr("checksums.json", json.dumps(checksums, indent=2))

        # 计算最终哈希
        sha256 = self._file_sha256(output_path)
        print(f"✅ Package built: {output_path}")
        print(f"   SHA256: {sha256}")
        print(f"   Size:   {output_path.stat().st_size / 1024:.1f} KB")

        return output_path

    def _add_directory(self, zf: zipfile.ZipFile, src: Path, arc_prefix: str):
        """递归添加目录到 ZIP"""
        for item in sorted(src.rglob("*")):
            if item.is_file():
                arcname = arc_prefix + str(item.relative_to(src))
                zf.write(item, arcname)

    def _compute_checksums(self, pkg_path: Path) -> Dict[str, str]:
        """计算包内各文件的 SHA256"""
        checksums = {}
        with zipfile.ZipFile(pkg_path, "r") as zf:
            for name in zf.namelist():
                if name == "checksums.json":
                    continue
                data = zf.read(name)
                checksums[name] = hashlib.sha256(data).hexdigest()
        return checksums

    @staticmethod
    def _file_sha256(path: Path) -> str:
        sha = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha.update(chunk)
        return sha.hexdigest()


# ---------------------------------------------------------------------------
# 包读取器
# ---------------------------------------------------------------------------

class PackageReader:
    """读取和提取 .qooskills 包"""

    def __init__(self, package_path: Path):
        self.package_path = Path(package_path)
        if not self.package_path.exists():
            raise FileNotFoundError(f"Package not found: {package_path}")
        if not zipfile.is_zipfile(self.package_path):
            raise ValueError(f"Not a valid .qooskills package: {package_path}")

        self._zf: Optional[zipfile.ZipFile] = None

    def __enter__(self):
        self._zf = zipfile.ZipFile(self.package_path, "r")
        return self

    def __exit__(self, *args):
        if self._zf:
            self._zf.close()

    def read_manifest(self) -> PackageManifest:
        """读取清单 (不打开 ZIP 全量)"""
        with zipfile.ZipFile(self.package_path, "r") as zf:
            if "manifest.json" not in zf.namelist():
                raise ValueError("Package missing manifest.json")
            data = json.loads(zf.read("manifest.json").decode("utf-8"))
            return PackageManifest.from_dict(data)

    def list_files(self) -> List[str]:
        with zipfile.ZipFile(self.package_path, "r") as zf:
            return zf.namelist()

    def read_file(self, path: str) -> bytes:
        with zipfile.ZipFile(self.package_path, "r") as zf:
            return zf.read(path)

    def extract(self, target_dir: Path) -> Path:
        """提取包到目标目录"""
        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(self.package_path, "r") as zf:
            zf.extractall(target_dir)
        return target_dir

    def verify_checksums(self) -> bool:
        """校验文件完整性"""
        with zipfile.ZipFile(self.package_path, "r") as zf:
            namelist = zf.namelist()
            if "checksums.json" not in namelist:
                print("⚠️  No checksums.json found — skipping integrity check")
                return True

            expected = json.loads(zf.read("checksums.json").decode("utf-8"))
            all_ok = True
            for name, expected_hash in expected.items():
                if name not in namelist:
                    print(f"❌ Missing: {name}")
                    all_ok = False
                    continue
                actual_hash = hashlib.sha256(zf.read(name)).hexdigest()
                if actual_hash != expected_hash:
                    print(f"❌ Checksum mismatch: {name}")
                    all_ok = False

            if all_ok:
                print("✅ All checksums verified")
            return all_ok


# ---------------------------------------------------------------------------
# 包校验器
# ---------------------------------------------------------------------------

class PackageValidator:
    """校验 .qooskills 包的完整性、合规性"""

    @staticmethod
    def validate_structure(pkg_path: Path) -> List[str]:
        """校验包结构，返回错误列表"""
        errors = []

        if not zipfile.is_zipfile(pkg_path):
            errors.append("Not a valid ZIP file")
            return errors

        with zipfile.ZipFile(pkg_path, "r") as zf:
            names = zf.namelist()

            if "manifest.json" not in names:
                errors.append("Missing manifest.json")

            has_python = any(n.startswith("python/") for n in names)
            has_cpp = any(n.startswith("cpp/") for n in names)
            if not has_python and not has_cpp:
                errors.append("No code found (python/ or cpp/ directory)")

            if "python/__init__.py" not in names and has_python:
                errors.append("python/__init__.py missing")

        return errors

    @staticmethod
    def validate_manifest(manifest: PackageManifest) -> List[str]:
        """校验清单字段，返回警告列表"""
        warnings = []

        if not manifest.name or "/" not in manifest.name:
            warnings.append("name should follow reverse-domain format (com.example.skill)")

        if not manifest.version:
            warnings.append("version is required")

        if not manifest.entry_point and not manifest.main_module:
            warnings.append("entry_point or main_module should be specified")

        if not manifest.description:
            warnings.append("description is recommended for marketplace listing")

        if not manifest.author:
            warnings.append("author is recommended")

        return warnings

    @classmethod
    def full_validate(cls, pkg_path: Path) -> Dict[str, Any]:
        """完整校验，返回 {errors, warnings, manifest}"""
        result = {"errors": [], "warnings": [], "manifest": None}

        result["errors"] = cls.validate_structure(pkg_path)

        try:
            reader = PackageReader(pkg_path)
            manifest = reader.read_manifest()
            result["manifest"] = manifest.to_dict()
            result["warnings"] = cls.validate_manifest(manifest)
        except Exception as e:
            result["errors"].append(f"Manifest parse error: {e}")

        return result


# ---------------------------------------------------------------------------
# 便捷函数
# ---------------------------------------------------------------------------

def create_default_manifest(
    name: str,
    version: str = "0.1.0",
    category: SkillCategory = SkillCategory.UTILITY,
) -> PackageManifest:
    """快速创建默认清单"""
    return PackageManifest(
        name=name,
        version=version,
        display_name=name.rsplit(".", 1)[-1].replace("_", " ").title(),
        category=category,
        entry_point=f"{name.replace('.', '_')}.main:main",
        main_module=name.replace(".", "_"),
    )
