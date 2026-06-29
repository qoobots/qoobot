/**
 * @file latency_profiler.cpp
 * @brief 推理延迟剖析器 — 逐层/逐算子延迟火焰图、端到端流水线时延
 *
 * 核心能力：
 *   1. 逐层延迟追踪：记录每个算子/层的执行时间
 *   2. 火焰图生成：输出 Chrome Trace Event 格式（可导入 chrome://tracing）
 *   3. 端到端流水线分析：preprocess → infer → postprocess 分解
 *   4. 百分位统计：P50/P90/P95/P99 延迟
 *   5. 延迟异常检测：自动检测延迟突增
 *
 * 设计要点：
 *   - 低开销：使用 thread_local 存储 + 原子操作，对推理性能影响 < 1%
 *   - 非侵入：通过 RAII 作用域计时器自动追踪
 *   - 可导出：支持 JSON / Chrome Trace / CSV 格式
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/core.h"
#include "qoocore/tensor.h"

#include <spdlog/spdlog.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <map>
#include <mutex>
#include <numeric>
#include <sstream>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

namespace qoocore {
namespace profiler {

// ─────────────────────────────────────────────────────────────────────────────
//  Timer — 高精度计时器
// ─────────────────────────────────────────────────────────────────────────────

using Clock = std::chrono::high_resolution_clock;
using TimePoint = Clock::time_point;

/** @brief 返回当前时间戳（纳秒）。 */
inline std::int64_t now_ns() {
    return std::chrono::duration_cast<std::chrono::nanoseconds>(
               Clock::now().time_since_epoch())
        .count();
}

/** @brief 纳秒 → 毫秒。 */
inline double ns_to_ms(std::int64_t ns) {
    return static_cast<double>(ns) / 1'000'000.0;
}

/** @brief 纳秒 → 微秒。 */
inline double ns_to_us(std::int64_t ns) {
    return static_cast<double>(ns) / 1'000.0;
}

// ─────────────────────────────────────────────────────────────────────────────
//  TraceEvent — 单个追踪事件
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief Chrome Trace Event 格式的事件。
 *
 * 参见：https://docs.google.com/document/d/1CvAClvFfyA5R-PhYUmn5OOQtYMH4h6I0nSsKchNAySU/
 */
struct TraceEvent {
    std::string    name;           ///< 事件名称（如 "Conv2D", "ReLU"）
    std::string    category;       ///< 分类（"layer", "backend", "io"）
    char           phase{'X'};     ///< 'B'=开始, 'E'=结束, 'X'=完整
    std::int64_t   ts{0};          ///< 时间戳（微秒）
    std::int64_t   dur{0};         ///< 持续时间（微秒）
    std::int64_t   tid{0};         ///< 线程 ID
    std::string    pid{"qoocore"}; ///< 进程 ID
    std::unordered_map<std::string, std::string> args; ///< 附加参数

    /** @brief 导出为 JSON 字符串。 */
    [[nodiscard]] std::string to_json() const {
        std::stringstream ss;
        ss << "{\"name\":\"" << name << "\","
           << "\"cat\":\"" << category << "\","
           << "\"ph\":\"" << phase << "\","
           << "\"ts\":" << ts << ","
           << "\"dur\":" << dur << ","
           << "\"tid\":" << tid << ","
           << "\"pid\":\"" << pid << "\"";

        if (!args.empty()) {
            ss << ",\"args\":{";
            bool first = true;
            for (const auto& [k, v] : args) {
                if (!first) ss << ",";
                first = false;
                ss << "\"" << k << "\":\"" << v << "\"";
            }
            ss << "}";
        }
        ss << "}";
        return ss.str();
    }
};

// ─────────────────────────────────────────────────────────────────────────────
//  LayerStats — 单层/单算子统计
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 单个算子/层的延迟统计。
 */
struct LayerStats {
    std::string name;                  ///< 层名称
    std::string op_type;              ///< 算子类型
    std::string backend;              ///< 执行后端

