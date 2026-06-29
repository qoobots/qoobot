# qoodev API 设计文档

> 最后更新：2026-06-29
>
> **定位**：qoodev CLI/SDK/WebSocket 协议 API 规范。

---

## 1. CLI 命令参考

### 1.1 项目管理

```bash
# 创建新项目
qoo init [--template=hello_skill|skill_service|ml_model] [--name=NAME] [--path=PATH]

# 构建项目
qoo build [--target=TARGET] [--release]

# 清理构建产物
qoo clean
```

### 1.2 仿真控制

```bash
# 启动仿真
qoo sim [--backend=isaac_sim|mujoco] [--scene=SCENE] [--headless]

# 仿真控制
qoo sim pause
qoo sim resume
qoo sim reset
qoo sim step [--count=N]

# 传感器控制
qoo sim sensor list
qoo sim sensor enable NAME
qoo sim sensor disable NAME
qoo sim sensor stream NAME [--format=rosbag|mp4]
```

### 1.3 调试

```bash
# 启动调试会话
qoo debug [--target=local|remote:HOST:PORT]

# 断点操作
qoo debug breakpoint set FILE:LINE [--condition=EXPR]
qoo debug breakpoint list
qoo debug breakpoint delete ID

# 执行控制
qoo debug continue
qoo debug step [--over|--into|--out]
qoo debug pause

# 变量查看
qoo debug variables [--scope=local|global]
qoo debug evaluate EXPR
qoo debug watch EXPR

# 行为树调试
qoo debug bt status
qoo debug bt tick [--count=N]
```

### 1.4 性能剖析

```bash
# 启动性能追踪
qoo profile [--duration=SECONDS] [--output=FORMAT]

# 查看报告
qoo profile report [--type=flamegraph|timeline|summary]

# 资源监控
qoo monitor [--metrics=cpu,gpu,npu,memory,power]
```

### 1.5 技能打包

```bash
# 打包技能
qoo package [--output=FILE.qooskills] [--sign]

# 验证技能包
qoo package verify FILE.qooskills

# 发布到商店
qoo publish FILE.qooskills [--store=URL] [--api-key=KEY]
```

---

## 2. Python SDK API

```python
"""qoodev SDK — 技能开发基础类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class SkillConfig:
    """技能配置"""
    name: str
    version: str
    description: str
    permissions: List[str]
    min_qoobot_version: str


class Skill(ABC):
    """技能基类"""
    
    def __init__(self, config: SkillConfig):
        self.config = config
        
    @abstractmethod
    def on_start(self) -> None:
        """技能启动回调"""
        ...
    
    @abstractmethod  
    def on_stop(self) -> None:
        """技能停止回调"""
        ...
    
    @abstractmethod
    def on_tick(self, dt: float) -> None:
        """每帧更新 (由 qoobrain 调用)"""
        ...
    
    def get_sensors(self) -> Dict[str, Any]:
        """获取所有传感器数据"""
        ...
    
    def get_actuators(self) -> Dict[str, Any]:
        """获取执行器控制接口"""
        ...
    
    def log(self, level: str, message: str) -> None:
        """日志输出"""
        ...


# 技能注册装饰器
def register_skill(config: SkillConfig):
    """注册技能到 qoobrain 运行时"""
    def decorator(cls):
        qoobrain.SkillRegistry.register(config.name, cls, config)
        return cls
    return decorator


# 使用示例
@register_skill(SkillConfig(
    name="hello_skill",
    version="1.0.0",
    description="Hello World 示例技能",
    permissions=["speech", "movement.basic"],
    min_qoobot_version="1.0.0"
))
class HelloSkill(Skill):
    def on_start(self):
        self.log("info", "Hello QooBot!")
        
    def on_stop(self):
        self.log("info", "Goodbye!")
        
    def on_tick(self, dt):
        pass
```

---

## 3. WebSocket 调试协议

### 3.1 连接建立

```
Client → Server: {"type": "connect", "token": "jwt_token"}
Server → Client: {"type": "connected", "session_id": "uuid"}
```

### 3.2 数据流 (服务端推送)

```json
// 传感器帧
{"type": "sensor_frame", "sensor": "camera_front", "timestamp": 1719667200000000,
 "data": {"encoding": "jpeg", "bytes_base64": "..."}}

// 行为树状态  
{"type": "bt_state", "nodes": [{"id": "root", "status": "RUNNING"},
  {"id": "move_to", "status": "SUCCESS"}, {"id": "grasp", "status": "RUNNING"}]}

// 日志
{"type": "log", "level": "INFO", "message": "Object detected: cup", "timestamp": 1719667200000}
```

### 3.3 命令 (客户端请求)

```json
// 设置断点
{"type": "cmd", "cmd": "set_breakpoint", "file": "skill.py", "line": 42,
 "condition": "x > 100"}

// 获取变量  
{"type": "cmd", "cmd": "get_variables", "scope": "local"}

// 执行表达式
{"type": "cmd", "cmd": "evaluate", "expression": "robot.position"}
```

---

## 4. gRPC 仿真服务

```protobuf
service SimulationService {
    rpc StartSim(StartSimRequest) returns (StartSimResponse);
    rpc StopSim(StopSimRequest) returns (google.protobuf.Empty);
    rpc PauseSim(PauseSimRequest) returns (google.protobuf.Empty);
    rpc ResumeSim(ResumeSimRequest) returns (google.protobuf.Empty);
    rpc StepSim(StepSimRequest) returns (SimState);
    rpc LoadScene(LoadSceneRequest) returns (LoadSceneResponse);
    rpc GetSimState(google.protobuf.Empty) returns (SimState);
    rpc StreamSensors(SensorStreamRequest) returns (stream SensorFrame);
}
```

---

## 5. 技能清单格式 (.qooskills)

```yaml
# skill.yaml (技能清单)
manifest_version: "1.0"
skill:
  name: "coffee_maker"
  version: "1.2.0"
  display_name: "咖啡助手"
  description: "自动制作咖啡的技能"
  author: "developer_name"
  icon: "icon.png"
  
  permissions:
    - navigation.indoor
    - manipulation.grasp
    - speech.tts
    - camera.rgb
    
  dependencies:
    qoobrain: ">=1.0.0"
    qoocore: ">=1.0.0"
    
  resources:
    cpu_cores: 2
    memory_mb: 512
    gpu_memory_mb: 256
    disk_mb: 100
    
  privacy:
    data_collected:
      - type: "camera_images"
        purpose: "object_detection"
        storage: "local_only"
        retention: "session_only"
        
  entry_point: "main.py:create_skill"
```
