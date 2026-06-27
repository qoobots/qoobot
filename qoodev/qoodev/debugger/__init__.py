"""远程调试器 — 断点调试、条件断点、Python/C++ 混合栈追踪。

通过 WebSocket 连接到运行中的技能进程，支持:
  - 远程断点设置/移除
  - 条件断点 (变量值、表达式)
  - 步进 (step over / step into / step out)
  - 变量检查 (局部/全局)
  - 调用栈追踪
  - Python + C++ 混合调试
"""

import asyncio
import json
import threading
import sys
import inspect
import linecache
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import traceback


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class DebugEvent(Enum):
    BREAKPOINT_HIT = "breakpoint_hit"
    STEP_COMPLETE = "step_complete"
    EXCEPTION = "exception"
    PROCESS_EXIT = "process_exit"
    OUTPUT = "output"


class StepType(Enum):
    OVER = "step_over"
    INTO = "step_into"
    OUT = "step_out"
    CONTINUE = "continue"


@dataclass
class SourceLocation:
    """源码位置"""
    file: str
    line: int
    function: str = ""
    source_line: str = ""

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "line": self.line,
            "function": self.function,
            "source": self.source_line,
        }


@dataclass
class StackFrame:
    """调用栈帧"""
    index: int
    location: SourceLocation
    locals: Dict[str, Any] = field(default_factory=dict)
    globals_: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "location": self.location.to_dict(),
            "locals": {k: _serialize_value(v) for k, v in self.locals.items()},
            "globals": {k: _serialize_value(v) for k, v in self.globals_.items()},
        }


@dataclass
class RemoteBreakpoint:
    """远程断点"""
    id: str
    file: str
    line: int
    condition: Optional[str] = None    # Python 表达式
    enabled: bool = True
    hit_count: int = 0
    temporary: bool = False             # 命中一次后自动删除
    log_message: Optional[str] = None   # 日志断点 (不暂停，仅输出)
    ignore_count: int = 0               # 前 N 次忽略

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "file": self.file,
            "line": self.line,
            "condition": self.condition,
            "enabled": self.enabled,
            "hit_count": self.hit_count,
            "temporary": self.temporary,
            "log_message": self.log_message,
        }


@dataclass
class DebugState:
    """调试器状态"""
    running: bool = False
    paused: bool = False
    current_location: Optional[SourceLocation] = None
    call_stack: List[StackFrame] = field(default_factory=list)
    breakpoints: Dict[str, RemoteBreakpoint] = field(default_factory=dict)
    last_event: Optional[DebugEvent] = None


def _serialize_value(value: Any) -> Any:
    """安全序列化变量值"""
    if value is None:
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        if len(str(value)) > 500:
            return f"<{type(value).__name__}: {len(value)} items>"
        return [_serialize_value(v) for v in value[:20]]
    if isinstance(value, dict):
        if len(str(value)) > 500:
            return f"<dict: {len(value)} keys>"
        return {str(k): _serialize_value(v) for k, v in list(value.items())[:20]}
    try:
        s = str(value)
        if len(s) > 200:
            s = s[:200] + "..."
        return f"<{type(value).__name__}> {s}"
    except Exception:
        return f"<{type(value).__name__}>"


# ---------------------------------------------------------------------------
# Python 调试钩子 (sys.settrace)
# ---------------------------------------------------------------------------

