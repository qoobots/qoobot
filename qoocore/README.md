# qoocore — 人形机器人芯片与加速框架

> 机器人的"Apple Silicon + Core ML + Neural Engine"：
> 端侧模型推理运行时、模型编译优化、硬件加速抽象。

## 定位

qoocore 是 QooBot 生态的底层计算基础设施，让 AI 模型在各种边缘芯片上
高效运行，提供统一的模型推理接口和硬件加速能力。

## 模块

| 模块 | 说明 | 状态 |
|------|------|------|
| `runtime/` | 端侧模型推理运行时（ONNX Runtime / TensorRT / ExecuTorch） | 📋 规划中 |
| `compiler/` | 模型编译器（PyTorch/ONNX → 芯片专用格式） | 📋 规划中 |
| `accelerator/` | 硬件加速抽象层（GPU / NPU / DSP / FPGA） | 📋 规划中 |
| `quantizer/` | 模型量化工具（INT8 / INT4 / 混合精度） | 📋 规划中 |
| `scheduler/` | 推理任务调度器（多模型并发、优先级） | 📋 规划中 |
| `benchmark/` | 芯片性能基准测试套件 | 📋 规划中 |
| `memory/` | 内存管理与优化（共享内存、零拷贝） | 📋 规划中 |
| `pipeline/` | 多模型流水线编排（感知→推理→控制） | 📋 规划中 |

## 支持平台

| 平台 | 芯片 | 加速后端 |
|------|------|----------|
| NVIDIA Jetson | Orin / AGX | TensorRT / CUDA |
| Qualcomm | Snapdragon / RB5 | QNN / SNPE |
| Intel | Core Ultra / Meteor Lake | OpenVINO |
| Rockchip | RK3588 | RKNN |
| Horizon | J5 / J6 | BPU SDK |
| AMD | Ryzen AI | Vitis AI / MIGraphX |
| Apple | M 系列（未来） | Core ML / ANE |

## 性能目标

| 模型类型 | 延迟目标 | 典型场景 |
|----------|----------|----------|
| 目标检测 | <10ms | 实时避障 |
| 姿态估计 | <5ms | 运动控制 |
| VLA 推理 | <100ms | 任务规划 |
| 语音识别 | <200ms | 语音交互 |
| 深度估计 | <16ms (60fps) | 导航 |

## iPhone 类比

| Apple 技术 | qoocore 对应 |
|------------|-------------|
| Apple Silicon | 多芯片适配层 |
| Core ML | runtime（统一推理接口） |
| Neural Engine | accelerator（NPU 加速） |
| Metal | accelerator（GPU 加速） |
| Core ML Tools | compiler + quantizer |

## 与 qoobrain 的关系

```
qoobrain (大脑OS) ──模型推理请求──→ qoocore (芯片加速)
                                       │
                                       ├── GPU 加速
                                       ├── NPU 加速
                                       └── DSP 加速
```

## 许可

Apache-2.0
