/**
 * stats_reporter.cpp — 统计上报器
 * 职责：定期向云端上报技能使用统计、批量上报、HTTP 客户端
 */
#include "qoostore/skill_types.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <chrono>
#include <thread>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <vector>
#include <string>

namespace qoostore::edge {

/**
 * 统计上报器
 * 收集技能使用统计并定期批量上报到云端
 */
class StatsReporter {
public:
    struct ReporterConfig {
        std::string cloud_endpoint = "https://api.qoobot.ai/api/v1/edge/stats";
        std::string robot_id;               // 机器人设备 ID
        std::chrono::seconds report_interval{60}; // 上报间隔
        int batch_size = 100;               // 批量大小
        int max_queue_size = 1000;          // 最大队列大小
    };

    struct StatsRecord {
        std::string skill_id;
        std::string version;
        std::chrono::system_clock::time_point session_start;
        std::chrono::system_clock::time_point session_end;
        int duration_seconds = 0;
        double avg_cpu_percent = 0.0;
        double avg_memory_mb = 0.0;
        uint64_t network_rx_bytes = 0;
        uint64_t network_tx_bytes = 0;
        int error_count = 0;
    };

    explicit StatsReporter(const ReporterConfig& config)
        : config_(config), running_(false) {}

    ~StatsReporter() {
        stop();
    }

    /**
     * 启动上报线程
     */
    void start() {
        if (running_.exchange(true)) return;

        reporter_thread_ = std::thread([this]() {
            std::cout << "[StatsReporter] Started, interval="
                      << config_.report_interval.count() << "s" << std::endl;

            while (running_.load()) {
                std::unique_lock<std::mutex> lock(mutex_);
                cv_.wait_for(lock, config_.report_interval, [this]() {
                    return !running_.load() || !pending_stats_.empty();
                });

                if (!running_.load()) break;

                // 批量上报
                flushBatch();
            }

            // 停止前上报剩余数据
            flushBatch();
        });
    }

    /**
     * 停止上报线程
     */
    void stop() {
        running_.store(false);
        cv_.notify_all();
        if (reporter_thread_.joinable()) {
            reporter_thread_.join();
        }
        std::cout << "[StatsReporter] Stopped" << std::endl;
    }

    /**
     * 记录技能使用统计
     */
    void recordSession(const StatsRecord& record) {
        std::lock_guard<std::mutex> lock(mutex_);

        if (pending_stats_.size() >= static_cast<size_t>(config_.max_queue_size)) {
            std::cerr << "[StatsReporter] Queue full, dropping oldest record" << std::endl;
            pending_stats_.pop();
        }

        pending_stats_.push(record);
        cv_.notify_one();
    }

    /**
     * 记录崩溃上报
     */
    void reportCrash(const CrashReport& crash) {
        std::lock_guard<std::mutex> lock(mutex_);
        pending_crashes_.push(crash);
    }

    /**
     * 获取待上报记录数
     */
    size_t getPendingCount() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return pending_stats_.size();
    }

    /**
     * 获取队列是否健康（未满）
     */
    bool isHealthy() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return pending_stats_.size() < static_cast<size_t>(config_.max_queue_size * 0.8);
    }

