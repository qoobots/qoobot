# qoocompliance — 仿生人法规与合规

> 机器人的"全球准入 + FCC/CE + 隐私法规"：
> 安全标准、无线认证、隐私合规、出口管制、责任保险框架。

## 定位

qoocompliance 是 QooBot 生态的法规与合规基础设施，确保机器人在全球各市场
合法合规运行，覆盖安全、无线、隐私、责任等关键法规领域。

## 模块

| 模块 | Package | 说明 | 状态 |
|------|---------|------|------|
| `safety/` | `com.qoobot.qoocompliance.safety` | 机器人安全标准（ISO 13482/10218/13849/SIL/HAZOP/FMEA/协作/移动） | ✅ v0.4 |
| `wireless/` | `com.qoobot.qoocompliance.wireless` | 无线与电磁兼容（FCC/CE RED/SRRC/MIC/EMC/共存） | ✅ v0.4 |
| `privacy/` | `com.qoobot.qoocompliance.privacy` | 隐私与数据保护（GDPR/CCPA/PIPL/DPIA/传感器/跨境） | ✅ v0.4 |
| `aiethics/` | `com.qoobot.qoocompliance.aiethics` | AI 伦理与合规（EU AI Act/透明度/偏见/伦理审查） | ✅ v0.4 |
| `consumer/` | `com.qoobot.qoocompliance.consumer` | 消费者安全（CE 机械指令/LVD/UL/儿童/产品责任） | ✅ v0.4 |
| `trade/` | `com.qoobot.qoocompliance.trade` | 出口管制（ECCN/加密/实体清单/制裁） | ✅ v0.4 |
| `environmental/` | `com.qoobot.qoocompliance.environmental` | 环保与可持续（RoHS/WEEE/REACH/碳足迹/能效） | ✅ v0.4 |
| `checklist/` | `com.qoobot.qoocompliance.checklist` | 合规检查清单引擎 + REST API | ✅ v0.4 |
| `monitor/` | `com.qoobot.qoocompliance.monitor` | 法规变更监控 + REST API | ✅ v0.4 |
| `management/` | `com.qoobot.qoocompliance.management` | 合规管理（文档模板/认证进度/审查记录） | ✅ v0.4 |
| `domain/` | `com.qoobot.qoocompliance.domain` | JPA 实体层（7个 Entity） | ✅ v0.4 |
| `repository/` | `com.qoobot.qoocompliance.repository` | Spring Data JPA 仓库（7个 Repository） | ✅ v0.4 |

## 全球市场准入路线图

```
          ┌──────────────────────────────────────────┐
          │         QooBot 全球市场准入               │
          │                                          │
  中国 ───┤ SRRC(无线) + CCC(安全) + 机器人CR认证      │
          │ + PIPL(隐私) + 出口管制法                  │
          │                                          │
  欧盟 ───┤ CE(RED/EMC/MD) + GDPR + AI Act           │
          │ + ISO 10218(协作机器人)                    │
          │                                          │
  美国 ───┤ FCC(无线) + UL(安全) + FDA(医疗场景)       │
          │ + CCPA(加州隐私) + EAR(出口管制)            │
          │                                          │
  日本 ───┤ MIC(无线) + PSE(安全) + 机器人安全准则      │
          │                                          │
  韩国 ───┤ KC(无线/安全) + 智能机器人法                │
          └──────────────────────────────────────────┘
```

## 关键安全标准

| 标准 | 范围 | 核心要求 |
|------|------|----------|
| ISO 10218-1/2 | 工业机器人 | 安全设计、防护措施 |
| ISO/TS 15066 | 协作机器人 | 力/功率限制、碰撞阈值 |
| ISO 13482 | 服务机器人 | 个人护理机器人安全 |
| IEC 61508 | 功能安全 | SIL 等级、安全生命周期 |
| ISO 13849 | 机械安全 | PL 等级、冗余架构 |
| IEC 62443 | 工业网络安全 | 纵深防御、安全等级 |

## AI 合规（AI Act 等）

| 风险等级 | 场景 | 要求 |
|----------|------|------|
| 不可接受 | 社会评分、实时生物识别 | 禁止 |
| 高风险 | 手术机器人、工业协作 | 合规评估 + 人类监督 + 透明度 |
| 有限风险 | 客服机器人 | 透明度告知 |
| 最小风险 | 游戏机器人 | 无额外要求 |

## 技术栈

| 组件 | 技术 | 状态 |
|------|------|------|
| 语言 | Java 17 | ✅ v0.4 |
| 框架 | Spring Boot 3.4 | ✅ v0.4 |
| 构建 | Maven（父 POM: qoobot-cloud:0.2.0-SNAPSHOT） | ✅ v0.4 |
| 存储 | Spring Data JPA + Hibernate + PostgreSQL | ✅ v0.4 |
| 数据库迁移 | Flyway（V1 建表 + V2 补字段 + V3 种子数据） | ✅ v0.4 |
| API 文档 | springdoc-openapi (Swagger UI) | ✅ v0.4 |
| 监控 | Spring Boot Actuator | ✅ v0.4 |
| 测试 | JUnit 5 + Mockito + Spring Boot Test | 🔲 规划中 |

## API 端点

启动后访问 Swagger UI: http://localhost:8086/swagger-ui.html

- **合规检查清单**: `POST/GET/PUT /api/v1/compliance/*`（6 核心端点 + 8 域约 45 端点）
- **法规监控**: `GET /api/v1/regulations/*`（3 端点）
- 详见 [docs/10API设计文档.md](docs/10API设计文档.md)

## 数据库

v0.4 已启用 PostgreSQL + Flyway 迁移，包含以下 7 张表：
- `compliance_regulation` — 法规数据
- `compliance_checklist` — 检查清单
- `compliance_item` — 检查项
- `certification_progress` — 认证进度
- `compliance_review` — 审查记录
- `regulation_change` — 法规变更
- `audit_record` — 审计记录

Flyway 迁移脚本：`src/main/resources/db/migration/`（V1 建表 + V2 补字段 + V3 种子数据）

## iPhone 类比

| Apple 合规 | qoocompliance 对应 |
|-----------|-------------|
| FCC 认证 | wireless（各国无线认证） |
| CE 标志 | wireless + safety + consumer |
| 隐私标签 | privacy |
| 环保报告 | environmental |
| 出口合规 | trade |

## 与 qoobrain 的关系

```
qoocompliance ──合规要求──→ qoobrain (大脑OS)
    │                      │
    ├── 安全边界注入         ├── 安全决策约束
    ├── 隐私数据处理规范     ├── 数据最小化策略
    ├── 审计日志要求         ├── qooauth 审计模块
    └── 出口合规检查         └── 模型/算法分发限制
```

## 许可

Apache-2.0
