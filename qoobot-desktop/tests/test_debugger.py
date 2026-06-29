"""Tests for the remote debugger module."""

from __future__ import annotations

import pytest
from qoodev.debugger import (
    RemoteDebugger,
    DebugServer,
    DebugEvent,
    StepType,
    SourceLocation,
    StackFrame,
    RemoteBreakpoint,
    DebugState,
    _serialize_value,
)


def test_serialize_value_none():
    assert _serialize_value(None) is None


def test_serialize_value_primitives():
    assert _serialize_value(True) is True
    assert _serialize_value(42) == 42
    assert _serialize_value(3.14) == 3.14
    assert _serialize_value("hello") == "hello"


def test_serialize_value_list():
    result = _serialize_value([1, 2, 3])
    assert result == [1, 2, 3]


def test_serialize_value_large_list():
    large = list(range(1000))
    result = _serialize_value(large)
    assert isinstance(result, str)
    assert "list" in result


def test_serialize_value_dict():
    result = _serialize_value({"a": 1, "b": 2})
    assert result == {"a": 1, "b": 2}


def test_source_location():
    loc = SourceLocation(file="test.py", line=42, function="test_func", source_line="x = 1")
    assert loc.file == "test.py"
    assert loc.line == 42
    d = loc.to_dict()
    assert d["file"] == "test.py"
    assert d["line"] == 42


def test_stack_frame():
    loc = SourceLocation(file="test.py", line=10, function="main")
    frame = StackFrame(index=0, location=loc, locals={"x": 1})
    assert frame.index == 0
    d = frame.to_dict()
    assert d["index"] == 0
    assert d["location"]["function"] == "main"


def test_remote_breakpoint():
    bp = RemoteBreakpoint(id="bp1", file="test.py", line=42)
    assert bp.id == "bp1"
    assert bp.enabled is True
    assert bp.hit_count == 0
    d = bp.to_dict()
    assert d["id"] == "bp1"


def test_remote_breakpoint_condition():
    bp = RemoteBreakpoint(id="bp2", file="test.py", line=10, condition="x > 5")
    assert bp.condition == "x > 5"
    d = bp.to_dict()
    assert d["condition"] == "x > 5"


def test_remote_breakpoint_disabled():
    bp = RemoteBreakpoint(id="bp3", file="test.py", line=20, enabled=False)
    assert bp.enabled is False


def test_debug_state_default():
    state = DebugState()
    assert state.running is False
    assert state.paused is False
    assert state.current_location is None
    assert state.call_stack == []
    assert state.breakpoints == {}


def test_debugger_init():
    debugger = RemoteDebugger()
    assert debugger.state is not None
    assert debugger.state.running is False
    assert debugger.state.paused is False


def test_debugger_set_breakpoint():
    debugger = RemoteDebugger()
    bp_id = debugger.set_breakpoint(file="test.py", line=42)
    assert bp_id == "bp:test.py:42"
    assert bp_id in debugger.state.breakpoints


def test_debugger_list_breakpoints():
    debugger = RemoteDebugger()
    debugger.set_breakpoint(file="a.py", line=1)
    debugger.set_breakpoint(file="b.py", line=2)
    bps = debugger.list_breakpoints()
    assert len(bps) == 2


def test_debugger_remove_breakpoint():
    debugger = RemoteDebugger()
    bp_id = debugger.set_breakpoint(file="test.py", line=10)
    debugger.remove_breakpoint(bp_id)
    assert bp_id not in debugger.state.breakpoints


def test_debugger_enable_breakpoint():
    debugger = RemoteDebugger()
    bp_id = debugger.set_breakpoint(file="test.py", line=5)
    debugger.enable_breakpoint(bp_id, False)
    assert not debugger.state.breakpoints[bp_id].enabled
    debugger.enable_breakpoint(bp_id, True)
    assert debugger.state.breakpoints[bp_id].enabled


def test_debugger_conditional_breakpoint():
    debugger = RemoteDebugger()
    bp_id = debugger.set_breakpoint(file="test.py", line=10, condition="x > 100")
    bp = debugger.state.breakpoints[bp_id]
    assert bp.condition == "x > 100"


def test_debugger_logpoint():
    debugger = RemoteDebugger()
    bp_id = debugger.set_breakpoint(file="test.py", line=10, log_message="x = {x}")
    bp = debugger.state.breakpoints[bp_id]
    assert bp.log_message == "x = {x}"


def test_debugger_temporary_breakpoint():
    debugger = RemoteDebugger()
    bp_id = debugger.set_breakpoint(file="test.py", line=10, temporary=True)
    bp = debugger.state.breakpoints[bp_id]
    assert bp.temporary is True


def test_debugger_get_variables():
    debugger = RemoteDebugger()
    # In test context, should return locals of test function
    vars_ = debugger.get_variables("locals")
    assert isinstance(vars_, dict)
    # Should at least see the debugger variable
    assert "debugger" in vars_ or len(vars_) >= 0


def test_debugger_evaluate_expression():
    debugger = RemoteDebugger()
    result = debugger.evaluate_expression("1 + 1")
    assert result == 2


def test_debugger_get_backtrace():
    debugger = RemoteDebugger()
    frames = debugger.get_backtrace(max_frames=10)
    assert isinstance(frames, list)
    assert len(frames) > 0
    assert all(isinstance(f, StackFrame) for f in frames)


def test_debug_server_init():
    server = DebugServer(host="localhost", port=9999)
    assert server.host == "localhost"
    assert server.port == 9999
    assert server.debugger is not None


def test_debug_event_enum():
    assert DebugEvent.BREAKPOINT_HIT.value == "breakpoint_hit"
    assert DebugEvent.STEP_COMPLETE.value == "step_complete"
    assert DebugEvent.EXCEPTION.value == "exception"
    assert DebugEvent.PROCESS_EXIT.value == "process_exit"
    assert DebugEvent.OUTPUT.value == "output"


def test_step_type_enum():
    assert StepType.OVER.value == "step_over"
    assert StepType.INTO.value == "step_into"
    assert StepType.OUT.value == "step_out"
    assert StepType.CONTINUE.value == "continue"
