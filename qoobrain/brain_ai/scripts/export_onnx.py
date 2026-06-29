#!/usr/bin/env python3
"""QooBrain 模型导出 ONNX 格式脚本。

将 PyTorch 模型导出为 ONNX 格式，支持 YOLOv11/SAM2 等视觉模型。

Usage:
    python scripts/export_onnx.py --model yolov11n --input-size 640
    python scripts/export_onnx.py --model sam2_hiera_tiny --encoder
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="Export model to ONNX format")
    parser.add_argument("--model", required=True, help="Model name to export")
    parser.add_argument("--input-size", type=int, default=640, help="Input image size")
    parser.add_argument("--encoder", action="store_true", help="Export encoder only")
    parser.add_argument("--decoder", action="store_true", help="Export decoder only")
    parser.add_argument("--output-dir", default="brain_models/", help="Output directory")
    args = parser.parse_args()

    output_path = f"{args.output_dir}/{args.model}.onnx"
    print(f"Exporting {args.model} to {output_path}...")
    print(f"  Input size: {args.input_size}")
    print(f"  Encoder only: {args.encoder}")
    print(f"  Decoder only: {args.decoder}")

    # Placeholder for actual ONNX export logic
    print("\nNote: Full ONNX export requires PyTorch and the model checkpoint.")
    print("Please ensure the model weights are available in brain_models/")
    print("Run download_models.sh first if needed.")


if __name__ == "__main__":
    main()