class PythonDebugHook:
    """Python 调试钩子 — 使用 sys.settrace 实现断点和步进"""

    def __init__(self, debugger: "RemoteDebugger"):
        self.debugger = debugger
        self._original_trace = None
        self._skip_files: Set[str] = set()  # 跳过系统库

    def install(self):
        """安装调试钩子"""
        self._original_trace = sys.gettrace()
        sys.settrace(self._trace_dispatch)
        # 设置线程追踪
        threading.settrace(self._trace_dispatch)

    def uninstall(self):
        """卸载调试钩子"""
        sys.settrace(self._original_trace)
        threading.settrace(None)

    def _trace_dispatch(self, frame, event, arg):
        """追踪分发器"""
        if self._should_skip(frame):
            return self._trace_dispatch

        filename = frame.f_code.co_filename
        lineno = frame.f_lineno
        func_name = frame.f_code.co_name

        if event == "line":
            return self._handle_line(frame, filename, lineno, func_name)

        if event == "call":
            return self._handle_call(frame, filename, lineno, func_name)

        if event == "return":
            return self._handle_return(frame, filename, lineno, func_name, arg)

        if event == "exception":
            return self._handle_exception(frame, filename, lineno, func_name, arg)

        return self._trace_dispatch

    def _should_skip(self, frame) -> bool:
        """判断是否跳过此帧"""
        filename = frame.f_code.co_filename
        # 跳过系统库
        if "site-packages" in filename:
            return True
        if filename.startswith(sys.prefix):
            return True
        if "<" in filename:  # <stdin>, <string>, etc.
            return True
        return filename in self._skip_files

    def _handle_line(self, frame, filename, lineno, func_name):
        """行事件 — 检查断点"""
        loc = SourceLocation(
            file=filename,
            line=lineno,
            function=func_name,
            source_line=linecache.getline(filename, lineno).rstrip() if filename else "",
        )

        self.debugger.state.current_location = loc
        self.debugger._collect_stack(frame)

        # 检查断点
        for bp in list(self.debugger.state.breakpoints.values()):
            if not bp.enabled:
                continue
            if not self._match_location(bp, filename, lineno):
                continue

            if bp.ignore_count > 0:
                bp.ignore_count -= 1
                continue

            # 条件检查
            if bp.condition:
                try:
                    if not eval(bp.condition, frame.f_globals, frame.f_locals):
                        continue
                except Exception:
                    continue

            bp.hit_count += 1

            # 日志断点
            if bp.log_message:
                try:
                    msg = eval(f'f"{bp.log_message}"', frame.f_globals, frame.f_locals)
                    self.debugger._emit_event(DebugEvent.OUTPUT, data={"message": f"[logpoint] {msg}"})
                except Exception:
                    pass
                if bp.temporary:
                    del self.debugger.state.breakpoints[bp.id]
                return self._trace_dispatch  # 日志断点不暂停

            # 命中断点 — 暂停
            self.debugger.state.paused = True
            self.debugger._emit_event(DebugEvent.BREAKPOINT_HIT, data={
                "breakpoint": bp.to_dict(),
                "location": loc.to_dict(),
            })

            if bp.temporary:
                del self.debugger.state.breakpoints[bp.id]

            # 阻塞等待恢复
            self._wait_for_resume()
            break

        # 检查是否正在步进
        if self.debugger._step_state.get("active"):
            step_type = self.debugger._step_state["type"]
            if step_type == StepType.OVER:
                # 检查是否回到同层级
                if self._is_same_level(frame):
                    self._complete_step(loc)
            elif step_type == StepType.INTO:
                self._complete_step(loc)
            elif step_type == StepType.OUT:
                pass  # 在 _handle_return 中处理

        return self._trace_dispatch

    def _handle_call(self, frame, filename, lineno, func_name):
        return self._trace_dispatch

    def _handle_return(self, frame, filename, lineno, func_name, retval):
        if self.debugger._step_state.get("active") and \
           self.debugger._step_state.get("type") == StepType.OUT:
            loc = SourceLocation(file=filename, line=lineno, function=func_name)
            self._complete_step(loc)
        return self._trace_dispatch

    def _handle_exception(self, frame, filename, lineno, func_name, exc_info):
        exc_type, exc_value, exc_tb = exc_info
        self.debugger._emit_event(DebugEvent.EXCEPTION, data={
            "type": exc_type.__name__,
            "message": str(exc_value),
            "location": {
                "file": filename,
                "line": lineno,
                "function": func_name,
            },
            "traceback": traceback.format_exc(),
        })
        return self._trace_dispatch

    def _match_location(self, bp: RemoteBreakpoint, filename: str, lineno: int) -> bool:
        """检查断点位置是否匹配"""
        # 支持相对路径和文件名匹配
        if bp.file == filename:
            return bp.line == lineno
        if filename.endswith(bp.file):
            return bp.line == lineno
        if Path(filename).name == Path(bp.file).name:
            return bp.line == lineno
        return False

    def _is_same_level(self, frame) -> bool:
        """检查是否回到 step_over 的起始层级"""
        target_frame = self.debugger._step_state.get("frame")
        if target_frame is None:
            return True
        # 同函数同层级
        return frame.f_code == target_frame.f_code or frame.f_back is target_frame

    def _complete_step(self, loc: SourceLocation):
        """完成步进"""
        self.debugger.state.paused = True
        self.debugger._step_state = {"active": False}
        self.debugger._emit_event(DebugEvent.STEP_COMPLETE, data={
            "location": loc.to_dict(),
        })
        self._wait_for_resume()

    def _wait_for_resume(self):
        """阻塞等待恢复 (在 trace 函数中不能使用 asyncio)"""
        import time
        while self.debugger.state.paused:
            time.sleep(0.05)


