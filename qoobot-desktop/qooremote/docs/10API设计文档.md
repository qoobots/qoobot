# 10 — API 设计文档

> 版本：v0.1.0 | 最后更新：2026-06-30 | 状态：Draft
> 子项目：qooremote（远程机器人监控遥控工具）

---

## 1. API 总览

qooremote 涉及三套 API：

| API | 协议 | 使用者 | 用途 |
|-----|------|--------|------|
| qoocloud Signaling API | WebSocket (JSON) | console / web / mobile | 认证/信令/机器人列表/会话管理 |
| WebRTC DataChannel API | SCTP (JSON) | console / web | 机器人状态订阅/控制指令/告警 |
| Python Core API | Python import | console (内部) | 桌面端内部模块间调用 |

---

## 2. qoocloud Signaling API

### 2.1 连接与认证

```
连接地址: wss://<cloud-host>/signaling

认证方式: JWT Bearer Token (连接时通过 URL 参数或首条消息传递)
```

**连接请求**：

```json
// 客户端 → 服务器 (首条消息)
{
  "type": "auth",
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "client_type": "console",
  "client_version": "0.1.0",
  "capabilities": ["video", "audio", "teleop", "recording"]
}
```

**认证响应**：

```json
// 服务器 → 客户端
{
  "type": "auth_ok",
  "session_id": "sess-abc123",
  "operator_id": "op-42",
  "roles": ["operator"],
  "server_time": 1719700000000
}
```

**认证失败**：

```json
{
  "type": "auth_error",
  "code": 401,
  "message": "Invalid or expired token"
}
```

### 2.2 机器人发现

```json
// 客户端 → 服务器
{
  "type": "list_robots",
  "request_id": "req-001"
}

// 服务器 → 客户端
{
  "type": "robots_list",
  "request_id": "req-001",
  "robots": [
    {
      "robot_id": "qoobot-01",
      "name": "家庭管家 01",
      "status": "online",
      "mode": "autonomous",
      "battery_percent": 67,
      "task": "巡检中",
      "last_seen": 1719700000000
    },
    {
      "robot_id": "qoobot-02",
      "name": "工厂巡检 02",
      "status": "offline",
      "last_seen": 1719680000000
    }
  ]
}
```

### 2.3 会话建立

```json
// 客户端 → 服务器 (请求建立遥控会话)
{
  "type": "session_request",
  "request_id": "req-002",
  "robot_id": "qoobot-01",
  "mode": "monitor",           // monitor | control | teach
  "offer": {
    "type": "offer",
    "sdp": "v=0\r\no=- ..."
  }
}

// 服务器 → 客户端
{
  "type": "session_accepted",
  "request_id": "req-002",
  "session_id": "sess-xyz789",
  "robot_id": "qoobot-01",
  "answer": {
    "type": "answer",
    "sdp": "v=0\r\no=- ..."
  },
  "ice_servers": [
    {"urls": ["stun:stun.qoobot.dev:3478"]},
    {
      "urls": ["turn:turn.qoobot.dev:3478?transport=udp"],
      "username": "user",
      "credential": "pass"
    }
  ]
}

// 拒绝
{
  "type": "session_rejected",
  "request_id": "req-002",
  "reason": "robot_busy",
  "message": "机器人当前正在被其他操作员控制"
}
```

### 2.4 ICE 候选交换

```json
// 客户端 → 服务器
{
  "type": "ice_candidate",
  "session_id": "sess-xyz789",
  "candidate": {
    "candidate": "candidate:1 1 UDP 2130706431 192.168.1.100 54321 typ host",
    "sdpMid": "0",
    "sdpMLineIndex": 0
  }
}
```

### 2.5 会话控制

```json
// 结束会话
{
  "type": "session_end",
  "session_id": "sess-xyz789",
  "reason": "operator_disconnect"
}

// 会话事件（服务器推送）
{
  "type": "session_event",
  "session_id": "sess-xyz789",
  "event": "robot_disconnected",
  "message": "机器人端连接中断",
  "timestamp": 1719700100000
}
```

---

## 3. DataChannel 控制协议

### 3.1 通道定义

WebRTC 建立后创建三条 DataChannel：

