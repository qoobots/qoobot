"""
QooBot 双足行走强化学习训练脚本。

支持 PPO 和 SAC 算法 (基于 stable-baselines3)。
训练 QooBot 双足机器人在 MuJoCo 物理引擎中稳定行走。

Usage:
    # PPO 训练
    qoo sim train --algo ppo --timesteps 1_000_000

    # SAC 训练
    qoo sim train --algo sac --timesteps 2_000_000

    # 继续训练
    qoo sim train --algo ppo --resume ./logs/qoobot_walking_ppo/checkpoint.zip

    # 仅评估
    qoo sim train --algo ppo --eval ./logs/qoobot_walking_ppo/best_model.zip

    # 无渲染快速训练
    qoo sim train --algo ppo --timesteps 5_000_000 --no-render
"""

import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


def train(
    algo: str = "ppo",
    total_timesteps: int = 1_000_000,
    resume: Optional[str] = None,
    eval_model: Optional[str] = None,
    log_dir: Optional[str] = None,
    no_render: bool = False,
    use_mpc_guide: bool = False,
    seed: int = 42,
    **kwargs,
):
    """训练 QooBot 行走策略。

    Args:
        algo: 算法 ("ppo" 或 "sac")
        total_timesteps: 总训练步数
        resume: 继续训练的 checkpoint 路径
        eval_model: 仅评估的模型路径
        log_dir: 日志目录
        no_render: 禁用渲染
        use_mpc_guide: 使用 MPC 引导
        seed: 随机种子
    """
    # ── 检查依赖 ────────────────────────────────────
    try:
        import gymnasium as gym
    except ImportError:
        print("[ERROR] Gymnasium 未安装。请运行: pip install gymnasium")
        sys.exit(1)

    try:
        from stable_baselines3 import PPO, SAC
        from stable_baselines3.common.callbacks import (
            CheckpointCallback,
            EvalCallback,
            StopOnNoModelImprovement,
        )
        from stable_baselines3.common.monitor import Monitor
        from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
        from stable_baselines3.common.env_util import make_vec_env
        from stable_baselines3.common.logger import configure
        HAS_SB3 = True
    except ImportError:
        print("[ERROR] stable-baselines3 未安装。请运行: pip install stable-baselines3")
        sys.exit(1)

    # ── 导入环境 ─────────────────────────────────────
    # 确保环境已注册
    from cli.sim_bridge.walking_env import QooBotWalkingEnv

    # ── 日志目录 ─────────────────────────────────────
    if log_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = f"./logs/qoobot_walking_{algo}_{timestamp}"

    os.makedirs(log_dir, exist_ok=True)
    tensorboard_log = os.path.join(log_dir, "tensorboard")
    os.makedirs(tensorboard_log, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  QooBot 双足行走 RL 训练")
    print(f"  算法: {algo.upper()}")
    print(f"  总步数: {total_timesteps:,}")
    print(f"  日志目录: {log_dir}")
    print(f"  MPC 引导: {'是' if use_mpc_guide else '否'}")
    print(f"{'='*60}\n")

    # ── 仅评估模式 ──────────────────────────────────
    if eval_model:
        return _evaluate_only(algo, eval_model, no_render)

    # ── 创建环境 ─────────────────────────────────────
    def make_env(rank: int = 0, seed: int = 42):
        def _init():
            env = QooBotWalkingEnv(
                render_mode=None,  # 训练时不渲染
                max_episode_steps=1000,
                target_velocity=0.5,
                use_mpc_guide=use_mpc_guide,
            )
            env = Monitor(env)
            env.reset(seed=seed + rank)
            return env
        return _init

    # 训练环境 (4 并行)
    n_envs = 4
    print(f"[INFO] 创建 {n_envs} 个并行训练环境...")
    train_env = DummyVecEnv([make_env(i, seed) for i in range(n_envs)])
    train_env = VecNormalize(train_env, norm_obs=True, norm_reward=True, clip_obs=10.)

    # 评估环境
    print("[INFO] 创建评估环境...")
    eval_env = DummyVecEnv([make_env(100, seed + 100)])
    eval_env = VecNormalize(eval_env, norm_obs=True, norm_reward=False, clip_obs=10.)

    # ── 算法配置 ─────────────────────────────────────
    policy_kwargs = dict(
        net_arch=dict(pi=[256, 256], vf=[256, 256]),
        activation_fn=None,  # 默认 ReLU
    )

    if algo == "ppo":
        model = PPO(
            "MlpPolicy",
            train_env,
            learning_rate=3e-4,
            n_steps=2048,
            batch_size=64,
            n_epochs=10,
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=0.01,
            vf_coef=0.5,
            max_grad_norm=0.5,
            policy_kwargs=policy_kwargs,
            tensorboard_log=tensorboard_log,
            verbose=1,
            seed=seed,
        )
    elif algo == "sac":
        model = SAC(
            "MlpPolicy",
            train_env,
            learning_rate=3e-4,
            buffer_size=300_000,
            batch_size=256,
            tau=0.005,
            gamma=0.99,
            train_freq=1,
            gradient_steps=1,
            ent_coef="auto",
            policy_kwargs=policy_kwargs,
            tensorboard_log=tensorboard_log,
            verbose=1,
            seed=seed,
        )
    else:
        print(f"[ERROR] 未知算法: {algo}。支持: ppo, sac")
        sys.exit(1)

    # ── 继续训练 ─────────────────────────────────────
    if resume:
        print(f"[INFO] 从 checkpoint 继续训练: {resume}")
        # 加载 VecNormalize 统计
        stats_path = resume.replace(".zip", "_vecnormalize.pkl")
        if os.path.exists(stats_path):
            train_env = VecNormalize.load(stats_path, train_env)
        model = model.load(resume, env=train_env, tensorboard_log=tensorboard_log)

    # ── 回调 ─────────────────────────────────────────
    callbacks = []

    # Checkpoint 保存
    checkpoint_callback = CheckpointCallback(
        save_freq=max(10_000 // n_envs, 1000),
        save_path=os.path.join(log_dir, "checkpoints"),
        name_prefix=f"qoobot_{algo}",
        save_replay_buffer=False,
        save_vecnormalize=True,
    )
    callbacks.append(checkpoint_callback)

    # 评估回调
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=os.path.join(log_dir, "best_model"),
        log_path=os.path.join(log_dir, "eval_logs"),
        eval_freq=max(20_000 // n_envs, 5000),
        n_eval_episodes=5,
        deterministic=True,
        render=False,
    )
    callbacks.append(eval_callback)

    # 早停 (无改善)
    early_stop = StopOnNoModelImprovement(
        max_no_improvement_evals=20,
        min_evals=10,
        verbose=1,
    )
    callbacks.append(early_stop)

    # ── 训练 ─────────────────────────────────────────
    print(f"\n[INFO] 开始训练... (按 Ctrl+C 可中断并保存)")
    print(f"[INFO] 使用 TensorBoard 查看: tensorboard --logdir {tensorboard_log}\n")

    try:
        model.learn(
            total_timesteps=total_timesteps,
            callback=callbacks,
            progress_bar=True,
        )
    except KeyboardInterrupt:
        print("\n[WARN] 训练被中断，正在保存模型...")

    # ── 保存最终模型 ────────────────────────────────
    final_path = os.path.join(log_dir, "final_model.zip")
    model.save(final_path)
    train_env.save(os.path.join(log_dir, "vecnormalize.pkl"))
    print(f"\n[OK] 最终模型已保存: {final_path}")
    print(f"[OK] VecNormalize 统计已保存: {log_dir}/vecnormalize.pkl")

    # ── 清理 ─────────────────────────────────────────
    train_env.close()
    eval_env.close()

    return model


def _evaluate_only(algo: str, model_path: str, no_render: bool):
    """仅评估已训练的模型。"""
    import gymnasium as gym
    from stable_baselines3 import PPO, SAC

    from cli.sim_bridge.walking_env import QooBotWalkingEnv

    render_mode = None if no_render else "human"
    env = QooBotWalkingEnv(render_mode=render_mode, max_episode_steps=2000)

    # 加载模型
    if algo == "ppo":
        model = PPO.load(model_path)
    elif algo == "sac":
        model = SAC.load(model_path)
    else:
        raise ValueError(f"未知算法: {algo}")

    print(f"\n{'='*60}")
    print(f"  评估模式")
    print(f"  模型: {model_path}")
    print(f"  渲染: {'关闭' if no_render else '开启'}")
    print(f"{'='*60}\n")

    if not no_render:
        print("[INFO] 渲染窗口已打开，按 Ctrl+C 退出\n")

    obs, _ = env.reset()
    total_reward = 0
    step = 0

    try:
        while True:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            step += 1

            if step % 100 == 0:
                print(f"  Step {step:5d} | Reward: {total_reward:8.2f} | "
                      f"Height: {info.get('base_height', 0):.3f} | "
                      f"Vel X: {info.get('base_vel_x', 0):.3f}")

            if terminated or truncated:
                print(f"\n  Episode 结束:")
                print(f"    总步数: {step}")
                print(f"    总奖励: {total_reward:.2f}")
                print(f"    终止原因: {'跌倒' if terminated else '超时'}")
                obs, _ = env.reset()
                total_reward = 0
                step = 0

    except KeyboardInterrupt:
        print("\n[INFO] 评估已停止")

    env.close()


# ── 命令行入口 ────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="QooBot 行走 RL 训练")
    parser.add_argument("--algo", default="ppo", choices=["ppo", "sac"], help="算法")
    parser.add_argument("--timesteps", type=int, default=1_000_000, help="总训练步数")
    parser.add_argument("--resume", type=str, help="继续训练的 checkpoint")
    parser.add_argument("--eval", type=str, dest="eval_model", help="仅评估模型")
    parser.add_argument("--log-dir", type=str, help="日志目录")
    parser.add_argument("--no-render", action="store_true", help="禁用渲染")
    parser.add_argument("--mpc-guide", action="store_true", help="MPC 引导")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")

    args = parser.parse_args()
    train(**vars(args))
