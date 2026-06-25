<p align="center">
  <img src="./docs/static/qoobot-logo.svg" alt="QooBot" width="600">
</p>

<p align="center">
  <strong>开源、开放，为所有机器人而生。</strong>
</p>

<p align="center">
  <a href="https://github.com/qoobots/qoobot/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>
  <a href="https://github.com/qoobots/qoobot/stargazers"><img src="https://img.shields.io/github/stars/qoobots/qoobot?style=social" alt="Stars"></a>
  <a href="https://github.com/qoobots/qoobot/network/members"><img src="https://img.shields.io/github/forks/qoobots/qoobot?style=social" alt="Forks"></a>
  <a href="https://discord.gg/qoobot"><img src="https://img.shields.io/badge/community-discord-5865F2?logo=discord&amp;logoColor=white" alt="Discord"></a>
  <a href="https://github.com/qoobots/qoobot/discussions"><img src="https://img.shields.io/badge/discussions-welcome-181717?logo=github" alt="Discussions"></a>
</p>

<p align="center">
  <a href="./README_EN.md">English</a> |
  <a href="#-qoobot-是什么">概述</a> •
  <a href="#-架构全景">架构</a> •
  <a href="#-子项目">项目</a> •
  <a href="#-快速开始">快速开始</a> •
  <a href="#-路线图">路线图</a> •
  <a href="#-社区">社区</a> •
  <a href="#-许可证">许可证</a>
</p>

---

## 🤖 QooBot 是什么？

QooBot 是一个面向具身智能机器人的**开源全栈生态**。我们正在构建驱动下一代物理 AI 的通用操作系统——覆盖工业机械臂、人形机器人、仓储自动化、家用服务等一切形态。

> 一个大脑，任意身体，无处不在。

我们的使命是为机器人领域做开源操作系统为计算领域所做的事：**降低门槛、加速创新、构建全球社区**。

---

## 🧭 为什么选择 QooBot？

| 行业痛点 | QooBot 的方案 |
|-----------|----------------|
| 🧩 **碎片化** — 每台机器人运行私有软件，无法跨平台复用 | **统一大脑 OS** — 一套系统适配不同形态和厂商的机器人 |
| 🔒 **厂商锁定** — 封闭生态限制选择与创新 | **开放标准** — Apache 2.0 协议，社区驱动，自由 Fork |
| 🐌 **重复造轮子** — 每个团队从零实现感知、规划、控制 | **共享基础** — 感知/认知/运动等生产级模块开箱即用 |
| 🌍 **高门槛** — 机器人开发需要跨领域深度专业知识 | **开发者优先** — 丰富的 SDK、仿真器、调试器与全球技能市场 |
| ⚡ **端云割裂** — 缺少端侧+云端的统一智能栈 | **无缝伸缩** — 从芯片级推理到云端协同，一套架构 |

---

## 🏗 架构全景

<p align="center">
  <img src="./docs/static/architecture_zh.svg" alt="QooBot 架构全景" width="100%">
</p>

QooBot 分为**四层架构**，涵盖 **12 个子项目**：

### 🧬 核心层 — 机器人本体能力

直接运行于机器人端的项目：

| 项目 | 说明 |
|---------|-------------|
| **[qoobrain](./qoobrain/)** | **大脑操作系统** — 感知、认知、决策、运动规划、实时通信。机器人的中枢神经系统。 |
| **[qoocore](./qoocore/)** | **芯片与加速** — 端侧推理运行时、模型编译、NPU/GPU/DSP 硬件抽象。 |
| **[qoobody](./qoobody/)** | **硬件参考设计** — 传感器接口、执行器驱动、计算平台规范、机械与能源参考设计。 |

### 🔌 平台层 — 开发者与用户服务

连接机器人、开发者和用户的项目：

| 项目 | 说明 |
|---------|-------------|
| **[qooeco](./qooeco/)** | **技能市场** — 机器人技能的发现、发布与商业化，第三方算法集成与分发。 |
| **[qoocloud](./qoocloud/)** | **云端服务** — 远程推理、集群管理、OTA 升级、数据同步、多机器人编排。 |
| **[qoosvc](./qoosvc/)** | **系统服务** — 语音助手、空间理解、导航、多机器人互联、自诊断。 |

### 🛡️ 保障层 — 质量与信任

确保可靠性与合规性的项目：

| 项目 | 说明 |
|---------|-------------|
| **[qoocode](./qoocode/)** | **开发者工具链** — IDE 插件、机器人仿真器、行为调试器、性能剖析、数据标注工具。 |
| **[qooauth](./qooauth/)** | **账号与安全** — 统一的机器人/用户身份认证、授权、隐私框架。 |
| **[qooregs](./qooregs/)** | **法规合规** — 安全标准（ISO 10218、ISO 13482）、无线认证、出口管制、区域隐私法规。 |

### 🌍 生态层 — 产业与社区

构建全球机器人产业生态的项目：

