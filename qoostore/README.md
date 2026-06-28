# qoostore — 机器人应用生态（端云协同）

> **架构**：端云协同 — 云端商店 + 机器人端运行环境
> 对标 Apple App Store（云端商店 + iOS 端 App Store 客户端）

qoostore 是 QooBot 的 **机器人 App Store**，采用端云协同架构：
- **qoostore-cloud**：云端技能商店后端（发布/审核/计费/分发/运营）
- **qoostore-edge**：机器人端技能运行环境（安装/沙箱/权限/监控）

## 项目结构

```
qoostore/
├── qoostore-cloud/          # 云端 — Spring Boot 微服务
│   ├── pom.xml            # Maven 构建（Java 21 + Spring Cloud）
│   └── ...
├── qoostore-edge/           # 机器人端 — C++17 + Python 3.11
│   ├── CMakeLists.txt     # CMake 构建入口
│   └── ...
├── docs/                  # 共享设计文档
└── README.md
```

## 模块

| 模块 | 运行位置 | 职责 | 技术栈 |
|------|---------|------|--------|
| qoostore-cloud | 云端 | 技能商店/发布审核/计费/分发/运营分析 | Java 21 + Spring Cloud |
| qoostore-edge | 机器人端 | 技能安装/沙箱隔离/权限管控/运行时监控 | C++17 + Python 3.11 |

## 技能分类

| 类别 | 示例 |
|------|------|
| 🏠 家庭 | 清洁、整理、烹饪辅助、老人看护 |
| 🏭 工业 | 装配、质检、搬运、焊接 |
| 🏥 医疗 | 手术辅助、康复训练、药品配送 |
| 🛒 零售 | 导购、理货、盘点 |
| 🌾 农业 | 采摘、巡检、喷洒 |
| 🎮 娱乐 | 下棋、舞蹈、陪伴 |

## 许可

Apache-2.0