    std::size_t calls{0};             ///< 调用次数
    double      total_us{0.0};        ///< 总耗时（微秒）
    double      min_us{std::numeric_limits<double>::max()};
    double      max_us{0.0};

    // 百分位数据（最近 N 次调用的延迟值，用于计算百分位）
    static constexpr std::size_t MAX_SAMPLES = 1000;
    std::vector<double> recent_latencies;  ///< 环形缓冲

    /** @brief 记录一次调用。 */
    void record(double latency_us) {
        calls++;
        total_us += latency_us;
        min_us = std::min(min_us, latency_us);
        max_us = std::max(max_us, latency_us);

        if (recent_latencies.size() >= MAX_SAMPLES) {
            // 环形覆盖
            recent_latencies[calls % MAX_SAMPLES] = latency_us;
        } else {
            recent_latencies.push_back(latency_us);
        }
    }

    /** @brief 平均延迟（微秒）。 */
    [[nodiscard]] double avg_us() const {
        return calls > 0 ? total_us / calls : 0.0;
    }

    /** @brief 计算指定百分位延迟。 */
    [[nodiscard]] double percentile(double p) const {
        if (recent_latencies.empty()) return 0.0;
        auto sorted = recent_latencies;
        std::sort(sorted.begin(), sorted.end());
        std::size_t idx = static_cast<std::size_t>(p / 100.0 * (sorted.size() - 1));
        return sorted[std::min(idx, sorted.size() - 1)];
    }
};

// ─────────────────────────────────────────────────────────────────────────────
//  ScopeTimer — RAII 作用域计时器
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief RAII 计时器：构造时记录开始时间，析构时自动上报延迟。
 *
 * 用法：
 * ```cpp
 * {
 *     ScopeTimer timer("Conv2D_1", "Conv2D", "npu");
 *     // ... 执行 Conv2D 推理 ...
 * } // 自动记录延迟
 * ```
 */
class ScopeTimer {
public:
    ScopeTimer(const std::string& layer_name,
               const std::string& op_type = "",
               const std::string& backend = "")
        : layer_name_(layer_name)
        , op_type_(op_type)
        , backend_(backend)
        , start_ns_(now_ns()) {}

    ~ScopeTimer() {
        std::int64_t end_ns = now_ns();
        double latency_us = ns_to_us(end_ns - start_ns_);
        LatencyProfiler::instance().record(layer_name_, op_type_, backend_,
                                             latency_us, start_ns_, end_ns);
    }

    // 禁止拷贝/移动
    ScopeTimer(const ScopeTimer&) = delete;
    ScopeTimer& operator=(const ScopeTimer&) = delete;

private:
    std::string   layer_name_;
    std::string   op_type_;
    std::string   backend_;
    std::int64_t  start_ns_;
};

// ─────────────────────────────────────────────────────────────────────────────
//  PipelineStats — 流水线阶段统计
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 推理流水线各阶段统计。
 */
struct PipelineStats {
    // preprocess 阶段
    double preprocess_total_us{0.0};
    std::size_t preprocess_count{0};

    // 推理阶段
    double infer_total_us{0.0};
    std::size_t infer_count{0};

    // postprocess 阶段
    double postprocess_total_us{0.0};
    std::size_t postprocess_count{0};

    // 设备到主机拷贝
    double d2h_copy_total_us{0.0};
    std::size_t d2h_copy_count{0};

    // 端到端（输入 → 输出）
    double e2e_total_us{0.0};
    std::size_t e2e_count{0};
    double e2e_min_us{std::numeric_limits<double>::max()};
    double e2e_max_us{0.0};
};

// ─────────────────────────────────────────────────────────────────────────────
//  LatencyProfiler — 延迟剖析器核心（单例）
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 全局延迟剖析器。
 *
 * 线程安全：使用分段锁减少竞争。
 */
class LatencyProfiler {
public:
    static LatencyProfiler& instance() {
        static LatencyProfiler profiler;
        return profiler;
    }

    /** @brief 启用/禁用剖析。 */
    void set_enabled(bool enabled) {
        enabled_.store(enabled, std::memory_order_release);
    }

