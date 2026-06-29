"""qoo sim — 仿真环境管理命令。

管理仿真引擎的生命周期：启动/停止/暂停/恢复，
加载场景，监控传感器数据。
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from qoodev.sim_bridge.interface import SimConfig, SimState
from qoodev.sim_bridge.manager import SimManager, list_backends
from qoodev.sim_bridge.scene_loader import SceneLoader, list_presets

app = typer.Typer(
    name="sim",
    help="仿真环境管理 — 启动/停止仿真、加载场景、监控传感器",
)
console = Console()
logger = logging.getLogger(__name__)


# ── 全局管理器 ─────────────────────────────────────────

_sim_manager: Optional[SimManager] = None


def _get_manager() -> SimManager:
    global _sim_manager
    if _sim_manager is None:
        raise typer.BadParameter(
            "仿真管理器未初始化。请先运行 qoo sim start"
        )
    return _sim_manager


# ── 命令 ──────────────────────────────────────────────

@app.command("start")
def sim_start(
    backend: str = typer.Option(
        "mujoco", "--backend", "-b",
        help="仿真后端: mujoco / isaac_sim"
    ),
    scene: str = typer.Option(
        "home", "--scene", "-s",
        help="场景名称或路径: home / factory / empty / 文件路径"
    ),
    headless: bool = typer.Option(
        False, "--headless",
        help="无渲染模式（适合 CI/CD）"
    ),
    time_step: float = typer.Option(
        0.001, "--time-step", "-t",
        help="仿真时间步长 (秒)"
    ),
    real_time: bool = typer.Option(
        True, "--real-time/--no-real-time",
        help="实时模式 vs 最快速度"
    ),
) -> None:
    """启动仿真引擎并加载场景。

    Examples:
        qoo sim start                          # 默认: MuJoCo + 家居场景
        qoo sim start --backend mujoco --scene factory
        qoo sim start --backend isaac_sim --scene /path/to/scene.usd
        qoo sim start --headless --scene empty   # CI 模式
    """
    global _sim_manager

    if _sim_manager is not None:
        console.print("[yellow]仿真管理器已在运行。请先执行 qoo sim stop[/yellow]")
        return

    # 配置
    config = SimConfig(
        backend=backend,
        headless=headless,
        time_step=time_step,
        real_time=real_time,
    )

    # 初始化
    with console.status(f"[cyan]初始化 {backend} 仿真引擎...[/cyan]"):
        _sim_manager = SimManager(config)
        _sim_manager.initialize()

    # 加载场景
    with console.status(f"[cyan]加载场景: {scene}...[/cyan]"):
        loader = SceneLoader()
        sim_scene = loader.load(scene)
        _sim_manager.load_scene(sim_scene)

    # 启动
    _sim_manager.start()
    _sim_manager.backend.state = SimState.RUNNING

    console.print()
    console.print(
        Panel.fit(
            f"[green]✓ 仿真已启动[/green]\n"
            f"后端: [bold]{backend}[/bold]\n"
            f"场景: [bold]{sim_scene.name}[/bold] — {sim_scene.description}\n"
            f"模式: {'无头' if headless else '渲染'}\n"
            f"时间步长: {time_step}s\n"
            f"机器人: {len(sim_scene.robots)} 个\n"
            f"物体: {len(sim_scene.objects)} 个",
            title="[bold]Simulation[/bold]",
            border_style="green",
        )
    )


@app.command("stop")
def sim_stop() -> None:
    """停止并关闭仿真引擎。"""
    global _sim_manager

    if _sim_manager is None:
        console.print("[yellow]仿真管理器未运行[/yellow]")
        return

    with console.status("[red]正在关闭仿真...[/red]"):
        _sim_manager.shutdown()
        _sim_manager = None

    console.print("[green]✓ 仿真已停止[/green]")


@app.command("pause")
def sim_pause() -> None:
    """暂停仿真。"""
    mgr = _get_manager()
    mgr.pause()
    console.print("[yellow]⏸ 仿真已暂停[/yellow]")


@app.command("resume")
def sim_resume() -> None:
    """恢复仿真。"""
    mgr = _get_manager()
    mgr.resume()
    console.print("[green]▶ 仿真已恢复[/green]")


@app.command("step")
def sim_step(
    count: int = typer.Argument(1, help="步进次数"),
) -> None:
    """手动推进仿真 N 步。"""
    mgr = _get_manager()
    for i in range(count):
        mgr.step_once()
    console.print(f"[green]✓ 已推进 {count} 步[/green]")


@app.command("monitor")
def sim_monitor(
    interval: float = typer.Option(
        0.5, "--interval", "-i",
        help="刷新间隔 (秒)"
    ),
    duration: float = typer.Option(
        0, "--duration", "-d",
        help="监控时长，0=持续监控"
    ),
) -> None:
    """实时监控仿真状态和传感器数据。

    显示: 状态、时间、实时因子、关节位置、传感器数据。
    """
    mgr = _get_manager()
    backend = mgr.backend
    if backend is None:
        console.print("[red]仿真未运行[/red]")
        return

    start_time = time.time()

    def generate_table() -> Table:
        table = Table(title="仿真监控", box=None)
        table.add_column("指标", style="cyan", width=20)
        table.add_column("值", style="white", width=50)

        stats = backend.get_stats()

        table.add_row("状态", f"[bold]{backend.state.name}[/bold]")
        table.add_row("仿真时间", f"{stats.total_time:.3f}s")
        table.add_row("总步数", str(stats.total_steps))
        table.add_row("实时因子", f"{stats.real_time_factor:.2f}x")
        table.add_row("步进耗时", f"{stats.step_time_ms:.2f}ms")
        table.add_row("物理耗时", f"{stats.physics_time_ms:.2f}ms")

        # 传感器数据
        try:
            sensor_data = backend.get_all_sensor_data()
            if sensor_data:
                for sd in sensor_data:
                    table.add_row(
                        f"传感器 [{sd.sensor_type.value}]",
                        f"时间={sd.timestamp:.3f}, "
                        f"形状={sd.data.shape if hasattr(sd.data, 'shape') else 'N/A'}"
                    )
        except Exception:
            pass

        # 关节状态
        if mgr.scene and mgr.scene.robots:
            for robot in mgr.scene.robots:
                try:
                    js = backend.get_joint_states(robot.name)
                    if js.get("positions"):
                        pos_str = ", ".join(
                            f"{k}={v:.4f}"
                            for k, v in list(js["positions"].items())[:4]
                        )
                        table.add_row(
                            f"关节 [{robot.name}]",
                            pos_str
                        )
                except Exception:
                    pass

        return table

    console.print("[cyan]开始监控 (Ctrl+C 停止)...[/cyan]")
    try:
        with Live(generate_table(), refresh_per_second=1 / interval, console=console) as live:
            while True:
                if duration > 0 and (time.time() - start_time) > duration:
                    break
                time.sleep(interval)
                live.update(generate_table())
    except KeyboardInterrupt:
        pass

    console.print("[yellow]监控已停止[/yellow]")


@app.command("scenes")
def sim_list_scenes() -> None:
    """列出可用场景。"""
    presets = list_presets()
    loader = SceneLoader()

    table = Table(title="可用场景", box=None)
    table.add_column("名称", style="cyan")
    table.add_column("类型", style="green")
    table.add_column("描述", style="white")
    table.add_column("机器人", justify="right")

    for name in presets:
        scene = loader.load(name)
        table.add_row(
            name,
            "预置",
            scene.description[:60],
            str(len(scene.robots)),
        )

    console.print(table)


@app.command("backends")
def sim_list_backends() -> None:
    """列出可用的仿真后端。"""
    backends = list_backends()

    if not backends:
        backends = ["mujoco", "isaac_sim"]

    table = Table(title="可用仿真后端", box=None)
    table.add_column("后端", style="cyan")
    table.add_column("状态", style="green")
    table.add_column("说明", style="white")

    for b in backends:
        try:
            if b == "mujoco":
                import mujoco
                status = "[green]✓ 可用[/green]"
                desc = "DeepMind MuJoCo 物理引擎"
            elif b == "isaac_sim":
                from omni.isaac.kit import SimulationApp
                status = "[green]✓ 可用[/green]"
                desc = "NVIDIA Isaac Sim (GPU 加速)"
            else:
                status = "[yellow]?[/yellow]"
                desc = "未知"
        except ImportError:
            status = "[red]✗ 未安装[/red]"
            if b == "mujoco":
                desc = "pip install mujoco"
            elif b == "isaac_sim":
                desc = "需安装 NVIDIA Isaac Sim"
            else:
                desc = ""

        table.add_row(b, status, desc)

    console.print(table)
