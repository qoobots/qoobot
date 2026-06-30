#pragma once

#include <string>
#include <vector>
#include <functional>
#include <cstdint>
#include <chrono>

namespace qooedge {

// ============================================================================
// 边缘节点类型
// ============================================================================

enum class NodeRole {
    LEADER,        // 主节点（协调者）
    WORKER,        // 工作节点
    RELAY,         // 中继节点
    OBSERVER       // 观察节点
};

enum class NodeState {
    ONLINE,
    OFFLINE,
    DEGRADED,      // 降级运行
    MAINTENANCE
};

// ============================================================================
// 任务卸载
// ============================================================================

enum class OffloadDecision {
    LOCAL_ONLY,       // 仅本地执行
    CLOUD_ONLY,       // 仅云端执行
    HYBRID,           // 端云混合
    EDGE_PEER,        // 卸载到边缘对等节点
    DEFERRED          // 延迟执行
};

enum class InferencePriority {
    REALTIME,         // 实时（< 10ms）
    HIGH,             // 高优先级（< 100ms）
    NORMAL,           // 标准（< 1s）
    BACKGROUND        // 后台（< 10s）
};

struct OffloadTask {
    std::string task_id;
    std::string model_name;
    std::vector<uint8_t> input_data;
    InferencePriority priority{InferencePriority::NORMAL};
    uint64_t deadline_ms{1000};
    bool require_low_latency{false};
};

struct OffloadResult {
    std::string task_id;
    std::vector<uint8_t> output_data;
    double latency_ms{0.0};
    double energy_joules{0.0};
    OffloadDecision actual_execution{OffloadDecision::LOCAL_ONLY};
    bool success{false};
    std::string error;
};

// ============================================================================
// 网络延迟预算
// ============================================================================

struct NetworkBudget {
    double rtt_ms{0.0};            // 往返延迟
    double bandwidth_mbps{0.0};    // 可用带宽
    double jitter_ms{0.0};         // 抖动
    double packet_loss{0.0};       // 丢包率 (0-1)
    std::string interface_type;    // "wifi6e", "5g", "ethernet"
};

// ============================================================================
// 端-云数据同步
// ============================================================================

enum class SyncDirection {
    UPLOAD,       // 端 → 云
    DOWNLOAD,     // 云 → 端
    BIDIRECTIONAL
};

enum class SyncStrategy {
    FULL,         // 全量同步
    INCREMENTAL,  // 增量同步
    DELTA,        // 差分同步
    LAZY          // 延迟同步
};

struct SyncTask {
    std::string sync_id;
    std::string resource_path;    // "/models/detection/v1"
    SyncDirection direction{SyncDirection::BIDIRECTIONAL};
    SyncStrategy strategy{SyncStrategy::INCREMENTAL};
    uint64_t data_size_bytes{0};
    std::string checksum;         // SHA-256
};

struct SyncProgress {
    std::string sync_id;
    double progress{0.0};         // 0.0 - 1.0
    uint64_t bytes_transferred{0};
    uint64_t total_bytes{0};
    double transfer_speed_mbps{0.0};
};

// ============================================================================
// Mesh 网络
// ============================================================================

struct MeshNode {
    std::string node_id;
    std::string robot_id;
    NodeRole role{NodeRole::WORKER};
    NodeState state{NodeState::ONLINE};
    std::string ip_address;
    uint16_t port{0};
    std::vector<std::string> capabilities;  // ["navigation", "perception", "manipulation"]
    NetworkBudget link_budget;
    uint64_t last_heartbeat{0};
};

struct MeshMessage {
    std::string message_id;
    std::string source_node;
    std::string target_node;      // "" = broadcast
    std::string topic;            // "perception/lidar", "nav/global_path"
    std::vector<uint8_t> payload;
    uint64_t timestamp{0};
    uint8_t ttl{8};              // 生存跳数
};

// ============================================================================
// 回调类型
// ============================================================================

using OffloadCallback = std::function<void(const OffloadResult&)>;
using SyncCallback = std::function<void(const SyncProgress&)>;
using MeshCallback = std::function<void(const MeshMessage&)>;
using NodeCallback = std::function<void(const MeshNode&, NodeState old_state, NodeState new_state)>;

} // namespace qooedge
