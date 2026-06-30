"""
qoodev Compiler Integration — v1.5+

Bridge to qoocore compiler toolchain for:
- Model compilation (PyTorch/ONNX/TensorFlow → .qoomodel)
- Multi-architecture cross-compilation (x86_64, aarch64, armv7l)
- Quantization (INT8, FP16) and graph optimization
- Skill + model joint packaging

Usage:
    from cli.compiler import CompilerBridge, CrossCompiler, Quantizer

    bridge = CompilerBridge()
    bridge.compile("model.onnx", output="model.qoomodel", target="aarch64")
"""

from __future__ import annotations

import dataclasses
import json
import os
import shutil
import subprocess
import tempfile
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


# ============================================================================
# Data Models
# ============================================================================

class TargetArch(Enum):
    X86_64 = "x86_64"
    AARCH64 = "aarch64"
    ARMV7L = "armv7l"
    RISCV64 = "riscv64"


class QuantizationMode(Enum):
    NONE = "none"
    FP16 = "fp16"
    INT8 = "int8"
    INT4 = "int4"
    MIXED = "mixed"


class OptimizationLevel(Enum):
    O0 = 0   # No optimization
    O1 = 1   # Basic (constant folding, dead code elimination)
    O2 = 2   # Standard (layer fusion, memory planning)
    O3 = 3   # Aggressive (kernel auto-tuning, layout optimization)


class Framework(Enum):
    PYTORCH = "pytorch"
    ONNX = "onnx"
    TENSORFLOW = "tensorflow"
    TFLITE = "tflite"
    PADDLE = "paddle"
    JAX = "jax"


@dataclasses.dataclass
class CompileConfig:
    """Compilation configuration."""
    framework: Framework = Framework.ONNX
    target_arch: TargetArch = TargetArch.X86_64
    optimization: OptimizationLevel = OptimizationLevel.O2
    quantization: QuantizationMode = QuantizationMode.NONE
    input_shapes: Dict[str, List[int]] = dataclasses.field(default_factory=dict)
    dynamic_axes: Dict[str, List[int]] = dataclasses.field(default_factory=dict)
    custom_ops: List[str] = dataclasses.field(default_factory=list)
    backend: str = "qoocore"  # qoocore, tvm, openvino, tensorrt
    extra_args: Dict[str, str] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class CompileResult:
    """Result of a compilation."""
    success: bool
    output_path: Path
    framework: Framework
    target_arch: TargetArch
    input_model: str
    output_size_bytes: int = 0
    compile_time_s: float = 0.0
    ops_count: int = 0
    quantized_ops_count: int = 0
    warnings: List[str] = dataclasses.field(default_factory=list)
    errors: List[str] = dataclasses.field(default_factory=list)
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class CrossCompileConfig:
    """Cross-compilation configuration for C++ skills."""
    target_arch: TargetArch
    sysroot: Optional[Path] = None
    toolchain_file: Optional[Path] = None
    cxx_flags: List[str] = dataclasses.field(default_factory=list)
    ld_flags: List[str] = dataclasses.field(default_factory=list)
    cmake_defines: Dict[str, str] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class CrossCompileResult:
    """Result of cross-compilation."""
    success: bool
    artifacts: List[Path]
    target_arch: TargetArch
    build_time_s: float = 0.0
    warnings: List[str] = dataclasses.field(default_factory=list)
    errors: List[str] = dataclasses.field(default_factory=list)


# ============================================================================
# Toolchain Detection
# ============================================================================

class ToolchainDetector:
    """Detect available compilation toolchains on the system."""

    @staticmethod
    def detect_qoocore() -> Optional[Path]:
        """Detect qoocore compiler installation."""
        # Check common paths
        candidates = [
            Path("/opt/qoocore/bin/qooc"),
            Path("/usr/local/bin/qooc"),
            Path.home() / ".qoobot/qoocore/bin/qooc",
            shutil.which("qooc"),
        ]
        for p in candidates:
            if p and Path(p).exists():
                return Path(p)
        return None

    @staticmethod
    def detect_cross_compiler(arch: TargetArch) -> Optional[Path]:
        """Detect cross-compiler for target architecture."""
        prefixes = {
            TargetArch.AARCH64: ["aarch64-linux-gnu-", "aarch64-none-linux-gnu-"],
            TargetArch.ARMV7L: ["arm-linux-gnueabihf-", "armv7l-linux-gnueabihf-"],
            TargetArch.RISCV64: ["riscv64-linux-gnu-", "riscv64-unknown-linux-gnu-"],
        }
        for prefix in prefixes.get(arch, []):
            gcc_path = shutil.which(f"{prefix}gcc") or shutil.which(f"{prefix}g++")
            if gcc_path:
                return Path(gcc_path)
        return None

    @staticmethod
    def detect_cmake() -> Optional[Path]:
        """Detect CMake installation."""
        cmake = shutil.which("cmake")
        return Path(cmake) if cmake else None

    @staticmethod
    def list_available_toolchains() -> Dict[str, Any]:
        """Return all available toolchains."""
        return {
            "qoocore": ToolchainDetector.detect_qoocore() is not None,
            "cmake": ToolchainDetector.detect_cmake() is not None,
            "cross_aarch64": ToolchainDetector.detect_cross_compiler(TargetArch.AARCH64) is not None,
            "cross_armv7l": ToolchainDetector.detect_cross_compiler(TargetArch.ARMV7L) is not None,
            "cross_riscv64": ToolchainDetector.detect_cross_compiler(TargetArch.RISCV64) is not None,
            "host_arch": os.uname().machine if hasattr(os, "uname") else "unknown",
        }


