# QooEdge — 边缘计算层

> **状态**: ✅ v0.1 已完成 | **优先级**: P1

## 定位

QooEdge 是 qoobot-os 的边缘计算中间件，介于端侧推理引擎 (QooCore) 和云端服务 (QooCloud) 之间，负责：

- 端-云任务卸载决策
- 边缘节点推理加速
- 低延迟流式数据处理
- 多机器人协同通信

## 模块

```
edge/
├── edge_runtime/     # 边缘推理运行时 (5功能)
├── edge_offload/     # 任务卸载决策引擎 (7功能)
├── edge_sync/        # 端-云数据同步引擎 (6功能)
└── edge_mesh/        # 多机器人Mesh网络 (7功能)
```

## 依赖

- QooCore (ai-engine)
- QooCloud (qoobot-service/cloud)
- QooNet (qoobot-service/network)

## 状态

✅ v0.1 已完成 — 4个核心模块全部实现，25个功能点全部交付，33个测试用例全部通过。

## 构建与测试

```bash
cd qoobot-os/edge
mkdir build && cd build
cmake .. && cmake --build .
./test/test_qooedge   # 运行测试
```

## 相关文档

- [功能清单与开发进度](docs/01功能清单完成进度.md)
- [qoobot-os 总体功能清单](../docs/01功能清单完成进度.md)
