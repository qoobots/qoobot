"""
brain_models/model_path_resolver.py — 统一模型路径解析器

从 model_registry.json 读取元数据，提供模型名称→绝对路径的映射。
所有 brain_ai 和 brain_core 运行时模块应通过此解析器获取模型路径，
避免硬编码路径或文件名不一致的问题。

Usage::

    from brain_models.model_path_resolver import resolve_model_path, ModelResolver

    # 单个模型路径
    path = resolve_model_path("yolov11n")  # → D:/project/brain_models/cv/yolo11n.onnx

    # 批量解析
    resolver = ModelResolver()
    llm_paths = resolver.resolve_category("llm")

    # 自动选择 (根据优先级和设备)
    llm_path = resolver.resolve_best_available("llm")
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ============================================================================
# 路径常量 — 自动检测
# ============================================================================

def _find_project_root() -> Path:
    """从当前文件向上查找项目根目录 (包含 brain_models/ 的父目录)"""
    current = Path(__file__).resolve()
    # brain_models/model_path_resolver.py → 往上一级是 brain_models/
    # 再往上是项目根目录
    for candidate in [current.parent.parent, current.parent.parent.parent]:
        if (candidate / "brain_models" / "model_registry.json").exists():
            return candidate
    # Fallback: 从环境变量读取
    env_root = os.environ.get("BRAIN_OS_ROOT", os.environ.get("QOOBOT_ROOT"))
    if env_root:
        return Path(env_root)
    raise RuntimeError(
        "Cannot locate project root. Set BRAIN_OS_ROOT environment variable "
        "or ensure brain_models/model_registry.json exists relative to the project root."
    )


PROJECT_ROOT = _find_project_root()
REGISTRY_PATH = PROJECT_ROOT / "brain_models" / "model_registry.json"
MODELS_ROOT = PROJECT_ROOT / "brain_models"


# ============================================================================
# 数据类型
# ============================================================================

@dataclass
class ModelPath:
    """单个模型的路径信息"""
    model_id: str
    name: str
    category: str
    format: str
    local_dir: Path
    files: List[Tuple[str, Path]] = field(default_factory=list)  # (filename, absolute_path)


# ============================================================================
# 解析器核心
# ============================================================================

class ModelResolver:
    """模型路径解析器 — 单例模式

    Usage::

        resolver = ModelResolver()
        path = resolver.resolve("yolov11n")      # → Path 对象或 None
        info = resolver.get_info("yolov11n")    # → ModelPath 对象或 None
    """

    _instance: Optional["ModelResolver"] = None
    _registry: Optional[dict] = None

    def __new__(cls) -> "ModelResolver":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._models: Dict[str, ModelPath] = {}
            cls._instance._by_category: Dict[str, List[str]] = {}
            cls._instance._loaded = False
        return cls._instance

    def _load(self) -> None:
        """加载注册表 (延迟加载)"""
        if self._loaded:
            return

        if not REGISTRY_PATH.exists():
            logger.warning(f"[ModelResolver] Registry not found: {REGISTRY_PATH}")
            self._loaded = True
            return

        try:
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                self._registry = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error(f"[ModelResolver] Failed to load registry: {exc}")
            self._loaded = True
            return

        # 构建 ModelPath 缓存
        for model_id, info in self._registry.get("models", {}).items():
            local_path = info.get("local_path", "")
            local_dir = PROJECT_ROOT / local_path

            # 收集模型文件
            files = []
            is_model_dir = info.get("model_dir", False)
            if is_model_dir:
                # 目录型模型 (如 CTranslate2) — 返回目录路径而非文件
                files.append(("__model_dir__", local_dir))
            else:
                engine = info.get("engine_file")
                if engine:
                    files.append((engine, local_dir / engine))

                # SAM2 有两部分
                for part_name, part_info in info.get("parts", {}).items():
                    part_file = part_info.get("file")
                    if part_file:
                        files.append((part_file, local_dir / part_file))

            mp = ModelPath(
                model_id=model_id,
                name=info.get("name", model_id),
                category=info.get("category", "unknown"),
                format=info.get("format", "unknown"),
                local_dir=local_dir,
                files=files,
            )
            self._models[model_id] = mp

            # 按分类索引
            cat = info.get("category", "unknown")
            if cat not in self._by_category:
                self._by_category[cat] = []
            self._by_category[cat].append(model_id)

        self._loaded = True
        logger.debug(f"[ModelResolver] Loaded {len(self._models)} models from registry")

    # ── 查询 API ─────────────────────────────────────────────

    def resolve(self, model_id: str, file_index: int = 0) -> Optional[Path]:
        """解析模型主文件路径

        Args:
            model_id: 注册表模型 ID (如 "yolov11n")
            file_index: 多文件模型中的索引 (0=encoder/主文件, 1=decoder)

        Returns:
            绝对路径或 None
        """
        self._load()
        mp = self._models.get(model_id)
        if not mp or not mp.files:
            return None
        if file_index < len(mp.files):
            return mp.files[file_index][1]
        return None

    def resolve_all(self, model_id: str) -> List[Path]:
        """解析模型所有文件路径"""
        self._load()
        mp = self._models.get(model_id)
        if not mp:
            return []
        return [f[1] for f in mp.files]

    def resolve_category(self, category: str) -> Dict[str, Path]:
        """解析某类别下所有模型的主文件路径

        Returns:
            {model_id: path, ...}  (只包含主文件存在的模型)
        """
        self._load()
        result = {}
        for model_id in self._by_category.get(category, []):
            path = self.resolve(model_id)
            if path:
                result[model_id] = path
        return result

    def resolve_best_available(self, category: str) -> Tuple[Optional[str], Optional[Path]]:
        """按优先级解析最适合当前设备的模型

        规则:
          1. P0_critical > P1 > P2
          2. 同优先级选文件存在且大小有效的
          3. LLM 类别优先选 INT4 (GPU) > GGUF (CPU)

        Returns:
            (model_id, path) 或 (None, None)
        """
        self._load()
        if not self._registry:
            return None, None

        candidates = []
        for model_id in self._by_category.get(category, []):
            info = self._registry["models"].get(model_id, {})
            priority = info.get("priority", "P2")
            priority_order = {"P0_critical": 0, "P1_fallback": 1, "P1_general": 1, "P2_experimental": 2}
            candidates.append((priority_order.get(priority, 2), model_id, info))

        candidates.sort(key=lambda x: x[0])

        for _, model_id, info in candidates:
            path = self.resolve(model_id)
            if path and path.exists():
                size = path.stat().st_size
                if size > 1024:  # > 1KB — not an LFS stub
                    return model_id, path

        return None, None

    def get_info(self, model_id: str) -> Optional[ModelPath]:
        """获取模型完整信息"""
        self._load()
        return self._models.get(model_id)

    def list_models(self, category: Optional[str] = None) -> List[str]:
        """列出所有模型 ID"""
        self._load()
        if category:
            return self._by_category.get(category, [])
        return list(self._models.keys())

    def model_exists(self, model_id: str, check_lfs: bool = True) -> bool:
        """检查模型文件是否存在且有效 (非 LFS 占位符)"""
        path = self.resolve(model_id)
        if not path or not path.exists():
            return False
        # 目录型模型：检查目录是否为非空
        if path.is_dir():
            try:
                return any(path.iterdir())
            except PermissionError:
                return True  # 目录存在但无权限访问
        if not check_lfs:
            return True
        # 0 字节文件 (空占位符)
        if path.stat().st_size == 0:
            return False
        # 检查 LFS 占位符 (< 200 字节且含 LFS 签名)
        if path.stat().st_size < 200:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    if "oid sha256:" in f.read(130):
                        return False
            except Exception:
                pass
        return True


# ============================================================================
# 便捷函数
# ============================================================================

def resolve_model_path(model_id: str) -> Optional[Path]:
    """便捷函数: 解析模型主文件路径

    Usage::

        from brain_models.model_path_resolver import resolve_model_path
        path = resolve_model_path("yolov11n")
    """
    return ModelResolver().resolve(model_id)


def find_model(model_id: str) -> Optional[str]:
    """便捷函数: 解析模型路径并返回字符串

    Usage::

        model_path = find_model("yolov11n")  # "D:/project/brain_models/cv/yolo11n.onnx"
    """
    path = resolve_model_path(model_id)
    return str(path) if path else None
