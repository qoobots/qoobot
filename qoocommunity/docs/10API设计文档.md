# qoocommunity — API 设计文档

> 版本：v0.1 | 最后更新：2026-06-29 | 状态：Draft | 子项目：qoocommunity（开源社区）

---

## 1. 社区 API

### 1.1 贡献者 API

```
GET    /api/v1/contributors                      — 贡献者列表
GET    /api/v1/contributors/{github_id}           — 贡献者详情
GET    /api/v1/contributors/{github_id}/stats     — 贡献统计
GET    /api/v1/contributors/wall                 — 贡献者墙
POST   /api/v1/contributors/cla/sign             — 签署 CLA
GET    /api/v1/contributors/cla/status           — CLA 签署状态
```

### 1.2 贡献者详情

```json
{
  "github_id": "dev_zhang",
  "display_name": "Zhang Wei",
  "avatar_url": "https://avatars.githubusercontent.com/u/12345",
  "level": "maintainer",
  "joined_at": "2026-03-15",
  "cla_signed": true,
  "stats": {
    "total_prs": 47,
    "merged_prs": 42,
    "issues_created": 15,
    "forum_posts": 128,
    "reviews": 89
  },
  "badges": ["first_pr", "bug_hunter", "doc_writer", "core_contributor"],
  "repos": ["qoobrain", "qoosvc"]
}
```

---

## 2. 活动 API

```
GET    /api/v1/events                            — 活动列表
GET    /api/v1/events/{id}                       — 活动详情
POST   /api/v1/events/{id}/register              — 活动报名
POST   /api/v1/events/{id}/cfp                   — 提交演讲提案 (CFP)
GET    /api/v1/events/{id}/schedule              — 活动日程
GET    /api/v1/events/{id}/recordings            — 活动回放
```

---

## 3. RFC API

```
GET    /api/v1/rfcs                              — RFC 列表
GET    /api/v1/rfcs/{id}                         — RFC 详情
POST   /api/v1/rfcs                              — 创建 RFC
POST   /api/v1/rfcs/{id}/vote                    — 投票
GET    /api/v1/rfcs/{id}/votes                   — 投票结果
```

---

## 4. GitHub Webhook 集成

### 4.1 Webhook 事件处理

```
POST /api/v1/webhooks/github
X-Hub-Signature-256: sha256=xxx

Events:
  · issues: 新 Issue → 自动标签 + 欢迎回复
  · pull_request: 新 PR → CLA 检查 + CI 触发
  · pull_request_review: Review 提交 → 更新贡献统计
  · push: 代码推送 → 文档自动构建
  · release: 发布 → 通知社区
```

### 4.2 社区机器人命令

```
GitHub Issue/PR 评论中的机器人命令:
  /assign @user        — 分配任务
  /label bug           — 添加标签
  /cc @maintainer      — 通知维护者
  /help                — 显示帮助
```

---

## 5. 文档搜索 API

```
GET  /api/v1/docs/search?q=camera+calibration&version=latest&lang=zh

Response:
{
  "results": [
    {
      "title": "相机标定指南",
      "url": "/latest/dev-guide/camera-calibration/",
      "snippet": "本文介绍如何使用 qoobrain SDK 进行相机标定...",
      "version": "v2.1",
      "language": "zh"
    }
  ],
  "total": 23,
  "took_ms": 45
}
```

---

## 6. 错误码

| 错误码 | 描述 |
|:-------|------|
| `COMM_OK` (0) | 成功 |
| `COMM_ERR_NOT_FOUND` (10001) | 资源不存在 |
| `COMM_ERR_CLA_REQUIRED` (10002) | 需要签署 CLA |
| `COMM_ERR_DUPLICATE` (10003) | 重复操作 |
| `COMM_ERR_FORBIDDEN` (10004) | 权限不足 |
| `COMM_ERR_RFC_CLOSED` (10005) | RFC 已关闭 |
| `COMM_ERR_EVENT_FULL` (10006) | 活动报名已满 |
| `COMM_ERR_UNAUTHORIZED` (10007) | 未登录 |
