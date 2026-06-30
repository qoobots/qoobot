/**
 * @file inference_pipeline.cpp
 * @brief 推理流水线执行 — 感知→认知→规划 前后帧 Overlap 并行
 *
 * 机器人推理管线的核心需求：感知/认知/规划三个推理阶段必须在
 * 严格的时间内完成，但可以流水线化以提高吞吐量。
 *
 * 流水线设计：
 * ```
 * Frame N:   [Perception N] → [Cognition N] → [Planning N]
 * Frame N+1:                 [Perception N+1] → [Cognition N+1] → ...
 * Frame N+2:                                    [Perception N+2] → ...
 * ```
 *
 * 关键特性：
 *   - 三阶段流水线：感知/认知/规划
 *   - 前后帧 Overlap：感知帧 N+1 与认知帧 N 并行
 *   - 硬实时约束：每阶段有 deadline，超时则跳过/降级
 *   - 动态批处理：可合并多帧感知请求为 batch
 *   - 延迟/吞吐量可配置权衡
 *   - 与 RealtimeScheduler 协同调度
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/backend.h"
#include "qoocore/core.h"
#include "qoocore/engine.h"
#include "qoocore/tensor.h"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <numeric>
#include <condition_variable>
#include <deque>
#include <functional>
#include <memory>
#include <mutex>
#include <queue>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

#include <spdlog/spdlog.h>

namespace qoocore {
namespace pipeline {

// ═══════════════════════════════════════════════════════════════════════════════
//  流水线阶段定义
// ═══════════════════════════════════════════════════════════════════════════════

/// 流水线阶段类型
enum class StageType : uint8_t {
    PERCEPTION,   ///< 感知阶段：检测/分割/跟踪
    COGNITION,    ///< 认知阶段：场景理解/意图推理/LLM
    PLANNING,     ///< 规划阶段：路径规划/运动规划/控制
    POSTPROCESS,  ///< 后处理（可选）
};

/// 转为字符串
[[nodiscard]] const char* stage_type_to_string(StageType t) {
    switch (t) {
        case StageType::PERCEPTION:  return "perception";
        case StageType::COGNITION:   return "cognition";
        case StageType::PLANNING:    return "planning";
        case StageType::POSTPROCESS: return "postprocess";
        default:                     return "unknown";
    }
}

/// 流水线阶段配置
struct StageConfig {
    StageType type{StageType::PERCEPTION};
    ModelHandle model_handle{INVALID_MODEL_HANDLE};
    std::chrono::microseconds deadline{16000};  ///< 截止时间（默认 16ms = 60FPS）
    std::chrono::microseconds budget{12000};    ///< 执行时间预算
    bool required{true};                         ///< 是否必须执行（false = 可跳过）
    int priority{0};                             ///< 调度优先级（越大越优先）
    bool enable_batching{false};                 ///< 是否启用帧合并批处理
    std::size_t max_batch_size{1};               ///< 最大批处理帧数
};

/// 流水线阶段状态
enum class StageState : uint8_t {
    IDLE,
    WAITING_FOR_INPUT,  ///< 等待上游输出
    EXECUTING,          ///< 正在执行
    COMPLETED,          ///< 执行完成
    TIMEOUT,            ///< 超时
    SKIPPED,            ///< 被跳过
    FAILED,             ///< 执行失败
};

/// 单帧的流水线状态
struct FramePipelineState {
    uint64_t frame_id{0};
    std::chrono::steady_clock::time_point frame_start;

    // 每个阶段的状态和输出
    struct StageResult {
        StageState state{StageState::IDLE};
        std::vector<Tensor> outputs;
        std::chrono::microseconds execution_time{0};
        std::string error_message;
    };
    std::unordered_map<StageType, StageResult> stages;

    // 帧完成回调
    std::function<void(uint64_t frame_id, bool success,
                       const std::vector<Tensor>& final_outputs)> on_frame_complete;
};

// ═══════════════════════════════════════════════════════════════════════════════
//  流水线调度器
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * @brief 推理流水线调度器
 *
 * 管理多阶段流水线的执行，支持前后帧 Overlap。
 * 每个阶段由独立的执行单元处理，通过无锁队列传递数据。
 */
