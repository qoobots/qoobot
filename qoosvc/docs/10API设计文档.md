# qoosvc — API 设计文档

> 版本：v0.1 | 最后更新：2026-06-29 | 状态：Draft | 子项目：qoosvc（系统服务）
> API 类型：Python SDK · gRPC · ROS2 Topic/Service

---

## 1. API 总览

qoosvc 提供三层 API 接口，适配不同使用场景：

| API 层 | 协议 | 适用场景 | 调用方 |
|:-------|------|---------|------|
| Python SDK | 本地函数调用 | 技能开发 | qoostore 技能、qoobrain 模块 |
| gRPC API | gRPC/Protobuf | 跨进程/跨语言调用 | 外部工具、云端服务 |
| ROS2 API | Topic/Service | 机器人节点通信 | qoobrain 节点、传感器驱动 |

---

## 2. Python SDK

### 2.1 Speech SDK

```python
from qoosvc.speech import SpeechClient

# 初始化
speech = SpeechClient(language="zh-CN", model_path="/opt/qoo/models/")

# 语音唤醒
speech.set_wake_word("Hey QooBot", sensitivity=0.5)
speech.on_wake(lambda: print("已唤醒!"))

# ASR 识别（流式）
for text, is_final in speech.recognize_stream(audio_source="mic"):
    if is_final:
        print(f"识别结果: {text}")

# NLU 意图识别
result = speech.understand("带我去厨房")
# => IntentResult(intent="navigate", slots={"destination": "kitchen"}, confidence=0.94)

# TTS 合成
speech.speak("好的，正在前往厨房", emotion="happy", speed=1.0)

# 说话人识别
speaker_id = speech.identify_speaker(audio_clip)
# => "user_father" or "unknown"
```

### 2.2 Navigation SDK

```python
from qoosvc.navigation import NavigationClient, NavGoal

nav = NavigationClient()

# 设置目的地
goal = NavGoal(x=3.5, y=2.1, theta=0.0, frame="map")
nav.set_goal(goal)

# 监听导航状态
nav.on_status(lambda status: print(f"状态: {status}"))
# status: PLANNING → EXECUTING → ARRIVED / BLOCKED / RECOVERING

# 取消导航
nav.cancel()

# 区域管理
nav.add_zone("kitchen", zone_type="speed_limit", max_speed=0.3)
nav.add_zone("stairs", zone_type="restricted", allow=False)

# 导航恢复
nav.recover()  # 手动触发恢复
```

### 2.3 Spatial SDK

```python
from qoosvc.spatial import SpatialClient

spatial = SpatialClient()

# 获取当前位置
pose = spatial.get_pose()
# => Pose(x=1.2, y=3.4, theta=0.78)

# 获取语义地图
rooms = spatial.get_semantic_map()
# => [Room(id="kitchen", center=(3.0, 2.0), area=15.2), ...]

# 物体检索
location = spatial.find_object("我的钥匙")
# => ObjectLocation(position=(1.5, 2.3), last_seen="2小时前", confidence=0.85)

# 导航到物体
nav.navigate_to_object("我的钥匙")
```

### 2.4 Diagnostic SDK

```python
from qoosvc.diagnostic import DiagnosticClient

diag = DiagnosticClient()

# 运行开机自检
post_result = diag.run_post()
# => POSTResult(score=98, failures=[], warnings=["电池循环次数>500"])

# 获取健康报告
health = diag.get_health_report()
# => HealthReport(
#      overall_score=92,
#      components={
#          "battery": ComponentHealth(score=88, status="warning"),
#          "motors": ComponentHealth(score=95, status="ok"),
#          "sensors": ComponentHealth(score=97, status="ok"),
#      },
#      recommendations=["建议6个月内更换电池"]
#    )
```

### 2.5 Interaction SDK

```python
from qoosvc.interaction import InteractionClient

interact = InteractionClient()

# 对话
response = interact.chat("今天天气怎么样？")
# => "今天晴天，气温22-28度，适合户外活动"

# 手势识别
interact.on_gesture("wave", lambda: print("用户招手"))

# LED 表情
interact.set_face(emotion="happy", eyes="^^")

# 触屏显示
interact.show_screen("status", data={"battery": 85, "tasks": [...]})
```

---

## 3. gRPC API

### 3.1 Speech Service

```protobuf
service SpeechService {
  rpc Recognize(stream AudioChunk) returns (stream RecognitionResult);
  rpc Synthesize(SynthesizeRequest) returns (stream AudioChunk);
  rpc Understand(UnderstandRequest) returns (IntentResult);
  rpc IdentifySpeaker(AudioClip) returns (SpeakerResult);
  rpc SetWakeWord(WakeWordConfig) returns (Status);
  rpc GetVoices(Empty) returns (VoiceList);
}
```

### 3.2 Navigation Service