| 项目 | 说明 |
|---------|-------------|
| **[qoogear](./qoogear/)** | **配件生态** — 第三方外设认证、末端执行器、可穿戴设备、配件通信标准。 |
| **[qoocommunity](./qoocommunity/)** | **全球社区** — 贡献者网络、年度开发者大会、高校合作、大使计划。 |
| **[qoochain](./qoochain/)** | **供应链** — 生产制造标准、出厂标定、质量检测、BOM 参考设计。 |

---

## 🚀 快速开始

### 环境要求

- **Python** ≥ 3.10
- **Node.js** ≥ 20
- **CUDA** ≥ 12.0（可选，用于 GPU 加速）

### 快速启动

```bash
# 克隆仓库
git clone https://github.com/qoobots/qoobot.git
cd qoobot/qoobrain

# 安装依赖
pip install -e ".[dev]"

# 启动大脑 OS
python -m brain_ai.launch

# 运行测试
pytest tests/ -v
```

### 编写你的第一个技能

```python
from qoobrain import Skill, Perception, Action

class PickAndPlace(Skill):
    """一个简单的抓取放置技能。"""

    def setup(self):
        self.perception = Perception(cameras=["front_rgbd"])
        self.action = Action(controller="arm_6dof")

    async def run(self, target: str):
        obj = await self.perception.detect(target)
        grasp = await self.action.plan_grasp(obj)
        await self.action.execute(grasp)
```

---

## 📊 项目状态

| # | 项目 | 状态 | 详情 |
|---|---------|--------|---------|
| 1 | **qoobrain** | 🟢 **Alpha** | Python 313/315 测试通过 · TS 15/21 |
| 2 | qoobody | 📋 设计中 | 硬件接口规范设计 |
| 3 | qoocore | 📋 设计中 | 推理运行时架构设计 |
| 4 | qooeco | 📋 设计中 | 技能市场设计 |
| 5 | qoocloud | 📋 设计中 | 云端架构设计 |
| 6 | qoosvc | 📋 设计中 | 系统服务设计 |
| 7 | qoocode | 📋 设计中 | 工具链设计 |
| 8 | qooauth | 📋 设计中 | 安全框架设计 |
| 9 | qoogear | 📋 设计中 | 配件认证体系设计 |
| 10 | qoocommunity | 📋 设计中 | 社区运营体系设计 |
| 11 | qoochain | 📋 设计中 | 供应链标准设计 |
| 12 | qooregs | 📋 设计中 | 合规框架设计 |

---

## 🗺 路线图

### 当前阶段（Alpha）
- [x] 大脑操作系统核心：感知、规划、决策引擎
- [x] HITL（人在回路）可视化面板
- [x] 语音交互基础
- [x] 多智能体通信协议
- [x] Python 与 TypeScript 测试套件
- [ ] 在 ≥ 3 个平台上完成真机部署

### 下一阶段（Beta）
- [ ] 仿真环境（Isaac Sim + MuJoCo 集成）
- [ ] Skill SDK v1.0 及开发者文档
- [ ] 云端推理与集群管理 Alpha
- [ ] 配件 HAL 接口规范 v1.0
- [ ] 社区治理模型（RFC 流程）

### 未来（v1.0）
- [ ] 全球技能市场上线
- [ ] 端侧推理编译器（qoocore）
- [ ] 安全与身份框架（qooauth）
- [ ] 多机器人协作框架
- [ ] 供应链参考实现
- [ ] 首届年度开发者大会

---

## 🌍 社区

QooBot 由全球机器人社区共同构建。

| 渠道 | 链接 |
|---------|------|
| 💬 **Discord** | [加入 Discord](https://discord.gg/qoobot) |
| 💡 **讨论区** | [GitHub Discussions](https://github.com/qoobots/qoobot/discussions) |
| 🐛 **问题反馈** | [提交 Issue](https://github.com/qoobots/qoobot/issues) |
| 📖 **文档** | [开发文档](https://docs.qoobot.dev)（即将上线） |
| 🎓 **学术合作** | 联系我们：`research@qoobot.dev` |

### 参与贡献

我们欢迎各种形式的贡献——代码、文档、硬件设计、研究和社区建设。

```bash
# Fork 并克隆
git clone https://github.com/YOUR_USERNAME/qoobot.git

# 创建分支
git checkout -b feat/your-feature

# 修改并测试
pytest tests/ -v

# 提交 PR
```

详见 [CONTRIBUTING.md](./CONTRIBUTING.md) 获取完整的贡献指南。

### 治理模型

QooBot 采用开放式治理模型。项目决策通过 RFC 流程和社区共识透明进行，维护者基于持续贡献价值提名产生。

---

## 🤝 合作伙伴

<p align="center">
  <em>我们正在积极构建合作伙伴网络。如果您的组织有意采用 QooBot 或参与联合开发，请联系 <a href="mailto:partners@qoobot.dev">partners@qoobot.dev</a>。</em>
</p>

---

## 📄 许可证

```
Copyright 2024-2026 The QooBot Authors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

本仓库所有子项目均采用 **[Apache License 2.0](./LICENSE)** 许可协议。

---

<p align="center">
  <sub>由全球机器人社区用 ❤️ 构建。一个大脑，任意身体，无处不在。</sub>
</p>