# ============================================================================
# Model Compiler
# ============================================================================

class ModelCompiler:
    """Compile ML models using qoocore or fallback toolchains."""

    def __init__(self):
        self._qooc_path = ToolchainDetector.detect_qoocore()

    def compile(self, input_model: Union[str, Path], config: Optional[CompileConfig] = None,
                output: Optional[Union[str, Path]] = None) -> CompileResult:
        """Compile a model to .qoomodel format."""
        import time as _time

        config = config or CompileConfig()
        input_path = Path(input_model)
        if not input_path.exists():
            return CompileResult(
                success=False, output_path=Path(""), framework=config.framework,
                target_arch=config.target_arch, input_model=str(input_path),
                errors=[f"Input model not found: {input_path}"],
            )

        output_path = Path(output) if output else input_path.with_suffix(".qoomodel")
        start = _time.time()

        if self._qooc_path:
            result = self._compile_via_qoocore(input_path, output_path, config)
        else:
            result = self._compile_fallback(input_path, output_path, config)

        result.compile_time_s = _time.time() - start
        if result.success and output_path.exists():
            result.output_size_bytes = output_path.stat().st_size
        return result

    def _compile_via_qoocore(self, input_path: Path, output_path: Path,
                             config: CompileConfig) -> CompileResult:
        """Compile using qoocore compiler."""
        cmd = [
            str(self._qooc_path), "compile",
            str(input_path),
            "-o", str(output_path),
            "--target", config.target_arch.value,
            "--opt", str(config.optimization.value),
            "--quant", config.quantization.value,
        ]
        if config.input_shapes:
            for name, shape in config.input_shapes.items():
                cmd.extend(["--input-shape", f"{name}:{','.join(map(str, shape))}"])
        if config.custom_ops:
            cmd.extend(["--custom-ops", ",".join(config.custom_ops)])

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if proc.returncode == 0:
                return CompileResult(
                    success=True, output_path=output_path, framework=config.framework,
                    target_arch=config.target_arch, input_model=str(input_path),
                    warnings=self._parse_warnings(proc.stderr),
                )
            else:
                return CompileResult(
                    success=False, output_path=output_path, framework=config.framework,
                    target_arch=config.target_arch, input_model=str(input_path),
                    errors=[proc.stderr.strip()],
                )
        except subprocess.TimeoutExpired:
            return CompileResult(
                success=False, output_path=output_path, framework=config.framework,
                target_arch=config.target_arch, input_model=str(input_path),
                errors=["Compilation timed out (>300s)"],
            )
        except Exception as e:
            return CompileResult(
                success=False, output_path=output_path, framework=config.framework,
                target_arch=config.target_arch, input_model=str(input_path),
                errors=[str(e)],
            )

    def _compile_fallback(self, input_path: Path, output_path: Path,
                          config: CompileConfig) -> CompileResult:
        """Fallback compilation using ONNX optimizer or simple copy."""
        try:
            import onnx
            model = onnx.load(str(input_path))
            # Basic ONNX optimization
            from onnx import optimizer
            passes = ["eliminate_deadend", "eliminate_identity", "eliminate_nop_transpose",
                      "fuse_consecutive_transposes", "fuse_matmul_add_bias_into_gemm"]
            optimized = optimizer.optimize(model, passes)
            onnx.save(optimized, str(output_path))
            return CompileResult(
                success=True, output_path=output_path, framework=config.framework,
                target_arch=config.target_arch, input_model=str(input_path),
                warnings=["qoocore not available; using ONNX optimizer only"],
                ops_count=len(model.graph.node),
            )
        except ImportError:
            # Last resort: copy as-is
            try:
                shutil.copy2(input_path, output_path)
                return CompileResult(
                    success=True, output_path=output_path, framework=config.framework,
                    target_arch=config.target_arch, input_model=str(input_path),
                    warnings=["qoocore and onnx not available; model copied without optimization"],
                )
            except Exception as e:
                return CompileResult(
                    success=False, output_path=output_path, framework=config.framework,
                    target_arch=config.target_arch, input_model=str(input_path),
                    errors=[f"Fallback failed: {e}"],
                )

    @staticmethod
    def _parse_warnings(stderr: str) -> List[str]:
        """Parse warning lines from stderr."""
        return [line.strip() for line in stderr.splitlines()
                if "warn" in line.lower() or "WARNING" in line]


