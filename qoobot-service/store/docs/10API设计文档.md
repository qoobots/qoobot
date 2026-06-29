# qoostore — API 设计文档

> 版本：v0.1 | 最后更新：2026-06-29 | 状态：Draft | 子项目：qoostore（技能市场）

---

## 1. REST API 总览

### 1.1 技能浏览与搜索

```
GET    /api/v1/skills                  — 技能列表 (分页/筛选/排序)
GET    /api/v1/skills/{id}             — 技能详情
GET    /api/v1/skills/search           — 技能搜索 (?q=cooking&lang=zh)
GET    /api/v1/skills/recommended      — 个性化推荐
GET    /api/v1/skills/featured         — 编辑精选
GET    /api/v1/skills/{id}/reviews     — 技能评价列表
GET    /api/v1/skills/{id}/versions    — 版本历史
GET    /api/v1/categories              — 分类列表
GET    /api/v1/categories/{id}/skills  — 分类下技能
```

### 1.2 用户端操作

```
POST   /api/v1/user/skills/{id}/install      — 安装技能
POST   /api/v1/user/skills/{id}/uninstall    — 卸载技能
GET    /api/v1/user/skills                    — 我的技能列表
PUT    /api/v1/user/skills/{id}/settings     — 更新技能配置
POST   /api/v1/user/skills/{id}/reviews      — 提交评价
POST   /api/v1/user/skills/{id}/report       — 举报技能
GET    /api/v1/user/wishlist                  — 愿望清单
POST   /api/v1/user/wishlist/{skillId}       — 加入愿望清单
```

### 1.3 开发者 API

```
POST   /api/v1/developer/skills               — 上传技能
PUT    /api/v1/developer/skills/{id}          — 更新技能信息
POST   /api/v1/developer/skills/{id}/versions — 上传新版本
GET    /api/v1/developer/skills               — 我的技能列表
GET    /api/v1/developer/analytics            — 数据分析面板
GET    /api/v1/developer/earnings             — 收入明细
POST   /api/v1/developer/skills/{id}/withdraw — 提现申请
```

### 1.4 审核管理

```
GET    /api/v1/admin/reviews/pending          — 待审核列表
POST   /api/v1/admin/reviews/{id}/approve     — 审核通过
POST   /api/v1/admin/reviews/{id}/reject      — 审核拒绝(含原因)
POST   /api/v1/admin/skills/{id}/suspend      — 下架技能
POST   /api/v1/admin/reports/{id}/resolve     — 处理举报
```

---

## 2. 技能上传请求示例

```
POST /api/v1/developer/skills
Content-Type: multipart/form-data

Fields:
  manifest: (JSON)
  {
    "name": "智能清洁助手",
    "description": "AI驱动的全屋清扫技能",
    "category": "household",
    "version": "1.0.0",
    "permissions": ["navigation.move", "spatial.read_map"],
    "price_model": { "type": "one_time", "amount": 9.99, "currency": "CNY" },
    "min_robot_version": "2.0.0",
    "supported_models": ["QS", "QL", "QP"]
  }
  package: (binary .qooskill file)

Response:
{
  "skill_id": "skill_abc123",
  "review_id": "review_xyz789",
  "status": "pending_review",
  "estimated_review_time": "24h"
}
```

---

## 3. 端侧安装 API (gRPC)

```protobuf
service EdgeStoreService {
  // 安装技能
  rpc Install(InstallRequest) returns (InstallResponse);
  
  // 卸载技能
  rpc Uninstall(UninstallRequest) returns (Status);
  
  // 列出已安装技能
  rpc ListInstalled(Empty) returns (SkillList);
  
  // 检查更新
  rpc CheckUpdates(Empty) returns (UpdateList);
  
  // 获取技能状态
  rpc GetSkillStatus(SkillId) returns (SkillStatus);
  
  // 更新技能权限
  rpc UpdatePermissions(PermissionUpdate) returns (Status);
}
```

---

## 4. 错误码

| 错误码 | 描述 |
|:-------|------|
| `STORE_OK` (0) | 成功 |
| `STORE_ERR_SKILL_NOT_FOUND` (2001) | 技能不存在 |
| `STORE_ERR_INSUFFICIENT_BALANCE` (2002) | 余额不足 |
| `STORE_ERR_ALREADY_INSTALLED` (2003) | 已安装 |
| `STORE_ERR_INCOMPATIBLE` (2004) | 机型不兼容 |
| `STORE_ERR_REVIEW_REJECTED` (2005) | 审核未通过 |
| `STORE_ERR_SIGNATURE_INVALID` (2006) | 签名验证失败 |
| `STORE_ERR_SANDBOX_FAILED` (2007) | 沙箱创建失败 |
| `STORE_ERR_PERMISSION_DENIED` (2008) | 用户拒绝权限 |

---

## 5. 支付回调

```
POST /api/v1/payment/callback
Content-Type: application/json
X-Signature: sha256=xxx  (支付平台签名)

Request:
{
  "order_id": "ord_20260629001",
  "transaction_id": "wx_20260629001",
  "status": "success",
  "amount": 9.99,
  "paid_at": "2026-06-29T10:30:00Z"
}

Response:
{ "code": 0, "message": "success" }
```