| 通道名 | 方向 | 可靠性 | 用途 |
|--------|------|:------:|------|
| `state` | Robot → Operator | 不可靠(部分) | 机器人状态上报（30Hz 高频快照） |
| `command` | Operator → Robot | 可靠 | 控制指令 |
| `alert` | Robot → Operator | 可靠 | 告警通知 |

### 3.2 控制指令格式

```json
// 通道: command (Operator → Robot)

// 末端位姿控制
{
  "type": "teleop.pose",
  "seq": 12345,
  "timestamp": 1719700000100,
  "frame": "left_hand",
  "pose": {
    "position": {"x": 0.5, "y": 0.2, "z": 0.8},
    "orientation": {"roll": 0.0, "pitch": 1.57, "yaw": 0.0}
  },
  "max_velocity": 0.5,
  "max_acceleration": 1.0,
  "gripper": "close",
  "hmac": "sha256:..."
}

// 关节控制
{
  "type": "teleop.joint",
  "seq": 12346,
  "timestamp": 1719700000120,
  "mode": "position",
  "targets": [
    {"id": 0, "position": 0.523, "max_velocity": 2.0, "max_torque": 50.0}
  ],
  "hmac": "sha256:..."
}

// 模式切换
{
  "type": "mode.switch",
  "seq": 12347,
  "timestamp": 1719700000130,
  "from": "autonomous",
  "to": "manual",
  "reason": "operator_takeover",
  "hmac": "sha256:..."
}

// 紧急制动
{
  "type": "safety.emergency_stop",
  "seq": 12348,
  "timestamp": 1719700000140,
  "hmac": "sha256:..."
}
```

### 3.3 状态上报格式

```json
// 通道: state (Robot → Operator, 30Hz)

// 完整快照 (每 500ms 一次)
{
  "type": "state.snapshot",
  "seq": 98765,
  "timestamp": 1719700000000,
  "robot_id": "qoobot-01",
  "status": {
    "mode": "autonomous",
    "cpu_percent": 45.2,
    "memory_used_mb": 2048,
    "temperature": {"soc": 62.5}
  },
  "power": {
    "battery_percent": 67,
    "estimated_runtime_minutes": 45
  },
  "joints": [{"name": "left_shoulder_pitch", "position": 0.523, "velocity": 0.12}]
}

// 增量更新 (每 33ms 一次)
{
  "type": "state.delta",
  "seq": 98766,
  "timestamp": 1719700000033,
  "joints_delta": [{"id": 0, "p": 0.525, "v": 0.15}]
}
```

### 3.4 告警格式

```json
// 通道: alert (Robot → Operator)

{
  "type": "alert.new",
  "alert": {
    "id": "alt-20260630-001",
    "level": "warning",
    "type": "battery_low",
    "message": "电量降至 18%，预估剩余 12 分钟",
    "timestamp": 1719699900000
  }
}

// 告警清除
{
  "type": "alert.clear",
  "alert_id": "alt-20260630-001",
  "timestamp": 1719700000000
}
```

---

## 4. Python Core API

### 4.1 SignalingClient

```python
class SignalingClient:
    """WebSocket 信令客户端"""

    async def connect(self, url: str, token: str) -> bool:
        """建立 WebSocket 连接并认证"""
        ...

    async def disconnect(self) -> None:
        """断开连接"""
        ...

    async def list_robots(self) -> list[RobotInfo]:
        """获取在线机器人列表"""
        ...

    async def request_session(
        self,
        robot_id: str,
        mode: SessionMode
    ) -> SessionInfo:
        """建立遥控会话"""
        ...

    async def end_session(self, session_id: str) -> None:
        """结束遥控会话"""
        ...

    async def send_ice_candidate(
        self,
        session_id: str,
        candidate: RTCIceCandidate
    ) -> None:
        """发送 ICE 候选"""
        ...

    @property
    def connected(self) -> bool: ...
    @property
    def latency_ms(self) -> float: ...

    # 事件
    on_robot_list_updated: Signal
    on_session_established: Signal
    on_session_ended: Signal
    on_connection_lost: Signal
```

### 4.2 WebRTCManager

