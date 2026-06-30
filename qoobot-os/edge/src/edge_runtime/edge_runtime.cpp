/**
 * edge_runtime.cpp — 边缘推理运行时实现
 *
 * 管理本地模型加载、推理任务队列和优先级调度。
 * 在端侧 AI 引擎 (QooCore) 上运行推理任务。
 */

#include "qooedge/edge_runtime.h"
#include <iostream>
#include <sstream>
#include <queue>
#include <map>
#include <mutex>
#include <condition_variable>
#include <thread>
#include <atomic>
#include <chrono>
#include <algorithm>

namespace qooedge {

namespace {

// 任务优先队列比较器
struct TaskCompare {
    bool operator()(const std::pair<InferencePriority, OffloadTask>& a,
                    const std::pair<InferencePriority, OffloadTask>& b) const {
        return static_cast<int>(a.first) > static_cast<int>(b.first);
    }
};

} // anonymous namespace

class EdgeRuntimeImpl : public EdgeRuntime {
public:
    EdgeRuntimeImpl() {
        stats_["tasks_completed"] = 0;
        stats_["tasks_failed"] = 0;
        stats_["total_latency_ms"] = 0.0;
    }

    ~EdgeRuntimeImpl() override {
        shutdown();
    }

    bool initialize(const std::string& model_registry_path) override {
        std::cout << "[EdgeRuntime] Initializing with model registry: "
                  << model_registry_path << std::endl;
        model_registry_path_ = model_registry_path;

        // 启动工作线程
        running_.store(true);
        worker_thread_ = std::thread(&EdgeRuntimeImpl::workerLoop, this);

        std::cout << "[EdgeRuntime] Initialized. Worker thread started." << std::endl;
        return true;
    }

    void submitTask(const OffloadTask& task, OffloadCallback callback) override {
        if (!running_.load()) {
            OffloadResult result;
            result.task_id = task.task_id;
            result.success = false;
            result.error = "Runtime is shutting down";
            if (callback) callback(result);
            return;
        }

        {
            std::lock_guard<std::mutex> lock(queue_mutex_);
            task_queue_.push({task.priority, task});
            callbacks_[task.task_id] = std::move(callback);
            queued_count_++;
        }

        queue_cv_.notify_one();

        std::cout << "[EdgeRuntime] Task queued: " << task.task_id
                  << " model=" << task.model_name
                  << " priority=" << static_cast<int>(task.priority) << std::endl;
    }

    void cancelTask(const std::string& task_id) override {
        std::lock_guard<std::mutex> lock(queue_mutex_);
        callbacks_.erase(task_id);
        std::cout << "[EdgeRuntime] Task cancelled: " << task_id << std::endl;
    }

    size_t getQueueDepth() const override {
        std::lock_guard<std::mutex> lock(queue_mutex_);
        return task_queue_.size();
    }

    std::string getStatistics() const override {
        std::lock_guard<std::mutex> lock(stats_mutex_);
        std::ostringstream oss;
        oss << "{"
            << "\"tasks_completed\":" << stats_.at("tasks_completed") << ","
            << "\"tasks_failed\":" << stats_.at("tasks_failed") << ","
            << "\"avg_latency_ms\":" << getAverageLatency() << ","
            << "\"queue_depth\":" << getQueueDepth()
            << "}";
        return oss.str();
    }

    bool loadModel(const std::string& model_name,
                    const std::string& version) override {
        std::lock_guard<std::mutex> lock(model_mutex_);
        std::string model_key = model_name + "@" + version;
        loaded_models_[model_key] = version;

        std::cout << "[EdgeRuntime] Model loaded: " << model_key << std::endl;
        return true;
    }

    void unloadModel(const std::string& model_name) override {
        std::lock_guard<std::mutex> lock(model_mutex_);
        for (auto it = loaded_models_.begin(); it != loaded_models_.end(); ) {
            if (it->first.starts_with(model_name)) {
                std::cout << "[EdgeRuntime] Model unloaded: " << it->first << std::endl;
                it = loaded_models_.erase(it);
            } else {
                ++it;
            }
        }
    }

