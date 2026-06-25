# QooBot — 具身智能机器人全栈生态

> 像 iPhone 重新定义了手机一样，QooBot 重新定义机器人——  
> 硬件是"iPhone"，qoobrain 是"iOS"，qooeco 是"App Store"，qoocloud 是"iCloud"。

---

## 项目地图

| 项目 | 定位 | iPhone 类比 | 说明 |
|------|------|-------------|------|
| **[qoobody](./qoobody/)** | 硬件本体 | 📱 iPhone 硬件 | 传感器、执行器、计算平台、机械结构、能源系统 |
| **[qoobrain](./qoobrain/)** | 大脑操作系统 | ⚙️ iOS | 感知、认知、决策、规划、运动控制、通信 |
| **[qooeco](./qooeco/)** | 应用生态 | 🏪 App Store | 技能市场、开发者工具、第三方算法集成 |
| **[qoocloud](./qoocloud/)** | 云端服务 | ☁️ iCloud | 云端推理、数据同步、远程协作、多机管理 |

## 架构全景

```
                        ┌──────────────────────────────────┐
                        │          qoocloud (云端)          │
                        │  推理 · 同步 · 协作 · OTA · 监控  │
                        └──────────────┬───────────────────┘
                                       │ gRPC / MQTT
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
        │    ┌─────────────────┐       │       ┌─────────────────┐    │
        │    │   qoobrain      │◄──────┼──────►│    qooeco       │    │
        │    │   大脑操作系统    │       │       │    应用生态      │    │
        │    │  (iOS 类比)     │       │       │  (App Store 类比)│    │
        │    └────────┬────────┘       │       └─────────────────┘    │
        │             │  HAL 接口      │                              │
        │    ┌────────▼────────┐       │                              │
        │    │    qoobody      │       │                              │
        │    │   硬件本体       │       │                              │
        │    │ (iPhone 硬件类比)│       │                              │
        │    └─────────────────┘       │                              │
        │                              │                              │
        │        QooBot 全栈           │                              │
        └──────────────────────────────┘                              │
```

## 数据流

```
传感器数据 → qoobody (HAL) → qoobrain (感知→认知→决策→规划→控制) → qoobody (执行器)
                │                    │                    │
                │                    ├──→ qoocloud (云端大模型推理)
                │                    │
                │                    └──→ qooeco (技能调用)
                │
                └── qoocloud (数据回传、OTA)
```

## 快速开始

### qoobrain (大脑操作系统)

```bash
cd qoobrain
pip install -e brain_sdk/ -e brain_ai/
python -m pytest brain_ai/tests brain_sdk/tests -v
```

### qoobody (硬件本体)

```bash
cd qoobody
# 参考 README 中的硬件接口规范
```

### qooeco (应用生态)

```bash
cd qooeco
# 参考 README 中的开发者指南
```

### qoocloud (云端服务)

```bash
cd qoocloud
# 参考 README 中的部署指南
```

## 项目状态

| 项目 | 状态 | 测试 |
|------|------|------|
| qoobrain | Alpha | Python: 313/315 ✅ · TS: 15/21 |
| qoobody | 📋 规划中 | - |
| qooeco | 📋 规划中 | - |
| qoocloud | 📋 规划中 | - |

## 许可

所有子项目均采用 Apache-2.0 许可协议。
