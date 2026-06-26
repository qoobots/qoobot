# QooCore — QooBot 端侧 AI 推理引擎

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/QooBot/qoocore)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Android-orange.svg)
![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)

> 对标 Qualcomm AI Engine / NVIDIA Jetson 软件栈的端侧 AI 推理引擎
> 为 QooBot 机器人操作系统提供芯片级 AI 加速能力

---

## 目录

- [特性](#特性)
- [架构](#架构)
- [快速开始](#快速开始)
- [设计文档](#设计文档)
- [API 示例](#api-示例)
- [编译工具链](#编译工具链)
- [支持芯片](#支持芯片)
- [路线图](#路线图)
- [贡献](#贡献)
- [许可证](#许可证)

---

## 特性

| 特性 | 描述 |
|------|------|
| **多后端统一抽象** | 一套 API 同时支持 NPU / GPU / DSP / CPU，动态选择最优后端 |
| **零拷贝流水线** | ION/DMA-BUF 跨硬件内存共享，相机 → NPU → GPU 无 memcpy |
| **编译工具链** | ONNX → IR → 优化 → 量化 → .qoomodel，完整模型编译流程 |
| **亚毫秒级延迟** | YOLO 系列 < 10ms（NPU INT8），视觉语言动作模型 < 100ms |
| **多模型并发** | 检测 + 分割 + 规划并发推理，> 30 fps |
| **插件化 HAL** | 新芯片厂商只需实现 `NpuHal` 接口，即可接入 |
| **Sim2Real 就绪** | 编译工具链支持域随机化参数注入 |

---

## 架构

```
┌─────────────────────────────────────────────────┐
│  Layer 4 · 应用层                                       │
│  qoobrain（感知）· qoocloud（混合推理）· CLI/SDK       │
├─────────────────────────────────────────────────┤
│  Layer 3 · 运行时层（核心）                              │
│  统一推理引擎 → 实时调度器 → 异构后端抽象（HAL）          │
├─────────────────────────────────────────────────┤
│  Layer 2 · 编译层                                      │
│  模型导入 → 图优化 → 量化编译 → 模型剪枝 → 编译器后端    │
├─────────────────────────────────────────────────┤
│  Layer 1 · 基础设施层                                   │
│  内存管理 · 专用算子库 · 硬件适配 · 观测诊断             │
└─────────────────────────────────────────────────┘
```

详细架构请参阅 [`docs/02架构设计.md`](docs/02架构设计.md)。

---

## 快速开始

### 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Linux (Ubuntu 22.04+) / Android 14+ |
| 编译器 | GCC 12+ / Clang 16+ |
| CMake | 3.25+ |
| 依赖 | FlatBuffers 24.x, spdlog 1.14+, yaml-cpp 0.8+ |

### 构建

```bash
git clone https://github.com/QooBot/qoocore.git
cd qoocore

# 配置（Linux aarch64，目标 NPU + GPU）
mkdir build && cd build
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DQOOCORE_ENABLE_NPU_QNN=ON \
  -DQOOCORE_ENABLE_GPU_CUDA=ON \
  -DQOOCORE_BUILD_PYTHON=ON \
  -DQOOCORE_BUILD_TESTS=ON

# 编译
make -j$(nproc)

# 安装到系统
sudo make install

# Python 包安装
pip install python/
```

### 运行测试

```bash
cd build
ctest --output-on-failure
```

---

## 设计文档

| 文档 | 描述 |
|------|------|
| [`docs/01功能清单完成进度.md`](docs/01功能清单完成进度.md) | 功能清单与完成进度 |
| [`docs/02架构设计.md`](docs/02架构设计.md) | 系统架构、模块划分、技术选型 |
| [`docs/03交互设计.md`](docs/03交互设计.md) | C++ API、Python SDK、CLI 命令 |
| [`docs/04数据设计.md`](docs/04数据设计.md) | .qoomodel 格式、Tensor 布局、ION 设计 |
| [`docs/05项目目录结构.md`](docs/05项目目录结构.md) | 代码目录、构建系统、代码规范 |

---

## API 示例

### C++ API

```cpp
#include <qoocore/engine.h>
#include <qoocore/tensor.h>

int main() {
    auto& engine = qoocore::InferenceEngine::instance();

    // 1. 初始化
    engine.init();

    // 2. 加载模型
    auto handle = engine.load_model("yolov11n.qoomodel");

    // 3. 创建输入张量
    auto input = qoocore::Tensor::create({1, 3, 640, 640},
                                          qoocore::DType::UINT8);

    // 4. 推理
    auto output = engine.infer(handle, input);

    // 5. 处理输出
    // ...

    // 6. 清理
    engine.unload_model(handle);
    engine.shutdown();
    return 0;
}
```

### Python SDK

```python
import qoocore

engine = qoocore.InferenceEngine()
engine.init()

model = engine.load_model("yolov11n.qoomodel")
result = model.infer(input_image)
print(result)
```

### CLI

```bash
# 编译模型
qoocore compile -i model.onnx -o model.qoomodel --backend npu_qnn --int8

# 推理
qoocore infer -m model.qoomodel -i input.jpg -o output.json

# 性能剖析
qoocore profile -m model.qoomodel --warmup 10 --iterations 100
```

---

## 编译工具链

QooCore 提供完整的模型编译工具链：

```bash
# ONNX → .qoomodel
qoocore compile \
  --input yolov11n.onnx \
  --output yolov11n.qoomodel \
  --backend npu_qnn \
  --quant int8 \
  --calibration-data ./calib_images/

# 支持格式
#   - ONNX (.onnx, opset 17+)
#   - PyTorch (.pt, TorchScript)
#   - TensorFlow (.pb, SavedModel)
#   - TFLite (.tflite)
```

编译输出 `.qoomodel` 文件格式：

```
.qoomodel 文件布局
┌──────────────────────────┐
│  Magic Number (4B)       │  QOO\x01
├─── Compiled Model─────────┤  编译后的模型执行代码
├─── Model Weights─────────┤  量化后的权重数据
├─── Model Config───────────┤  YAML 格式，zstd 压缩
├─── Metadata───────────────┤  JSON 格式，zstd 压缩
├─── Checksum───────────────┤  SHA-256 校验和
└──────────────────────────┘
```

---

## 支持芯片

| 厂商 | 芯片 | 后端 | 状态 |
|------|------|------|------|
| Qualcomm | Snapdragon 8 Gen 3 | QNN | 🚧 开发中 |
| Horizon | Journey 5 / 6 | BPU | 📋 计划中 |
| Rockchip | RK3588 | RKNN | 📋 计划中 |
| NVIDIA | Jetson Orin | CUDA | 📋 计划中 |
| ARM | Cortex-A78AE | Neon | ✅ 已支持 |

---

## 路线图

| 阶段 | 目标 | 关键产出 | 状态 |
|------|------|---------|------|
| Phase 1 · v0.1 | 核心编译工具链 + 一款 NPU 后端 | `.qoomodel` 格式、QNN 后端、CLI compile | 🚧 开发中 |
| Phase 2 · v0.3 | 完整运行时 + 多后端支持 | 统一推理引擎、GPU/DSP 后端、零拷贝内存 | 📋 计划中 |
| Phase 3 · v0.5 | 算子库 + 内存优化 + 调度 | 专用算子、多模型并发调度 | 📋 计划中 |
| Phase 4 · v1.0 | 观测诊断 + 云端协同 | 性能剖析面板、OTA 更新、3 款芯片适配 | 📋 计划中 |

---

## 项目结构

```
qoocore/
├── docs/               # 设计文档（5 份）
├── include/qoocore/   # 公共 C++ 头文件
├── src/                # C++ 实现
├── python/             # Python SDK
├── cli/                # CLI 工具
├── schema/             # 数据格式 Schema
├── tests/              # 测试
├── third_party/        # 第三方依赖
├── cmake/              # CMake 模块
├── CMakeLists.txt      # 顶层构建
└── README.md
```

---

## 贡献

欢迎贡献！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)（待创建）。

开发流程：

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/xxx`)
3. 提交更改 (`git commit -m 'Add xxx'`)
4. 推送到分支 (`git push origin feature/xxx`)
5. 创建 Pull Request

---

## 许可证

Apache License 2.0 — 详见 [LICENSE](LICENSE) 文件。

---

## 相关项目

- [QooBot/qoobrain](https://github.com/QooBot/qoobrain) — 感知与认知模型
- [QooBot/qoobody](https://github.com/QooBot/qoobody) — 机械结构与运动学
- [QooBot/qoocloud](https://github.com/QooBot/qoocloud) — 云端混合推理

---

## 联系

- 项目主页：https://github.com/QooBot/qoocore
- Issue 追踪：https://github.com/QooBot/qoocore/issues
- 邮件列表：qoobot-dev@googlegroups.com（待创建）

---

*QooCore — 让机器人拥有端侧智能。*
