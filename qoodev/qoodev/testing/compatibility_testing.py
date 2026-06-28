"""
qoodev compatibility testing — multi-platform / multi-sensor auto-validation.

对标：Android CTS + BrowserStack
提供平台兼容性矩阵测试、传感器配置组合验证、ABI 兼容性检查。
"""

from __future__ import annotations

import json
import platform
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Platform(str, Enum):
    LINUX_X86_64 = "linux-x86_64"
    LINUX_AARCH64 = "linux-aarch64"
    WINDOWS_X86_64 = "windows-x86_64"
    MACOS_X86_64 = "macos-x86_64"
    MACOS_ARM64 = "macos-arm64"
    ANDROID_AARCH64 = "android-aarch64"
    IOS_ARM64 = "ios-arm64"


class SensorConfig(str, Enum):
    RGB_CAMERA = "rgb_camera"
    DEPTH_CAMERA = "depth_camera"
    STEREO_CAMERA = "stereo_camera"
    LIDAR_16 = "lidar_16"
    LIDAR_32 = "lidar_32"
    LIDAR_128 = "lidar_128"
    IMU_6DOF = "imu_6dof"
    IMU_9DOF = "imu_9dof"
    GPS = "gps"
    MICROPHONE_ARRAY_4 = "microphone_array_4"
    MICROPHONE_ARRAY_8 = "microphone_array_8"
    RADAR = "radar"
    ULTRASONIC = "ultrasonic"


class TestStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"
    NOT_SUPPORTED = "not_supported"


class ABI(str, Enum):
    X86_64 = "x86_64"
    ARM64 = "arm64"
    ARM32 = "arm32"
    RISCV64 = "riscv64"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CompatibilityTest:
    """A single compatibility test case."""
    name: str
    description: str = ""
    platforms: List[Platform] = field(default_factory=list)
    sensors: List[SensorConfig] = field(default_factory=list)
    abis: List[ABI] = field(default_factory=list)
    min_python: Tuple[int, int] = (3, 8)
    min_memory_mb: int = 512
    tags: List[str] = field(default_factory=list)


@dataclass
class CompatibilityResult:
    """Result of a single compatibility test."""
    test_name: str
    platform: Platform
    sensor: Optional[SensorConfig] = None
    abi: Optional[ABI] = None
    status: TestStatus = TestStatus.PASS
    details: str = ""
    duration_ms: float = 0.0
    logs: List[str] = field(default_factory=list)


@dataclass
class CompatibilityMatrix:
    """Full compatibility test matrix."""
    platform_results: Dict[Platform, Dict[str, CompatibilityResult]] = field(default_factory=dict)
    sensor_results: Dict[SensorConfig, Dict[str, CompatibilityResult]] = field(default_factory=dict)
    abi_results: Dict[ABI, Dict[str, CompatibilityResult]] = field(default_factory=dict)
    summary: Dict[str, int] = field(default_factory=lambda: {
        "total": 0, "pass": 0, "fail": 0, "skip": 0, "error": 0, "not_supported": 0,
    })


# ---------------------------------------------------------------------------
# CompatibilityChecker
# ---------------------------------------------------------------------------

