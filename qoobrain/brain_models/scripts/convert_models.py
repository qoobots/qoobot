#!/usr/bin/env python3
"""
Brain OS 模型转换与验证脚本

管理模型部署格式的转换和优化：
  - ONNX 模型结构验证 (opset, 输入/输出形状, 算子兼容性)
  - TensorRT Engine 构建检查 (trtexec 可用性, 生成构建命令)
  - GGUF 量化信息检查
  - TensorRT-LLM 编译配置生成
  - 模型完整性摘要报告

注意：实际转换操作（如 FP32→INT8/INT4）通常在目标 Jetson 设备上
执行，本脚本提供验证和命令生成功能。

Usage:
  python convert_models.py --check            # 检查所有模型转换状态
  python convert_models.py --validate-onnx    # 验证 ONNX 模型结构
  python convert_models.py --generate-configs # 生成 TRT-LLM 编译配置
  python convert_models.py --model qwen2.5-7b-instruct-int4  # 单模型
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ============================================================================
# 路径配置
# ============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent          # brain_models/scripts/
BRAIN_MODELS_DIR = SCRIPT_DIR.parent                  # brain_models/
PROJECT_ROOT = BRAIN_MODELS_DIR.parent                # qoobot/
REGISTRY_FILE = BRAIN_MODELS_DIR / "model_registry.json"
CONFIG_DIR = BRAIN_MODELS_DIR / "config"

# ============================================================================
# 工具函数
# ============================================================================

def load_registry() -> dict:
    with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def check_command(cmd: str) -> bool:
    """检查命令是否可用"""
    try:
        subprocess.run([cmd, "--version"], capture_output=True, timeout=5, check=False)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def human_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def check_file_status(filepath: Path, min_size: int = 1024) -> str:
    """检查模型文件状态"""
    if not filepath.exists():
        return "MISSING"
    size = filepath.stat().st_size
    if size < 200 and filepath.suffix in [".onnx", ".engine", ".gguf", ".fbow"]:
        # 可能是 Git LFS 占位符
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(130)
        if "oid sha256:" in content:
            return "LFS_STUB"
    if size < min_size:
        return f"SMALL({size}B)"
    return "OK"


# ============================================================================
# 模型验证器
# ============================================================================

class ModelConverter:
    """模型转换管理器"""

    def __init__(self, registry: dict):
        self.registry = registry
        self.results: List[dict] = []

    def check_tools(self) -> dict:
        """检查转换工具链可用性"""
        tools = {}

        # trtexec (TensorRT ONNX → Engine)
        tools["trtexec"] = check_command("trtexec") or self._find_trtexec()

        # onnxruntime
        try:
            import onnxruntime
            tools["onnxruntime"] = onnxruntime.__version__
        except ImportError:
            tools["onnxruntime"] = None

        # onnx (Python package)
        try:
            import onnx
            tools["onnx"] = onnx.__version__
        except ImportError:
            tools["onnx"] = None

        # tensorrt_llm
        try:
            import tensorrt_llm
            tools["tensorrt_llm"] = tensorrt_llm.__version__
        except ImportError:
            tools["tensorrt_llm"] = None

        # huggingface_hub
        try:
            import huggingface_hub
            tools["huggingface_hub"] = huggingface_hub.__version__
        except ImportError:
            tools["huggingface_hub"] = None

        # CUDA
        try:
            result = subprocess.run(["nvcc", "--version"], capture_output=True, text=True, timeout=5)
            tools["cuda"] = "available" if result.returncode == 0 else None
        except FileNotFoundError:
            tools["cuda"] = None

        # GPU
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                tools["gpu"] = result.stdout.strip()
        except FileNotFoundError:
            tools["gpu"] = None

        return tools

    def _find_trtexec(self) -> Optional[str]:
        """查找 trtexec 路径 (常见 Jetson/工作站路径)"""
        candidates = [
            "/usr/src/tensorrt/bin/trtexec",
            "/usr/bin/trtexec",
            "/opt/tensorrt/bin/trtexec",
            "/usr/local/tensorrt/bin/trtexec",
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    def validate_onnx_model(self, model_id: str) -> dict:
        """验证 ONNX 模型结构"""
        model_info = self.registry["models"].get(model_id)
        result = {
            "model_id": model_id,
            "type": "onnx_validation",
            "status": "SKIPPED",
            "details": [],
        }

        if model_info["format"] != "onnx":
            result["status"] = "N/A"
            result["details"].append("非 ONNX 格式")
            return result

        local_dir = PROJECT_ROOT / model_info["local_path"]

        try:
            import onnx
        except ImportError:
            result["status"] = "WARN"
            result["details"].append("onnx 包未安装，无法验证结构")
            return result

        # 确定要验证的文件
        files_to_check = []
        if "parts" in model_info:
            for part_name, part_info in model_info["parts"].items():
                files_to_check.append(part_info["file"])
        else:
            eng = model_info.get("engine_file")
            if eng:
                files_to_check.append(eng)

        for filename in files_to_check:
            filepath = local_dir / filename
            status = check_file_status(filepath)

            if status != "OK":
                result["status"] = "WARN"
                result["details"].append(f"{filename}: {status}")
                continue

            try:
                model = onnx.load(str(filepath))
                onnx.checker.check_model(model)

                # 提取元数据
                opset = model.opset_import[0].version
                inputs = [
                    {"name": inp.name, "shape": [d.dim_value for d in inp.type.tensor_type.shape.dim]}
                    for inp in model.graph.input
                ]
                outputs = [
                    {"name": out.name, "shape": [d.dim_value for d in out.type.tensor_type.shape.dim]}
                    for out in model.graph.output
                ]

                expected_input = model_info.get("input_shape")
                expected_output = model_info.get("output_shape")
                if "parts" in model_info:
                    expected_input = model_info["parts"].get(part_name, {}).get("input_shape")
                    expected_output = model_info["parts"].get(part_name, {}).get("output_shape")

                file_size = filepath.stat().st_size
                result["details"].append({
                    "file": filename,
                    "size": human_size(file_size),
                    "opset": opset,
                    "inputs": inputs,
                    "outputs": outputs,
                    "valid": True,
                })

                if expected_input and inputs:
                    ei_shape = expected_input
                    ai_shape = inputs[0]["shape"]
                    if ai_shape != ei_shape:
                        result["details"].append(
                            f"  形状不匹配: 预期{ei_shape}, 实际{ai_shape}"
                        )
                        result["status"] = "WARN"
                    else:
                        result["details"].append(f"  形状一致: {ai_shape}")

            except Exception as e:
                result["status"] = "FAIL"
                result["details"].append({"file": filename, "error": str(e)})

        if result["status"] == "SKIPPED":
            result["status"] = "OK"

        return result

    def generate_trt_llm_config(self, model_id: str) -> Optional[str]:
        """生成 TensorRT-LLM 编译配置"""
        model_info = self.registry["models"].get(model_id)
        if not model_info or model_info["format"] != "tensorrt_engine":
            return None

        config = {
            "_comment": f"TensorRT-LLM 编译配置 — {model_info['name']}",
            "_generated_by": "brain_models/scripts/convert_models.py",
            "_generated_at": datetime.now(timezone.utc).isoformat(),
            "build_config": {
                "max_input_len": model_info.get("max_context_length", 4096),
                "max_output_len": 2048,
                "max_batch_size": 1,
                "max_beam_width": 1,
                "max_num_tokens": model_info.get("max_context_length", 4096),
            },
            "plugin_config": {
                "gpt_attention_plugin": model_info.get("quantization", "INT4_weight_only"),
                "gemm_plugin": model_info.get("quantization", "INT4_weight_only"),
                "context_fmha": True,
                "paged_kv_cache": True,
                "remove_input_padding": True,
            },
            "quantization": {
                "quant_algo": model_info.get("quantization", "INT4_weight_only"),
                "kv_cache_quant_algo": "INT8" if "INT4" in model_info.get("quantization", "") else None,
            },
            "trtexec_flags": [
                "--fp16",
                "--int8" if "INT4" in model_info.get("quantization", "") else "",
                "--useCudaGraph",
                f'--workspace={int(model_info.get("estimated_size_gb", 4) * 3072)}',
                "--optShapes=input_ids:1x128,attention_mask:1x128",
                "--maxShapes=input_ids:1x2048,attention_mask:1x2048",
                f"--buildOnly",
            ],
        }

        config_dir = CONFIG_DIR / "trt_llm"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / f"{model_id}_build_config.json"

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        return str(config_file)

    def check_gguf_model(self, model_id: str) -> dict:
        """检查 GGUF 模型"""
        model_info = self.registry["models"].get(model_id)
        result = {
            "model_id": model_id,
            "type": "gguf_check",
            "status": "SKIPPED",
            "details": [],
        }

        if model_info["format"] != "gguf":
            result["status"] = "N/A"
            return result

        local_dir = PROJECT_ROOT / model_info["local_path"]
        engine_file = model_info.get("engine_file", "")
        filepath = local_dir / engine_file

        status = check_file_status(filepath, min_size=100_000_000)  # GGUF > 100MB
        if status == "OK":
            file_size = filepath.stat().st_size
            result["status"] = "OK"
            result["details"].append({
                "file": engine_file,
                "size": human_size(file_size),
                "quantization": model_info.get("quantization", "unknown"),
            })
        else:
            result["status"] = "WARN"
            result["details"].append(f"{engine_file}: {status}")

        return result

    def generate_trtexec_command(self, model_id: str, onnx_path: str = None) -> Optional[str]:
        """生成 trtexec 命令行"""
        model_info = self.registry["models"].get(model_id)
        if not model_info or model_info["format"] != "onnx":
            return None

        local_dir = PROJECT_ROOT / model_info["local_path"]
        engine_file = model_info.get("engine_file", "model.engine")
        input_shape = model_info.get("input_shape", [1, 3, 640, 640])

        onnx_file = onnx_path or (local_dir / engine_file.replace(".engine", ".onnx"))
        engine_file = local_dir / engine_file.replace(".onnx", ".engine")

        shape_str = "x".join(str(d) for d in input_shape)

        cmd_parts = [
            "trtexec",
            f"--onnx={onnx_file}",
            f"--saveEngine={engine_file}",
            f"--minShapes=input:{shape_str}",
            f"--optShapes=input:{shape_str}",
            f"--maxShapes=input:{shape_str}",
            "--fp16",
            "--useCudaGraph",
            "--memPoolSize=workspace:2048",
            "--verbose",
        ]

        return " \\\n  ".join(cmd_parts)

    def run_check(self, model_ids: Optional[List[str]] = None) -> None:
        """运行转换状态检查"""
        tools = self.check_tools()

        print("\n" + "=" * 70)
        print("  Brain OS 模型转换状态检查")
        print("=" * 70)
        print(f"\n  工具链状态:")
        for tool, status in tools.items():
            icon = "✅" if status else "❌"
            val = status if status else "未安装"
            print(f"    {icon} {tool:20s} {val}")

        if not model_ids:
            model_ids = list(self.registry["models"].keys())

        print(f"\n  模型状态 ({len(model_ids)} 个):")
        print(f"  {'模型':35s} {'格式':15s} {'状态':10s} {'备注'}")
        print(f"  {'-'*66}")

        all_ok = True

        for model_id in model_ids:
            model_info = self.registry["models"].get(model_id)
            if not model_info:
                continue

            fmt = model_info["format"]
            local_dir = PROJECT_ROOT / model_info["local_path"]

            # 检查主文件
            engine_file = model_info.get("engine_file", "")
            if engine_file:
                filepath = local_dir / engine_file
                status = check_file_status(filepath, min_size=1024)
            else:
                status = "NO_ENGINE"

            # 翻译状态为可读
            status_map = {
                "OK": "✅ 就绪",
                "MISSING": "⬜ 未下载",
                "LFS_STUB": "📎 LFS占位",
                "SMALL": "⚠️ 不完整",
                "NO_ENGINE": "⬜ 未编译",
            }

            display_status = status
            for key, label in status_map.items():
                if key in str(status):
                    display_status = label
                    break

            if "OK" not in str(status):
                all_ok = False

            print(f"  {model_id:35s} {fmt:15s} {display_status:10s} "
                  f"{'需转换' if fmt == 'tensorrt_engine' and status != 'OK' else ''}")

        print(f"\n  总结: {'全部就绪 ✅' if all_ok else '部分模型需要下载/转换 ⚠️'}")

        # 转换建议
        convert_needed = [
            mid for mid in model_ids
            if self.registry["models"][mid]["format"] == "tensorrt_engine"
            and check_file_status(
                PROJECT_ROOT / self.registry["models"][mid]["local_path"] / self.registry["models"][mid].get("engine_file", ""),
                min_size=1024
            ) != "OK"
        ]

        if convert_needed:
            print(f"\n  TensorRT Engine 构建指南:")
            print(f"  {'-'*50}")
            print(f"  以下模型需要在 Jetson Orin 上编译为 TensorRT Engine:\n")
            for mid in convert_needed:
                info = self.registry["models"][mid]
                print(f"    {info['name']}:")
                print(f"      1. 下载原始权重: python download_models.py --model {mid}")
                print(f"      2. 构建 Engine: 参考 config/trt_llm/{mid}_build_config.json")
                print(f"      3. 验证: python convert_models.py --validate-onnx --model {mid}")
                print()

        # ONNX 模型引擎构建
        onnx_models = [
            mid for mid in model_ids
            if self.registry["models"][mid]["format"] == "onnx"
        ]
        if onnx_models and tools.get("trtexec"):
            print(f"\n  ONNX → TensorRT Engine 构建命令 (可选, 加速推理):")
            print(f"  {'-'*50}")
            for mid in onnx_models:
                cmd = self.generate_trtexec_command(mid)
                if cmd:
                    print(f"\n    # {self.registry['models'][mid]['name']}")
                    print(f"    {cmd}")
            print()

    def print_onnx_validation(self, model_ids: Optional[List[str]] = None) -> None:
        """打印 ONNX 模型验证结果"""
        if not model_ids:
            model_ids = [
                mid for mid, info in self.registry["models"].items()
                if info["format"] == "onnx"
            ]

        print(f"\n  ONNX 模型结构验证:")
        print(f"  {'-'*50}")

        for model_id in model_ids:
            result = self.validate_onnx_model(model_id)
            icon = {"OK": "✅", "WARN": "⚠️", "FAIL": "❌", "N/A": "⬜"}.get(result["status"], "?")
            print(f"  {icon} {model_id}")
            for detail in result["details"]:
                if isinstance(detail, dict):
                    print(f"      文件: {detail.get('file', '?')} | 大小: {detail.get('size', '?')} | "
                          f"opset: {detail.get('opset', '?')}")
                else:
                    print(f"      {detail}")


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Brain OS 模型转换与验证工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--check", action="store_true", help="检查所有模型转换状态")
    parser.add_argument("--validate-onnx", action="store_true", help="验证 ONNX 模型结构")
    parser.add_argument("--generate-configs", action="store_true", help="生成 TRT-LLM 编译配置")
    parser.add_argument("--model", type=str, help="指定模型 ID (默认: 所有)")
    args = parser.parse_args()

    registry = load_registry()
    converter = ModelConverter(registry)

    # 默认行为：check
    if not (args.check or args.validate_onnx or args.generate_configs):
        args.check = True

    model_ids = [args.model] if args.model else None

    if args.check:
        converter.run_check(model_ids)

    if args.validate_onnx:
        converter.print_onnx_validation(model_ids)

    if args.generate_configs:
        targets = model_ids or [
            mid for mid, info in registry["models"].items()
            if info["format"] == "tensorrt_engine"
        ]
        for mid in targets:
            config_file = converter.generate_trt_llm_config(mid)
            if config_file:
                print(f"  ✅ {mid} → {config_file}")

    print()

if __name__ == "__main__":
    main()