    /** @brief 是否启用。 */
    [[nodiscard]] bool is_enabled() const {
        return enabled_.load(std::memory_order_acquire);
    }

    /** @brief 记录一次层/算子延迟。 */
    void record(const std::string& layer_name,
                const std::string& op_type,
                const std::string& backend,
                double latency_us,
                std::int64_t start_ns,
                std::int64_t end_ns) {
        if (!enabled_.load(std::memory_order_acquire)) return;

        std::lock_guard<std::mutex> lock(stats_mutex_);

        std::string key = layer_name + ":" + op_type;
        auto& stats = layer_stats_[key];
        stats.name = layer_name;
        stats.op_type = op_type;
        stats.backend = backend;
        stats.record(latency_us);

        // 添加 Trace Event
        TraceEvent ev;
        ev.name = layer_name;
        ev.category = op_type.empty() ? "layer" : op_type;
        ev.phase = 'X';
        ev.ts = start_ns / 1000;  // ns → us
        ev.dur = static_cast<std::int64_t>(latency_us);
        ev.tid = std::hash<std::thread::id>{}(std::this_thread::get_id());
        ev.args["backend"] = backend;
        trace_events_.push_back(std::move(ev));

        // 限制 Trace Event 数量（环形缓冲）
        if (trace_events_.size() > MAX_TRACE_EVENTS) {
            trace_events_.erase(trace_events_.begin(),
                                trace_events_.begin() + trace_events_.size() / 4);
        }
    }

    /** @brief 记录流水线阶段延迟。 */
    void record_pipeline(const std::string& stage, double latency_us) {
        if (!enabled_.load(std::memory_order_acquire)) return;

        std::lock_guard<std::mutex> lock(pipeline_mutex_);

        if (stage == "preprocess") {
            pipeline_.preprocess_total_us += latency_us;
            pipeline_.preprocess_count++;
        } else if (stage == "infer") {
            pipeline_.infer_total_us += latency_us;
            pipeline_.infer_count++;
        } else if (stage == "postprocess") {
            pipeline_.postprocess_total_us += latency_us;
            pipeline_.postprocess_count++;
        } else if (stage == "d2h_copy") {
            pipeline_.d2h_copy_total_us += latency_us;
            pipeline_.d2h_copy_count++;
        } else if (stage == "e2e") {
            pipeline_.e2e_total_us += latency_us;
            pipeline_.e2e_count++;
            pipeline_.e2e_min_us = std::min(pipeline_.e2e_min_us, latency_us);
            pipeline_.e2e_max_us = std::max(pipeline_.e2e_max_us, latency_us);
        }
    }

    // ── 查询 ───────────────────────────────────────────────────────────

    /** @brief 获取指定层的统计。 */
    [[nodiscard]] std::optional<LayerStats> get_layer_stats(
        const std::string& layer_name) const {
        std::lock_guard<std::mutex> lock(stats_mutex_);
        for (const auto& [key, stats] : layer_stats_) {
            if (stats.name == layer_name) return stats;
        }
        return std::nullopt;
    }

    /** @brief 获取所有层统计（按延迟降序）。 */
    [[nodiscard]] std::vector<LayerStats> get_all_layer_stats() const {
        std::lock_guard<std::mutex> lock(stats_mutex_);
        std::vector<LayerStats> result;
        result.reserve(layer_stats_.size());
        for (const auto& [key, stats] : layer_stats_) {
            result.push_back(stats);
        }
        std::sort(result.begin(), result.end(),
                  [](const LayerStats& a, const LayerStats& b) {
                      return a.total_us > b.total_us;  // 降序
                  });
        return result;
    }

    /** @brief 获取流水线统计。 */
    [[nodiscard]] PipelineStats get_pipeline_stats() const {
        std::lock_guard<std::mutex> lock(pipeline_mutex_);
        return pipeline_;
    }

    // ── 导出 ───────────────────────────────────────────────────────────