class Quantizer:
    """Model quantization utilities."""

    @staticmethod
    def quantize(input_model: Union[str, Path], mode: QuantizationMode,
                 calibration_data: Optional[Union[str, Path]] = None,
                 output: Optional[Union[str, Path]] = None) -> CompileResult:
        """Quantize a model to lower precision."""
        input_path = Path(input_model)
        output_path = Path(output) if output else input_path.with_suffix(f".{mode.value}.qoomodel")

        if mode == QuantizationMode.NONE:
            shutil.copy2(input_path, output_path)
            return CompileResult(
                success=True, output_path=output_path, framework=Framework.ONNX,
                target_arch=TargetArch.X86_64, input_model=str(input_path),
                output_size_bytes=output_path.stat().st_size,
            )

        # Use qoocore quantizer if available
        qooc = ToolchainDetector.detect_qoocore()
        if qooc:
            cmd = [str(qooc), "quantize", str(input_path), "-o", str(output_path),
                   "--mode", mode.value]
            if calibration_data:
                cmd.extend(["--calib", str(calibration_data)])
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if proc.returncode == 0:
                    return CompileResult(
                        success=True, output_path=output_path, framework=Framework.ONNX,
                        target_arch=TargetArch.X86_64, input_model=str(input_path),
                        output_size_bytes=output_path.stat().st_size(),
                    )
            except Exception:
                pass

        return CompileResult(
            success=False, output_path=output_path, framework=Framework.ONNX,
            target_arch=TargetArch.X86_64, input_model=str(input_path),
            errors=["Quantization requires qoocore toolchain"],
        )


# ============================================================================
# Cross Compiler
# ============================================================================

class CrossCompiler:
    """Cross-compile C++ skills for different target architectures."""

    def __init__(self):
        self._detector = ToolchainDetector()

    def compile(self, source_dir: Union[str, Path], config: CrossCompileConfig,
                build_dir: Optional[Union[str, Path]] = None) -> CrossCompileResult:
        """Cross-compile a C++ skill project."""
        import time as _time

        src = Path(source_dir)
        build = Path(build_dir) if build_dir else src / f"build_{config.target_arch.value}"
        build.mkdir(parents=True, exist_ok=True)
        start = _time.time()

        # Check cross-compiler availability
        compiler = self._detector.detect_cross_compiler(config.target_arch)
        if not compiler and config.target_arch != TargetArch.X86_64:
            return CrossCompileResult(
                success=False, artifacts=[], target_arch=config.target_arch,
                errors=[f"No cross-compiler found for {config.target_arch.value}. "
                        f"Install gcc-{config.target_arch.value} toolchain."],
            )

        # CMake-based build
        cmake = self._detector.detect_cmake()
        if not cmake:
            return CrossCompileResult(
                success=False, artifacts=[], target_arch=config.target_arch,
                errors=["CMake not found. Install cmake >= 3.16."],
            )

        try:
            # Configure
            cmake_args = [str(cmake), "-S", str(src), "-B", str(build)]
            if config.toolchain_file:
                cmake_args.extend(["-DCMAKE_TOOLCHAIN_FILE", str(config.toolchain_file)])
            else:
                # Auto-generate toolchain
                tc = self._generate_toolchain(config, build)
                cmake_args.extend(["-DCMAKE_TOOLCHAIN_FILE", str(tc)])

            for k, v in config.cmake_defines.items():
                cmake_args.append(f"-D{k}={v}")

            proc = subprocess.run(cmake_args, capture_output=True, text=True, timeout=60,
                                  cwd=str(src))
            if proc.returncode != 0:
                return CrossCompileResult(
                    success=False, artifacts=[], target_arch=config.target_arch,
                    errors=[f"CMake configure failed:\n{proc.stderr}"],
                )

            # Build
            build_proc = subprocess.run(
                [str(cmake), "--build", str(build), "--parallel"],
                capture_output=True, text=True, timeout=600, cwd=str(src),
            )
            if build_proc.returncode != 0:
                return CrossCompileResult(
                    success=False, artifacts=[], target_arch=config.target_arch,
                    errors=[f"Build failed:\n{build_proc.stderr}"],
                    build_time_s=_time.time() - start,
                )

            # Collect artifacts
            artifacts = list(build.rglob("*.so")) + list(build.rglob("*.a")) + \
                        list(build.rglob("*.qooskills"))

            return CrossCompileResult(
                success=True, artifacts=artifacts, target_arch=config.target_arch,
                build_time_s=_time.time() - start,
            )

        except subprocess.TimeoutExpired:
            return CrossCompileResult(
                success=False, artifacts=[], target_arch=config.target_arch,
                errors=["Build timed out"],
            )
        except Exception as e:
            return CrossCompileResult(
                success=False, artifacts=[], target_arch=config.target_arch,
                errors=[str(e)],
            )

    def _generate_toolchain(self, config: CrossCompileConfig,
                            build_dir: Path) -> Path:
        """Generate a CMake toolchain file."""
        tc_path = build_dir / f"toolchain_{config.target_arch.value}.cmake"
        prefix_map = {
            TargetArch.AARCH64: "aarch64-linux-gnu",
            TargetArch.ARMV7L: "arm-linux-gnueabihf",
            TargetArch.RISCV64: "riscv64-linux-gnu",
        }
        prefix = prefix_map.get(config.target_arch, "")

        content = f"""\
# Auto-generated toolchain for {config.target_arch.value}
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR {config.target_arch.value})
set(CMAKE_C_COMPILER {prefix}-gcc)
set(CMAKE_CXX_COMPILER {prefix}-g++)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
"""
        if config.sysroot:
            content += f"\nset(CMAKE_SYSROOT {config.sysroot})\n"
            content += "set(CMAKE_FIND_ROOT_PATH ${CMAKE_SYSROOT})\n"

        tc_path.write_text(content, encoding="utf-8")
        return tc_path


