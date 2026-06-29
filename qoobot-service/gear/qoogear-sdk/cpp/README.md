# qoogear-sdk — C++17 MFQ 配件开发 SDK

## 构建

```bash
mkdir build && cd build
cmake ..
make -j$(nproc)
```

## 使用

```cpp
#include <qoogear/peripheral_base.h>
#include <qoogear/comm/can_interface.h>
#include <qoogear/security/cert_verifier.h>

using namespace qoogear;

// 创建夹具配件
GripperAccessory gripper;
gripper.connect();
gripper.activate();
gripper.grasp(50.0f);
gripper.stop();
gripper.disconnect();

// CAN 通信
comm::CANInterface can("can0", 1000000);
can.open();
can.send({0x100, {0x01, 0x02, 0x03}});

// 证书验证
security::CertVerifier verifier;
auto cert = verifier.verify_cert_hash("MFQ2026...");
if (cert.is_valid) {
    // 配件已认证
}
```
