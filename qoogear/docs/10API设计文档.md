# qoogear — API 设计文档

> 版本：v0.1 | 最后更新：2026-06-29 | 状态：Draft | 子项目：qoogear（配件生态）
> API 类型：REST (认证平台) · C++/Python SDK (机器人端) · Protobuf (配件通信)

---

## 1. MFQ 认证平台 REST API

### 1.1 认证管理

```
POST   /api/v1/mfq/applications              — 提交认证申请
GET    /api/v1/mfq/applications              — 申请列表
GET    /api/v1/mfq/applications/{id}         — 申请详情
PUT    /api/v1/mfq/applications/{id}         — 更新申请
POST   /api/v1/mfq/applications/{id}/submit  — 提交审核
POST   /api/v1/mfq/applications/{id}/approve — 审核通过
POST   /api/v1/mfq/applications/{id}/reject  — 审核拒绝
```

### 1.2 配件数据库

```
GET    /api/v1/accessories                    — 认证配件列表
GET    /api/v1/accessories/{id}               — 配件详情
GET    /api/v1/accessories/search?q=gripper   — 搜索配件
GET    /api/v1/accessories/categories         — 配件分类
```

### 1.3 申请示例

```json
{
  "vendor": {
    "name": "GripTech Robotics",
    "website": "https://griptech.io",
    "contact_email": "cert@griptech.io"
  },
  "accessory": {
    "name": "QooGrip Pro",
    "type": "end_effector",
    "mfq_level": "premium",
    "capability_manifest": { "...": "..." },
    "self_test_report": "https://griptech.io/mfq_test_report.pdf",
    "technical_specs": "https://griptech.io/qoogrip_spec.pdf"
  }
}
```

---

## 2. 机器人端 SDK API

### 2.1 Python SDK

```python
from qoogear import AccessoryManager

# 获取配件管理器
manager = AccessoryManager()

# 获取所有已连接配件
accessories = manager.list_accessories()
# => [Gripper(name="QooGrip Pro", type="end_effector"), ...]

# 获取指定类型配件
gripper = manager.get_end_effector("gripper")
gripper.grasp(force=50, position=30)

sensor = manager.get_sensor("temperature")
reading = sensor.read()

# 监听配件事件
manager.on_accessory_connected(lambda a: print(f"配件已连接: {a.name}"))
manager.on_accessory_disconnected(lambda a: print(f"配件已断开: {a.name}"))
```

### 2.2 C++ SDK

```cpp
#include <qoogear/accessory_manager.h>

auto& manager = qoogear::AccessoryManager::instance();

// 获取末端执行器
auto gripper = manager.get_end_effector("gripper");
if (gripper) {
    gripper->grasp(50.0f, 30.0f);
}

// 配件能力查询
auto capabilities = manager.get_capabilities("camera_001");
for (auto& cap : capabilities) {
    std::cout << "能力: " << cap.name << std::endl;
}
```

---

## 3. 配件通信 Protobuf

### 3.1 通用消息格式

```protobuf
// 配件 ID
message AccessoryId {
  uint16 vendor_id = 1;
  uint16 product_id = 2;
  uint32 serial_number = 3;
}

// 能力宣告 (配件→本体)
message CapabilityAnnouncement {
  AccessoryId id = 1;
  string name = 2;
  AccessoryType type = 3;
  string mfq_cert_hash = 4;
  repeated Capability capabilities = 5;
}

// 状态上报 (配件→本体, 周期)
message StatusReport {
  AccessoryState state = 1;
  map<string, float> metrics = 2;
  repeated string active_errors = 3;
  uint32 uptime_seconds = 4;
}

// 控制指令 (本体→配件)
message ControlCommand {
  uint32 sequence_number = 1;
  oneof command {
    GripperCommand gripper = 10;
    MotorCommand motor = 11;
    SensorCommand sensor = 12;
  }
}
```

---

## 4. 错误码

| 错误码 | 描述 |
|:-------|------|
| `GEAR_OK` (0) | 成功 |
| `GEAR_ERR_NOT_FOUND` (1001) | 配件未找到 |
| `GEAR_ERR_NOT_COMPATIBLE` (1002) | 配件不兼容 |
| `GEAR_ERR_CERT_INVALID` (1003) | MFQ 证书无效 |
| `GEAR_ERR_COMM_FAILURE` (1004) | 配件通信故障 |
| `GEAR_ERR_DRIVER_LOAD_FAILED` (1005) | 驱动加载失败 |
| `GEAR_ERR_SAFETY_TRIP` (1006) | 安全保护触发 |
