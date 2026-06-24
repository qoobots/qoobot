# brain_models — 模型权重存储

## 目录结构

```
brain_models/
├── cv/                         # 计算机视觉模型
│   ├── yolov11n.onnx           # YOLOv11 Nano（速度优先）
│   ├── yolov11s.onnx           # YOLOv11 Small（精度均衡）
│   ├── sam2_hiera_tiny.encoder.onnx  # SAM2 Tiny 编码器
│   └── sam2_hiera_tiny.decoder.onnx  # SAM2 Tiny 解码器
├── llm/                        # 语言模型（Git LFS）
│   ├── qwen2.5-7b-instruct/    # Qwen2.5-7B（主推理引擎）
│   │   └── README.md           # 下载说明
│   └── qwen2.5-1.5b-instruct-q4_k_m.gguf  # CPU 备选（量化版）
├── slam/                       # SLAM 词汇表
│   └── orb_vocab.fbow          # ORB-SLAM3 字典（112MB）
└── vla/                        # VLA 模型（Phase 2）
    └── .gitkeep
```

## 模型下载

### YOLOv11（已包含）
`cv/yolov11n.onnx` 和 `cv/yolov11s.onnx` 已通过 Git LFS 追踪。

### Qwen2.5-7B
```bash
# 需要 huggingface_hub
pip install huggingface_hub
python -c "
from huggingface_hub import snapshot_download
snapshot_download('Qwen/Qwen2.5-7B-Instruct', local_dir='brain_models/llm/qwen2.5-7b-instruct')
"
```

### ORB-SLAM3 词汇表（已包含）
`slam/orb_vocab.fbow` 已包含在仓库中（通过 Git LFS）。

## Git LFS 初始化

首次克隆时需要拉取 LFS 文件：
```bash
git lfs install
git lfs pull
```
