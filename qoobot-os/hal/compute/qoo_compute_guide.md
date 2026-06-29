# compute — 计算平台参考方案

> 基于 qoobody 设计文档的参考实现方案

## 目录结构

```
compute/
├── soc_reference/          # SoC 参考选型与配置
│   └── qoo_soc_guide.md    # 多档位 SoC 选型指南
├── os_config/              # 操作系统与内核配置
│   └── qoo_linux_config.md # Linux 内核裁剪与实时配置
└── accelerator/            # AI 加速器集成
    └── qoo_npu_integration.md  # NPU 驱动与运行时集成
```

---

## 1. SoC 多档位选型指南

### 1.1 档位定义

| 档位 | 目标产品 | 算力需求 | 功耗预算 | 推荐 SoC |
|------|---------|---------|---------|---------|
| **Lite** | 桌面机械臂 | 10~20 TOPS NPU, 200 GFLOPS GPU | < 30W | Rockchip RK3588 / NXP i.MX 95 |
| **Standard** | 移动底盘 / 服务机器人 | 30~100 TOPS NPU, 1 TFLOPS GPU | < 60W | NVIDIA Jetson Orin NX 16GB |
| **Pro** | 仿生人 / 工业协作 | 200~275 TOPS NPU, 3~5 TFLOPS GPU | < 100W | NVIDIA Jetson AGX Orin 64GB |
| **Enterprise** | 多机协作 / 云端协同 | 集群部署 | 按需 | 边缘服务器 + AGX Orin |

### 1.2 Standard 档位详细配置 (推荐开发基准)

```
SoC: NVIDIA Jetson Orin NX 16GB
├── CPU: 8-core Arm Cortex-A78AE @ 2.0 GHz
├── GPU: 1024-core NVIDIA Ampere, 32 Tensor Cores
├── NPU: 100 TOPS (INT8), 50 TOPS (FP16)
├── Memory: 16 GB LPDDR5, 102.4 GB/s
├── Storage: 256 GB NVMe SSD
├── Video: 4x MIPI CSI-2 (8 lanes), 2x GbE
├── USB: 2x USB 3.2, 1x USB-C
├── PCIe: x8 Gen4
└── Power: 15~40W (可配置)
```

### 1.3 Linux 内核实时配置

```bash
# 安装 PREEMPT_RT 内核
sudo apt install linux-image-rt-amd64

# 关键内核参数
cat >> /etc/sysctl.d/99-qoobot-rt.conf << EOF
# 实时调度
kernel.sched_rt_runtime_us = -1
# 禁用 NUMA 平衡 (减少延迟抖动)
kernel.numa_balancing = 0
# 提高网络缓冲
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
EOF

# CPU 隔离 (隔离核心 4-7 给实时任务)
# 添加 isolcpus=4-7 到 /boot/extlinux/extlinux.conf
```

---

## 2. AI 推理运行时配置

### 2.1 TensorRT 引擎

```python
# qoo_npu_inference.py - NPU 推理引擎封装
import tensorrt as trt
import numpy as np

class QooNPUEngine:
    """QooBot NPU 推理引擎"""

    def __init__(self, model_path: str):
        self.logger = trt.Logger(trt.Logger.WARNING)
        self.runtime = trt.Runtime(self.logger)

        with open(model_path, 'rb') as f:
            self.engine = self.runtime.deserialize_cuda_engine(f.read())

        self.context = self.engine.create_execution_context()

        # 分配输入/输出缓冲区
        self.inputs, self.outputs, self.bindings = [], [], []
        self.stream = None  # CUDA stream

    def allocate_buffers(self):
        """分配 GPU 缓冲区"""
        for i in range(self.engine.num_io_tensors):
            name = self.engine.get_tensor_name(i)
            shape = self.engine.get_tensor_shape(name)
            dtype = trt.nptype(self.engine.get_tensor_dtype(name))
            size = trt.volume(shape)

            # 使用 CUDA 锁页内存 (零拷贝)
            h_mem = cuda.pagelocked_empty(size, dtype)
            d_mem = cuda.mem_alloc(h_mem.nbytes)

            if self.engine.get_tensor_mode(name) == trt.TensorIOMode.INPUT:
                self.inputs.append({'name': name, 'host': h_mem, 'device': d_mem})
            else:
                self.outputs.append({'name': name, 'host': h_mem, 'device': d_mem})

            self.bindings.append(int(d_mem))

    def infer(self, input_data: np.ndarray) -> np.ndarray:
        """执行推理"""
        # 拷贝输入到 GPU
        np.copyto(self.inputs[0]['host'], input_data.ravel())
        cuda.memcpy_htod(self.inputs[0]['device'], self.inputs[0]['host'])

        # 执行推理
        self.context.execute_async_v2(
            bindings=self.bindings,
            stream_handle=self.stream.handle
        )

        # 拷贝输出回 CPU
        cuda.memcpy_dtoh(self.outputs[0]['host'], self.outputs[0]['device'])

        return self.outputs[0]['host'].reshape(self.output_shape)
```

### 2.2 端侧模型部署流程

```
1. 模型导出 (qoocore)
   PyTorch/ONNX → qoocore 编译 → .qoomodel

2. 模型优化 (qoocore + TensorRT)
   .qoomodel → INT8 量化 → TensorRT engine

3. 部署到计算平台
   TensorRT engine → NVMe 存储 → 运行时加载

4. 推理运行时 (本模块)
   QooNPUEngine → 加载 engine → 实时推理
```

---

## 3. 异构计算数据流

```
传感器输入
    │
    ├── 视觉 (MIPI) ──→ ISP (硬件) ──→ GPU (预处理) ──→ NPU (推理)
    │                                                    │
    ├── LiDAR (UDP) ──→ CPU (解码) ─────────────────────┤
    │                                                    │
    ├── IMU (SPI)  ──→ MCU (滤波) ──────────────────────┤
    │                                                    │
    └── 音频 (I2S) ──→ DSP (降噪) ──────────────────────┤
                                                         ▼
                                              推理结果 → qoobrain
                                                         │
                                                         ▼
                                              控制指令 → CAN/EtherCAT
```

### 3.1 流水线并行策略

| 阶段 | 执行单元 | 延迟预算 | 说明 |
|------|---------|---------|------|
| 传感器采集 | ISP/DMA | < 5ms | 硬件直接 DMA 到内存 |
| 预处理 | GPU/CUDA | < 5ms | 图像 resize/normalize |
| 模型推理 | NPU | < 15ms | 目标检测/分割/位姿估计 |
| 后处理 | CPU | < 3ms | NMS/坐标转换 |
| 融合与决策 | CPU/GPU | < 10ms | 多模态融合 |
| 控制指令下发 | MCU | < 2ms | CAN/EtherCAT |
| **总计** | | **< 40ms** | 端到端感知-控制延迟 |
