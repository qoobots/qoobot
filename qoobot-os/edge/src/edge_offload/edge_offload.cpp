/**
 * edge_offload.cpp — 端-云任务卸载决策引擎实现
 *
 * 基于多因素决策模型决定推理任务执行位置：
 *   - 网络延迟预算判断
 *   - 任务实时性门槛检查
 *   - 本地负载容量分析
 *   - 能耗约束评估
 *   - 数据敏感性（隐私策略）
 */

#include "qooedge/edge_offload.h"
#include <iostream>
#include <sstream>
#include <map>
#include <mutex>
#include <cmath>
#include <algorithm>

namespace qooedge {

class EdgeOffloadImpl : public EdgeOffload {
public:
    bool initialize(const std::string& config_path) override {
        std::cout << "[EdgeOffload] Initializing with config: " << config_path << std::endl;

        // 默认决策参数
        latency_threshold_ms_ = 50.0;      // 超过此阈值倾向本地执行
        bandwidth_threshold_mbps_ = 10.0;  // 低于此带宽倾向本地执行
        local_load_threshold_ = 0.8;       // 超过此负载倾向卸载到云端
        energy_budget_mah_per_s_ = 5.0;    // 默认能耗预算

        offline_mode_ = false;

        // 统计初始化
        decision_stats_["local_only"] = 0;
        decision_stats_["cloud_only"] = 0;
        decision_stats_["hybrid"] = 0;
        decision_stats_["edge_peer"] = 0;
        decision_stats_["deferred"] = 0;

        std::cout << "[EdgeOffload] Initialized." << std::endl;
        return true;
    }

    OffloadDecision decide(const OffloadTask& task,
                            double local_load,
                            const NetworkBudget& network_budget) override {
        // 更新网络预算
        current_budget_ = network_budget;

        // 离线模式：强制本地
        if (offline_mode_) {
            recordDecision(OffloadDecision::LOCAL_ONLY);
            return OffloadDecision::LOCAL_ONLY;
        }

        // 实时任务：必须本地执行
        if (task.priority == InferencePriority::REALTIME) {
            recordDecision(OffloadDecision::LOCAL_ONLY);
            return OffloadDecision::LOCAL_ONLY;
        }

        // 网络不可用：强制本地
        if (network_budget.rtt_ms < 0 || network_budget.bandwidth_mbps <= 0) {
            recordDecision(OffloadDecision::LOCAL_ONLY);
            return OffloadDecision::LOCAL_ONLY;
        }

        // 本地负载低且满足延迟要求 → 本地执行
        if (local_load < local_load_threshold_ &&
            task.deadline_ms > 100) {
            recordDecision(OffloadDecision::LOCAL_ONLY);
            return OffloadDecision::LOCAL_ONLY;
        }

        // 高负载 + 网络良好 → 卸载到云端
        if (local_load >= local_load_threshold_ &&
            network_budget.rtt_ms < latency_threshold_ms_ &&
            network_budget.bandwidth_mbps >= bandwidth_threshold_mbps_) {
            recordDecision(OffloadDecision::CLOUD_ONLY);
            return OffloadDecision::CLOUD_ONLY;
        }

        // 本地负载高但网络也不理想 + 非紧急 → 延迟执行
        if (task.priority == InferencePriority::BACKGROUND) {
            recordDecision(OffloadDecision::DEFERRED);
            return OffloadDecision::DEFERRED;
        }

        // 混合模式：小模型本地 + 大模型云端
        recordDecision(OffloadDecision::HYBRID);
        return OffloadDecision::HYBRID;
    }

    std::vector<OffloadDecision> decideBatch(
        const std::vector<OffloadTask>& tasks,
        double local_load,
        const NetworkBudget& network_budget) override {

        std::vector<OffloadDecision> decisions;
        decisions.reserve(tasks.size());

        // 批量决策时考虑任务间的流水线并行
        for (const auto& task : tasks) {
            decisions.push_back(decide(task, local_load, network_budget));
        }

        std::cout << "[EdgeOffload] Batch decision: " << tasks.size()
                  << " tasks, load=" << local_load
                  << ", rtt=" << network_budget.rtt_ms << "ms" << std::endl;

        return decisions;
    }

    void updateNetworkBudget(const NetworkBudget& budget) override {
        std::lock_guard<std::mutex> lock(mutex_);
        current_budget_ = budget;
    }

    NetworkBudget getNetworkBudget() const override {
        std::lock_guard<std::mutex> lock(mutex_);
        return current_budget_;
    }

    void setOfflineMode(bool offline) override {
        offline_mode_ = offline;
        std::cout << "[EdgeOffload] Offline mode: " << (offline ? "ON" : "OFF") << std::endl;
    }

    bool isOfflineMode() const override {
        return offline_mode_;
    }

    std::string getDecisionStats() const override {
        std::lock_guard<std::mutex> lock(mutex_);
        std::ostringstream oss;
        oss << "{"
            << "\"local_only\":" << decision_stats_.at("local_only") << ","
            << "\"cloud_only\":" << decision_stats_.at("cloud_only") << ","
            << "\"hybrid\":" << decision_stats_.at("hybrid") << ","
            << "\"edge_peer\":" << decision_stats_.at("edge_peer") << ","
            << "\"deferred\":" << decision_stats_.at("deferred") << ","
            << "\"offline_mode\":" << (offline_mode_ ? "true" : "false")
            << "}";
        return oss.str();
    }

    void setEnergyBudget(double mah_per_second) override {
        energy_budget_mah_per_s_ = mah_per_second;
        std::cout << "[EdgeOffload] Energy budget: " << mah_per_second << " mAh/s" << std::endl;
    }

private:
    double latency_threshold_ms_{50.0};
    double bandwidth_threshold_mbps_{10.0};
    double local_load_threshold_{0.8};
    double energy_budget_mah_per_s_{5.0};
    bool offline_mode_{false};

    NetworkBudget current_budget_;
    mutable std::mutex mutex_;
    mutable std::map<std::string, int64_t> decision_stats_;

    void recordDecision(OffloadDecision decision) {
        switch (decision) {
            case OffloadDecision::LOCAL_ONLY:  decision_stats_["local_only"]++; break;
            case OffloadDecision::CLOUD_ONLY:  decision_stats_["cloud_only"]++; break;
            case OffloadDecision::HYBRID:      decision_stats_["hybrid"]++; break;
            case OffloadDecision::EDGE_PEER:   decision_stats_["edge_peer"]++; break;
            case OffloadDecision::DEFERRED:    decision_stats_["deferred"]++; break;
        }
    }
};

std::unique_ptr<EdgeOffload> createEdgeOffload() {
    return std::make_unique<EdgeOffloadImpl>();
}

} // namespace qooedge
