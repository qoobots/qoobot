/**
 * edge_sync.cpp — 端-云数据同步引擎实现
 *
 * 管理机器人端与云端之间的双向数据同步：
 *   - 模型权重同步、地图数据同步、知识图谱同步、日志指标同步、配置策略同步
 *   - 支持全量/增量/差分/延迟四种同步策略
 *   - 网络条件约束（仅 WiFi / 仅充电时同步）
 */

#include "qooedge/edge_sync.h"
#include <algorithm>
#include <iostream>
#include <sstream>
#include <map>
#include <mutex>
#include <thread>
#include <atomic>
#include <chrono>

namespace qooedge {

class EdgeSyncImpl : public EdgeSync {
public:
    ~EdgeSyncImpl() override {
        shutting_down_ = true;
        // 等待所有模拟同步线程完成
        for (auto& t : sync_threads_) {
            if (t.joinable()) t.join();
        }
    }

    bool initialize(const std::string& cloud_endpoint,
                     const std::string& device_id) override {
        cloud_endpoint_ = cloud_endpoint;
        device_id_ = device_id;

        std::cout << "[EdgeSync] Initialized: endpoint=" << cloud_endpoint
                  << " device=" << device_id << std::endl;
        return true;
    }

    void startSync(const SyncTask& task, SyncCallback callback) override {
        std::lock_guard<std::mutex> lock(mutex_);

        ActiveSync active;
        active.task = task;
        active.callback = std::move(callback);
        active.start_time = std::chrono::steady_clock::now();
        active.progress.sync_id = task.sync_id;
        active.progress.total_bytes = task.data_size_bytes;

        active_syncs_[task.sync_id] = active;

        std::cout << "[EdgeSync] Sync started: " << task.sync_id
                  << " resource=" << task.resource_path
                  << " strategy=" << static_cast<int>(task.strategy)
                  << " size=" << task.data_size_bytes << " bytes" << std::endl;

        // 模拟同步过程（生产环境使用 gRPC streaming）
        simulateSync(task.sync_id);
    }

    void cancelSync(const std::string& sync_id) override {
        std::lock_guard<std::mutex> lock(mutex_);
        auto it = active_syncs_.find(sync_id);
        if (it != active_syncs_.end()) {
            it->second.cancelled = true;
            std::cout << "[EdgeSync] Sync cancelled: " << sync_id << std::endl;
        }
    }

    void setSyncPolicy(SyncStrategy default_strategy) override {
        default_strategy_ = default_strategy;
        std::cout << "[EdgeSync] Default strategy: " << static_cast<int>(default_strategy) << std::endl;
    }

    void setNetworkConstraints(bool wifi_only, bool charging_only) override {
        wifi_only_ = wifi_only;
        charging_only_ = charging_only;
        std::cout << "[EdgeSync] Constraints: wifi_only=" << wifi_only
                  << " charging_only=" << charging_only << std::endl;
    }

    std::vector<SyncProgress> getActiveSyncs() const override {
        std::lock_guard<std::mutex> lock(mutex_);
        std::vector<SyncProgress> result;
        for (const auto& [id, active] : active_syncs_) {
            result.push_back(active.progress);
        }
        return result;
    }

    bool checkForUpdate(const std::string& resource_path) override {
        std::lock_guard<std::mutex> lock(mutex_);
        // 检查本地资源版本与云端版本
        auto it = resource_versions_.find(resource_path);
        if (it == resource_versions_.end()) return true; // 本地不存在

        // 生产环境：通过 HTTPS 查询云端版本 API
        std::cout << "[EdgeSync] Checking update: " << resource_path
                  << " local=" << it->second << std::endl;
        return false; // 模拟：版本一致
    }

    std::string getResourceVersion(const std::string& resource_path) const override {
        std::lock_guard<std::mutex> lock(mutex_);
        auto it = resource_versions_.find(resource_path);
        return it != resource_versions_.end() ? it->second : "";
    }

    void forceSyncNow() override {
        std::cout << "[EdgeSync] Force sync triggered" << std::endl;
        // 强制同步所有注册资源（先复制资源列表，避免持锁调用 startSync）
        std::vector<std::pair<std::string, std::string>> resources;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            for (const auto& [path, version] : resource_versions_) {
                resources.emplace_back(path, version);
            }
        }
        for (const auto& [path, version] : resources) {
            SyncTask task;
            task.sync_id = "force_" + path;
            task.resource_path = path;
            task.direction = SyncDirection::BIDIRECTIONAL;
            task.strategy = default_strategy_;

            startSync(task, nullptr);
        }
    }

    void setSyncInterval(uint32_t interval_sec) override {
        sync_interval_sec_ = interval_sec;
        std::cout << "[EdgeSync] Sync interval: " << interval_sec << "s" << std::endl;
    }

private:
    struct ActiveSync {
        SyncTask task;
        SyncProgress progress;
        SyncCallback callback;
        std::chrono::steady_clock::time_point start_time;
        bool cancelled{false};
    };

    std::string cloud_endpoint_;
    std::string device_id_;
    SyncStrategy default_strategy_{SyncStrategy::INCREMENTAL};
    bool wifi_only_{true};
    bool charging_only_{true};
    uint32_t sync_interval_sec_{300};

    mutable std::mutex mutex_;
    std::map<std::string, ActiveSync> active_syncs_;
    std::map<std::string, std::string> resource_versions_;
    std::atomic<bool> shutting_down_{false};
    std::vector<std::thread> sync_threads_;

    void simulateSync(const std::string& sync_id) {
        sync_threads_.emplace_back([this, sync_id]() {
            for (int i = 0; i <= 100; i += 10) {
                if (shutting_down_) return;
                {
                    std::lock_guard<std::mutex> lock(mutex_);
                    auto it = active_syncs_.find(sync_id);
                    if (it == active_syncs_.end() || it->second.cancelled) return;

                    it->second.progress.progress = i / 100.0;
                    it->second.progress.bytes_transferred =
                        static_cast<uint64_t>(it->second.task.data_size_bytes * i / 100);

                    if (it->second.callback) {
                        it->second.callback(it->second.progress);
                    }
                }
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
            }

            // 同步完成
            {
                std::lock_guard<std::mutex> lock(mutex_);
                auto it = active_syncs_.find(sync_id);
                if (it != active_syncs_.end()) {
                    it->second.progress.progress = 1.0;
                    it->second.progress.bytes_transferred = it->second.task.data_size_bytes;
                    it->second.progress.total_bytes = it->second.task.data_size_bytes;

                    // 更新资源版本
                    resource_versions_[it->second.task.resource_path] =
                        it->second.task.checksum;

                    if (it->second.callback) {
                        it->second.callback(it->second.progress);
                    }

                    std::cout << "[EdgeSync] Sync completed: " << sync_id
                              << " resource=" << it->second.task.resource_path << std::endl;

                    active_syncs_.erase(it);
                }
            }
        });
    }
};

std::unique_ptr<EdgeSync> createEdgeSync() {
    return std::make_unique<EdgeSyncImpl>();
}

} // namespace qooedge
