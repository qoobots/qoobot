# -*- coding: utf-8 -*-
"""服务管理命令"""

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="svc", help="服务管理")
console = Console()


@app.command("list")
def list_services():
    """列出所有系统服务及状态"""
    table = Table(title="QooBot 系统服务")
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


@app.command("start")
def start_service(service: str = typer.Argument(..., help="要启动的服务名称")):
    """启动指定服务"""
    console.print(f"[green]启动 {service}...[/green]")


@app.command("stop")
def stop_service(service: str = typer.Argument(..., help="要停止的服务名称")):
    """停止指定服务"""
    console.print(f"[yellow]停止 {service}...[/yellow]")


@app.command("restart")
def restart_service(service: str = typer.Argument(..., help="要重启的服务名称")):
    """重启指定服务"""
    console.print(f"[blue]重启 {service}...[/blue]")


@app.command("status")
def service_status(service: str = typer.Argument(..., help="服务名称")):
    """查看服务详细状态"""
    console.print(f"[cyan]{service}[/cyan]: RUNNING")
