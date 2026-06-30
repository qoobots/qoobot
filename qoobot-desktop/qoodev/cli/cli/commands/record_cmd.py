"""qoo record CLI — 数据录制与回放命令"""

from pathlib import Path
from typer import Typer, Option, Argument
from typing import Optional, List
from datetime import datetime
import uuid

app = Typer(name="record", help="Record and replay sensor/control data")


@app.command("start")
def start_record(
    output: str = Argument(..., help="Output .qoodata file path"),
    task: str = Option("demo", "--task", "-t", help="Task name"),
    operator: str = Option("", "--operator", help="Operator name"),
    robot: str = Option("", "--robot", help="Robot model"),
    scene: str = Option("", "--scene", help="Scene name"),
    description: str = Option("", "--description", "-d", help="Task description"),
    tags: Optional[List[str]] = Option(None, "--tag", help="Tags"),
):
    """Start recording sensor/control data"""
    from qoodev.data_recorder import DataRecorder, EpisodeMetadata, TeleoperationRecorder

    episode_id = f"ep_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    metadata = EpisodeMetadata(
        episode_id=episode_id,
        task_name=task,
        description=description,
        operator=operator,
        robot_model=robot,
        scene_name=scene,
        tags=list(tags) if tags else [],
    )

    recorder = DataRecorder(Path(output))
    recorder.open(metadata)
    teleop = TeleoperationRecorder(recorder)

    print(f"🔴 Recording started: {output}")
    print(f"   Episode: {episode_id}")
    print(f"   Task: {task}")
    print(f"   Press Ctrl+C to stop recording")

    try:
        # 保持录制状态 (实际使用时连接到传感器/控制流)
        import time
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n⏹ Stopping...")
    finally:
        recorder.close()
        print(f"✅ Recording saved: {output}")


@app.command("inspect")
def inspect_record(
    data_path: str = Argument(..., help="Path to .qoodata file"),
    stats: bool = Option(False, "--stats", "-s", help="Show statistics"),
    markers: bool = Option(False, "--markers", "-m", help="Show markers"),
    head: int = Option(0, "--head", help="Show first N frames"),
):
    """Inspect a .qoodata recording"""
    from qoodev.data_recorder import DataReader, DataType

    path = Path(data_path)
    if not path.exists():
        print(f"❌ File not found: {data_path}")
        raise SystemExit(1)

    reader = DataReader(path)
    reader.open()

    print(f"📁 {data_path}")
    print(f"   Episode: {reader._metadata.get('episode', {}).get('id', 'N/A')}")
    print(f"   Task:    {reader._metadata.get('episode', {}).get('task', 'N/A')}")
    print()

    if stats:
        s = reader.get_stats()
        print("📊 Statistics:")
        print(f"   Total frames: {s['total_frames']}")
        print(f"   Duration:     {s['duration']:.2f}s")
        print(f"   Avg FPS:      {s['avg_fps']:.1f}")
        print(f"   By type:")
        for dtype, count in s['by_type'].items():
            print(f"     {dtype}: {count}")

    if markers:
        print("\n🏷 Markers:")
        for marker in reader.markers():
            print(f"   [{marker['timestamp']:.2f}s] {marker['label']}")

    if head > 0:
        print(f"\n📋 First {head} frames:")
        for i, frame in enumerate(reader.frames()):
            if i >= head:
                break
            print(f"   [{frame.timestamp:.3f}s] {frame.dtype.name} ({len(frame.payload)} bytes)")

    reader.close()


@app.command("replay")
def replay(
    data_path: str = Argument(..., help="Path to .qoodata file"),
    speed: float = Option(1.0, "--speed", "-s", help="Playback speed (1.0=normal)"),
    loop: bool = Option(False, "--loop", "-l", help="Loop playback"),
    start_time: float = Option(0.0, "--start", help="Start time (seconds)"),
    end_time: float = Option(0.0, "--end", help="End time (seconds, 0=to end)"),
    bp_marker: Optional[str] = Option(None, "--bp-marker", help="Break at marker label"),
    bp_time: Optional[float] = Option(None, "--bp-time", help="Break at timestamp"),
    bp_type: Optional[str] = Option(None, "--bp-type", help="Break at frame type"),
):
    """Replay a recorded session"""
    from qoodev.data_recorder.replay import PlaybackEngine, BreakpointFactory

    engine = PlaybackEngine(Path(data_path))

    print(f"▶ Replaying: {data_path}")
    print(f"   Frames: {engine.total_frames}")
    print(f"   Duration: {engine.duration:.2f}s")
    print(f"   Speed: {speed}x")

    # 设置断点
    if bp_marker:
        engine.add_breakpoint(BreakpointFactory.at_marker(bp_marker))
    if bp_time is not None:
        engine.add_breakpoint(BreakpointFactory.at_time(bp_time))
    if bp_type:
        from qoodev.data_recorder import DataType
        engine.add_breakpoint(BreakpointFactory.at_frame_type(DataType[bp_type.upper()]))

    # 事件回调
    engine.on("frame", lambda frame, position: print(
        f"   [{position.timestamp:.3f}s] {frame.dtype.name}"
    ) if frame.dtype.name == "MARKER" else None)

    engine.on("breakpoint_hit", lambda breakpoint, frame: print(
        f"\n🔴 Breakpoint hit: {breakpoint.id}"
    ))

    engine.on("playback_end", lambda: print("\n⏹ Playback ended"))

    # 跳转到起始位置
    if start_time > 0:
        engine.seek(timestamp=start_time)

    engine.set_speed(speed)
    engine.set_loop(loop)
    engine.play()

    try:
        import time
        while engine.state.name != "STOPPED":
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n⏹ Stopped")
    finally:
        engine.close()


@app.command("export")
def export_data(
    data_path: str = Argument(..., help="Path to .qoodata file"),
    format: str = Option("jsonl", "--format", "-f", help="Export format: jsonl, hdf5"),
    output: Optional[str] = Option(None, "--output", "-o", help="Output path"),
    include_types: Optional[List[str]] = Option(None, "--include", help="Frame types to include"),
):
    """Export recording to other formats"""
    from qoodev.data_recorder import DataExporter, DataType

    path = Path(data_path)
    out = Path(output) if output else path.with_suffix(f".{format}")

    type_filters = None
    if include_types:
        type_filters = [DataType[t.upper()] for t in include_types]

    if format == "jsonl":
        DataExporter.to_jsonl(path, out, type_filters)
    elif format == "hdf5":
        DataExporter.to_hdf5(path, out)
    else:
        print(f"❌ Unsupported format: {format}")
        raise SystemExit(1)


@app.command("compare")
def compare(
    data_paths: List[str] = Argument(..., help="Paths to .qoodata files to compare"),
):
    """Compare multiple recordings"""
    from qoodev.data_recorder import DataReader

    for dp in data_paths:
        path = Path(dp)
        if not path.exists():
            print(f"❌ File not found: {dp}")
            continue

        reader = DataReader(path)
        reader.open()
        stats = reader.get_stats()
        print(f"\n📁 {path.name}")
        print(f"   Frames:  {stats['total_frames']}")
        print(f"   Duration: {stats['duration']:.2f}s")
        print(f"   FPS:     {stats['avg_fps']:.1f}")
        print(f"   Types:   {', '.join(stats['by_type'].keys())}")
        print(f"   Markers: {len(stats['markers'])}")
        reader.close()
