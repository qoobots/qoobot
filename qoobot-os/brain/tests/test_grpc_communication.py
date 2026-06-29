"""
test_grpc_communication.py — Standalone integration test.
Verifies gRPC communication with the REAL proto-generated types.
"""
from __future__ import annotations

import logging
import os
import sys
import time
import unittest

import grpc

# ── Proto path setup ──────────────────────────────────────
# Generated code: brain_ai/brain_ai/proto_gen/brain_os/...
# The generated .py files do "from brain_os.cognition import types_pb2",
# so brain_os/ must be directly importable → add proto_gen/ to path.
_PROTO_GEN = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "brain_ai", "brain_ai", "proto_gen",
))
sys.path.insert(0, _PROTO_GEN)

from brain_os.cognition import (  # noqa: E402
    service_pb2,
    service_pb2_grpc,
)
from brain_os.cognition import types_pb2 as cognition_types
from brain_os.common import types_pb2 as common_types
from brain_os.decision import (  # noqa: E402
    service_pb2 as decision_svc_pb2,
    service_pb2_grpc as decision_svc_pb2_grpc,
)
from brain_os.decision import types_pb2 as decision_types
from brain_os.knowledge import (  # noqa: E402
    service_pb2 as knowledge_svc_pb2,
    service_pb2_grpc as knowledge_svc_pb2_grpc,
)
from brain_os.knowledge import types_pb2 as knowledge_types

logging.basicConfig(level=logging.WARNING, format="[%(levelname)s] %(name)s: %(message)s")

GRPC_ADDRESS = "localhost:50052"
SERVER_DELAY = 1.0


# ── Inline servicers (minimal stubs for testing) ──────────

class _CognitionServicer(service_pb2_grpc.CognitionServiceServicer):

    def ParseIntent(self, request, context):
        return service_pb2.ParseIntentResponse(
            status=common_types.Status(code=0, message="ok"),
            intent=cognition_types.Intent(
                type=cognition_types.INTENT_PICK,
                raw_text=request.utterance,
                confidence=0.92,
                language=request.language,
            ),
        )

    def DecomposeTask(self, request, context):
        import google.protobuf.struct_pb2 as spb
        params = spb.Struct()
        params["target"] = request.intent.raw_text
        return service_pb2.DecomposeTaskResponse(
            status=common_types.Status(code=0, message="ok"),
            plan_id="plan-001",
            subtasks=[
                cognition_types.SubTask(
                    task_id="sub-001",
                    skill_name="LocateObject",
                    parameters=params,
                    depends_on=[],
                    status=cognition_types.TASK_PENDING,
                ),
                cognition_types.SubTask(
                    task_id="sub-002",
                    skill_name="PickObject",
                    parameters=params,
                    depends_on=["sub-001"],
                    status=cognition_types.TASK_PENDING,
                ),
            ],
            rationale="Test decomposition.",
        )

    def GenerateBehaviorTree(self, request, context):
        return service_pb2.GenerateBTResponse(
            status=common_types.Status(code=0, message="ok"),
            tree=cognition_types.BehaviorTree(
                tree_id="bt-001",
                xml_str=(
                    '<root BTCPP_format="4">'
                    '  <BehaviorTree ID="MainTree">'
                    '    <Sequence name="seq">'
                    '      <LocateObject name="locate" object="test"/>'
                    '      <PickObject    name="pick"   object="test"/>'
                    '    </Sequence>'
                    '  </BehaviorTree>'
                    '</root>'
                ),
                description="Test BT",
            ),
        )

    def Clarify(self, request, context):
        return service_pb2.ClarifyResponse(
            status=common_types.Status(code=0, message="ok"),
            refined_intent=request.original_intent,
        )


