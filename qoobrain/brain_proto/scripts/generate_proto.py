"""
generate_proto.py — Generate Python gRPC code from .proto files.

Run from workspace root:
    python brain_proto/scripts/generate_proto.py

Or specify paths:
    python brain_proto/scripts/generate_proto.py \
        --proto-dir brain_proto \
        --python-out brain_ai/brain_ai/proto_gen \
        --sdk-out brain_sdk/brain_os/proto_gen
"""
from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Proto files in dependency order
PROTO_FILES = [
    "brain_os/common/types.proto",
    "brain_os/cognition/types.proto",
    "brain_os/cognition/service.proto",
    "brain_os/decision/types.proto",
    "brain_os/decision/service.proto",
    "brain_os/perception/types.proto",
    "brain_os/perception/service.proto",
    "brain_os/control/types.proto",
    "brain_os/control/service.proto",
    "brain_os/safety/types.proto",
    "brain_os/safety/service.proto",
    "brain_os/knowledge/types.proto",
    "brain_os/knowledge/service.proto",
]


def find_workspace_root() -> str:
    """Find workspace root by looking for CMakeLists.txt."""
    d = os.getcwd()
    for _ in range(10):
        if os.path.exists(os.path.join(d, "CMakeLists.txt")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return os.getcwd()


def generate(proto_dir: str, output_dir: str) -> bool:
    """Generate Python proto+grpc code."""
    proto_root = os.path.abspath(proto_dir)
    output_abs = os.path.abspath(output_dir)
    os.makedirs(output_abs, exist_ok=True)

    # Collect .proto file absolute paths
    proto_paths = []
    for proto_rel in PROTO_FILES:
        proto_abs = os.path.join(proto_root, proto_rel)
        if os.path.exists(proto_abs):
            proto_paths.append(proto_abs)
        else:
            logger.warning(f"Proto file not found: {proto_abs}")

    if not proto_paths:
        logger.error("No proto files found!")
        return False

    # Build protoc command
    cmd = [
        sys.executable, "-m", "grpc_tools.protoc",
        f"--proto_path={proto_root}",
        f"--python_out={output_abs}",
        f"--grpc_python_out={output_abs}",
        *proto_paths,
    ]

    logger.info(f"Generating: {len(proto_paths)} .proto files → {output_abs}")
    logger.debug(f"CMD: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"protoc failed (exit {result.returncode}):")
        logger.error(result.stderr)
        return False

    if result.stderr:
        logger.warning(f"protoc warnings: {result.stderr}")

    generated = [f for f in os.listdir(output_abs) if f.endswith(".py")]
    logger.info(f"Generated {len(generated)} Python files in {output_abs}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Generate Python gRPC code from .proto files"
    )
    parser.add_argument(
        "--proto-dir", default="brain_proto",
        help="Root dir of .proto files (relative to workspace root)",
    )
    parser.add_argument(
        "--python-out", default="brain_ai/brain_ai/proto_gen",
        help="Output dir for brain_ai proto code",
    )
    parser.add_argument(
        "--sdk-out", default="brain_sdk/brain_os/proto_gen",
        help="Output dir for brain_sdk proto code",
    )
    args = parser.parse_args()

    workspace = find_workspace_root()
    os.chdir(workspace)
    logger.info(f"Working directory: {workspace}")

    ok = generate(args.proto_dir, args.python_out)
    if ok and args.sdk_out != args.python_out:
        ok = generate(args.proto_dir, args.sdk_out)

    if ok:
        logger.info("Proto generation complete.")
    else:
        logger.error("Proto generation failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