```protobuf
service NavigationService {
  rpc SetGoal(NavGoal) returns (NavTaskId);
  rpc GetStatus(NavTaskId) returns (NavStatus);
  rpc CancelNavigation(NavTaskId) returns (Status);
  rpc GetCurrentPose(Empty) returns (Pose);
  rpc ManageZone(ZoneDefinition) returns (Status);
  rpc ListZones(Empty) returns (ZoneList);
  rpc Recover(NavTaskId) returns (Status);
}
```

### 3.3 Diagnostic Service

```protobuf
service DiagnosticService {
  rpc RunPOST(POSTConfig) returns (POSTResult);
  rpc GetHealthReport(Empty) returns (HealthReport);
  rpc GetComponentStatus(ComponentType) returns (ComponentHealth);
  rpc SubscribeAlerts(Empty) returns (stream Alert);
  rpc TriggerHeal(ComponentType) returns (Status);
}
```

---

## 4. ROS2 API

### 4.1 Topics

| Topic | 消息类型 | 方向 | 频率 | 描述 |
|:------|---------|:----:|:----:|------|
| `/qoosvc/speech/wake` | `WakeEvent` | OUT | Event | 唤醒事件 |
| `/qoosvc/speech/asr_result` | `ASRResult` | OUT | 10Hz | ASR 识别结果 |
| `/qoosvc/speech/tts_audio` | `Audio` | OUT | 100Hz | TTS 合成音频 |
| `/qoosvc/nav/status` | `NavStatus` | OUT | 5Hz | 导航状态 |
| `/qoosvc/nav/cmd_vel` | `Twist` | OUT | 50Hz | 速度指令 |
| `/qoosvc/spatial/pose` | `PoseStamped` | OUT | 30Hz | 当前位姿 |
| `/qoosvc/spatial/map` | `OccupancyGrid` | OUT | 1Hz | 栅格地图 |
| `/qoosvc/diag/health` | `HealthReport` | OUT | 0.1Hz | 健康报告 |
| `/qoosvc/diag/alert` | `Alert` | OUT | Event | 诊断告警 |
| `/qoosvc/interaction/gesture` | `Gesture` | OUT | Event | 手势识别事件 |

### 4.2 Services

| Service | 请求 | 响应 | 描述 |
|:--------|------|------|------|
| `/qoosvc/speech/understand` | `UnderstandReq` | `IntentResult` | NLU 意图识别 |
| `/qoosvc/speech/identify` | `IdentifyReq` | `SpeakerResult` | 说话人识别 |
| `/qoosvc/nav/set_goal` | `NavGoal` | `NavTaskId` | 设置导航目标 |
| `/qoosvc/nav/cancel` | `NavTaskId` | `Status` | 取消导航 |
| `/qoosvc/spatial/find` | `FindObjectReq` | `ObjectLocation` | 物体检索 |
| `/qoosvc/diag/run_post` | `POSTConfig` | `POSTResult` | 运行自检 |

---

## 5. 错误码

| 错误码 | 类别 | 描述 |
|:-------|------|------|
| `SVC_OK` (0) | 通用 | 成功 |
| `SVC_ERR_INTERNAL` (1000) | 通用 | 内部错误 |
| `SVC_ERR_NOT_READY` (1001) | 通用 | 服务未就绪 |
| `SVC_ERR_TIMEOUT` (1002) | 通用 | 操作超时 |
| `SPEECH_ERR_NO_WAKE` (2001) | 语音 | 未检测到唤醒词 |
| `SPEECH_ERR_LOW_CONFIDENCE` (2002) | 语音 | ASR/NLU 置信度过低 |
| `SPEECH_ERR_UNSUPPORTED_LANG` (2003) | 语音 | 不支持的语言 |
| `NAV_ERR_NO_MAP` (3001) | 导航 | 无可用地图 |
| `NAV_ERR_PATH_NOT_FOUND` (3002) | 导航 | 路径规划失败 |
| `NAV_ERR_BLOCKED` (3003) | 导航 | 路径被阻塞 |
| `NAV_ERR_IN_ZONE` (3004) | 导航 | 目标在禁区内 |
| `SPATIAL_ERR_NOT_LOCALIZED` (4001) | 空间 | 未定位 |
| `SPATIAL_ERR_OBJECT_NOT_FOUND` (4002) | 空间 | 物体未找到 |
| `DIAG_ERR_TEST_FAILED` (5001) | 诊断 | 硬件检测未通过 |
| `DIAG_ERR_HEAL_FAILED` (5002) | 诊断 | 自愈失败 |

---

## 6. 版本策略

- **主版本号**（X.0.0）：不兼容的 API 变更
- **次版本号**（0.X.0）：向后兼容的功能新增
- **修订版本号**（0.0.X）：向后兼容的问题修复
- SDK 版本与 qoosvc 服务版本解耦，通过 API 兼容性矩阵保证向前兼容
