// grpc_client/brain_ai_client.cpp
// Implementation of BrainAIClient — C++ gRPC client for brain_ai.

#include "brain_ai_client.h"

#include <chrono>
#include <iostream>
#include <thread>

namespace brain_core {
namespace {

// Timeout for all RPCs
constexpr auto RPC_TIMEOUT = std::chrono::seconds(10);

// Helper: create a client context with timeout.
std::unique_ptr<grpc::ClientContext> MakeContext() {
    auto ctx = std::make_unique<grpc::ClientContext>();
    ctx->set_deadline(std::chrono::system_clock::now() + RPC_TIMEOUT);
    return ctx;
}

} // namespace

// ── Constructor / Destructor ──────────────────────────────────────

BrainAIClient::BrainAIClient(const std::string& server_address)
    : server_address_(server_address) {
    auto channel = grpc::CreateChannel(
        server_address_,
        grpc::InsecureChannelCredentials(),
    );
    cognition_stub_ = brain_os::cognition::CognitionService::NewStub(channel);
    decision_stub_ = brain_os::decision::DecisionService::NewStub(channel);
    knowledge_stub_ = brain_os::knowledge::KnowledgeService::NewStub(channel);
    std::cout << "[BrainAIClient] Connected to " << server_address_ << std::endl;
}

BrainAIClient::~BrainAIClient() = default;

// ── ParseIntent ────────────────────────────────────────────────────

IntentResult BrainAIClient::ParseIntent(
    const std::string& robot_id,
    const std::string& utterance,
    const std::string& language,
) {
    IntentResult result;
    result.ok = false;

    brain_os::cognition::ParseIntentRequest req;
    req.set_robot_id(robot_id);
    req.set_utterance(utterance);
    req.set_language(language);

    brain_os::cognition::ParseIntentResponse resp;
    auto ctx = MakeContext();
    grpc::Status status = cognition_stub_->ParseIntent(
        ctx.get(), req, &resp,
    );

    if (!status.ok()) {
        result.error_message = "gRPC error: " + status.error_message();
        std::cerr << "[BrainAIClient::ParseIntent] " << result.error_message
                  << std::endl;
        return result;
    }

    if (resp.status().code() != 0) {
        result.error_message = resp.status().message();
        return result;
    }

    result.ok          = true;
    result.intent_id   = resp.intent().intent_id();
    result.action      = resp.intent().action();
    result.target      = resp.intent().target();
    result.confidence  = resp.intent().confidence();
    return result;
}

// ── DecomposeTask ─────────────────────────────────────────────────

TaskResult BrainAIClient::DecomposeTask(
    const std::string& robot_id,
    const std::string& /*intent_json*/,
    const std::string& /*scene_graph_json*/,
) {
    TaskResult result;
    result.ok = false;

    // TODO: deserialize intent_json → Intent proto
    // Stub: create a default intent for now
    brain_os::cognition::DecomposeTaskRequest req;
    req.set_robot_id(robot_id);
    auto* intent = req.mutable_intent();
    intent->set_action("pick_and_place");
    intent->set_target("red_cube");

    brain_os::cognition::DecomposeTaskResponse resp;
    auto ctx = MakeContext();
    grpc::Status status = cognition_stub_->DecomposeTask(
        ctx.get(), req, &resp,
    );

    if (!status.ok()) {
        result.error_message = "gRPC error: " + status.error_message();
        return result;
    }

    result.ok           = (resp.status().code() == 0);
    result.plan_id     = resp.plan_id();
    result.rationale   = resp.rationale();
    // TODO: serialize subtasks → JSON
    result.subtasks_json = "[stub: subtasks]";
    return result;
}

// ── GenerateBehaviorTree ──────────────────────────────────────────

BTResult BrainAIClient::GenerateBehaviorTree(
    const std::string& robot_id,
    const std::string& plan_id,
    const std::string& /*subtasks_json*/,
) {
    BTResult result;
    result.ok = false;

    brain_os::cognition::GenerateBTRequest req;
    req.set_robot_id(robot_id);
    req.set_plan_id(plan_id);
    // TODO: deserialize subtasks_json → repeated SubTask

    brain_os::cognition::GenerateBTResponse resp;
    auto ctx = MakeContext();
    grpc::Status status = cognition_stub_->GenerateBehaviorTree(
        ctx.get(), req, &resp,
    );

    if (!status.ok()) {
        result.error_message = "gRPC error: " + status.error_message();
        return result;
    }

    result.ok  = (resp.status().code() == 0);
    result.xml = resp.tree().xml();
    return result;
}

// ── ExecutePlan ───────────────────────────────────────────────────

ExecutePlanResult BrainAIClient::ExecutePlan(
    const std::string& robot_id,
    const std::string& bt_xml,
    const std::string& plan_id,
    bool               require_hitl,
) {
    ExecutePlanResult result;
    result.ok = false;

    brain_os::decision::ExecutePlanRequest req;
    req.set_robot_id(robot_id);
    req.set_plan_id(plan_id);
    req.set_require_hitl(require_hitl);
    // TODO: serialize BT → request.tree()

    brain_os::decision::ExecutePlanResponse resp;
    auto ctx = MakeContext();
    grpc::Status status = decision_stub_->ExecutePlan(
        ctx.get(), req, &resp,
    );

    if (!status.ok()) {
        result.error_message = "gRPC error: " + status.error_message();
        return result;
    }

    result.ok            = (resp.status().code() == 0);
    result.plan_id      = resp.plan_id();
    result.hitl_required = resp.has_hitl_event();

    if (result.hitl_required) {
        for (const auto& traj : resp.hitl_event().trajectories()) {
            TrajectoryCandidate c;
            c.trajectory_id = traj.trajectory_id();
            c.rank          = traj.rank();
            c.score         = traj.score();
            c.risk_level    = (traj.risk_level() == brain_os::decision::RISK_LOW)
                             ? "low" : "medium";
            c.description   = traj.description();
            result.candidates.push_back(c);
        }
    }
    return result;
}

// ── GenerateTrajectories ─────────────────────────────────────────

std::vector<TrajectoryCandidate> BrainAIClient::GenerateTrajectories(
    const std::string& robot_id,
    const std::string& plan_id,
    int                num_candidates,
) {
    std::vector<TrajectoryCandidate> results;

    brain_os::decision::GenerateTrajectoriesRequest req;
    req.set_robot_id(robot_id);
    req.set_plan_id(plan_id);
    req.set_num_candidates(std::max(1, std::min(num_candidates, 5)));

    brain_os::decision::GenerateTrajectoriesResponse resp;
    auto ctx = MakeContext();
    grpc::Status status = decision_stub_->GenerateTrajectories(
        ctx.get(), req, &resp,
    );

    if (!status.ok()) {
        std::cerr << "[BrainAIClient::GenerateTrajectories] gRPC error: "
                  << status.error_message() << std::endl;
        return results;
    }

    for (const auto& traj : resp.trajectories()) {
        TrajectoryCandidate c;
        c.trajectory_id = traj.trajectory_id();
        c.rank          = traj.rank();
        c.score         = traj.score();
        c.risk_level    = (traj.risk_level() == brain_os::decision::RISK_LOW)
                         ? "low" : "medium";
        c.description   = traj.description();
        results.push_back(c);
    }
    return results;
}

// ── SelectTrajectory ──────────────────────────────────────────────

bool BrainAIClient::SelectTrajectory(
    const std::string& robot_id,
    const std::string& plan_id,
    const std::string& trajectory_id,
) {
    brain_os::decision::SelectTrajectoryRequest req;
    req.set_robot_id(robot_id);
    req.set_plan_id(plan_id);
    req.set_trajectory_id(trajectory_id);

    brain_os::decision::SelectTrajectoryResponse resp;
    auto ctx = MakeContext();
    grpc::Status status = decision_stub_->SelectTrajectory(
        ctx.get(), req, &resp,
    );

    if (!status.ok()) {
        std::cerr << "[BrainAIClient::SelectTrajectory] gRPC error: "
                  << status.error_message() << std::endl;
        return false;
    }
    return (resp.status().code() == 0);
}

// ── StoreEpisode ──────────────────────────────────────────────────

EpisodeResult BrainAIClient::StoreEpisode(
    const std::string& robot_id,
    const std::string& task_json,
    bool               success,
    const std::string& error_msg,
) {
    EpisodeResult result;
    result.ok = false;

    brain_os::knowledge::StoreEpisodeRequest req;
    auto* ep = req.mutable_episode();
    ep->set_robot_id(robot_id);
    ep->set_success(success);
    ep->set_error_msg(error_msg);
    // TODO: deserialize task_json → Task proto

    brain_os::knowledge::StoreEpisodeResponse resp;
    auto ctx = MakeContext();
    grpc::Status status = knowledge_stub_->StoreEpisode(
        ctx.get(), req, &resp,
    );

    if (!status.ok()) {
        result.error_message = "gRPC error: " + status.error_message();
        return result;
    }

    result.ok        = (resp.status().code() == 0);
    result.episode_id = resp.episode_id();
    return result;
}

} // namespace brain_core

// ── Minimal test (compile-time check) ────────────────────────────

#ifdef BRAIN_AI_CLIENT_TEST_MAIN
#include <iostream>
int main() {
    brain_core::BrainAIClient client("localhost:50052");
    auto result = client.ParseIntent("robot-01", "把红色方块放到蓝色盒子里", "zh-CN");
    if (result.ok) {
        std::cout << "Intent parsed: action=" << result.action
                  << " target=" << result.target << std::endl;
    } else {
        std::cerr << "ParseIntent failed: " << result.error_message << std::endl;
    }
    return 0;
}
#endif
