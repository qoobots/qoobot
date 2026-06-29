# qooremote — API 设计文档

> 版本：v0.1 | 最后更新：2026-06-29 | 状态：Draft | 子项目：qooremote（远程遥控）
> API 类型：WebSocket (信令) · WebRTC (媒体/数据) · REST (管理)

---

## 1. API 总览

| API 层 | 协议 | 用途 |
|:-------|------|------|
| WebSocket 信令 | WSS + Protobuf/JSON | 会话建立、ICE 交换、控制信令 |
| WebRTC 媒体 | SRTP (DTLS加密) | 音视频流 |
| WebRTC DataChannel | SCTP (DTLS加密) | 操控指令、传感器数据 |
| REST API | HTTPS | 会话管理、录制管理、历史查询 |

---

## 2. WebSocket 信令协议

### 2.1 消息格式

```json
{
  "type": "message_type",
  "session_id": "sess_abc123",
  "timestamp": 1719650000000,
  "payload": { ... }
}
```

### 2.2 消息类型

| Type | 方向 | 描述 |
|:-----|:---:|------|
| `session.create` | C→S | 创建遥控会话 |
| `session.join` | C→S | 加入已有会话 |
| `session.leave` | C→S | 离开会话 |
| `session.terminate` | C→S | 终止会话 |
| `teleop.takeover` | C→S | 请求接管控制 |
| `teleop.release` | C→S | 释放控制 |
| `teleop.emergency_stop` | C→S | 紧急停止 |
| `webrtc.offer` | C→S / S→C | SDP Offer |
| `webrtc.answer` | C→S / S→C | SDP Answer |
| `webrtc.ice_candidate` | C→S / S→C | ICE Candidate |
| `robot.status` | R→C | 机器人状态推送 |
| `robot.sensor` | R→C | 传感器数据（通过DataChannel） |
| `heartbeat` | 双向 | 心跳 |

### 2.3 会话生命周期

```
Client                    Server                   Robot
  │                         │                        │
  │── session.create ──────▶│                        │
  │                         │── assign robot ──────▶│
  │◀── session.created ────│◀── robot.ready ────────│
  │                         │                        │
  │── webrtc.offer ───────▶│                        │
  │                         │── webrtc.offer ──────▶│
  │                         │◀── webrtc.answer ─────│
  │◀── webrtc.answer ──────│                        │
  │                         │                        │
  │◀══════ WebRTC P2P ═══════════════════════════▶│
  │                         │                        │
  │── teleop.takeover ────▶│                        │
  │                         │── teleop.takeover ───▶│
  │◀── teleop.takenover ───│◀── teleop.takenover ──│
  │                         │                        │
  │══ 操控指令 (DataChannel) ═════════════════════▶│
  │◀═ 视频/传感器 ════════════════════════════════│
```

---

## 3. REST API

### 3.1 会话管理

```
GET    /api/v1/sessions              — 会话列表
POST   /api/v1/sessions              — 创建会话
GET    /api/v1/sessions/{id}         — 会话详情
DELETE /api/v1/sessions/{id}         — 终止会话
POST   /api/v1/sessions/{id}/takeover — 请求接管
POST   /api/v1/sessions/{id}/release  — 释放控制
```

### 3.2 录制管理

```
GET    /api/v1/recordings            — 录制列表
GET    /api/v1/recordings/{id}       — 录制详情
POST   /api/v1/recordings/{id}/start — 开始录制
POST   /api/v1/recordings/{id}/stop  — 停止录制
GET    /api/v1/recordings/{id}/download — 下载录制文件
```

### 3.3 机器人列表

```
GET    /api/v1/robots                — 可用机器人列表
GET    /api/v1/robots/{id}/status    — 机器人实时状态
GET    /api/v1/robots/{id}/streams   — 可用视频流列表
```

---

## 4. WebRTC DataChannel 协议

### 4.1 控制指令通道 (reliable, ordered)

```json
{
  "type": "control",
  "seq": 12345,
  "timestamp_us": 1719650000123456,
  "commands": [
    {
      "joint": "arm_shoulder_pitch",
      "type": "position",
      "value": 0.45,
      "velocity_limit": 1.0,
      "torque_limit": 10.0
    }
  ]
}
```

### 4.2 传感器数据通道 (unreliable, unordered)

```json
{
  "type": "sensor",
  "timestamp_us": 1719650000123456,
  "joint_states": {
    "arm_shoulder_pitch": {"position": 0.45, "velocity": 0.1, "torque": 2.3},
    "arm_elbow": {"position": -1.2, "velocity": -0.05, "torque": 1.8}
  },
  "imu": {
    "accel": {"x": 0.01, "y": 0.02, "z": 9.81},
    "gyro": {"x": 0.001, "y": 0.002, "z": 0.0}
  }
}
```

---

## 5. 错误码

| 错误码 | 描述 |
|:-------|------|
| `REMOTE_OK` (0) | 成功 |
| `REMOTE_ERR_ROBOT_OFFLINE` (10001) | 机器人离线 |
| `REMOTE_ERR_SESSION_FULL` (10002) | 会话已满 |
| `REMOTE_ERR_TAKEOVER_DENIED` (10003) | 接管请求被拒绝 |
| `REMOTE_ERR_NO_PERMISSION` (10004) | 无权限 |
| `REMOTE_ERR_EMERGENCY_STOP` (10005) | 紧急停止状态 |
| `REMOTE_ERR_TIMEOUT` (10006) | 操作超时 |
| `REMOTE_ERR_WEBRTC_FAILED` (10007) | WebRTC 连接失败 |
