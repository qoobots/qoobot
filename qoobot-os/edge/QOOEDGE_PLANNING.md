# QooEdge — 边缘计算层

> **状态**: 🚧 P1 规划中 | **优先级**: P1 (次于 P0 核心模块)

## 定位

QooEdge 是 qoobot-os 的边缘计算中间件，介于端侧推理引擎 (QooCore) 和云端服务 (QooCloud) 之间，负责：

- 端-云任务卸载决策
- 边缘节点推理加速
- 低延迟流式数据处理
- 多机器人协同通信

## 规划模块

```
edge/
├── edge_runtime/     # 边缘运行时
├── edge_offload/     # 任务卸载引擎
├── edge_sync/        # 端-云同步
└── edge_mesh/        # 多机器人Mesh网络
```

## 依赖

- QooCore (ai-engine)
- QooCloud (qoobot-service/cloud)
- QooNet (qoobot-service/network)

## 状态

当前处于 P1 规划阶段，待 P0 核心模块 (brain/core/auth/dev) 完成后启动。
