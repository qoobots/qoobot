# qoocommunity — 人形机器人品牌与社区

> 机器人的"WWDC + 开发者关系 + Today at Apple"：
> 年度开发者大会、开发者计划、技术社区、高校合作、内容生态。

## 定位

qoocommunity 是 QooBot 生态的品牌与社区平台，通过开发者大会、培训认证、
社区运营和高校合作，构建全球人形机器人开发者生态。

## 模块

| 模块 | 说明 | 状态 |
|------|------|------|
| `qoocommunity-cloud/` | ☁️ 后端微服务（Spring Boot 3.2 + PostgreSQL） | 🚧 开发中 |
| `qoocommunity-web/` | 🌐 Web 前端（Vue 3 + Element Plus + Vite） | 🚧 开发中 |
| `qoocommunity-mobile/` | 📱 移动 App（UniApp + Vue 3） | 🔲 规划中 |
| `qoocommunity-miniapp/` | 📲 微信小程序 | 🔲 规划中 |
| `qoocommunity-docs/` | 📚 文档站点（VitePress） | 🔲 规划中 |

### 云微服务模块

| 微服务 | 端口 | 说明 | 状态 |
|--------|:----:|------|:----:|
| `qoocommunity-gateway` | 8300 | API 网关（Spring Cloud Gateway） | 🚧 开发中 |
| `qoocommunity-forum` | 8310 | 论坛服务 | 🚧 开发中 |
| `qoocommunity-qa` | 8310 | 问答服务 | 🚧 开发中 |
| `qoocommunity-academy` | 8311 | 学院服务 | 🚧 开发中 |
| `qoocommunity-event` | 8312 | 活动服务 | 🚧 开发中 |
| `qoocommunity-contributor` | — | 贡献者服务 | 🚧 开发中 |
| `qoocommunity-governance` | — | 治理服务 | 🚧 开发中 |
| `qoocommunity-content` | — | 内容服务 | 🚧 开发中 |

## 开发者成长路径

```
           ┌─────────────────────────────────────────┐
           │          QooBot 开发者成长体系            │
           │                                         │
  入门 ───►│ qoocommunity Academy 在线课程             │
           │         │                               │
  实践 ───►│ qoodev 仿真环境 + 示例项目                │
           │         │                               │
  认证 ───►│ QooBot Certified Developer 认证考试       │
           │         │                               │
  发布 ───►│ qoostore 技能市场上架                       │
           │         │                               │
  专家 ───►│ qoocommunity 技术布道 / 大会演讲           │
           │                                         │
           └─────────────────────────────────────────┘
```

## 年度开发者大会

| 环节 | 内容 |
|------|------|
| Keynote | 年度技术路线图发布 |
| Sessions | 技术深度分享（感知、规划、控制、仿真） |
| Labs | 动手实验（端到端机器人开发） |
| Expo | 合作伙伴与初创公司展示 |
| Awards | 年度最佳技能/应用/论文颁奖 |
| Networking | 开发者社交晚宴 |

## iPhone 类比

| Apple 社区 | qoocommunity 对应 |
|------------|------------------|
| WWDC | conference（年度大会） |
| Apple Developer Program | dev_program |
| Apple Developer Forums | forums |
| Today at Apple | academy + workshop |
| Swift Student Challenge | hackathon + university |
| App Store 精选 | showcase |

## 与 qoobrain 的关系

```
qoocommunity ──培养──→ 开发者
     │                    │
     │                    ├── 学习 qoobrain SDK
     │                    ├── 使用 qoodev 工具链
     │                    └── 发布到 qoostore 市场
     │
     └── 反哺 qoobrain 生态（案例、反馈、贡献）
```

## 许可

Apache-2.0
