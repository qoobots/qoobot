# qoocompliance — API 设计文档

> 版本：v0.1 | 最后更新：2026-06-29 | 状态：Draft | 子项目：qoocompliance（法规合规）

---

## 1. API 设计原则

- RESTful 风格，JSON 格式
- 所有 API 需通过 qooauth 认证
- 分页接口统一使用 `page`/`size` 参数
- 审计操作记录在响应头 `X-Audit-Id`

---

## 2. 检查清单 API

### 2.1 生成检查清单

```
POST /api/v1/checklists/generate
Content-Type: application/json

Request:
{
  "markets": ["EU", "US"],
  "product_type": "personal_service_robot",
  "subprojects": ["qoobody", "qoobrain", "qoosvc", "qoocloud"]
}

Response:
{
  "checklist_id": "CL-2026-0001",
  "total_items": 105,
  "items_by_subproject": {
    "qoobody": 42,
    "qoobrain": 18,
    "qoosvc": 8,
    "qoocloud": 37
  },
  "generated_at": "2026-06-29T10:00:00Z"
}
```

### 2.2 获取检查清单

```
GET /api/v1/checklists/CL-2026-0001?page=1&size=20&filter[status]=pending

Response:
{
  "data": [
    {
      "id": "CL-EU-MD-001",
      "regulation": "2006/42/EC",
      "clause": "Annex I - 1.1.2",
      "title": "安全集成原则",
      "market": "EU",
      "subproject": "qoobody",
      "priority": "P0",
      "status": "pending",
      "assignee": null,
      "due_date": "2026-09-30"
    }
  ],
  "total": 45,
  "page": 1,
  "size": 20
}
```

### 2.3 更新检查项

```
PUT /api/v1/checklists/CL-2026-0001/items/CL-EU-MD-001

Request:
{
  "status": "passed",
  "evidence": ["safety_review_v3.pdf", "test_report_20260629.pdf"],
  "comment": "通过安全集成设计审查，FMEA 无高风险项"
}
```

---

## 3. 法规管理 API

### 3.1 获取法规列表

```
GET /api/v1/regulations?market=EU&category=safety&page=1&size=20

Response:
{
  "data": [
    {
      "id": "REG-EU-001",
      "name": "2006/42/EC Machinery Directive",
      "jurisdiction": "EU",
      "category": "safety",
      "effective_date": "2009-12-29",
      "last_amended": "2023-06-14",
      "status": "active",
      "impacted_subprojects": ["qoobody"],
      "checklist_count": 38
    }
  ]
}
```

### 3.2 法规变更监控

```
GET /api/v1/regulations/changes?since=2026-01-01

Response:
{
  "changes": [
    {
      "id": "CHG-2026-0042",
      "regulation_id": "REG-EU-005",
      "regulation_name": "EU AI Act",
      "change_type": "new_article",
      "summary": "新增高风险 AI 系统透明度要求",
      "impacted_subprojects": ["qoobrain"],
      "severity": "high",
      "detected_at": "2026-05-15",
      "action_required": "review_within_30_days"
    }
  ]
}
```

---

## 4. 文档生成 API

### 4.1 生成合规文档

```
POST /api/v1/documents/generate
Content-Type: application/json

Request:
{
  "template_id": "TPL-DoC-EU",
  "checklist_id": "CL-2026-0001",
  "format": "pdf",
  "data": {
    "manufacturer": "QooBot Inc.",
    "product_name": "QooBot S",
    "model_number": "QS-2026-001",
    "standards": ["ISO 13482:2014", "EN 55032:2015"]
  }
}

Response:
{
  "document_id": "DOC-2026-0150",
  "status": "generated",
  "download_url": "/api/v1/documents/DOC-2026-0150/download",
  "generated_at": "2026-06-29T10:05:00Z"
}
```

### 4.2 下载文档

```
GET /api/v1/documents/{documentId}/download
Response: binary PDF/DOCX stream
```

---

## 5. 认证进度 API

### 5.1 获取认证总览

```
GET /api/v1/certifications/progress?market=EU

Response:
{
  "market": "EU",
  "overall_progress": 72.5,
  "mandatory_certs": [
    {
      "name": "CE Marking",
      "progress": 85,
      "blockers": [],
      "estimated_completion": "2026-09-15"
    },
    {
      "name": "RED (Radio Equipment Directive)",
      "progress": 60,
      "blockers": ["EMC测试排期中"],
      "estimated_completion": "2026-10-30"
    }
  ],
  "total_checklist_items": 105,
  "passed": 58,
  "failed": 2,
  "in_progress": 12,
  "pending": 33
}
```

---

## 6. 错误码

| 错误码 | HTTP | 描述 |
|:-------|:----:|------|
| `CMPL_OK` (0) | 200 | 成功 |
| `CMPL_ERR_NOT_FOUND` (4001) | 404 | 法规/清单/文档不存在 |
| `CMPL_ERR_INVALID_MARKET` (4002) | 400 | 不支持的市场 |
| `CMPL_ERR_TEMPLATE_ERROR` (4003) | 500 | 模板生成失败 |
| `CMPL_ERR_UNAUTHORIZED` (4004) | 403 | 无权访问 |
| `CMPL_ERR_LOCKED` (4005) | 423 | 清单已被锁定(审核中) |