```python
class WebRTCManager:
    """WebRTC PeerConnection 管理器"""

    async def create_offer(self) -> RTCSessionDescription:
        """创建 SDP Offer"""
        ...

    async def set_remote_answer(self, sdp: str) -> None:
        """设置远端 SDP Answer"""
        ...

    async def add_ice_candidate(self, candidate: dict) -> None:
        """添加 ICE 候选"""
        ...

    def on_video_track(self, track: VideoStreamTrack) -> None:
        """接收视频轨回调"""
        ...

    def on_audio_track(self, track: AudioStreamTrack) -> None:
        """接收音频轨回调"""
        ...

    def on_data_channel(self, channel: DataChannel) -> None:
        """接收数据通道回调"""
        ...

    async def send_command(self, channel: str, message: dict) -> None:
        """在指定通道发送消息"""
        ...

    async def close(self) -> None: ...

    @property
    def connection_state(self) -> str: ...
    @property
    def video_stats(self) -> dict: ...
```

### 4.3 TeleopController

```python
class TeleopController:
    """遥操作控制器基类"""

    def set_mode(self, mode: ControlMode) -> None:
        """设置操控模式: end_effector | joint | gamepad"""
        ...

    async def send_pose_command(
        self,
        frame: str,
        position: tuple[float, float, float],
        orientation: tuple[float, float, float],
        max_velocity: float = 0.5
    ) -> None:
        """发送末端位姿指令"""
        ...

    async def send_joint_command(
        self,
        targets: list[JointTarget],
        mode: JointControlMode = JointControlMode.POSITION
    ) -> None:
        """发送关节指令"""
        ...

    async def switch_mode(
        self,
        to: RobotMode,
        reason: str = "operator_action"
    ) -> None:
        """切换机器人运行模式"""
        ...

    async def emergency_stop(self) -> None:
        """紧急制动"""
        ...

    def update_from_gamepad(self, state: GamepadState) -> None:
        """手柄状态→控制指令映射"""
        ...

    @property
    def current_mode(self) -> ControlMode: ...
```

### 4.4 Recorder

```python
class MultiChannelRecorder:
    """多通道同步录制器"""

    def start(
        self,
        path: str,
        channels: dict[str, bool],
        sample_rate_hz: int = 100
    ) -> None:
        """开始录制"""
        ...

    def mark_event(self, label: str, note: str = "") -> None:
        """标记录制事件"""
        ...

    def pause(self) -> None: ...
    def resume(self) -> None: ...
    def stop(self) -> RecordingMetadata: ...

    def record_joint_state(self, timestamp: int, joints: list[JointState]) -> None: ...
    def record_imu(self, timestamp: int, imu: IMUData) -> None: ...
    def record_command(self, timestamp: int, command: dict) -> None: ...

    @property
    def state(self) -> RecordingState: ...
    @property
    def duration_seconds(self) -> float: ...
    @property
    def size_bytes(self) -> int: ...


class RecordingPlayer:
    """录制回放器"""

    def load(self, path: str) -> None: ...
    def play(self, speed: float = 1.0) -> None: ...
    def pause(self) -> None: ...
    def seek(self, timestamp_ms: int) -> None: ...
    def stop(self) -> None: ...

    @property
    def metadata(self) -> RecordingMetadata: ...

    # 回放数据回调
    on_joint_frame: Signal     # (timestamp, joints)
    on_imu_frame: Signal       # (timestamp, imu)
    on_marker_reached: Signal  # (timestamp, label)
```

---

## 5. 错误码定义

| 码 | 说明 |
|:----:|------|
| 0 | 成功 |
| 401 | 认证失败 (Token 无效/过期) |
| 403 | 权限不足 |
| 404 | 机器人未找到 |
| 409 | 冲突 (机器人忙/已被接管) |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |
| 503 | 服务暂不可用 |
| 1001 | WebSocket 连接失败 |
| 1002 | 信令超时 |
| 1003 | 会话已过期 |
| 2001 | WebRTC 连接失败 |
| 2002 | ICE 协商失败 |
| 2003 | DataChannel 未就绪 |
| 3001 | 控制指令被拒绝 (权限不足) |
| 3002 | 控制指令被拒绝 (安全校验失败) |
| 3003 | 机器人处于不可控状态 |

---

## 6. 变更日志

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-06-30 | v0.1.0 | 初始 API 设计，定义信令协议、DataChannel 协议、Python Core API |