class _DecisionServicer(decision_svc_pb2_grpc.DecisionServiceServicer):

    def ExecutePlan(self, request, context):
        return decision_svc_pb2.ExecutePlanResponse(
            status=common_types.Status(code=0, message="ok"),
            plan_id=request.plan_id or "plan-test-001",
            state=decision_types.PLAN_IDLE,
        )

    def GenerateTrajectories(self, request, context):
        trajs = []
        for i in range(max(1, min(request.num_candidates, 5))):
            t = decision_types.Trajectory(
                trajectory_id=f"traj-{i}",
                robot_id=request.robot_id,
                score=0.95 - i * 0.05,
                description=f"{'Recommended' if i == 0 else f'Candidate {i+1}'}",
                is_recommended=(i == 0),
            )
            trajs.append(t)
        return decision_svc_pb2.GenerateTrajectoriesResponse(
            status=common_types.Status(code=0, message="ok"),
            trajectories=trajs,
        )

    def SelectTrajectory(self, request, context):
        return decision_svc_pb2.SelectTrajectoryResponse(
            status=common_types.Status(code=0, message="selected"),
        )

    def CancelPlan(self, request, context):
        return decision_svc_pb2.CancelPlanResponse(
            status=common_types.Status(code=0, message="cancelled"),
        )

    def StreamPlanStatus(self, request, context):
        for i in range(5):
            if not context.is_active():
                break
            yield decision_types.PlanStatus(
                plan_id=request.plan_id,
                state=decision_types.PLAN_EXECUTING,
                progress=0.2 * i,
                current_step=f"step_{i}",
            )
            time.sleep(0.05)


class _KnowledgeServicer(knowledge_svc_pb2_grpc.KnowledgeServiceServicer):

    def __init__(self):
        self._episodes = []
        self._skills = []

    def SearchEpisodes(self, request, context):
        return knowledge_svc_pb2.SearchEpisodesResponse(
            status=common_types.Status(code=0, message="ok"),
            episodes=self._episodes[:request.top_k],
        )

    def StoreEpisode(self, request, context):
        ep = request.episode
        self._episodes.append(ep)
        return knowledge_svc_pb2.StoreEpisodeResponse(
            status=common_types.Status(code=0, message="stored"),
            episode_id=ep.robot_id or "ep-test-001",
        )

    def SearchKnowledge(self, request, context):
        return knowledge_svc_pb2.SearchKnowledgeResponse(
            status=common_types.Status(code=0, message="ok"),
        )

    def ListSkills(self, request, context):
        return knowledge_svc_pb2.ListSkillsResponse(
            status=common_types.Status(code=0, message="ok"),
            skills=self._skills,
        )

    def RegisterSkill(self, request, context):
        self._skills.append(request.skill)
        return knowledge_svc_pb2.RegisterSkillResponse(
            status=common_types.Status(code=0, message="registered"),
            skill_id=request.skill.skill_id or "skill-test-001",
        )


# ── Helpers ────────────────────────────────────────────────

def _start_server(address=GRPC_ADDRESS):
    server = grpc.server(
        __import__("concurrent.futures").futures.ThreadPoolExecutor(max_workers=4),
    )
    service_pb2_grpc.add_CognitionServiceServicer_to_server(
        _CognitionServicer(), server,
    )
    decision_svc_pb2_grpc.add_DecisionServiceServicer_to_server(
        _DecisionServicer(), server,
    )
    knowledge_svc_pb2_grpc.add_KnowledgeServiceServicer_to_server(
        _KnowledgeServicer(), server,
    )
    server.add_insecure_port(address)
    server.start()
    return server


# ── unittest suite ─────────────────────────────────────────

class GrpcCommunicationTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server = _start_server(GRPC_ADDRESS)
        time.sleep(SERVER_DELAY)
        cls.ch = grpc.insecure_channel(GRPC_ADDRESS)
        cls.cog = service_pb2_grpc.CognitionServiceStub(cls.ch)
        cls.dec = decision_svc_pb2_grpc.DecisionServiceStub(cls.ch)
        cls.kno = knowledge_svc_pb2_grpc.KnowledgeServiceStub(cls.ch)

    @classmethod
    def tearDownClass(cls):
        cls.ch.close()
        cls.server.stop(grace=1.0)

    # Cognition ──────────────────────────────────────────────

    def test_01_parse_intent(self):
        resp = self.cog.ParseIntent(
            service_pb2.ParseIntentRequest(
                robot_id="r1",
                utterance="把红色方块放到蓝色盒子里",
                language="zh-CN",
            ),
            timeout=5.0,
        )
        self.assertEqual(resp.status.code, 0)
        self.assertGreaterEqual(resp.intent.confidence, 0.0)
        print(f"  ✅ ParseIntent: type={resp.intent.type}, "
              f"conf={resp.intent.confidence:.2f}")

    def test_02_decompose_task(self):
        req = service_pb2.DecomposeTaskRequest(
            robot_id="r1",
            intent=cognition_types.Intent(
                type=cognition_types.INTENT_PICK,
                raw_text="pick the cup",
            ),
        )
        resp = self.cog.DecomposeTask(req, timeout=5.0)
        self.assertEqual(resp.status.code, 0)
        self.assertGreater(len(resp.subtasks), 0)
        print(f"  ✅ DecomposeTask: plan={resp.plan_id}, "
              f"subtasks={len(resp.subtasks)}")

    def test_03_generate_bt(self):
        resp = self.cog.GenerateBehaviorTree(
            service_pb2.GenerateBTRequest(
                robot_id="r1", plan_id="p1",
            ),
            timeout=5.0,
        )
        self.assertEqual(resp.status.code, 0)
        self.assertIn("<BehaviorTree", resp.tree.xml_str)
        print(f"  ✅ GenerateBT: xml_len={len(resp.tree.xml_str)}")

    def test_04_clarify(self):
        resp = self.cog.Clarify(
            service_pb2.ClarifyRequest(
                robot_id="r1",
                question="哪个物体？",
                user_answer="红色方块",
                original_intent=cognition_types.Intent(type=cognition_types.INTENT_PICK),
            ),
            timeout=5.0,
        )
        self.assertEqual(resp.status.code, 0)
        print(f"  ✅ Clarify: refined")

    # Decision ──────────────────────────────────────────────

    def test_10_execute_plan(self):
        resp = self.dec.ExecutePlan(
            decision_svc_pb2.ExecutePlanRequest(
                robot_id="r1", plan_id="p-exec-1",
            ),
            timeout=5.0,
        )
        self.assertEqual(resp.status.code, 0)
        print(f"  ✅ ExecutePlan: plan={resp.plan_id}, "
              f"state={decision_types.PlanState.Name(resp.state)}")

    def test_11_generate_trajectories(self):
        resp = self.dec.GenerateTrajectories(
            decision_svc_pb2.GenerateTrajectoriesRequest(
                robot_id="r1", plan_id="p1", num_candidates=3,
            ),
            timeout=5.0,
        )
        self.assertEqual(resp.status.code, 0)
        self.assertGreater(len(resp.trajectories), 0)
        print(f"  ✅ GenerateTrajectories: {len(resp.trajectories)} candidates")

    def test_12_select_trajectory(self):
        gen = self.dec.GenerateTrajectories(
            decision_svc_pb2.GenerateTrajectoriesRequest(
                robot_id="r1", plan_id="p-sel-1", num_candidates=2,
            ),
            timeout=5.0,
        )
        tid = gen.trajectories[0].trajectory_id
        resp = self.dec.SelectTrajectory(
            decision_svc_pb2.SelectTrajectoryRequest(
                robot_id="r1", plan_id="p-sel-1", trajectory_id=tid,
            ),
            timeout=5.0,
        )
        self.assertEqual(resp.status.code, 0)
        print(f"  ✅ SelectTrajectory: selected={tid}")

    # Knowledge ─────────────────────────────────────────────

    def test_20_store_episode(self):
        from brain_os.knowledge import types_pb2 as kt
        ep = kt.Episode(
            robot_id="r1",
            task_type="pick_and_place",
            success=True,
            duration_sec=12.5,
        )
        resp = self.kno.StoreEpisode(
            knowledge_svc_pb2.StoreEpisodeRequest(episode=ep),
            timeout=5.0,
        )
        self.assertEqual(resp.status.code, 0)
        print(f"  ✅ StoreEpisode: id={resp.episode_id}")


