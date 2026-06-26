# qoogear — 人形机器人配件与外设生态

> 机器人的"AirPods + Apple Watch + MFi"：
> 第三方配件认证、末端执行器生态、可穿戴设备、外设通信协议。

## 定位

qoogear 是 QooBot 生态的配件与外设平台，定义配件认证标准（Made for QooBot），
让第三方厂商可以开发兼容的传感器、夹具、可穿戴设备等外设，丰富机器人能力边界。

## 模块

| 模块 | 说明 | 状态 |
|------|------|------|
| `mfi/` | Made for QooBot 认证（硬件/软件/安全认证） | 📋 规划中 |
| `tools/` | 末端执行器生态（夹具、吸盘、焊枪、3D 打印头） | 📋 规划中 |
| `wearables/` | 可穿戴设备（操作手套、AR 眼镜、外骨骼） | 📋 规划中 |
| `sensors/` | 外接传感器（触觉皮肤、六维力传感器、激光雷达） | 📋 规划中 |
| `mobility/` | 移动平台附件（充电桩、升降平台、轨道系统） | 📋 规划中 |
| `connectivity/` | 配件通信协议（UWB、蓝牙 LE、WiFi Direct、NFC） | 📋 规划中 |
| `power/` | 配件供电标准（磁吸充电、无线充电、热插拔） | 📋 规划中 |
| `sdk_gear/` | 配件开发 SDK（驱动模板、测试套件、认证工具） | 📋 规划中 |

## MFi 认证体系

```
Made for QooBot 认证流程：

  第三方厂商          qoogear 认证中心           qoobot 生态
      │                    │                       │
      ├─ 提交设计 ────────►│                       │
      │                    ├─ 硬件合规审查           │
      │                    ├─ 软件接口兼容测试        │
      │                    ├─ 安全审计              │
      │                    ├─ 互操作性验证           │
      │◄── 认证证书 ───────┤                       │
      │                    │                       │
      ├─ 量产 ────────────►├─ 授权芯片烧录 ────────►│
      │                    │                       │
      └─ 上市 ────────────►│                       ├─ qoocloud 上架
```

## 配件生态矩阵

| 类别 | 现有方案 | QooBot 原生 |
|------|----------|------------|
| 二指夹具 | Robotiq / OnRobot | qoogear Gripper |
| 三指灵巧手 | Shadow / Inspire | qoogear DexHand |
| 六维力传感器 | ATI / Robotiq FT | qoogear Force |
| 触觉皮肤 | GelSight / DIGIT | qoogear Touch |
| 3D 相机 | RealSense / ZED | qoogear Vision |
| AR 眼镜 | HoloLens / Apple Vision Pro | qoogear Glass |
| 操作手套 | HaptX / Manus | qoogear Glove |

## iPhone 类比

| Apple 配件 | qoogear 对应 |
|------------|-------------|
| AirPods | 外接麦克风阵列 / 语音配件 |
| Apple Watch | 可穿戴监控手环 |
| MFi 认证 | Made for QooBot |
| MagSafe | 磁吸供电/配件连接 |
| AirTag | 机器人定位标签 |
| Apple Pencil | 精细操作末端工具 |

## 与 qoobrain 的关系

```
qoogear 配件 ──HAL/插件接口──→ qoobrain (大脑OS)
     │                              │
     ├── 传感器数据流                │
     ├── 配件能力注册                │
     └── 即插即用识别                │
```

## 许可

Apache-2.0