# ---------------------------------------------------------------------------
# 远程调试器
# ---------------------------------------------------------------------------

class RemoteDebugger:
    """远程调试器 — 管理调试会话"""

    def __init__(self):
        self.state = DebugState()
        self.hook = PythonDebugHook(self)
        self._step_state: Dict[str, Any] = {"active": False}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._event_callbacks: Dict[DebugEvent, List[Callable]] = defaultdict(list)

    def attach(self):
        """附加到当前进程"""
        self.hook.install()
        self.state.running = True
        print("🐛 Debugger attached")

    def detach(self):
        """分离调试器"""
        self.hook.uninstall()
        self.state.running = False
        self.state.paused = False
        print("🐛 Debugger detached")

    # ---- 断点管理 ----

    def set_breakpoint(
        self,
        file: str,
        line: int,
        condition: Optional[str] = None,
        temporary: bool = False,
        log_message: Optional[str] = None,
    ) -> str:
        """设置断点"""
        bp_id = f"bp:{file}:{line}"
        bp = RemoteBreakpoint(
            id=bp_id,
            file=file,
            line=line,
            condition=condition,
            temporary=temporary,
            log_message=log_message,
        )
        self.state.breakpoints[bp_id] = bp
        return bp_id

    def remove_breakpoint(self, bp_id: str):
        """移除断点"""
        self.state.breakpoints.pop(bp_id, None)

    def list_breakpoints(self) -> List[RemoteBreakpoint]:
        return list(self.state.breakpoints.values())

    def enable_breakpoint(self, bp_id: str, enabled: bool = True):
        if bp_id in self.state.breakpoints:
            self.state.breakpoints[bp_id].enabled = enabled

    # ---- 执行控制 ----

    def step_over(self):
        """单步跳过"""
        self._step_state = {
            "active": True,
            "type": StepType.OVER,
            "frame": inspect.currentframe().f_back if inspect.currentframe() else None,
        }
        self.state.paused = False

    def step_into(self):
        """单步进入"""
        self._step_state = {
            "active": True,
            "type": StepType.INTO,
        }
        self.state.paused = False

    def step_out(self):
        """单步跳出"""
        self._step_state = {
            "active": True,
            "type": StepType.OUT,
        }
        self.state.paused = False

    def continue_(self):
        """继续执行"""
        self._step_state = {"active": False}
        self.state.paused = False

    def pause(self):
        """暂停执行"""
        self.state.paused = True

    # ---- 变量检查 ----

    def get_variables(self, scope: str = "locals") -> Dict[str, Any]:
        """获取当前作用域变量"""
        frame = inspect.currentframe()
        if frame is None:
            return {}

        target_frame = frame.f_back  # 跳过 get_variables 自身
        if target_frame is None:
            return {}

        if scope == "locals":
            return {k: _serialize_value(v) for k, v in target_frame.f_locals.items()}
        elif scope == "globals":
            return {k: _serialize_value(v) for k, v in target_frame.f_globals.items()}
        return {}

    def evaluate_expression(self, expression: str) -> Any:
        """在暂停帧中求值表达式"""
        frame = inspect.currentframe()
        if frame is None or frame.f_back is None:
            return None

        target_frame = frame.f_back
        try:
            result = eval(expression, target_frame.f_globals, target_frame.f_locals)
            return _serialize_value(result)
        except Exception as e:
            return f"Error: {e}"

    def get_backtrace(self, max_frames: int = 50) -> List[StackFrame]:
        """获取完整调用栈"""
        frames = []
        frame = inspect.currentframe()
        if frame:
            target = frame.f_back
            idx = 0
            while target and idx < max_frames:
                loc = SourceLocation(
                    file=target.f_code.co_filename,
                    line=target.f_lineno,
                    function=target.f_code.co_name,
                    source_line=linecache.getline(
                        target.f_code.co_filename, target.f_lineno
                    ).rstrip() if target.f_code.co_filename else "",
                )
                sf = StackFrame(
                    index=idx,
                    location=loc,
                    locals={k: _serialize_value(v) for k, v in target.f_locals.items()},
                    globals_={k: _serialize_value(v) for k, v in target.f_globals.items()},
                )
                frames.append(sf)
                target = target.f_back
                idx += 1

        return frames

    # ---- 事件 ----

    def on_event(self, event: DebugEvent, callback: Callable):
        self._event_callbacks[event].append(callback)

    def _emit_event(self, event: DebugEvent, data: Optional[Dict] = None):
        """发送调试事件"""
        for cb in self._event_callbacks.get(event, []):
            try:
                cb(event=event, data=data)
            except Exception:
                pass

    def _collect_stack(self, frame, max_frames: int = 20):
        """收集调用栈信息"""
        frames = []
        f = frame
        idx = 0
        while f and idx < max_frames:
            loc = SourceLocation(
                file=f.f_code.co_filename,
                line=f.f_lineno,
                function=f.f_code.co_name,
            )
            sf = StackFrame(index=idx, location=loc)
            frames.append(sf)
            f = f.f_back
            idx += 1
        self.state.call_stack = frames