class InferencePipeline {
public:
    /// 流水线配置
    struct Config {
        std::vector<StageConfig> stages;          ///< 阶段配置
        std::size_t max_inflight_frames{3};       ///< 最大飞行中帧数
        std::chrono::microseconds tick_interval{1000}; ///< 调度时钟周期
        bool enable_profiling{false};
        bool enable_frame_drop{true};             ///< 超时是否丢帧
        std::string name{"default"};              ///< 流水线名称
    };

    explicit InferencePipeline(const Config& config)
        : config_(config) {
        validate_config();
    }

    ~InferencePipeline() {
        stop();
    }

    // ── 生命周期 ────────────────────────────────────────────────────────
    /**
     * @brief 启动流水线。
     * @param engine  推理引擎引用
     */
    Result<void> start(InferenceEngine& engine) {
        if (running_) {
            return Error<void>(ErrorCode::ENGINE_NOT_INIT, "Pipeline already running");
        }

        engine_ = &engine;
        running_ = true;
        frame_counter_ = 0;

        spdlog::info("[pipeline:{}] Starting with {} stages, max {} inflight frames",
                      config_.name, config_.stages.size(), config_.max_inflight_frames);

        // 打印阶段信息
        for (const auto& stage : config_.stages) {
            spdlog::info("[pipeline:{}]   Stage '{}': deadline={}us, budget={}us, required={}",
                          config_.name, stage_type_to_string(stage.type),
                          stage.deadline.count(), stage.budget.count(), stage.required);
        }

        // 启动调度线程
        scheduler_thread_ = std::thread(&InferencePipeline::scheduler_loop, this);

        return Ok();
    }

    /**
     * @brief 停止流水线。
     */
    void stop() {
        if (!running_) return;

        spdlog::info("[pipeline:{}] Stopping...", config_.name);
        running_ = false;
        cv_.notify_all();

        if (scheduler_thread_.joinable()) {
            scheduler_thread_.join();
        }

        // 等待所有飞行中的帧完成
        std::lock_guard<std::mutex> lock(frames_mutex_);
        inflight_frames_.clear();

        spdlog::info("[pipeline:{}] Stopped. Total frames: {}, dropped: {}",
                      config_.name, total_frames_.load(), dropped_frames_.load());
    }

    // ── 帧提交 ──────────────────────────────────────────────────────────
    /**
     * @brief 提交一帧数据到流水线。
     *
     * @param inputs    原始输入（传感器数据）
     * @param callback  帧完成回调
     * @return 帧 ID（用于追踪）
     */
    uint64_t submit_frame(const std::vector<Tensor>& inputs,
                           std::function<void(uint64_t, bool,
                           const std::vector<Tensor>&)> callback = nullptr) {

        uint64_t frame_id = frame_counter_++;

        auto frame = std::make_unique<FramePipelineState>();
        frame->frame_id = frame_id;
        frame->frame_start = std::chrono::steady_clock::now();
        frame->on_frame_complete = std::move(callback);

        // 初始化所有阶段
        for (const auto& stage : config_.stages) {
            frame->stages[stage.type] = {};
        }

        // 将原始输入放入感知阶段的"输入"
        auto& perception_stage = frame->stages[StageType::PERCEPTION];
        // Clone inputs (Tensor is move-only)
        for (const auto& t : inputs) {
            auto c = t.clone();
            if (c.ok()) perception_stage.outputs.push_back(std::move(c).value());
        }

        {
            std::lock_guard<std::mutex> lock(frames_mutex_);
            pending_frames_.push_back(std::move(frame));
        }
        cv_.notify_one();

        spdlog::debug("[pipeline:{}] Frame {} submitted, pending={}",
                       config_.name, frame_id, pending_frames_.size());

        return frame_id;
    }