# ============================================================================
# Unified Compiler Bridge
# ============================================================================

class CompilerBridge:
    """Unified interface for all compilation tasks."""

    def __init__(self):
        self.model_compiler = ModelCompiler()
        self.cross_compiler = CrossCompiler()
        self.quantizer = Quantizer()
        self.detector = ToolchainDetector()

    def compile_model(self, model_path: Union[str, Path], **kwargs) -> CompileResult:
        """Compile an ML model."""
        config = CompileConfig(**{k: v for k, v in kwargs.items()
                                  if k in CompileConfig.__dataclass_fields__})
        return self.model_compiler.compile(model_path, config,
                                           output=kwargs.get("output"))

    def compile_skill(self, source_dir: Union[str, Path], target: str = "aarch64",
                      **kwargs) -> CrossCompileResult:
        """Cross-compile a C++ skill."""
        arch = TargetArch(target)
        config = CrossCompileConfig(
            target_arch=arch,
            sysroot=kwargs.get("sysroot"),
            cmake_defines=kwargs.get("defines", {}),
        )
        return self.cross_compiler.compile(source_dir, config,
                                           build_dir=kwargs.get("build_dir"))

    def quantize_model(self, model_path: Union[str, Path],
                       mode: str = "int8", **kwargs) -> CompileResult:
        """Quantize a model."""
        qmode = QuantizationMode(mode)
        return self.quantizer.quantize(model_path, qmode,
                                       calibration_data=kwargs.get("calibration_data"),
                                       output=kwargs.get("output"))

    def status(self) -> Dict[str, Any]:
        """Return toolchain availability status."""
        return self.detector.list_available_toolchains()


# ============================================================================
# CLI Integration Helpers
# ============================================================================

def format_compile_result(result: CompileResult) -> str:
    """Format compile result for CLI display."""
    if result.success:
        lines = [
            f"✓ Compiled: {result.input_model} → {result.output_path.name}",
            f"  Framework: {result.framework.value}",
            f"  Target: {result.target_arch.value}",
            f"  Size: {result.output_size_bytes / 1024:.1f} KB",
            f"  Time: {result.compile_time_s:.2f}s",
        ]
        if result.warnings:
            lines.append("  Warnings:")
            for w in result.warnings:
                lines.append(f"    - {w}")
        return "\n".join(lines)
    else:
        lines = [f"✗ Compilation failed: {result.input_model}"]
        for e in result.errors:
            lines.append(f"  Error: {e}")
        return "\n".join(lines)


__all__ = [
    "CompilerBridge",
    "ModelCompiler",
    "CrossCompiler",
    "Quantizer",
    "ToolchainDetector",
    "CompileConfig",
    "CompileResult",
    "CrossCompileConfig",
    "CrossCompileResult",
    "TargetArch",
    "QuantizationMode",
    "OptimizationLevel",
    "Framework",
    "format_compile_result",
]