# ---------------------------------------------------------------------------
# 调试服务器 (WebSocket)
# ---------------------------------------------------------------------------

class DebugServer:
    """WebSocket 调试服务器 — 连接 IDE 和运行时"""

    def __init__(self, host: str = "localhost", port: int = 5678):
        self.host = host
        self.port = port
        self.debugger = RemoteDebugger()
        self._clients: List[Any] = []
        self._server: Optional[Any] = None

    async def start(self):
        """启动调试服务器"""
        try:
            import websockets
        except ImportError:
            print("⚠️  websockets not installed. Install with: pip install websockets")
            print("   Debug server running in stub mode")
            return

        async def handler(websocket, path):
            self._clients.append(websocket)
            try:
                async for message in websocket:
                    await self._handle_message(websocket, message)
            finally:
                self._clients.remove(websocket)

        self._server = await websockets.serve(handler, self.host, self.port)
        print(f"🐛 Debug server listening on ws://{self.host}:{self.port}")

    async def stop(self):
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _handle_message(self, websocket, message: str):
        """处理调试协议消息"""
        try:
            msg = json.loads(message)
            cmd = msg.get("command", "")
            req_id = msg.get("request_id", 0)

            response = await self._execute_command(cmd, msg.get("arguments", {}))
            response["request_id"] = req_id
            response["command"] = cmd

            await websocket.send(json.dumps(response, default=str))
        except json.JSONDecodeError:
            await websocket.send(json.dumps({"error": "Invalid JSON"}))
        except Exception as e:
            await websocket.send(json.dumps({"error": str(e)}))

    async def _execute_command(self, cmd: str, args: Dict) -> Dict:
        """执行调试命令"""
        d = self.debugger

        if cmd == "attach":
            d.attach()
            return {"status": "attached"}

        if cmd == "detach":
            d.detach()
            return {"status": "detached"}

        if cmd == "set_breakpoint":
            bp_id = d.set_breakpoint(
                file=args["file"],
                line=args["line"],
                condition=args.get("condition"),
                temporary=args.get("temporary", False),
                log_message=args.get("log_message"),
            )
            return {"status": "ok", "breakpoint_id": bp_id}

        if cmd == "remove_breakpoint":
            d.remove_breakpoint(args["breakpoint_id"])
            return {"status": "ok"}

        if cmd == "list_breakpoints":
            return {"status": "ok", "breakpoints": [bp.to_dict() for bp in d.list_breakpoints()]}

        if cmd == "step_over":
            d.step_over()
            return {"status": "ok"}

        if cmd == "step_into":
            d.step_into()
            return {"status": "ok"}

        if cmd == "step_out":
            d.step_out()
            return {"status": "ok"}

        if cmd == "continue":
            d.continue_()
            return {"status": "ok"}

        if cmd == "pause":
            d.pause()
            return {"status": "ok"}

        if cmd == "stack_trace":
            frames = d.get_backtrace(args.get("max_frames", 50))
            return {"status": "ok", "frames": [f.to_dict() for f in frames]}

        if cmd == "variables":
            scope = args.get("scope", "locals")
            return {"status": "ok", "variables": d.get_variables(scope)}

        if cmd == "evaluate":
            result = d.evaluate_expression(args["expression"])
            return {"status": "ok", "result": result}

        if cmd == "state":
            return {
                "status": "ok",
                "state": {
                    "running": d.state.running,
                    "paused": d.state.paused,
                    "location": d.state.current_location.to_dict() if d.state.current_location else None,
                }
            }

        return {"error": f"Unknown command: {cmd}"}

    async def broadcast_event(self, event: str, data: Dict):
        """广播事件给所有连接的客户端"""
        for client in self._clients:
            try:
                await client.send(json.dumps({
                    "type": "event",
                    "event": event,
                    "data": data,
                }, default=str))
            except Exception:
                pass
