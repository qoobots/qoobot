"""
brain_ai/vla_agent/ — Vision-Language-Action (VLA) Agent.

基于 OpenVLA-7B 微调的端到端视觉-语言-动作模型。
将视觉观察 + 自然语言指令直接映射为机器人动作序列（action chunks）。

模块组成:
    VLAInferencer  — 主推理器，协调模型推理流程
    ActionDecoder  — 将 VLA 输出 token 解码为动作 chunk
    ChunkPredictor — 动作块预测器（类 π₀ 架构）
    ModelLoader    — 模型加载/卸载/热切换
    LoRAAdapter    — LoRA 微调适配器管理

P3 优先级（Phase 3 远期目标）。
当前实现为 stub/mock 模式，供接口验证和集成测试使用。
"""

from brain_ai.vla_agent.vla_inferencer import VLAInferencer
from brain_ai.vla_agent.action_decoder import ActionDecoder
from brain_ai.vla_agent.chunk_predictor import ChunkPredictor
from brain_ai.vla_agent.model_loader import ModelLoader
from brain_ai.vla_agent.lora_adapter import LoRAAdapter

__all__ = [
    "VLAInferencer",
    "ActionDecoder",
    "ChunkPredictor",
    "ModelLoader",
    "LoRAAdapter",
]