    // ── 性能统计 ────────────────────────────────────────────────────────
    struct PipelineStats {
        uint64_t total_frames{0};
        uint64_t completed_frames{0};
        uint64_t dropped_frames{0};
        uint64_t timeout_frames{0};

        // 端到端延迟
        double avg_e2e_latency_ms{0.0};
        double p50_e2e_latency_ms{0.0};
        double p95_e2e_latency_ms{0.0};
        double p99_e2e_latency_ms{0.0};

        // 各阶段延迟
        std::unordered_map<StageType, double> avg_stage_latency_ms;

        // 吞吐量
        double frames_per_second{0.0};
    };

    [[nodiscard]] PipelineStats get_stats() const {
        std::lock_guard<std::mutex> lock(stats_mutex_);
        return stats_;
    }

    [[nodiscard]] const Config& config() const noexcept { return config_; }
    [[nodiscard]] bool is_running() const noexcept { return running_; }

private:
    // ── 配置验证 ────────────────────────────────────────────────────────
    void validate_config() {
        // 检查阶段顺序：PERCEPTION → COGNITION → PLANNING
        bool has_perception = false, has_cognition = false, has_planning = false;
        for (const auto& stage : config_.stages) {
            switch (stage.type) {
                case StageType::PERCEPTION: has_perception = true; break;
                case StageType::COGNITION:  has_cognition  = true; break;
                case StageType::PLANNING:   has_planning   = true; break;
                default: break;
            }
        }

        if (!has_perception && !has_cognition && !has_planning) {
            spdlog::warn("[pipeline:{}] No standard stages defined", config_.name);
        }

        if (config_.max_inflight_frames == 0) {
            config_.max_inflight_frames = 1;
        }
    }

    // ── 调度循环 ────────────────────────────────────────────────────────
    void scheduler_loop() {
        spdlog::info("[pipeline:{}] Scheduler thread started", config_.name);

        while (running_) {
            // 1. 将 pending 帧提升为 inflight
            promote_pending_frames();

            // 2. 推进各飞行中帧的阶段执行
            advance_inflight_frames();

            // 3. 清理完成的帧
            cleanup_completed_frames();

            // 4. 等待下一个时钟周期
            std::unique_lock<std::mutex> lock(sched_mutex_);
            cv_.wait_for(lock, config_.tick_interval,
                         [this] { return !running_ || !pending_frames_.empty(); });
        }

        spdlog::info("[pipeline:{}] Scheduler thread stopped", config_.name);
    }

    /// 将 pending 帧提升为 inflight（受 max_inflight_frames 限制）
    void promote_pending_frames() {
        std::lock_guard<std::mutex> lock(frames_mutex_);

        while (!pending_frames_.empty() &&
               inflight_frames_.size() < config_.max_inflight_frames) {

            auto frame = std::move(pending_frames_.front());
            pending_frames_.pop_front();

            spdlog::debug("[pipeline:{}] Frame {} promoted to inflight ({} active)",
                           config_.name, frame->frame_id, inflight_frames_.size() + 1);

            inflight_frames_.push_back(std::move(frame));
        }
    }

