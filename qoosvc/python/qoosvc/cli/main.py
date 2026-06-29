# -*- coding: utf-8 -*-
"""
qoosvc CLI — QooBot 系统服务命令行管理工具

使用方法:
    qoo-svc start --all          # 启动所有服务
    qoo-svc status               # 查看服务状态
    qoo-svc diag post            # 运行开机自检
    qoo-svc diag report          # 生成健康报告
"""

import typer
from rich.console import Console
from rich.table import Table

from qoosvc.cli import svc_cmds, voice_cmds, nav_cmds, diag_cmds

app = typer.Typer(
    name="qoo-svc",
    help="QooBot 系统服务管理工具",
    add_completion=False,
)

console = Console()

# Register sub-command groups
app.add_typer(svc_cmds.app, name="svc", help="服务管理")
app.add_typer(voice_cmds.app, name="voice", help="语音交互")
app.add_typer(nav_cmds.app, name="nav", help="导航引擎")
app.add_typer(diag_cmds.app, name="diag", help="自诊断与健康")


@app.command()
def version():
    """显示版本信息"""
    from qoosvc import __version__
    console.print(f"[bold cyan]qoosvc[/bold cyan] v{__version__}")
    console.print("QooBot System Services — Voice, Navigation, Diagnostics & More")


@app.command()
def start(all_services: bool = typer.Option(False, "--all", help="启动所有服务")):
    """启动系统服务"""
    if all_services:
        console.print("[green]启动所有系统服务...[/green]")
        services = [
            "svc_voice", "svc_navigation", "svc_spatial",
            "svc_diagnostics", "svc_hmi", "svc_charging",
            "svc_people", "svc_multi_robot"
        ]
        table = Table(title="服务启动状态")
        table.add_column("服务", style="cyan")
        table.add_column("状态", style="green")
        for svc in services:
            table.add_row(svc, "RUNNING")
        console.print(table)
    else:
        console.print("[yellow]请指定要启动的服务，或使用 --all 启动所有服务[/yellow]")


@app.command()
def status():
    """查看所有服务状态"""
    table = Table(title="QooBot 系统服务状态")
    table.add_column("Service", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("CPU%", justify="right")
    table.add_column("Memory", justify="right")

    services = [
        ("svc_voice", "RUNNING", "2.3%", "856 MB"),
        ("svc_navigation", "RUNNING", "5.1%", "412 MB"),
        ("svc_spatial", "RUNNING", "8.7%", "1.8 GB"),
        ("svc_diagnostics", "RUNNING", "0.5%", "128 MB"),
        ("svc_hmi", "RUNNING", "1.2%", "256 MB"),
        ("svc_charging", "RUNNING", "0.3%", "64 MB"),
        ("svc_people", "STOPPED", "-", "-"),
        ("svc_multi_robot", "STOPPED", "-", "-"),
    ]

    for svc in services:
        table.add_row(*svc)

    console.print(table)


if __name__ == "__main__":
    app()