private:
    ReporterConfig config_;
    std::atomic<bool> running_;
    std::thread reporter_thread_;
    mutable std::mutex mutex_;
    std::condition_variable cv_;
    std::queue<StatsRecord> pending_stats_;
    std::queue<CrashReport> pending_crashes_;

    /**
     * 批量上报统计数据
     */
    void flushBatch() {
        std::vector<StatsRecord> batch;

        {
            std::lock_guard<std::mutex> lock(mutex_);
            while (!pending_stats_.empty() && batch.size() < static_cast<size_t>(config_.batch_size)) {
                batch.push_back(pending_stats_.front());
                pending_stats_.pop();
            }
        }

        if (batch.empty()) return;

        std::cout << "[StatsReporter] Flushing " << batch.size() << " records" << std::endl;

        // 构建 JSON payload
        std::string payload = buildPayload(batch);

        // HTTP POST 上报
        if (!httpPost(config_.cloud_endpoint, payload)) {
            std::cerr << "[StatsReporter] Upload failed, requeuing " << batch.size() << " records" << std::endl;
            std::lock_guard<std::mutex> lock(mutex_);
            for (auto& record : batch) {
                if (pending_stats_.size() < static_cast<size_t>(config_.max_queue_size)) {
                    pending_stats_.push(record);
                }
            }
        } else {
            std::cout << "[StatsReporter] Uploaded " << batch.size() << " records successfully" << std::endl;
        }

        // 同时上报崩溃数据
        flushCrashes();
    }

    /**
     * 上报崩溃数据
     */
    void flushCrashes() {
        std::vector<CrashReport> crashes;

        {
            std::lock_guard<std::mutex> lock(mutex_);
            while (!pending_crashes_.empty() && crashes.size() < 10) {
                crashes.push_back(pending_crashes_.front());
                pending_crashes_.pop();
            }
        }

        if (crashes.empty()) return;

        // 构建崩溃上报 payload
        std::stringstream ss;
        ss << "{\"robot_id\":\"" << config_.robot_id << "\",\"crashes\":[";
        for (size_t i = 0; i < crashes.size(); i++) {
            if (i > 0) ss << ",";
            ss << "{\"skill_id\":\"" << crashes[i].skill_id
               << "\",\"version\":\"" << crashes[i].version
               << "\",\"signal\":" << crashes[i].signal
               << ",\"backtrace\":\"" << crashes[i].backtrace << "\"}";
        }
        ss << "]}";

        std::string crash_endpoint = config_.cloud_endpoint + "/crashes";
        httpPost(crash_endpoint, ss.str());
    }

    /**
     * 构建 JSON payload
     */
    std::string buildPayload(const std::vector<StatsRecord>& batch) {
        std::stringstream ss;
        ss << "{\"robot_id\":\"" << config_.robot_id << "\",\"stats\":[";
        for (size_t i = 0; i < batch.size(); i++) {
            if (i > 0) ss << ",";
            const auto& r = batch[i];
            ss << "{"
               << "\"skill_id\":\"" << r.skill_id << "\","
               << "\"version\":\"" << r.version << "\","
               << "\"duration_seconds\":" << r.duration_seconds << ","
               << "\"avg_cpu_percent\":" << r.avg_cpu_percent << ","
               << "\"avg_memory_mb\":" << r.avg_memory_mb << ","
               << "\"network_rx_bytes\":" << r.network_rx_bytes << ","
               << "\"network_tx_bytes\":" << r.network_tx_bytes << ","
               << "\"error_count\":" << r.error_count
               << "}";
        }
        ss << "]}";
        return ss.str();
    }

    /**
     * HTTP POST 请求
     * 生产环境使用 libcurl
     */
    bool httpPost(const std::string& url, const std::string& payload) {
#ifdef QOOSTORE_HAS_CURL
        // 生产环境：使用 libcurl 发送 HTTP POST
        // CURL* curl = curl_easy_init();
        // curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
        // curl_easy_setopt(curl, CURLOPT_POSTFIELDS, payload.c_str());
        // curl_easy_setopt(curl, CURLOPT_TIMEOUT, 30L);
        // CURLcode res = curl_easy_perform(curl);
        // curl_easy_cleanup(curl);
        // return res == CURLE_OK;
#endif
        std::cout << "[StatsReporter] HTTP POST: " << url
                  << " payload_size=" << payload.length() << std::endl;
        return true; // Stub: 开发环境默认成功
    }
};

std::unique_ptr<StatsReporter> createStatsReporter(
        const StatsReporter::ReporterConfig& config) {
    return std::make_unique<StatsReporter>(config);
}

} // namespace qoostore::edge