    /// 推进飞行中帧的阶段执行
    void advance_inflight_frames() {
        std::lock_guard<std::mutex> lock(frames_mutex_);

        for (auto& frame : inflight_frames_) {
            auto now = std::chrono::steady_clock::now();

            // 按顺序推进阶段：PERCEPTION → COGNITION → PLANNING
            static const StageType stage_order[] = {
                StageType::PERCEPTION,
                StageType::COGNITION,
                StageType::PLANNING,
            };

            for (auto stage_type : stage_order) {
                auto& stage_state = frame->stages[stage_type];

                // 已完成或失败则跳过
                if (stage_state.state == StageState::COMPLETED ||
                    stage_state.state == StageState::TIMEOUT ||
                    stage_state.state == StageState::FAILED) {
                    continue;
                }

                // 检查上游依赖
                StageType upstream = get_upstream_stage(stage_type);
                if (upstream != StageType::PERCEPTION) {
                    auto& upstream_state = frame->stages[upstream];
                    if (upstream_state.state != StageState::COMPLETED) {
                        // 上游未完成，不能执行当前阶段
                        continue;
                    }
                }

                // 获取阶段配置
                const StageConfig* stage_cfg = get_stage_config(stage_type);
                if (!stage_cfg) continue;

                // 检查 deadline
                auto frame_elapsed = std::chrono::duration_cast<std::chrono::microseconds>(
                    now - frame->frame_start);
                if (frame_elapsed > stage_cfg->deadline) {
                    if (stage_cfg->required) {
                        stage_state.state = StageState::TIMEOUT;
                        stage_state.error_message = "Stage deadline exceeded";
                        spdlog::warn("[pipeline:{}] Frame {} stage '{}' TIMEOUT ({}us > {}us)",
                                     config_.name, frame->frame_id,
                                     stage_type_to_string(stage_type),
                                     frame_elapsed.count(), stage_cfg->deadline.count());
                    } else {
                        stage_state.state = StageState::SKIPPED;
                        spdlog::debug("[pipeline:{}] Frame {} stage '{}' SKIPPED (optional)",
                                       config_.name, frame->frame_id,
                                       stage_type_to_string(stage_type));
                    }
                    continue;
                }

                // 执行阶段推理
                stage_state.state = StageState::EXECUTING;
                auto stage_start = std::chrono::high_resolution_clock::now();

                auto result = execute_stage(*stage_cfg, frame->stages[upstream].outputs);

                auto stage_end = std::chrono::high_resolution_clock::now();
                stage_state.execution_time = std::chrono::duration_cast<
                    std::chrono::microseconds>(stage_end - stage_start);

                if (result.ok()) {
                    stage_state.outputs = std::move(result).value();
                    stage_state.state = StageState::COMPLETED;

                    spdlog::debug("[pipeline:{}] Frame {} stage '{}' completed in {}us",
                                   config_.name, frame->frame_id,
                                   stage_type_to_string(stage_type),
                                   stage_state.execution_time.count());
                } else {
                    stage_state.state = StageState::FAILED;
                    stage_state.error_message = result.error().message;

                    spdlog::error("[pipeline:{}] Frame {} stage '{}' FAILED: {}",
                                   config_.name, frame->frame_id,
                                   stage_type_to_string(stage_type),
                                   result.error().message);
                }

                // 每次只推进一个阶段（让其他帧也有机会执行）
                break;
            }
        }
    }

    /// 清理完成的帧
    void cleanup_completed_frames() {
        std::lock_guard<std::mutex> lock(frames_mutex_);

        auto it = inflight_frames_.begin();
        while (it != inflight_frames_.end()) {
            auto& frame = *it;
            bool all_done = true;
            bool any_failed = false;

            // 检查所有阶段是否都已完成/超时/跳过/失败
            for (const auto& stage_cfg : config_.stages) {
                auto& stage_state = frame->stages[stage_cfg.type];
                switch (stage_state.state) {
                    case StageState::COMPLETED:
                    case StageState::SKIPPED:
                        break;  // OK
                    case StageState::TIMEOUT:
                    case StageState::FAILED:
                        any_failed = true;
                        break;
                    default:
                        all_done = false;
                        break;
                }
            }

            if (!all_done) {
                ++it;
                continue;
            }

            // 帧完成
            auto frame_end = std::chrono::steady_clock::now();
            auto e2e_latency = std::chrono::duration_cast<
                std::chrono::microseconds>(frame_end - frame->frame_start);

            bool success = !any_failed;

            // 获取最终输出（规划阶段输出）
            const auto& final_outputs = frame->stages[StageType::PLANNING].outputs;

            // 回调
            if (frame->on_frame_complete) {
                frame->on_frame_complete(frame->frame_id, success, final_outputs);
            }

            // 更新统计
            update_stats(frame->frame_id, success, e2e_latency, *frame);

            spdlog::debug("[pipeline:{}] Frame {} {} in {}us",
                           config_.name, frame->frame_id,
                           success ? "completed" : "failed",
                           e2e_latency.count());

            it = inflight_frames_.erase(it);
        }
    }

