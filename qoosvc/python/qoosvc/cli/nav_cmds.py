# -*- coding: utf-8 -*-
"""导航引擎命令"""

import typer
from rich.console import Console

app = typer.Typer(name="nav", help="导航引擎")
console = Console()


@app.command("go")
def nav_go(
    x: float = typer.Option(..., "--x", help="目标 X 坐标 (米)"),
    y: float = typer.Option(..., "--y", help="目标 Y 坐标 (米)"),
):
    """导航到指定坐标"""
    console.print(f"[green]导航到 ({x}, {y})[/green]")
    console.print("  (需要导航服务运行中)")


@app.command("cancel")
def nav_cancel():
    """取消当前导航"""
    console.print("[yellow]取消导航[/yellow]")


@app.command("path")
def nav_path():
    """显示当前规划路径"""
    console.print("[cyan]当前路径:[/cyan]")
    console.print("  路径点: 0")
    console.print("  (需要导航服务运行中)")


@app.command("explore")
def nav_explore(duration: int = typer.Option(300, "--duration", help="探索时长 (秒)")):
    """启动自主探索"""
    console.print(f"[green]启动自主探索 (时长: {duration}s)[/green]")
    console.print("  (需要 SLAM + 导航服务运行中)")
