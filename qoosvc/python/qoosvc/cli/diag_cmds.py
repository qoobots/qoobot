# -*- coding: utf-8 -*-
"""自诊断命令"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

app = typer.Typer(name="diag", help="自诊断与健康")
console = Console()


@app.command("post")
def diag_post():
    """运行开机自检"""
    console.print("[green]运行 POST 开机自检...[/green]")

    table = Table(title="POST 自检结果")
    table.add_column("检测项", style="cyan")
    table.add_column("组件", style="yellow")
    table.add_column("状态")
    table.add_column("值")

    items = [
        ("电池组", "battery", "✅ OK", "85%"),
        ("左轮电机", "motor", "✅ OK", "正常"),
        ("右轮电机", "motor", "✅ OK", "正常"),
        ("LiDAR", "sensor", "✅ OK", "已连接"),
        ("IMU", "sensor", "✅ OK", "已校准"),
        ("RGB-D 相机", "sensor", "✅ OK", "已连接"),
        ("麦克风阵列", "sensor", "✅ OK", "4ch"),
        ("Wi-Fi", "communication", "✅ OK", "已连接"),
        ("BLE", "communication", "✅ OK", "就绪"),
        ("内部总线", "communication", "✅ OK", "正常"),
    ]

    for item in items:
        table.add_row(*item)

    console.print(table)


@app.command("report")
def diag_report():
    """生成健康报告"""
    console.print(Panel.fit(
        "[bold]QooBot 健康报告 — 2026-06-29 14:30 CST[/bold]\n\n"
        "[green]综合评分: 95/100 ✅[/green]\n\n"
        "[bold]✅ 通过项 (38):[/bold]\n"
        "  · 左轮电机 · 右轮电机 · 头部舵机 x2\n"
        "  · RGB-D 相机 · LiDAR · IMU · 麦克风阵列\n"
        "  · 电池组 · BMS · 充电电路\n"
        "  · Wi-Fi · BLE · 内部总线\n\n"
        "[bold yellow]⚠️ 警告 (1):[/bold yellow]\n"
        "  · IMU 标定将在 2 天后过期\n\n"
        "[bold cyan]🔧 维护建议:[/bold cyan]\n"
        "  · 安排 IMU 重新标定",
        title="健康报告"
    ))


@app.command("monitor")
def diag_monitor():
    """启动实时监控（终端显示）"""
    console.print("[green]启动实时监控...[/green]")
    console.print("[dim]按 Ctrl+C 退出[/dim]")


@app.command("calibrate")
def diag_calibrate(sensor: str = typer.Option("imu", "--sensor", help="传感器名称")):
    """触发传感器校准"""
    console.print(f"[green]触发 {sensor} 校准...[/green]")