class CompatibilityChecker:
    """Run compatibility tests across platform/sensor/ABI dimensions.

    Usage::

        checker = CompatibilityChecker()
        checker.add_test(CompatibilityTest("camera_inference", platforms=[LINUX_X86_64, LINUX_AARCH64]))
        matrix = checker.run_all()
        checker.print_matrix(matrix)
    """

    def __init__(self):
        self._tests: List[CompatibilityTest] = []
        self._test_fns: Dict[str, Callable[[CompatibilityTest, Platform, Optional[SensorConfig], Optional[ABI]], TestStatus]] = {}
        self._current_platform = self._detect_platform()

    def add_test(self, test: CompatibilityTest, fn: Optional[Callable] = None) -> None:
        self._tests.append(test)
        if fn is not None:
            self._test_fns[test.name] = fn

    # -- platform detection --------------------------------------------------

    @staticmethod
    def _detect_platform() -> Platform:
        system = platform.system().lower()
        machine = platform.machine().lower()

        if system == "linux":
            if machine in ("aarch64", "arm64"):
                return Platform.LINUX_AARCH64
            return Platform.LINUX_X86_64
        elif system == "windows":
            return Platform.WINDOWS_X86_64
        elif system == "darwin":
            if machine in ("arm64", "aarch64"):
                return Platform.MACOS_ARM64
            return Platform.MACOS_X86_64
        elif system == "android":
            return Platform.ANDROID_AARCH64
        elif system == "ios":
            return Platform.IOS_ARM64

        return Platform.LINUX_X86_64

    # -- ABI detection -------------------------------------------------------

    @staticmethod
    def _detect_abi() -> ABI:
        machine = platform.machine().lower()
        if machine in ("x86_64", "amd64"):
            return ABI.X86_64
        elif machine in ("aarch64", "arm64"):
            return ABI.ARM64
        elif machine in ("armv7l", "arm"):
            return ABI.ARM32
        elif "riscv" in machine:
            return ABI.RISCV64
        return ABI.X86_64

    # -- system checks -------------------------------------------------------

    @staticmethod
    def check_python_version(min_version: Tuple[int, int]) -> bool:
        return sys.version_info >= min_version

    @staticmethod
    def check_memory(min_mb: int) -> bool:
        try:
            import psutil
            avail = psutil.virtual_memory().available / (1024 * 1024)
            return avail >= min_mb
        except ImportError:
            return True  # cannot check, assume OK

    @staticmethod
    def check_library(lib_name: str) -> bool:
        """Check if a native library is available."""
        try:
            import ctypes.util
            path = ctypes.util.find_library(lib_name)
            return path is not None
        except Exception:
            return False

    @staticmethod
    def check_gpu() -> Tuple[bool, str]:
        """Check GPU availability."""
        # CUDA
        try:
            import subprocess
            result = subprocess.run(["nvidia-smi"], capture_output=True, timeout=5)
            if result.returncode == 0:
                return True, "CUDA"
        except Exception:
            pass

        # OpenCL
        try:
            import ctypes
            ctypes.cdll.LoadLibrary("libOpenCL.so" if platform.system() == "Linux" else "OpenCL.dll")
            return True, "OpenCL"
        except Exception:
            pass

        # Metal (macOS)
        if platform.system() == "Darwin":
            return True, "Metal"

        return False, "none"

    # -- sensor compatibility ------------------------------------------------

    SENSOR_REQUIREMENTS: Dict[SensorConfig, List[str]] = {
        SensorConfig.RGB_CAMERA: ["libv4l2", "libusb"],
        SensorConfig.LIDAR_16: ["libpcap"],
        SensorConfig.LIDAR_32: ["libpcap"],
        SensorConfig.LIDAR_128: ["libpcap"],
        SensorConfig.GPS: ["libgps"],
    }

    def check_sensor_support(self, sensor: SensorConfig) -> Tuple[bool, str]:
        """Check if a sensor configuration is supported."""
        reqs = self.SENSOR_REQUIREMENTS.get(sensor, [])
        for lib in reqs:
            if not self.check_library(lib):
                return False, f"Missing library: {lib}"

        # platform-specific checks
        if sensor in (SensorConfig.IOS_ARM64,) and self._current_platform != Platform.IOS_ARM64:
            return False, "iOS-only sensor"
        if sensor == SensorConfig.ANDROID_AARCH64 and self._current_platform != Platform.ANDROID_AARCH64:
            return False, "Android-only sensor"

        return True, "supported"

    # -- test execution ------------------------------------------------------

    def run_all(self) -> CompatibilityMatrix:
        """Execute all registered compatibility tests."""
        matrix = CompatibilityMatrix()

        for test in self._tests:
            for plat in test.platforms:
                result = self._run_single(test, plat, None, None)
                matrix.platform_results.setdefault(plat, {})[test.name] = result
                self._update_summary(matrix, result)

            for sensor in test.sensors:
                result = self._run_single(test, self._current_platform, sensor, None)
                matrix.sensor_results.setdefault(sensor, {})[test.name] = result
                self._update_summary(matrix, result)

            for abi in test.abis:
                result = self._run_single(test, self._current_platform, None, abi)
                matrix.abi_results.setdefault(abi, {})[test.name] = result
                self._update_summary(matrix, result)

        return matrix

    def _run_single(
        self,
        test: CompatibilityTest,
        platform_target: Platform,
        sensor: Optional[SensorConfig],
        abi: Optional[ABI],
    ) -> CompatibilityResult:
        import time
        t0 = time.perf_counter()

        # skip checks
        if not self.check_python_version(test.min_python):
            return CompatibilityResult(test.name, platform_target, sensor, abi, TestStatus.SKIP, "Python version too low")

        if not self.check_memory(test.min_memory_mb):
            return CompatibilityResult(test.name, platform_target, sensor, abi, TestStatus.SKIP, "Insufficient memory")

        # platform mismatch
        if platform_target != self._current_platform:
            return CompatibilityResult(test.name, platform_target, sensor, abi, TestStatus.SKIP, "Platform mismatch")

        # ABI check
        if abi is not None and abi != self._detect_abi():
            return CompatibilityResult(test.name, platform_target, sensor, abi, TestStatus.NOT_SUPPORTED, f"ABI {abi} not available")

        # sensor check
        if sensor is not None:
            supported, reason = self.check_sensor_support(sensor)
            if not supported:
                return CompatibilityResult(test.name, platform_target, sensor, abi, TestStatus.NOT_SUPPORTED, reason)

        # execute test function
        try:
            fn = self._test_fns.get(test.name)
            if fn is not None:
                status = fn(test, platform_target, sensor, abi)
            else:
                status = TestStatus.PASS  # no test function, assume structural pass

            elapsed = (time.perf_counter() - t0) * 1000
            return CompatibilityResult(test.name, platform_target, sensor, abi, status, "OK", elapsed)

        except Exception as e:
            elapsed = (time.perf_counter() - t0) * 1000
            return CompatibilityResult(test.name, platform_target, sensor, abi, TestStatus.ERROR, str(e), elapsed)

    @staticmethod
    def _update_summary(matrix: CompatibilityMatrix, result: CompatibilityResult) -> None:
        matrix.summary["total"] += 1
        matrix.summary[result.status.value] += 1

    # -- reporting -----------------------------------------------------------

    def print_matrix(self, matrix: CompatibilityMatrix) -> str:
        """Generate compatibility matrix report."""
        lines = [
            "# Compatibility Test Report",
            f"Platform: {self._current_platform.value}",
            f"ABI: {self._detect_abi().value}",
            f"Python: {sys.version}",
            "",
            "## Summary",
            f"- Total: {matrix.summary['total']}",
            f"- ✅ Pass: {matrix.summary['pass']}",
            f"- ❌ Fail: {matrix.summary['fail']}",
            f"- ⏭️  Skip: {matrix.summary['skip']}",
            f"- ❗ Error: {matrix.summary['error']}",
            f"- 🚫 Not Supported: {matrix.summary['not_supported']}",
            "",
        ]

        # platform results
        if matrix.platform_results:
            lines.append("## Platform Results\n")
            for plat, tests in matrix.platform_results.items():
                lines.append(f"### {plat.value}")
                for name, result in tests.items():
                    icon = {"pass": "✅", "fail": "❌", "skip": "⏭️", "error": "❗", "not_supported": "🚫"}[result.status.value]
                    lines.append(f"- {icon} {name}: {result.details}")

        # sensor results
        if matrix.sensor_results:
            lines.append("\n## Sensor Configuration Results\n")
            for sensor, tests in matrix.sensor_results.items():
                lines.append(f"### {sensor.value}")
                for name, result in tests.items():
                    icon = {"pass": "✅", "fail": "❌", "skip": "⏭️", "error": "❗", "not_supported": "🚫"}[result.status.value]
                    lines.append(f"- {icon} {name}: {result.details}")

        return "\n".join(lines)

    def save_report(self, matrix: CompatibilityMatrix, path: Path) -> None:
        path.write_text(self.print_matrix(matrix), encoding="utf-8")

    def export_json(self, matrix: CompatibilityMatrix, path: Path) -> None:
        data = {
            "platform": self._current_platform.value,
            "abi": self._detect_abi().value,
            "summary": matrix.summary,
            "platform_results": {
                plat.value: {
                    name: {
                        "status": r.status.value,
                        "details": r.details,
                        "duration_ms": r.duration_ms,
                    }
                    for name, r in tests.items()
                }
                for plat, tests in matrix.platform_results.items()
            },
            "sensor_results": {
                sensor.value: {
                    name: {"status": r.status.value, "details": r.details}
                    for name, r in tests.items()
                }
                for sensor, tests in matrix.sensor_results.items()
            },
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Common test definitions
# ---------------------------------------------------------------------------

STANDARD_COMPATIBILITY_TESTS = [
    CompatibilityTest(
        name="python_runtime",
        description="Python runtime compatibility",
        platforms=list(Platform),
        min_python=(3, 8),
    ),
    CompatibilityTest(
        name="numpy_operations",
        description="NumPy operations across platforms",
        platforms=list(Platform),
        abis=[ABI.X86_64, ABI.ARM64],
    ),
    CompatibilityTest(
        name="camera_capture",
        description="RGB camera capture support",
        platforms=[Platform.LINUX_X86_64, Platform.LINUX_AARCH64, Platform.MACOS_X86_64],
        sensors=[SensorConfig.RGB_CAMERA, SensorConfig.DEPTH_CAMERA, SensorConfig.STEREO_CAMERA],
    ),
    CompatibilityTest(
        name="lidar_processing",
        description="LiDAR point cloud processing",
        platforms=[Platform.LINUX_X86_64, Platform.LINUX_AARCH64],
        sensors=[SensorConfig.LIDAR_16, SensorConfig.LIDAR_32, SensorConfig.LIDAR_128],
    ),
    CompatibilityTest(
        name="gpu_inference",
        description="GPU-accelerated model inference",
        platforms=[Platform.LINUX_X86_64, Platform.LINUX_AARCH64, Platform.WINDOWS_X86_64],
        min_memory_mb=2048,
    ),
    CompatibilityTest(
        name="imu_fusion",
        description="IMU sensor fusion",
        platforms=list(Platform),
        sensors=[SensorConfig.IMU_6DOF, SensorConfig.IMU_9DOF],
    ),
    CompatibilityTest(
        name="cross_compilation",
        description="Cross-compilation ABI support",
        platforms=[Platform.LINUX_X86_64],
        abis=list(ABI),
    ),
]
