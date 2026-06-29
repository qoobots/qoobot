# qoogear-sdk — QooBot MFQ 配件开发 SDK

Made for QooBot (MFQ) 认证体系的核心开发工具包。

## 安装

```bash
pip install qoogear-sdk
```

## 快速开始

```python
from qoogear_sdk.peripheral import GripperAccessory, AccessoryInfo, AccessoryType
from qoogear_sdk.testing import SelfCheckRunner
from qoogear_sdk.simulator import AccessorySimulator, SimulatorConfig

# 创建配件驱动
info = AccessoryInfo(
    name="MyGripper",
    vendor_name="MyCompany",
    accessory_type=AccessoryType.END_EFFECTOR,
)
gripper = GripperAccessory(info)

# 连接并激活
gripper.connect()
gripper.activate()

# 执行抓取
gripper.grasp(force_n=50.0)

# 检查状态
status = gripper.get_status()
print(status)

# 运行认证自检
runner = SelfCheckRunner("MyGripper")
report = runner.run_all()
print(f"Self-check: {report['overall_result']}")

# 使用模拟器（无需硬件）
config = SimulatorConfig(accessory_type=AccessoryType.END_EFFECTOR)
sim = AccessorySimulator(config)
sim.start()
sim.set_command("grip_force", 80.0)
state = sim.get_state()
sim.stop()
```

## CLI 使用

```bash
qoogear init my-gripper       # 初始化配件项目
qoogear test                   # 运行认证自检套件
qoogear simulate gripper       # 启动夹具模拟器
qoogear build                  # 构建配件驱动包
qoogear submit                 # 提交认证申请
qoogear status MFQ-2026-0001   # 查询认证状态
```

## 模块

| 模块 | 说明 |
|------|------|
| `peripheral` | 配件基类（夹具/传感器/电源） |
| `protocols` | 通信协议库（CAN-FD/RS-485/BLE/WiFi） |
| `testing` | MFQ 认证自检套件 |
| `simulator` | 无硬件配件模拟器 |
| `utils` | 证书验证/认证芯片通信工具 |