# ── Manual runner ──────────────────────────────────────────

def main():
    print("=" * 60)
    print("  gRPC Communication Test (Python server ↔ Python client)")
    print("=" * 60)

    server = _start_server(GRPC_ADDRESS)
    time.sleep(SERVER_DELAY)

    ch = grpc.insecure_channel(GRPC_ADDRESS)
    cog = service_pb2_grpc.CognitionServiceStub(ch)
    dec = decision_svc_pb2_grpc.DecisionServiceStub(ch)
    kno = knowledge_svc_pb2_grpc.KnowledgeServiceStub(ch)

    passed, failed = 0, 0

    def _t(name, fn):
        nonlocal passed, failed
        try:
            fn()
            print(f"  ✅ {name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            failed += 1

    # ── CognitionService ─────────────────────────────

    def t_parse():
        r = cog.ParseIntent(
            service_pb2.ParseIntentRequest(
                robot_id="r1",
                utterance="把红色方块放到蓝色盒子里",
                language="zh-CN",
            ),
            timeout=5.0,
        )
        assert r.status.code == 0
        print(f"      → type={r.intent.type}, conf={r.intent.confidence:.2f}")

    def t_decompose():
        r = cog.DecomposeTask(
            service_pb2.DecomposeTaskRequest(
                robot_id="r1",
                intent=cognition_types.Intent(
                    type=cognition_types.INTENT_PICK,
                    raw_text="pick the cup",
                ),
            ),
            timeout=5.0,
        )
        assert r.status.code == 0 and len(r.subtasks) > 0
        print(f"      → plan={r.plan_id}, subtasks={len(r.subtasks)}")

    def t_bt():
        r = cog.GenerateBehaviorTree(
            service_pb2.GenerateBTRequest(robot_id="r1", plan_id="p1"),
            timeout=5.0,
        )
        assert r.status.code == 0 and "<BehaviorTree" in r.tree.xml_str
        print(f"      → xml_len={len(r.tree.xml_str)}")

    # ── DecisionService ──────────────────────────────

    def t_exec():
        r = dec.ExecutePlan(
            decision_svc_pb2.ExecutePlanRequest(robot_id="r1", plan_id="p1"),
            timeout=5.0,
        )
        assert r.status.code == 0
        print(f"      → plan={r.plan_id}, state={decision_types.PlanState.Name(r.state)}")

    def t_traj():
        r = dec.GenerateTrajectories(
            decision_svc_pb2.GenerateTrajectoriesRequest(
                robot_id="r1", plan_id="p1", num_candidates=3,
            ),
            timeout=5.0,
        )
        assert r.status.code == 0 and len(r.trajectories) > 0
        print(f"      → {len(r.trajectories)} candidates")

    # ── KnowledgeService ─────────────────────────────

    def t_store():
        epi = knowledge_types.Episode(
            robot_id="r1",
            task_type="pick_and_place",
            success=True,
            duration_sec=12.5,
        )
        r = kno.StoreEpisode(
            knowledge_svc_pb2.StoreEpisodeRequest(episode=epi),
            timeout=5.0,
        )
        assert r.status.code == 0
        print(f"      → episode_id={r.episode_id}")

    for fn in [t_parse, t_decompose, t_bt, t_exec, t_traj, t_store]:
        _t(fn.__name__.replace("t_", ""), fn)

    ch.close()
    server.stop(grace=1.0)

    print()
    print(f"  Results: {passed} passed, {failed} failed")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
