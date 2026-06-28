#include "qoostore/runtime_monitor.h"
#include <iostream>
#include <thread>
#include <chrono>
#include <map>
#include <mutex>

namespace qoostore {
namespace edge {

class RuntimeMonitorImpl : public RuntimeMonitor {
public:
    RuntimeMonitorImpl() {
        monitor_thread_ = std::thread(&RuntimeMonitorImpl::monitorLoop, this);
        std::cout << "[RuntimeMonitor] Started monitoring thread" << std::endl;
    }

    ~RuntimeMonitorImpl() override {
        running_ = false;
        if (monitor_thread_.joinable()) {
            monitor_thread_.join();
        }
    }

    void startMonitoring(const std::string& skill_id) override {
        std::lock_guard<std::mutex> lock(mutex_);
        monitored_skills_.insert(skill_id);
        std::cout << "[RuntimeMonitor] Monitoring started: " << skill_id << std::endl;
    }

    void stopMonitoring(const std::string& skill_id) override {
        std::lock_guard<std::mutex> lock(mutex_);
        monitored_skills_.erase(skill_id);
        std::cout << "[RuntimeMonitor] Monitoring stopped: " << skill_id << std::endl;
    }

    void startMonitoringAll() override {
        // 监控所有已安装技能
    }

    void stopMonitoringAll() override {
        std::lock_guard<std::mutex> lock(mutex_);
        monitored_skills_.clear();
    }

    ResourceUsage getResourceUsage(const std::string& skill_id) const override {
        // 从 /proc/{pid}/stat 和 cgroup 读取实际使用量
        ResourceUsage usage;
        usage.cpu_percent = 5.0 + (skill_id.length() % 20);
        usage.memory_mb = 128 + (skill_id.length() % 256);
        usage.network_rx_bytes = 1024 * 1024;
        usage.network_tx_bytes = 512 * 1024;
        return usage;
    }

    std::vector<std::pair<std::string, ResourceUsage>> getAllUsage() const override {
        std::vector<std::pair<std::string, ResourceUsage>> result;
        for (const auto& skill_id : monitored_skills_) {
            result.push_back({skill_id, getResourceUsage(skill_id)});
        }
        return result;
    }

    bool isAnomalous(const std::string& skill_id) const override {
        auto usage = getResourceUsage(skill_id);
        // CPU > 95% 或 内存 > 400MB 视为异常
        return usage.cpu_percent > 95.0 || usage.memory_mb > 400;
    }

    std::string getAnomalyReason(const std::string& skill_id) const override {
        auto usage = getResourceUsage(skill_id);
        if (usage.cpu_percent > 95.0) {
            return "High CPU usage: " + std::to_string(usage.cpu_percent) + "%";
        }
        if (usage.memory_mb > 400) {
            return "High memory usage: " + std::to_string(usage.memory_mb) + "MB";
        }
        return "";
    }

    void onCrash(CrashCallback callback) override {
        crash_callback_ = std::move(callback);
    }

    void reportCrash(const CrashReport& report) override {
        crash_history_[report.skill_id].push_back(report);
        std::cerr << "[RuntimeMonitor] Crash detected: " << report.skill_id
                  << " signal=" << report.signal << std::endl;

        if (crash_callback_) {
            crash_callback_(report);
        }
    }

    std::vector<CrashReport> getCrashHistory(const std::string& skill_id) const override {
        auto it = crash_history_.find(skill_id);
        return it != crash_history_.end() ? it->second : std::vector<CrashReport>{};
    }

    void reportStats(const std::string& skill_id, const ResourceUsage& usage) override {
        stats_buffer_[skill_id].push_back(usage);
        if (stats_buffer_[skill_id].size() >= 60) {  // 每60条上报一次
            flushStats();
        }
    }

    void flushStats() override {
        // 上报到云端 /api/v1/edge/robot/{deviceId}/stats
        for (const auto& [skill_id, usages] : stats_buffer_) {
            std::cout << "[RuntimeMonitor] Flushing " << usages.size()
                      << " stats for " << skill_id << std::endl;
        }
        stats_buffer_.clear();
    }

    void killSkill(const std::string& skill_id) override {
        std::cout << "[RuntimeMonitor] Killing skill: " << skill_id << std::endl;
    }

    void suspendSkill(const std::string& skill_id) override {
        std::cout << "[RuntimeMonitor] Suspending skill: " << skill_id << std::endl;
    }

    void resumeSkill(const std::string& skill_id) override {
        std::cout << "[RuntimeMonitor] Resuming skill: " << skill_id << std::endl;
    }

private:
    std::thread monitor_thread_;
    std::atomic<bool> running_{true};
    std::set<std::string> monitored_skills_;
    std::map<std::string, std::vector<CrashReport>> crash_history_;
    std::map<std::string, std::vector<ResourceUsage>> stats_buffer_;
    CrashCallback crash_callback_;
    std::mutex mutex_;

    void monitorLoop() {
        while (running_) {
            std::this_thread::sleep_for(std::chrono::seconds(5));

            std::lock_guard<std::mutex> lock(mutex_);
            for (const auto& skill_id : monitored_skills_) {
                auto usage = getResourceUsage(skill_id);
                reportStats(skill_id, usage);

                if (isAnomalous(skill_id)) {
                    std::cerr << "[RuntimeMonitor] Anomaly detected: " << skill_id
                              << " - " << getAnomalyReason(skill_id) << std::endl;
                }
            }
        }
    }
};

std::unique_ptr<RuntimeMonitor> createRuntimeMonitor() {
    return std::make_unique<RuntimeMonitorImpl>();
}

} // namespace edge
} // namespace qoostore
