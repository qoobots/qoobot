"""Tests for the accelerated simulation module."""

from __future__ import annotations

import pytest
from qoodev.sim_bridge.accelerated_sim import (
    AcceleratedSimulation,
    AcceleratedSimConfig,
    SimWorkerResult,
)


def test_accelerated_config_defaults():
    config = AcceleratedSimConfig()
    assert config.speedup_factor == 10.0
    assert config.headless is True
    assert config.num_workers == 4
    assert config.physics_substeps == 10
    assert config.gpu_physics is False
    assert config.batch_scenes == 1
    assert config.deterministic is True
    assert config.backend == "mujoco"


def test_accelerated_config_custom():
    config = AcceleratedSimConfig(
        speedup_factor=5.0,
        num_workers=2,
        backend="isaac_sim",
    )
    assert config.speedup_factor == 5.0
    assert config.num_workers == 2
    assert config.backend == "isaac_sim"


def test_sim_worker_result_defaults():
    result = SimWorkerResult(
        worker_id=0,
        scene_id=1,
        steps_completed=100,
        wall_time_sec=2.0,
        sim_time_sec=10.0,
        effective_speedup=5.0,
    )
    assert result.worker_id == 0
    assert result.scene_id == 1
    assert result.steps_completed == 100
    assert result.effective_speedup == 5.0
    assert result.errors == []


def test_sim_worker_result_with_errors():
    result = SimWorkerResult(
        worker_id=1,
        scene_id=0,
        steps_completed=0,
        wall_time_sec=0.1,
        sim_time_sec=0,
        effective_speedup=0,
        errors=["Connection failed"],
    )
    assert len(result.errors) == 1
    assert result.errors[0] == "Connection failed"


def test_accelerated_sim_init():
    sim = AcceleratedSimulation()
    assert sim.config is not None
    assert sim.config.speedup_factor == 10.0
    assert sim._running is False


def test_accelerated_sim_custom_config():
    config = AcceleratedSimConfig(speedup_factor=20.0, num_workers=8)
    sim = AcceleratedSimulation(config=config)
    assert sim.config.speedup_factor == 20.0
    assert sim.config.num_workers == 8


def test_accelerated_sim_empty_summary():
    sim = AcceleratedSimulation()
    summary = sim.get_summary()
    assert summary["total_scenes"] == 0
    assert summary["total_steps"] == 0
    assert "No results" in summary["errors"]


def test_accelerated_sim_single_scene_simulated():
    """Run a single scene in simulated mode (no real backend)."""
    config = AcceleratedSimConfig(
        speedup_factor=100.0,  # High speedup for fast test
        num_workers=1,
        headless=True,
    )
    sim = AcceleratedSimulation(config=config)

    scene_cfg = {"scene": "empty"}
    result = sim.run_single(scene_cfg, total_steps=50)

    assert result.steps_completed == 50
    assert result.wall_time_sec > 0
    assert result.sim_time_sec > 0
    assert result.effective_speedup > 0
    assert result.errors == []


def test_accelerated_sim_batch_simulated():
    """Run batch scenes in simulated mode."""
    config = AcceleratedSimConfig(
        speedup_factor=100.0,
        num_workers=2,
        headless=True,
    )
    sim = AcceleratedSimulation(config=config)

    scene_configs = [
        {"scene": "empty", "id": 0},
        {"scene": "empty", "id": 1},
        {"scene": "empty", "id": 2},
    ]

    results = sim.run_batch(scene_configs, total_steps=30)

    assert len(results) == 3
    for r in results:
        assert r.steps_completed == 30
        assert r.errors == []

    summary = sim.get_summary()
    assert summary["total_scenes"] == 3
    assert summary["total_steps"] == 90
    assert summary["overall_speedup"] > 0


def test_accelerated_sim_with_callback():
    """Test that step callback is invoked."""
    config = AcceleratedSimConfig(speedup_factor=100.0, num_workers=1, headless=True)
    sim = AcceleratedSimulation(config=config)

    callbacks_received = []

    def on_step(worker_id, scene_id, step, sim_time):
        callbacks_received.append((worker_id, scene_id, step, sim_time))

    sim.run_single({"scene": "empty"}, total_steps=10, step_callback=on_step)

    assert len(callbacks_received) == 10
    assert callbacks_received[0][2] == 0  # First step index
    assert callbacks_received[-1][2] == 9  # Last step index


def test_accelerated_sim_backend_check():
    sim = AcceleratedSimulation()
    assert sim.is_using_real_backend() is False
