# qoocompliance 合规知识库

> 版本：v0.4 | 状态：Stable

法规解读、最佳实践、案例库持续积累的知识库。知识以 YAML 格式存储，便于程序解析和人工阅读。

## 目录结构

```
knowledge/
├── README.md              # 本文件
├── safety/                # 机器人安全标准知识库
│   ├── iso_13482.yaml     # ISO 13482 个人护理机器人安全要求
│   ├── iso_10218.yaml     # ISO 10218 工业机器人安全要求
│   ├── iso_13849.yaml     # ISO 13849 控制系统安全相关部件
│   └── iec_61508.yaml     # IEC 61508 功能安全
├── wireless/              # 无线与电磁兼容知识库
│   ├── fcc.yaml           # FCC 认证
│   ├── ce_red.yaml        # CE RED 指令
│   └── emc.yaml           # EMC 测试标准
├── privacy/               # 隐私与数据保护知识库
│   ├── gdpr.yaml          # GDPR 合规框架
│   ├── ccpa.yaml          # CCPA/CPRA 合规
│   └── pipl.yaml          # PIPL 合规
├── ai_ethics/             # AI 伦理与合规知识库
│   ├── eu_ai_act.yaml     # EU AI Act 合规
│   └── transparency.yaml  # 算法透明度要求
├── consumer/              # 消费者安全知识库
│   ├── ce_md.yaml         # CE 机械指令
│   └── ul_standards.yaml  # UL 安全认证
├── export/                # 出口管制与贸易知识库
│   ├── eccn.yaml          # ECCN 分类
│   └── sanctions.yaml     # 制裁合规
└── environmental/         # 环保与可持续知识库
    ├── rohs.yaml          # RoHS 合规
    └── reach.yaml         # REACH 合规
```

## 知识库条目格式 (YAML)

```yaml
regulation:
  id: "CN-SAF-001"
  title: "服务机器人安全要求"
  market: "CN"
  category: "ROBOT_SAFETY"
  authority: "国家标准化管理委员会"
  effective_date: "2024-01-01"
  summary: "中国服务机器人安全国家标准..."
  requirements:
    - id: "REQ-001"
      description: "紧急停止功能"
      priority: "P0"
      verification: "功能测试 + 文档审查"
    - id: "REQ-002"
      description: "安全防护等级"
      priority: "P0"
      verification: "型式试验"
  references:
    - "GB/T 39785-2021"
    - "GB 11291.1-2011"
```

## 使用方式

知识库内容供 qoocompliance 各 Service 在合规评估时引用，提供法规原文摘要、检查项映射和验证方法建议。