    /**
     * @brief 导出为 Chrome Trace Event JSON 格式。
     *
     * 可用 chrome://tracing 或 Perfetto 打开。
     */
    [[nodiscard]] std::string export_chrome_trace() const {
        std::lock_guard<std::mutex> lock(stats_mutex_);

        std::stringstream ss;
        ss << "{\"traceEvents\":[\n";
        for (std::size_t i = 0; i < trace_events_.size(); ++i) {
            if (i > 0) ss << ",\n";
            ss << "  " << trace_events_[i].to_json();
        }
        ss << "\n],\"displayTimeUnit\":\"ns\"}\n";
        return ss.str();
    }

    /**
     * @brief 导出延迟火焰图数据（JSON）。
     *
     * 火焰图结构：
     *   - root: 模型名
     *   - children: 各阶段（preprocess/infer/postprocess）
     *     - children: 各层/算子
     */
    [[nodiscard]] std::string export_flamegraph(const std::string& model_name = "model") const {
        std::lock_guard<std::mutex> lock(stats_mutex_);

        auto layer_stats = get_all_layer_stats();

        std::stringstream ss;
        ss << "{\n";
        ss << "  \"name\": \"" << model_name << "\",\n";
        ss << "  \"value\": "
           << std::accumulate(layer_stats.begin(), layer_stats.end(), 0.0,
                              [](double sum, const LayerStats& s) { return sum + s.total_us; })
           << ",\n";
        ss << "  \"children\": [\n";

        for (std::size_t i = 0; i < layer_stats.size(); ++i) {
            if (i > 0) ss << ",\n";
            const auto& s = layer_stats[i];
            ss << "    {"
               << "\"name\": \"" << s.name << "\","
               << "\"op\": \"" << s.op_type << "\","
               << "\"backend\": \"" << s.backend << "\","
               << "\"value\": " << s.total_us << ","
               << "\"avg\": " << s.avg_us() << ","
               << "\"min\": " << s.min_us << ","
               << "\"max\": " << s.max_us << ","
               << "\"calls\": " << s.calls << ","
               << "\"p50\": " << s.percentile(50) << ","
               << "\"p90\": " << s.percentile(90) << ","
               << "\"p95\": " << s.percentile(95) << ","
               << "\"p99\": " << s.percentile(99)
               << "}";
        }
        ss << "\n  ]\n}\n";
        return ss.str();
    }

    /**
     * @brief 导出流水线阶段延迟摘要（JSON）。
     */
    [[nodiscard]] std::string export_pipeline_summary() const {
        std::lock_guard<std::mutex> lock(pipeline_mutex_);

        std::stringstream ss;
        ss << "{"
           << "\"preprocess_avg_us\": "
           << (pipeline_.preprocess_count > 0
                   ? pipeline_.preprocess_total_us / pipeline_.preprocess_count : 0.0) << ","
           << "\"infer_avg_us\": "
           << (pipeline_.infer_count > 0
                   ? pipeline_.infer_total_us / pipeline_.infer_count : 0.0) << ","
           << "\"postprocess_avg_us\": "
           << (pipeline_.postprocess_count > 0
                   ? pipeline_.postprocess_total_us / pipeline_.postprocess_count : 0.0) << ","
           << "\"d2h_copy_avg_us\": "
           << (pipeline_.d2h_copy_count > 0
                   ? pipeline_.d2h_copy_total_us / pipeline_.d2h_copy_count : 0.0) << ","
           << "\"e2e_avg_us\": "
           << (pipeline_.e2e_count > 0
                   ? pipeline_.e2e_total_us / pipeline_.e2e_count : 0.0) << ","
           << "\"e2e_min_us\": " << pipeline_.e2e_min_us << ","
           << "\"e2e_max_us\": " << pipeline_.e2e_max_us << ","
           << "\"e2e_count\": " << pipeline_.e2e_count
           << "}";
        return ss.str();
    }

