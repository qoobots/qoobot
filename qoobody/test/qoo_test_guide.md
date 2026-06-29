# =============================================================================
# QooBody — Test & Validation Reference Guide
# =============================================================================

> 版本：v0.1 | 最后更新：2026-06-29

---

## 1. 概述

本目录包含 QooBody 硬件参考设计的测试与验证代码。测试覆盖五个维度：
硬件在环（HIL）测试、可靠性测试、性能基准测试、互操作性测试和持续集成测试。

对应设计文档：[docs/08测试与验证规范.md](../docs/08测试与验证规范.md)

---

## 2. 测试文件

| 文件 | 类别 | 说明 |
|------|------|------|
| `qoo_hil_platform.c` | HIL 平台 | HIL 仿真主机连接、传感器信号注入、故障注入引擎 |
| `qoo_hil_test.c` | HIL 测试 | 传感器管线、运动控制、安全系统、电源系统测试用例 |
| `qoo_perf_benchmark.c` | 性能基准 | 感知延迟、控制带宽、通信吞吐量、端到端延迟基准 |
| `qoo_reliability_test.c` | 可靠性 | 环境/机械应力、老化寿命、EMC 测试框架 |
| `qoo_interop_test.c` | 互操作 | 即插即用验证、协议一致性、兼容性评分 |

---

## 3. 构建与运行

### 3.1 使用 CMake 构建测试

```bash
# 配置（x86_64 主机，Release + 测试）
cmake -B build -DPLATFORM=x86_64 -DCMAKE_BUILD_TYPE=Release -DQOOBODY_BUILD_TESTS=ON

# 构建
cmake --build build --parallel $(nproc)

# 运行所有测试
cd build && ctest --output-on-failure -j $(nproc)

# 运行单个测试
./build/qoo_perf_benchmark
./build/qoo_hil_test
```

### 3.2 使用 Docker 运行 HIL 测试

```bash
docker build --target qoobody-test -t qoobody-test .
docker run --rm qoobody-test
```

---

## 4. 测试分类

### 4.1 传感器管线测试 (qoo_hil_test.c)

| 测试 | 验收标准 |
|------|---------|
| 端到端感知延迟 | < 50ms |
| 多传感器时间戳偏差 | < 100μs |
| 视觉 + LiDAR 满带宽不丢帧 | 丢帧率 = 0% |

### 4.2 运动控制测试 (qoo_hil_test.c)

| 测试 | 验收标准 |
|------|---------|
| 位置跟踪误差 | < 0.1° |
| 速度波动 | < 5% |
| 力矩响应时间 | < 5ms |
| 急停到静止 | < 200ms |

### 4.3 安全系统测试 (qoo_hil_test.c)

| 测试 | 验收标准 |
|------|---------|
| 碰撞检测延迟 | < 10ms |
| 力超限保护响应 | < 5ms |
| 主控心跳丢失 → 安全停止 | < 50ms |

### 4.4 性能基准 (qoo_perf_benchmark.c)

| 测试 | 基准值 |
|------|--------|
| 感知延迟 | < 30ms |
| 控制带宽 | ≥ 1kHz |
| CAN FD 吞吐量 | ≥ 4Mbps |
| EtherCAT 吞吐量 | ≥ 80Mbps |

### 4.5 互操作性 (qoo_interop_test.c)

各组件（电机、相机、LiDAR、IMU、BMS、无线模组）的即插即用兼容性评分：
- **A 级**：完全兼容，无需修改
- **B 级**：需要配置参数调整
- **C 级**：需要驱动适配

---

## 5. 持续集成

测试在每次 push/PR 时通过 GitHub Actions 自动运行。参见 [.github/workflows/ci.yml](../.github/workflows/ci.yml)。

CI 流水线包含：
- `build-x86_64`：主机构建 + 全量测试 + 地址/未定义行为检查
- `build-jetson-orin`：aarch64 交叉编译
- `build-safety-mcu`：ARM bare-metal 固件构建
- `static-analysis`：clang-tidy 静态分析
- `docs-check`：Markdown 链接检查
