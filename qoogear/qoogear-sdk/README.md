# qoogear-sdk — MFQ 配件开发 SDK

Made for QooBot (MFQ) 认证体系的核心开发工具包。

## 组件

| 组件 | 语言 | 说明 |
|------|------|------|
| [python/](python/) | Python 3.9+ | 配件驱动开发框架、通信协议库、自检套件、模拟器、CLI工具 |
| [cpp/](cpp/) | C++17 | 嵌入式/实时配件驱动、CAN/EtherCAT通信、硬件安全、证书验证 |
| [../proto/](../proto/) | Protobuf | 配件识别、认证数据、接口标准协议定义 |

## 快速开始

### Python

```bash
pip install -e python/
qoogear init my-gripper
qoogear test
qoogear simulate gripper
```

### C++

```bash
cd cpp/ && mkdir build && cd build
cmake .. && make -j$(nproc)
```

### 协议编译

```bash
protoc --proto_path=../proto --python_out=python/qoogear_sdk/proto \
    ../proto/peripheral.proto ../proto/certification.proto ../proto/standard.proto
```