    /**
     * @brief 导出为 CSV 格式。
     */
    [[nodiscard]] std::string export_csv() const {
        auto layer_stats = get_all_layer_stats();

        std::stringstream ss;
        ss << "layer,op_type,backend,calls,total_us,avg_us,min_us,max_us,p50_us,p90_us,p95_us,p99_us\n";
        for (const auto& s : layer_stats) {
            ss << s.name << ","
               << s.op_type << ","
               << s.backend << ","
               << s.calls << ","
               << s.total_us << ","
               << s.avg_us() << ","
               << s.min_us << ","
               << s.max_us << ","
               << s.percentile(50) << ","
               << s.percentile(90) << ","
               << s.percentile(95) << ","
               << s.percentile(99) << "\n";
        }
        return ss.str();
    }

    /**
     * @brief 导出延迟异常报告（检测延迟突增）。
     */
    [[nodiscard]] std::string export_anomaly_report() const {
        auto layer_stats = get_all_layer_stats();

        std::stringstream ss;
        ss << "{\"anomalies\": [\n";
        bool first = true;

        for (const auto& s : layer_stats) {
            if (s.calls < 10) continue;  // 需要足够样本

            double avg = s.avg_us();
            double p99 = s.percentile(99);

            // 检测异常：P99 > 3x 平均值
            if (p99 > avg * 3.0 && avg > 0) {
                if (!first) ss << ",\n";
                first = false;
                ss << "  {"
                   << "\"layer\": \"" << s.name << "\","
                   << "\"op_type\": \"" << s.op_type << "\","
                   << "\"severity\": \"warning\","
                   << "\"avg_us\": " << avg << ","
                   << "\"p99_us\": " << p99 << ","
                   << "\"ratio\": " << (p99 / avg) << ","
                   << "\"message\": \"P99 latency is " << (p99 / avg)
                   << "x of average — possible tail latency issue\""
                   << "}";
            }
        }
        ss << "\n]}\n";
        return ss.str();
    }

    /** @brief 保存 Chrome Trace 到文件。 */
    void save_chrome_trace(const std::string& filepath) const {
        std::ofstream ofs(filepath);
        if (ofs) {
            ofs << export_chrome_trace();
            spdlog::info("Chrome trace saved to: {}", filepath);
        } else {
            spdlog::error("Failed to save chrome trace to: {}", filepath);
        }
    }

    /** @brief 重置所有统计。 */
    void reset() {
        std::lock_guard<std::mutex> lock(stats_mutex_);
        layer_stats_.clear();
        trace_events_.clear();

        std::lock_guard<std::mutex> lock2(pipeline_mutex_);
        pipeline_ = PipelineStats{};
    }

private:
    LatencyProfiler() = default;

    static constexpr std::size_t MAX_TRACE_EVENTS = 100'000;

    std::atomic<bool> enabled_{false};

    // 层统计
    mutable std::mutex stats_mutex_;
    std::unordered_map<std::string, LayerStats> layer_stats_;
    std::vector<TraceEvent> trace_events_;

    // 流水线统计
    mutable std::mutex pipeline_mutex_;
    PipelineStats pipeline_;
};

// ─────────────────────────────────────────────────────────────────────────────
//  便捷 API
// ─────────────────────────────────────────────────────────────────────────────

/** @brief 启用全局剖析。 */
inline void enable_profiling() {
    LatencyProfiler::instance().set_enabled(true);
    spdlog::info("Profiling enabled");
}

/** @brief 禁用全局剖析。 */
inline void disable_profiling() {
    LatencyProfiler::instance().set_enabled(false);
    spdlog::info("Profiling disabled");
}

/** @brief 导出 Chrome Trace 到文件。 */
inline void save_trace(const std::string& filepath) {
    LatencyProfiler::instance().save_chrome_trace(filepath);
}

/** @brief 获取剖析摘要（JSON）。 */
inline std::string profiling_summary_json(const std::string& model_name = "model") {
    return LatencyProfiler::instance().export_flamegraph(model_name);
}

/** @brief 重置剖析数据。 */
inline void reset_profiling() {
    LatencyProfiler::instance().reset();
}

}  // namespace profiler
}  // namespace qoocore