    /// 执行单个阶段推理
    Result<std::vector<Tensor>> execute_stage(
        const StageConfig& stage,
        const std::vector<Tensor>& inputs) {

        if (!engine_) {
            return Error<std::vector<Tensor>>(ErrorCode::ENGINE_NOT_INIT,
                "Engine not set for pipeline");
        }

        if (stage.model_handle == INVALID_MODEL_HANDLE) {
            // 无模型阶段：透传输入作为输出（如纯后处理阶段）
            std::vector<Tensor> outputs;
            outputs.reserve(inputs.size());
            for (const auto& t : inputs) {
                auto c = t.clone();
                if (!c.ok()) {
                    return Error<std::vector<Tensor>>(c.error().code, c.error().message);
                }
                outputs.push_back(std::move(c).value());
            }
            return outputs;
        }

        // 通过引擎执行推理
        return engine_->infer_multi_input(stage.model_handle, inputs);
    }

    /// 获取上游阶段
    [[nodiscard]] static StageType get_upstream_stage(StageType type) {
        switch (type) {
            case StageType::COGNITION:   return StageType::PERCEPTION;
            case StageType::PLANNING:    return StageType::COGNITION;
            case StageType::POSTPROCESS: return StageType::PLANNING;
            default:                     return StageType::PERCEPTION;
        }
    }

    /// 获取阶段配置
    [[nodiscard]] const StageConfig* get_stage_config(StageType type) const {
        for (const auto& stage : config_.stages) {
            if (stage.type == type) return &stage;
        }
        return nullptr;
    }

    /// 更新统计信息
    void update_stats(uint64_t frame_id, bool success,
                       std::chrono::microseconds e2e_latency,
                       const FramePipelineState& frame) {

        (void)frame_id;

        std::lock_guard<std::mutex> lock(stats_mutex_);

        stats_.total_frames++;
        if (success) {
            stats_.completed_frames++;
        } else {
            stats_.dropped_frames++;
        }

        // 端到端延迟
        double latency_ms = static_cast<double>(e2e_latency.count()) / 1000.0;
        latency_samples_.push_back(latency_ms);

        // 更新各阶段延迟
        for (const auto& [stage_type, stage_result] : frame.stages) {
            if (stage_result.state == StageState::COMPLETED) {
                double stage_ms = static_cast<double>(
                    stage_result.execution_time.count()) / 1000.0;
                auto& avg = stats_.avg_stage_latency_ms[stage_type];
                avg = (avg * (stats_.total_frames - 1) + stage_ms) / stats_.total_frames;
            }
        }

        // 定期重新计算百分位
        if (latency_samples_.size() >= 100) {
            recompute_percentiles();
        }
    }

    void recompute_percentiles() {
        std::vector<double> sorted = latency_samples_;
        std::sort(sorted.begin(), sorted.end());

        auto percentile = [&sorted](double p) -> double {
            if (sorted.empty()) return 0.0;
            std::size_t idx = static_cast<std::size_t>(p / 100.0 * (sorted.size() - 1));
            return sorted[std::min(idx, sorted.size() - 1)];
        };

        stats_.avg_e2e_latency_ms = std::accumulate(sorted.begin(), sorted.end(), 0.0) /
                                     static_cast<double>(sorted.size());
        stats_.p50_e2e_latency_ms = percentile(50.0);
        stats_.p95_e2e_latency_ms = percentile(95.0);
        stats_.p99_e2e_latency_ms = percentile(99.0);

        // 吞吐量（基于平均延迟）
        if (stats_.avg_e2e_latency_ms > 0) {
            stats_.frames_per_second = 1000.0 / stats_.avg_e2e_latency_ms;
        }
    }

    // ── 成员变量 ───────────────────────────────────────────────────────
    Config config_;
    InferenceEngine* engine_{nullptr};
    std::atomic<bool> running_{false};

    // 帧管理
    std::deque<std::unique_ptr<FramePipelineState>> pending_frames_;
    std::deque<std::unique_ptr<FramePipelineState>> inflight_frames_;
    mutable std::mutex frames_mutex_;
    std::atomic<uint64_t> frame_counter_{0};

