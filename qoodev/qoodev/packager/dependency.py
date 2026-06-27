"""依赖管理 — 声明、解析、冲突检测。

类似 pip 的依赖图算法，支持：
- 语义化版本约束 (>=1.0.0, ^1.2.3, ~1.2.3, ==1.0.0)
- 传递依赖解析
- 冲突检测与报告
- 版本锁定 (lockfile)
"""

import re
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
from collections import defaultdict


# ---------------------------------------------------------------------------
# 版本解析
# ---------------------------------------------------------------------------

class VersionConstraint:
    """语义化版本约束"""

    OP_MAP = {
        ">=": lambda v, c: v >= c,
        "<=": lambda v, c: v <= c,
        ">":  lambda v, c: v > c,
        "<":  lambda v, c: v < c,
        "==": lambda v, c: v == c,
        "!=": lambda v, c: v != c,
        "^":  lambda v, c: v >= c and v < _bump_major(c),
        "~":  lambda v, c: v >= c and v < _bump_minor(c),
    }

    def __init__(self, constraint_str: str):
        self.raw = constraint_str.strip()
        self.parts: List[Tuple[str, Tuple[int, ...]]] = []

        # 解析多个约束 (逗号分隔)
        for part in self.raw.split(","):
            part = part.strip()
            if not part:
                continue

            m = re.match(r'(\^|~|>=|<=|>|<|==|!=)\s*(\d+(?:\.\d+)*)', part)
            if m:
                op = m.group(1)
                ver = tuple(int(x) for x in m.group(2).split("."))
                # 补齐到 3 段
                while len(ver) < 3:
                    ver = ver + (0,)
                self.parts.append((op, ver))
            else:
                # 裸版本号 = ==
                m2 = re.match(r'(\d+(?:\.\d+)*)', part)
                if m2:
                    ver = tuple(int(x) for x in m2.group(1).split("."))
                    while len(ver) < 3:
                        ver = ver + (0,)
                    self.parts.append(("==", ver))

    def matches(self, version: Tuple[int, ...]) -> bool:
        """检查版本是否满足约束"""
        while len(version) < 3:
            version = version + (0,)
        return all(
            self.OP_MAP[op](version, constraint_ver)
            for op, constraint_ver in self.parts
        )

    def __repr__(self):
        return f"VersionConstraint({self.raw})"


def _bump_major(ver: Tuple[int, ...]) -> Tuple[int, ...]:
    return (ver[0] + 1, 0, 0)


def _bump_minor(ver: Tuple[int, ...]) -> Tuple[int, ...]:
    return (ver[0], ver[1] + 1, 0)


def parse_version(version_str: str) -> Tuple[int, ...]:
    """解析版本字符串为元组"""
    return tuple(int(x) for x in version_str.strip().split("."))


def version_to_str(ver: Tuple[int, ...]) -> str:
    return ".".join(str(x) for x in ver)


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

@dataclass
class DependencySpec:
    """单个依赖规格"""
    name: str
    version_constraint: str  # 原始约束字符串
    constraint: VersionConstraint = field(init=False)
    optional: bool = False
    platform: Optional[str] = None

    def __post_init__(self):
        self.constraint = VersionConstraint(self.version_constraint)

    def to_dict(self) -> dict:
        d = {"name": self.name, "version": self.version_constraint}
        if self.optional:
            d["optional"] = True
        if self.platform:
            d["platform"] = self.platform
        return d


class ConflictError(Exception):
    """依赖冲突错误"""

    def __init__(self, package: str, required_by: Dict[str, str], resolved_version: str):
        self.package = package
        self.required_by = required_by
        self.resolved_version = resolved_version
        msg = f"Dependency conflict for '{package}':\n"
        for req, ver in required_by.items():
            msg += f"  - {req} requires {ver}\n"
        super().__init__(msg)


# ---------------------------------------------------------------------------
# 依赖图
# ---------------------------------------------------------------------------

@dataclass
class ResolvedDependency:
    """已解析的依赖"""
    name: str
    version: str
    source: str              # 来源包名
    dependencies: List[DependencySpec] = field(default_factory=list)


