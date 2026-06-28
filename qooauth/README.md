# QooAuth — 统一身份基础设施

> 版本：v0.2 | 状态：设计阶段 → 开发推进中
> 对标：Apple ID / Google Account

## 定位

QooAuth 是 QooBot 的统一身份基础设施，为所有云端/设备端/用户端服务提供认证、授权、加密能力。

## 技术栈

- **语言**：Java 17
- **框架**：Spring Boot 3.2 + Spring Cloud 2023.x + Spring Authorization Server 1.3
- **数据库**：PostgreSQL 16 + Redis 7.2
- **密码学**：Argon2id / Ed25519 / ECDSA P-256 / TLS 1.3
- **构建**：Maven 多模块

## 模块结构

| 模块 | 说明 |
|------|------|
| qooauth-common | 公共常量、枚举、异常、DTO、工具类 |
| qooauth-auth | 认证服务（注册/登录/MFA/OAuth2/OIDC/JWT/会话） |
| qooauth-user | 用户服务（资料管理/账户恢复/家庭共享） |
| qooauth-device | 设备身份服务（X.509证书/激活/绑定/Find My） |
| qooauth-security | 安全与威胁防护（异常检测/撞库防护/E2EE） |
| qooauth-audit | 审计与合规（操作审计/合规报告） |
| qooauth-api-key | API Key 管理 |
| qooauth-robot-trust | 机器人间信任（mTLS/协作授权） |
| qooauth-developer | 开发者认证（开发者证书/技能签名） |
| qooauth-gateway | API 网关 |

## 快速开始

### 环境要求

- JDK 17+
- Maven 3.9+
- PostgreSQL 16
- Redis 7.2

### 本地开发

```bash
# 启动依赖服务
docker-compose -f docker/docker-compose.yml up -d postgres redis

# 编译项目
mvn clean install -DskipTests

# 启动认证服务
cd qooauth-auth
mvn spring-boot:run -Dspring-boot.run.profiles=dev

# 启动用户服务
cd qooauth-user
mvn spring-boot:run -Dspring-boot.run.profiles=dev
```

### API 示例

```bash
# 注册
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"SecureP@ss123","nickname":"RobotMaster","acceptTos":true}'

# 登录
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"SecureP@ss123"}'

# 获取 OIDC Discovery
curl http://localhost:8080/.well-known/openid-configuration
```

## 设计文档

- [01 功能清单完成进度](docs/01功能清单完成进度.md)
- [02 架构设计](docs/02架构设计.md)
- [03 交互设计](docs/03交互设计.md)
- [04 数据设计](docs/04数据设计.md)
- [05 项目目录结构](docs/05项目目录结构.md)
