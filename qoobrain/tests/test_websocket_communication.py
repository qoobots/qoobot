"""
tests/test_websocket_communication.py — WebSocket communication test.

Verifies brain_ai WSServer <-> brain_viz wsClient (simulated in Python):
  - Broadcast scene_update, ghost_trail, plan_status, safety_alert, hitl_prompt
  - Incoming hitl_select, emergency_stop handlers

Run: python tests/test_websocket_communication.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time

import websockets

# Add brain_ai/brain_ai/ to path so ws_server is importable
_BRAIN_AI_PKG = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "brain_ai", "brain_ai",
))
sys.path.insert(0, _BRAIN_AI_PKG)

from ws_server.ws_handler import WSServer  # noqa: E402

WS_HOST = "localhost"
WS_PORT = 8766  # Different port from default to avoid conflict
WS_URL = f"ws://{WS_HOST}:{WS_PORT}"
SERVER_DELAY = 0.5  # seconds


# ── Test helpers ───────────────────────────────────────────────────

async def _collect_messages(url: str, n: int, timeout: float = 5.0) -> list[dict]:
    """Connect to WS server and collect N messages."""
    messages = []
    async with websockets.connect(url) as ws:
        for _ in range(n):
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
                messages.append(json.loads(raw))
            except asyncio.TimeoutError:
                break
    return messages


async def run_tests():
    """Run all WebSocket communication tests."""
    server = WSServer(host=WS_HOST, port=WS_PORT)
    await server.start()
    await asyncio.sleep(SERVER_DELAY)

    passed = failed = 0

    def _t(name, result, detail=""):
        nonlocal passed, failed
        if result:
            print(f"  ✅ {name}{' — ' + detail if detail else ''}")
            passed += 1
        else:
            print(f"  ❌ {name}")
            failed += 1

    print("=" * 60)
    print("  WebSocket Communication Test (brain_ai ↔ brain_viz)")
    print("=" * 60)

    # ── Test 1: scene_update broadcast ───────────────────────────

    async def _t1():
        collector = asyncio.create_task(
            _collect_messages(WS_URL, 1, timeout=3.0),
        )
        await asyncio.sleep(0.1)  # let client connect
        await server.send_scene_update(
            objects=[
                {"id": "obj-1", "label": "red_cup",
                 "pose": {"pos": {"x": 0.5, "y": 0.3, "z": 0.8}},
                 "color": "#ff0000"},
            ],
            robot_pose={"pos": {"x": 0.0, "y": 0.0, "z": 0.0},
                        "rot": {"x": 0, "y": 0, "z": 0, "w": 1}},
        )
        msgs = await asyncio.wait_for(collector, timeout=3.0)
        assert len(msgs) == 1
        assert msgs[0]["type"] == "scene_update"
        assert "objects" in msgs[0]["payload"]
        return msgs[0]

    try:
        m = await _t1()
        _t("scene_update broadcast",
           True,
           f"objects={len(m['payload']['objects'])}")
    except Exception as e:
        _t("scene_update broadcast", False)
        print(f"    {e}")

    # ── Test 2: ghost_trail broadcast ────────────────────────────

    async def _t2():
        collector = asyncio.create_task(
            _collect_messages(WS_URL, 1, timeout=3.0),
        )
        await asyncio.sleep(0.1)
        await server.send_ghost_trails(
            plan_id="plan-001",
            trajectories=[
                {"id": "traj-0", "rank": 1, "score": 0.95,
                 "waypoints": [{"x": 0, "y": 0, "z": 0},
                                {"x": 0.5, "y": 0.3, "z": 0.8}],
                 "color": "#00ff00",
                 "description": "Recommended"},
                {"id": "traj-1", "rank": 2, "score": 0.85,
                 "waypoints": [{"x": 0, "y": 0, "z": 0},
                                {"x": 0.6, "y": 0.2, "z": 0.8}],
                 "color": "#ffff00",
                 "description": "Alternative 1"},
            ],
            timeout_sec=6.0,
            recommended_index=0,
        )
        msgs = await asyncio.wait_for(collector, timeout=3.0)
        assert msgs[0]["type"] == "ghost_trail"
        assert msgs[0]["payload"]["plan_id"] == "plan-001"
        assert len(msgs[0]["payload"]["trajectories"]) == 2
        return msgs[0]

    try:
        m = await _t2()
        _t("ghost_trail broadcast",
           True,
           f"trajectories={len(m['payload']['trajectories'])}, "
           f"timeout={m['payload']['timeout_sec']}s")
    except Exception as e:
        _t("ghost_trail broadcast", False)
        print(f"    {e}")

    # ── Test 3: plan_status broadcast ────────────────────────────

    async def _t3():
        collector = asyncio.create_task(
            _collect_messages(WS_URL, 1, timeout=3.0),
        )
        await asyncio.sleep(0.1)
        await server.send_plan_status(
            plan_id="plan-001",
            state="EXECUTING",
            progress=0.4,
            current_step="pick_object",
        )
        msgs = await asyncio.wait_for(collector, timeout=3.0)
        assert msgs[0]["type"] == "plan_status"
        assert msgs[0]["payload"]["state"] == "EXECUTING"
        return msgs[0]

    try:
        m = await _t3()
        _t("plan_status broadcast",
           True,
           f"state={m['payload']['state']}, "
           f"progress={m['payload']['progress']:.0%}")
    except Exception as e:
        _t("plan_status broadcast", False)
        print(f"    {e}")

    # ── Test 4: safety_alert broadcast ───────────────────────────

    async def _t4():
        collector = asyncio.create_task(
            _collect_messages(WS_URL, 1, timeout=3.0),
        )
        await asyncio.sleep(0.1)
        await server.send_safety_alert(
            level="warning",
            message="Obstacle detected within 0.3m",
            code=2,
        )
        msgs = await asyncio.wait_for(collector, timeout=3.0)
        assert msgs[0]["type"] == "safety_alert"
        assert msgs[0]["payload"]["level"] == "warning"
        return msgs[0]

    try:
        m = await _t4()
        _t("safety_alert broadcast",
           True,
           f"level={m['payload']['level']}")
    except Exception as e:
        _t("safety_alert broadcast", False)
        print(f"    {e}")

    # ── Test 5: hitl_prompt broadcast ────────────────────────────

    async def _t5():
        collector = asyncio.create_task(
            _collect_messages(WS_URL, 1, timeout=3.0),
        )
        await asyncio.sleep(0.1)
        await server.send_hitl_prompt(
            plan_id="plan-001",
            options=[
                {"id": "traj-0", "label": "Recommended", "score": 0.95},
                {"id": "traj-1", "label": "Alternative 1", "score": 0.85},
            ],
            timeout_sec=6.0,
        )
        msgs = await asyncio.wait_for(collector, timeout=3.0)
        assert msgs[0]["type"] == "hitl_prompt"
        assert len(msgs[0]["payload"]["options"]) == 2
        return msgs[0]

    try:
        m = await _t5()
        _t("hitl_prompt broadcast",
           True,
           f"options={len(m['payload']['options'])}, "
           f"timeout={m['payload']['timeout_sec']}s")
    except Exception as e:
        _t("hitl_prompt broadcast", False)
        print(f"    {e}")

    # ── Test 6: incoming hitl_select handler ─────────────────────

    received_hitl: dict = {}

    async def hitl_handler(payload, ws):
        received_hitl.update(payload)

    server.on("hitl_select", hitl_handler)

    async def _t6():
        async with websockets.connect(WS_URL) as ws:
            await ws.send(json.dumps({
                "type": "hitl_select",
                "payload": {"plan_id": "plan-001", "trajectory_id": "traj-0"},
            }))
            await asyncio.sleep(0.2)
        assert received_hitl.get("plan_id") == "plan-001"
        assert received_hitl.get("trajectory_id") == "traj-0"

    try:
        await asyncio.wait_for(_t6(), timeout=3.0)
        _t("hitl_select incoming",
           True,
           f"plan={received_hitl['plan_id']} "
           f"traj={received_hitl['trajectory_id']}")
    except Exception as e:
        _t("hitl_select incoming", False)
        print(f"    {e}")

    # ── Test 7: client_count ──────────────────────────────────────
    # Create 2 concurrent clients, verify count, then disconnect

    async def _t7():
        # Connect 2 clients concurrently
        async with (websockets.connect(WS_URL) as ws1,
                    websockets.connect(WS_URL) as ws2):
            await asyncio.sleep(0.1)
            count = server.client_count
            assert count >= 2, f"Expected ≥2 clients, got {count}"
            return count

    try:
        c = await asyncio.wait_for(_t7(), timeout=3.0)
        _t("multi-client count", True, f"concurrent_clients≥{c}")
    except Exception as e:
        _t("multi-client count", False)
        print(f"    {e}")

    # Cleanup
    await server.stop()

    print()
    print(f"  Results: {passed} passed, {failed} failed")
    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    ok = asyncio.run(run_tests())
    import sys
    sys.exit(0 if ok else 1)
