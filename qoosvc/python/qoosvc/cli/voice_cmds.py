# -*- coding: utf-8 -*-
"""语音交互命令"""

import typer
from rich.console import Console

app = typer.Typer(name="voice", help="语音交互")
console = Console()


@app.command("test")
def voice_test():
    """语音交互测试（录音→识别→合成）"""
    console.print("[green]语音交互测试模式[/green]")
    console.print("  唤醒词: Hey QooBot (zh)")
    console.print("  ASR 引擎: Whisper.cpp")
    console.print("  TTS 引擎: Piper")
    console.print("[dim]按 Ctrl+C 退出[/dim]")


@app.command("asr")
def asr_file(audio_file: str = typer.Argument(..., help="音频文件路径")):
    """离线 ASR 识别音频文件"""
    console.print(f"[cyan]ASR 识别: {audio_file}[/cyan]")
    console.print("  结果: (需要实际引擎支持)")


@app.command("tts")
def tts_synthesize(
    text: str = typer.Argument(..., help="要合成的文本"),
    output: str = typer.Option("output.wav", "--output", "-o", help="输出文件路径"),
):
    """文字转语音"""
    console.print(f"[cyan]TTS 合成: '{text}' → {output}[/cyan]")
    console.print("  (需要 Piper TTS 引擎支持)")