class DependencyGraph:
    """依赖有向图"""

    def __init__(self):
        self.nodes: Dict[str, ResolvedDependency] = {}     # name -> ResolvedDependency
        self.edges: Dict[str, List[str]] = defaultdict(list)  # parent -> [children]

    def add_node(self, dep: ResolvedDependency):
        self.nodes[dep.name] = dep

    def add_edge(self, parent: str, child: str):
        if child not in self.edges[parent]:
            self.edges[parent].append(child)

    def topological_order(self) -> List[str]:
        """拓扑排序 (Kahn 算法)"""
        in_degree = defaultdict(int)
        for parent, children in self.edges.items():
            for child in children:
                in_degree[child] += 1
            if parent not in in_degree:
                in_degree[parent] = 0

        queue = [n for n in self.nodes if in_degree[n] == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for child in self.edges.get(node, []):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        if len(result) != len(self.nodes):
            remaining = set(self.nodes) - set(result)
            raise ConflictError(
                "dependency_cycle",
                {"cycle_nodes": ", ".join(remaining)},
                "N/A"
            )

        return result

    def to_dict(self) -> dict:
        return {
            "nodes": {
                name: {
                    "version": dep.version,
                    "source": dep.source,
                }
                for name, dep in self.nodes.items()
            },
            "edges": dict(self.edges),
        }


# ---------------------------------------------------------------------------
# 依赖解析器
# ---------------------------------------------------------------------------

class DependencyResolver:
    """依赖解析器 — 从声明到解析后的依赖图"""

    # 模拟注册表 (实际使用时应对接 qooeco 市场 API)
    REGISTRY: Dict[str, Dict[str, Dict]] = {
        "qoobot-sdk": {
            "1.0.0": {"deps": [], "python": ["numpy>=1.21"]},
            "1.1.0": {"deps": [], "python": ["numpy>=1.21", "pillow>=9.0"]},
            "1.2.0": {"deps": [{"name": "qoobot-utils", "version": ">=0.1.0"}], "python": ["numpy>=1.21"]},
        },
        "qoobot-utils": {
            "0.1.0": {"deps": [], "python": []},
            "0.2.0": {"deps": [], "python": ["pyyaml>=5.0"]},
        },
        "qoobot-perception": {
            "0.1.0": {"deps": [{"name": "qoobot-sdk", "version": ">=1.0.0"}], "python": ["torch>=2.0", "opencv-python>=4.5"]},
        },
        "qoobot-navigation": {
            "0.1.0": {"deps": [{"name": "qoobot-sdk", "version": ">=1.1.0"}], "python": ["numpy>=1.21"]},
            "0.2.0": {"deps": [
                {"name": "qoobot-sdk", "version": ">=1.2.0"},
                {"name": "qoobot-perception", "version": ">=0.1.0"}
            ], "python": ["numpy>=1.21"]},
        },
    }

    def __init__(self, registry: Optional[Dict] = None):
        self.registry = registry or self.REGISTRY
        self._resolved: Dict[str, Tuple[int, ...]] = {}  # name -> version
        self._visited: Set[str] = set()

    def resolve(
        self,
        dependencies: List[Union[DependencySpec, Dict[str, str]]],
        python_deps: Optional[List[str]] = None,
    ) -> DependencyGraph:
        """解析依赖图"""
        graph = DependencyGraph()

        for dep in dependencies:
            if isinstance(dep, dict):
                dep = DependencySpec(
                    name=dep["name"],
                    version_constraint=dep.get("version", "*"),
                    optional=dep.get("optional", False),
                    platform=dep.get("platform"),
                )
            self._resolve_one(dep, graph, parent="root")

        return graph

    def _resolve_one(
        self,
        dep: DependencySpec,
        graph: DependencyGraph,
        parent: str,
    ):
        """递归解析单个依赖"""
        # 检查是否已解析
        if dep.name in self._resolved:
            existing_ver = self._resolved[dep.name]
            if dep.constraint.matches(existing_ver):
                graph.add_edge(parent, dep.name)
                return
            else:
                raise ConflictError(
                    dep.name,
                    {
                        parent: dep.version_constraint,
                        "existing": version_to_str(existing_ver),
                    },
                    version_to_str(existing_ver),
                )

        # 查找最佳版本
        best_version = self._find_best_version(dep.name, dep.constraint)
        if best_version is None:
            available = list(self.registry.get(dep.name, {}).keys())
            raise ConflictError(
                dep.name,
                {parent: dep.version_constraint},
                f"no matching version (available: {available})",
            )

        ver_str = version_to_str(best_version)
        self._resolved[dep.name] = best_version

        pkg_info = self.registry.get(dep.name, {}).get(ver_str, {})
        sub_deps = pkg_info.get("deps", [])

        resolved = ResolvedDependency(
            name=dep.name,
            version=ver_str,
            source=parent,
            dependencies=[DependencySpec(**d) for d in sub_deps],
        )
        graph.add_node(resolved)
        graph.add_edge(parent, dep.name)

        # 递归解析传递依赖
        for sub_dep in sub_deps:
            sd = DependencySpec(**sub_dep) if isinstance(sub_dep, dict) else sub_dep
            self._resolve_one(sd, graph, parent=dep.name)

    def _find_best_version(
        self,
        name: str,
        constraint: VersionConstraint,
    ) -> Optional[Tuple[int, ...]]:
        """找到满足约束的最新版本"""
        versions = self.registry.get(name, {})
        if not versions:
            return None

        matching = []
        for ver_str in versions:
            ver = parse_version(ver_str)
            if constraint.matches(ver):
                matching.append(ver)

        if not matching:
            return None

        return max(matching)  # 选最新

    def generate_lockfile(self, graph: DependencyGraph, output_path: Path) -> Path:
        """生成版本锁定文件"""
        lock_data = {
            "format_version": "1.0",
            "generated_by": "qoodev-packager",
            "packages": {},
        }

        for name in graph.topological_order():
            node = graph.nodes[name]
            lock_data["packages"][name] = {
                "version": node.version,
                "dependencies": [d.to_dict() for d in node.dependencies],
            }

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(lock_data, f, indent=2)

        print(f"✅ Lockfile written: {output_path}")
        return output_path

    def verify_lockfile(self, lockfile_path: Path) -> List[str]:
        """校验 lockfile 与当前声明的兼容性，返回冲突列表"""
        conflicts = []
        # 此方法用于 CI 中验证 lockfile 是否过期
        # 实现略 — 加载 lockfile，对比当前依赖声明
        return conflicts