    // 调度
    std::thread scheduler_thread_;
    std::mutex sched_mutex_;
    std::condition_variable cv_;

    // 统计
    PipelineStats stats_;
    mutable std::mutex stats_mutex_;
    std::vector<double> latency_samples_;

    // 全局统计
    std::atomic<uint64_t> total_frames_{0};
    std::atomic<uint64_t> dropped_frames_{0};
};

// ═══════════════════════════════════════════════════════════════════════════════
//  流水线工厂函数
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * @brief 创建标准的 3 阶段推理流水线（感知→认知→规划）。
 *
 * @param perception_model  感知模型句柄
 * @param cognition_model   认知模型句柄
 * @param planning_model    规划模型句柄
 * @param target_fps        目标帧率（默认 60）
 * @return 流水线实例
 */
[[nodiscard]] std::unique_ptr<InferencePipeline> create_standard_pipeline(
    ModelHandle perception_model,
    ModelHandle cognition_model,
    ModelHandle planning_model,
    int target_fps = 60) {

    InferencePipeline::Config config;
    config.name = "standard_3stage";
    config.max_inflight_frames = 3;

    auto frame_interval_us = std::chrono::microseconds(1000000 / target_fps);

    // 感知阶段
    {
        StageConfig stage;
        stage.type = StageType::PERCEPTION;
        stage.model_handle = perception_model;
        stage.deadline = frame_interval_us * 4 / 10;  // 40% 时间预算
        stage.budget = frame_interval_us * 3 / 10;
        stage.required = true;
        stage.priority = 1;
        config.stages.push_back(stage);
    }

    // 认知阶段
    {
        StageConfig stage;
        stage.type = StageType::COGNITION;
        stage.model_handle = cognition_model;
        stage.deadline = frame_interval_us * 4 / 10;
        stage.budget = frame_interval_us * 3 / 10;
        stage.required = true;
        stage.priority = 0;
        config.stages.push_back(stage);
    }

    // 规划阶段
    {
        StageConfig stage;
        stage.type = StageType::PLANNING;
        stage.model_handle = planning_model;
        stage.deadline = frame_interval_us * 2 / 10;  // 20% 时间预算
        stage.budget = frame_interval_us * 1 / 10;
        stage.required = true;
        stage.priority = 0;
        config.stages.push_back(stage);
    }

    spdlog::info("[pipeline] Created standard 3-stage pipeline @ {} FPS ({}us/frame)",
                  target_fps, frame_interval_us.count());

    return std::make_unique<InferencePipeline>(config);
}

/**
 * @brief 创建简化 2 阶段流水线（感知→规划，跳过认知）。
 */
[[nodiscard]] std::unique_ptr<InferencePipeline> create_fast_pipeline(
    ModelHandle perception_model,
    ModelHandle planning_model,
    int target_fps = 120) {

    InferencePipeline::Config config;
    config.name = "fast_2stage";
    config.max_inflight_frames = 2;

    auto frame_interval_us = std::chrono::microseconds(1000000 / target_fps);

    {
        StageConfig stage;
        stage.type = StageType::PERCEPTION;
        stage.model_handle = perception_model;
        stage.deadline = frame_interval_us * 6 / 10;
        stage.budget = frame_interval_us * 5 / 10;
        stage.required = true;
        stage.priority = 1;
        config.stages.push_back(stage);
    }

    {
        StageConfig stage;
        stage.type = StageType::PLANNING;
        stage.model_handle = planning_model;
        stage.deadline = frame_interval_us * 4 / 10;
        stage.budget = frame_interval_us * 3 / 10;
        stage.required = true;
        stage.priority = 0;
        config.stages.push_back(stage);
    }

    spdlog::info("[pipeline] Created fast 2-stage pipeline @ {} FPS", target_fps);
    return std::make_unique<InferencePipeline>(config);
}

}  // namespace pipeline
}  // namespace qoocore