    std::vector<std::string> listLoadedModels() const override {
        std::lock_guard<std::mutex> lock(model_mutex_);
        std::vector<std::string> result;
        for (const auto& [name, _] : loaded_models_) {
            result.push_back(name);
        }
        return result;
    }

    void shutdown() override {
        running_.store(false);
        queue_cv_.notify_all();

        if (worker_thread_.joinable()) {
            worker_thread_.join();
        }

        // 拒绝所有待处理任务
        {
            std::lock_guard<std::mutex> lock(queue_mutex_);
            while (!task_queue_.empty()) {
                auto [_, task] = task_queue_.top();
                task_queue_.pop();

                auto cb_it = callbacks_.find(task.task_id);
                if (cb_it != callbacks_.end()) {
                    OffloadResult result;
                    result.task_id = task.task_id;
                    result.success = false;
                    result.error = "Runtime shutdown";
                    cb_it->second(result);
                    callbacks_.erase(cb_it);
                }
            }
        }

        std::cout << "[EdgeRuntime] Shutdown complete." << std::endl;
    }

private:
    std::string model_registry_path_;
    std::atomic<bool> running_{false};

    // 任务队列
    using TaskEntry = std::pair<InferencePriority, OffloadTask>;
    std::priority_queue<TaskEntry, std::vector<TaskEntry>, TaskCompare> task_queue_;
    std::map<std::string, OffloadCallback> callbacks_;
    std::map<std::string, std::string> loaded_models_;
    mutable std::mutex queue_mutex_;
    mutable std::mutex model_mutex_;
    mutable std::mutex stats_mutex_;
    std::condition_variable queue_cv_;

    // 工作线程
    std::thread worker_thread_;
    std::atomic<uint64_t> queued_count_{0};

    // 统计信息
    mutable std::map<std::string, double> stats_;

    void workerLoop() {
        while (running_.load()) {
            OffloadTask task;
            OffloadCallback callback;

            {
                std::unique_lock<std::mutex> lock(queue_mutex_);
                queue_cv_.wait(lock, [this] {
                    return !task_queue_.empty() || !running_.load();
                });

                if (!running_.load() && task_queue_.empty()) break;

                auto [priority, t] = task_queue_.top();
                task_queue_.pop();
                task = t;

                auto cb_it = callbacks_.find(task.task_id);
                if (cb_it != callbacks_.end()) {
                    callback = std::move(cb_it->second);
                    callbacks_.erase(cb_it);
                }
            }

            // 执行推理任务
            auto start = std::chrono::steady_clock::now();

            OffloadResult result;
            result.task_id = task.task_id;
            result.actual_execution = OffloadDecision::LOCAL_ONLY;
            result.success = true;

            // 模拟推理计算时间（实际通过 QooCore C API 调用）
            int compute_ms = task.priority == InferencePriority::REALTIME ? 5
                           : task.priority == InferencePriority::HIGH ? 20
                           : task.priority == InferencePriority::NORMAL ? 100
                           : 500;
            std::this_thread::sleep_for(std::chrono::milliseconds(compute_ms));

            auto end = std::chrono::steady_clock::now();
            result.latency_ms = std::chrono::duration<double, std::milli>(end - start).count();

            // 更新统计
            {
                std::lock_guard<std::mutex> lock(stats_mutex_);
                stats_["tasks_completed"]++;
                stats_["total_latency_ms"] += result.latency_ms;
            }

            // 回调结果
            if (callback) {
                callback(result);
            }

            std::cout << "[EdgeRuntime] Task completed: " << task.task_id
                      << " latency=" << result.latency_ms << "ms" << std::endl;
        }
    }

    double getAverageLatency() const {
        double total = stats_.at("total_latency_ms");
        double count = stats_.at("tasks_completed");
        return count > 0 ? total / count : 0.0;
    }
};

std::unique_ptr<EdgeRuntime> createEdgeRuntime() {
    return std::make_unique<EdgeRuntimeImpl>();
}

} // namespace qooedge
