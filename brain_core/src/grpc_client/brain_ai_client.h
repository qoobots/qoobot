// grpc_client/brain_ai_client.h
// C++ gRPC client for brain_ai services.
//
// Calls:
//   - CognitionService (ParseIntent / DecomposeTask / GenerateBehaviorTree)
//   - DecisionService  (ExecutePlan / GenerateTrajectories / SelectTrajectory)
//   - KnowledgeService (SearchEpisodes / StoreEpisode)
//
// Usage:
//   auto client = std::make_shared<BrainAIClient>("localhost:50052");
//   auto resp  = client->ParseIntent("把红色方块放到盒子里", "zh-CN");
//
// Prerequisite: run buf generate to produce proto_gen/ headers.

#pragma once

#include <memory>
#include <string>
#include <vector>
#include <functional>

#include <grpc/grpc.h>
#include <grpcpp/grpcpp.h>

// Generated headers (from brain_proto via buf generate)
// These paths assume proto_gen/ is in the include path.
#include "brain_os/cognition/service.grpc.pb.h"
#include "brain_os/cognition/types.pb.h"
#include "brain_os/decision/service.grpc.pb.h"
#include "brain_os/decision/types.pb.h"
#include "brain_os/knowledge/service.grpc.pb.h"
#include "brain_os/knowledge/types.pb.h"
#include "brain_os/common/types.pb.h"

namespace brain_core {

// ── Cognition Service Client ─────────────────────────────────────────

struct IntentResult {
    bool        ok;
    std::string error_message;
    std::string intent_id;
    std::string action;
    std::string target;
    double      confidence;
};

struct TaskResult {
    bool              ok;
    std::string       error_message;
    std::string       plan_id;
    std::string       rationale;
    // Serialized subtasks JSON for now (full proto in later sprint)
    std::string       subtasks_json;
};

struct BTResult {
    bool        ok;
    std::string error_message;
    std::string xml;
};

// ── Decision Service Client ──────────────────────────────────────────

struct TrajectoryCandidate {
    std::string trajectory_id;
    int         rank{0};
    double      score{0.0};
    std::string risk_level;
    std::string description;
};

struct ExecutePlanResult {
    bool        ok;
    std::string error_message;
    std::string plan_id;
    bool        hitl_required{false};
    // If hitl_required: list of candidate trajectories
    std::vector<TrajectoryCandidate> candidates;
};

// ── Knowledge Service Client ─────────────────────────────────────────

struct EpisodeResult {
    bool        ok;
    std::string error_message;
    std::string episode_id;
};

// ── Main Client ──────────────────────────────────────────────────────

class BrainAIClient final {
public:
    explicit BrainAIClient(const std::string& server_address);
    ~BrainAIClient();

    // Not copyable
    BrainAIClient(const BrainAIClient&) = delete;
    BrainAIClient& operator=(const BrainAIClient&) = delete;

    // ── Cognition RPCs ──────────────────────────────────────────────

    /// Parse a natural-language instruction into a structured intent.
    IntentResult ParseIntent(
        const std::string& robot_id,
        const std::string& utterance,
        const std::string& language = "zh-CN",
    );

    /// Decompose an intent into subtasks.
    TaskResult DecomposeTask(
        const std::string& robot_id,
        const std::string& intent_json,  // serialized Intent proto
        const std::string& scene_graph_json,
    );

    /// Generate a BehaviorTree XML from a task plan.
    BTResult GenerateBehaviorTree(
        const std::string& robot_id,
        const std::string& plan_id,
        const std::string& subtasks_json,
    );

    // ── Decision RPCs ───────────────────────────────────────────────

    /// Start executing a behavior tree plan.
    ExecutePlanResult ExecutePlan(
        const std::string& robot_id,
        const std::string& bt_xml,
        const std::string& plan_id,
        bool               require_hitl = false,
    );

    /// Generate candidate trajectories (called by DecisionService internally,
    /// exposed here for brain_core to query).
    std::vector<TrajectoryCandidate> GenerateTrajectories(
        const std::string& robot_id,
        const std::string& plan_id,
        int                num_candidates = 3,
    );

    /// Submit HITL trajectory selection.
    bool SelectTrajectory(
        const std::string& robot_id,
        const std::string& plan_id,
        const std::string& trajectory_id,  // empty = timeout/auto
    );

    // ── Knowledge RPCs ──────────────────────────────────────────────

    /// Store an episode after task execution.
    EpisodeResult StoreEpisode(
        const std::string& robot_id,
        const std::string& task_json,
        bool               success,
        const std::string& error_msg,
    );

    /// Search similar past episodes.
    // TODO: return actual episodes list (Sprint 2)

private:
    std::string server_address_;

    // Stubs (initialized in ctor)
    std::unique_ptr<brain_os::cognition::CognitionService::Stub> cognition_stub_;
    std::unique_ptr<brain_os::decision::DecisionService::Stub>  decision_stub_;
    std::unique_ptr<brain_os::knowledge::KnowledgeService::Stub> knowledge_stub_;
};

} // namespace brain_core
