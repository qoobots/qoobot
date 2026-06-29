/**
 * @file realtime_scheduler.cpp
 * @brief 实时推理调度器 — 优先级抢占 + 时间片轮转 + 多模型并发
 *
 * 机器人推理场景需要严格的实时性保证：
 *   - 控制回路 < 1ms (REALTIME 优先级)
 *   - 感知推理 < 16ms (HIGH 优先级, 60FPS)
 *   - 认知推理 < 100ms (NORMAL 优先级)
 *   - 后台任务无延迟要求 (LOW 优先级)
 *
 * 调度策略：
 *   1. 固定优先级抢占调度 (Rate Monotonic / Deadline Monotonic)
 *   2. 同一优先级内时间片轮转 (Round-Robin)
 *   3. NPU/GPU/DSP/CPU 异构资源感知
 *   4. 推理超时检测与降级
 *   5. 流水线执行 (前后帧 Overlap)
 *
 * @copyright QooBot Project
 * @version 0.3.0
 */

#include "qoocore/compiler.h"
#include "qoocore/core.h"
#include "qoocore/engine.h"
#include "qoocore/tensor.h"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <deque>
#include <functional>
#include <map>
#include <memory>
#include <mutex>
#include <queue>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

namespace qoocore {
namespace scheduler {

// ═══════════════════════════════════════════════════════════════════════════════
// 推理任务定义
// ═══════════════════════════════════════════════════════════════════════════════

/// 推理任务优先级（与 ModelConfig::Priority 对齐）
enum class TaskPriority : uint8_t {
    REALTIME = 0,  ///< 最高优先级：控制回路 < 1ms
    HIGH     = 1,  ///< 高优先级：感知 < 16ms
    NORMAL   = 2,  ///< 普通优先级：认知 < 100ms
    LOW      = 3,  ///< 低优先级：后台任务
    IDLE     = 4,  ///< 空闲：仅在无其他任务时执行
};

/// 任务状态
enum class TaskState : uint8_t {
    PENDING,       ///< 等待调度
    RUNNING,       ///< 正在执行
    PREEMPTED,     ///< 被高优先级任务抢占
    COMPLETED,     ///< 已完成
    TIMEOUT,       ///< 超时
    FAILED,        ///< 执行失败
    CANCELLED,     ///< 被取消
};

/// 推理任务描述
struct InferenceTask {
    uint64_t task_id{0};
    ModelHandle model_handle{INVALID_MODEL_HANDLE};
    TaskPriority priority{TaskPriority::NORMAL};

    // 输入/输出
    std::vector<Tensor> inputs;
    std::vector<Tensor> outputs;

    // 时间约束
    std::chrono::steady_clock::time_point enqueue_time;   ///< 入队时间
    std::chrono::steady_clock::time_point start_time;     ///< 开始执行时间
    std::chrono::steady_clock::time_point deadline;        ///< 截止时间
    std::chrono::microseconds budget{0};                   ///< 执行时间预算

    // 回调
    std::function<void(Result<std::vector<Tensor>>)> callback;

    // 状态
    std::atomic<TaskState> state{TaskState::PENDING};

    // 统计
    std::chrono::microseconds actual_execution_time{0};
    uint32_t preempt_count{0};

    /// 是否已超过截止时间
    [[nodiscard]] bool missed_deadline() const {
        if (deadline == std::chrono::steady_clock::time_point{}) return false;
        return std::chrono::steady_clock::now() > deadline;
    }
};

using InferenceTaskPtr = std::shared_ptr<InferenceTask>;

// ═══════════════════════════════════════════════════════════════════════════════
// 硬件资源管理
// ═══════════════════════════════════════════════════════════════════════════════

/// 硬件执行单元状态
struct ExecutionUnit {
    BackendType backend{BackendType::CPU};
    std::string name;
    uint32_t total_cores{1};
    std::atomic<uint32_t> available_cores{1};
    std::atomic<uint64_t> total_inferences{0};
    std::atomic<uint64_t> total_flops{0};
    std::atomic<uint64_t> busy_us{0};       ///< 忙碌时间（微秒）

    /// 是否可接受新任务
    [[nodiscard]] bool can_accept() const {
        return available_cores.load(std::memory_order_relaxed) > 0;
    }

    /// 预留一个核心
    bool reserve() {
        uint32_t expected = available_cores.load(std::memory_order_relaxed);
        while (expected > 0) {
            if (available_cores.compare_exchange_weak(expected, expected - 1,
                    std::memory_order_acquire, std::memory_order_relaxed)) {
                return true;
            }
        }
        return false;
    }

    /// 释放一个核心
    void release() {
        available_cores.fetch_add(1, std::memory_order_release);
    }
};

// ═══════════════════════════════════════════════════════════════════════════════
// 推理调度器配置
// ═══════════════════════════════════════════════════════════════════════════════

struct SchedulerConfig {
    // 优先级时间片（微秒）
    std::chrono::microseconds realtime_quantum{500};    ///< 500us
    std::chrono::microseconds high_quantum{2000};       ///< 2ms
    std::chrono::microseconds normal_quantum{10000};    ///< 10ms
    std::chrono::microseconds low_quantum{50000};       ///< 50ms

    // 抢占阈值
    bool enable_preemption{true};
    uint32_t max_preempt_count{3};  ///< 同一任务最多被抢占次数

    // 超时
    bool enable_timeout{true};
    std::chrono::microseconds default_timeout{30000};   ///< 30ms 默认超时

    // 批处理
    bool enable_batch_merging{true};  ///< 合并同模型的多请求
    uint32_t max_batch_size{8};

    // 流水线
    bool enable_pipeline{true};       ///< 启用流水线执行
    uint32_t pipeline_depth{3};       ///< 流水线深度（帧数）

    // 统计
    bool enable_stats{true};
    uint32_t stats_window_size{1000}; ///< 滑动窗口大小
};

// ═══════════════════════════════════════════════════════════════════════════════
// 调度统计
// ═══════════════════════════════════════════════════════════════════════════════

struct SchedulerStats {
    // 计数器
    std::atomic<uint64_t> tasks_enqueued{0};
    std::atomic<uint64_t> tasks_completed{0};
    std::atomic<uint64_t> tasks_timeout{0};
    std::atomic<uint64_t> tasks_failed{0};
    std::atomic<uint64_t> tasks_preempted{0};
    std::atomic<uint64_t> deadline_misses{0};

    // 延迟统计（微秒）
    struct LatencyWindow {
        static constexpr size_t WINDOW_SIZE = 256;
        std::array<std::chrono::microseconds, WINDOW_SIZE> samples{};
        std::atomic<size_t> write_idx{0};
        std::atomic<size_t> count{0};

        void record(std::chrono::microseconds latency) {
            size_t idx = write_idx.fetch_add(1, std::memory_order_relaxed) % WINDOW_SIZE;
            samples[idx] = latency;
            count.fetch_add(1, std::memory_order_relaxed);
        }

        [[nodiscard]] std::chrono::microseconds percentile(float p) const {
            size_t n = std::min(count.load(std::memory_order_relaxed), WINDOW_SIZE);
            if (n == 0) return std::chrono::microseconds{0};

            std::array<std::chrono::microseconds, WINDOW_SIZE> sorted = samples;
            std::sort(sorted.begin(), sorted.begin() + n);
            size_t idx = static_cast<size_t>(p * n);
            return sorted[std::min(idx, n - 1)];
        }
    };

    LatencyWindow end_to_end_latency;     ///< 端到端延迟
    LatencyWindow queue_wait_latency;     ///< 排队等待延迟
    LatencyWindow execution_latency;      ///< 执行延迟

    // 各优先级统计
    struct PriorityStats {
        std::atomic<uint64_t> completed{0};
        std::atomic<uint64_t> timeout{0};
        std::atomic<uint64_t> preempted{0};
    };
    std::array<PriorityStats, 5> per_priority;  ///< 按 TaskPriority 索引
};

// ═══════════════════════════════════════════════════════════════════════════════
// 实时推理调度器
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * @brief 实时推理调度器
 *
 * 实现固定优先级抢占调度 + 时间片轮转。
 * 线程安全，支持多生产者（提交任务）单消费者（调度循环）。
 */
class RealtimeScheduler {
public:
    explicit RealtimeScheduler(const SchedulerConfig& config = {})
        : config_(config) {}

    ~RealtimeScheduler() { shutdown(); }

    // ── 生命周期 ───────────────────────────────────────────────────────

    /**
     * @brief 启动调度器。
     * @param num_workers  工作线程数
     */
    void start(size_t num_workers = 4) {
        if (running_.load(std::memory_order_acquire)) return;

        running_.store(true, std::memory_order_release);
        stop_requested_.store(false, std::memory_order_release);

        // 初始化执行单元
        init_execution_units();

        // 启动调度线程
        scheduler_thread_ = std::thread(&RealtimeScheduler::scheduler_loop, this);

        // 启动工作线程
        for (size_t i = 0; i < num_workers; ++i) {
            worker_threads_.emplace_back(&RealtimeScheduler::worker_loop, this, i);
        }
    }

    /**
     * @brief 关闭调度器。
     */
    void shutdown() {
        stop_requested_.store(true, std::memory_order_release);
        queue_cv_.notify_all();

        if (scheduler_thread_.joinable()) {
            scheduler_thread_.join();
        }
        for (auto& t : worker_threads_) {
            if (t.joinable()) t.join();
        }

        running_.store(false, std::memory_order_release);
    }

    // ── 任务提交 ───────────────────────────────────────────────────────

    /**
     * @brief 提交推理任务。
     *
     * @param model_handle  模型句柄
     * @param inputs        输入张量列表
     * @param priority      任务优先级
     * @param budget_us     执行时间预算（微秒，0 = 无限制）
     * @param callback      完成回调（可选）
     * @return 任务 ID
     */
    uint64_t submit(
        ModelHandle model_handle,
        std::vector<Tensor> inputs,
        TaskPriority priority = TaskPriority::NORMAL,
        std::chrono::microseconds budget = std::chrono::microseconds{0},
        std::function<void(Result<std::vector<Tensor>>)> callback = nullptr) {

        auto task = std::make_shared<InferenceTask>();
        task->task_id = next_task_id_.fetch_add(1, std::memory_order_relaxed);
        task->model_handle = model_handle;
        task->inputs = std::move(inputs);
        task->priority = priority;
        task->enqueue_time = std::chrono::steady_clock::now();
        task->budget = budget;
        task->callback = std::move(callback);

        // 计算截止时间
        if (budget.count() > 0) {
            task->deadline = task->enqueue_time + budget;
        } else {
            // 使用默认超时
            auto timeout = get_default_timeout(priority);
            task->deadline = task->enqueue_time + timeout;
        }

        uint64_t task_id = task->task_id;

        {
            std::lock_guard<std::mutex> lock(queue_mutex_);
            priority_queues_[static_cast<size_t>(priority)].push_back(task);
            stats_.tasks_enqueued.fetch_add(1, std::memory_order_relaxed);
        }

        queue_cv_.notify_one();
        return task_id;
    }

    /**
     * @brief 取消任务（如果尚未开始执行）。
     */
    bool cancel(uint64_t task_id) {
        std::lock_guard<std::mutex> lock(queue_mutex_);

        for (auto& pq : priority_queues_) {
            auto it = std::find_if(pq.begin(), pq.end(),
                [task_id](const InferenceTaskPtr& t) {
                    return t->task_id == task_id;
                });
            if (it != pq.end()) {
                (*it)->state.store(TaskState::CANCELLED, std::memory_order_release);
                pq.erase(it);
                return true;
            }
        }
        return false;
    }

    // ── 查询 ───────────────────────────────────────────────────────────

    /**
     * @brief 获取调度统计。
     */
    [[nodiscard]] SchedulerStats stats() const { return stats_; }

    /**
     * @brief 导出统计为 JSON 字符串。
     */
    [[nodiscard]] std::string stats_json() const {
        std::ostringstream json;
        json << "{\n";
        json << "  \"tasks_enqueued\": " << stats_.tasks_enqueued.load() << ",\n";
        json << "  \"tasks_completed\": " << stats_.tasks_completed.load() << ",\n";
        json << "  \"tasks_timeout\": " << stats_.tasks_timeout.load() << ",\n";
        json << "  \"tasks_failed\": " << stats_.tasks_failed.load() << ",\n";
        json << "  \"tasks_preempted\": " << stats_.tasks_preempted.load() << ",\n";
        json << "  \"deadline_misses\": " << stats_.deadline_misses.load() << ",\n";
        json << "  \"latency_p50_us\": "
             << stats_.end_to_end_latency.percentile(0.50f).count() << ",\n";
        json << "  \"latency_p95_us\": "
             << stats_.end_to_end_latency.percentile(0.95f).count() << ",\n";
        json << "  \"latency_p99_us\": "
             << stats_.end_to_end_latency.percentile(0.99f).count() << ",\n";
        json << "  \"per_priority\": {\n";
        for (int i = 0; i < 5; ++i) {
            json << "    \"" << priority_name(static_cast<TaskPriority>(i)) << "\": {";
            json << "\"completed\":" << stats_.per_priority[i].completed.load() << ",";
            json << "\"timeout\":" << stats_.per_priority[i].timeout.load() << ",";
            json << "\"preempted\":" << stats_.per_priority[i].preempted.load();
            json << "}";
            if (i < 4) json << ",";
            json << "\n";
        }
        json << "  }\n}";
        return json.str();
    }

    /**
     * @brief 当前队列深度（按优先级）。
     */
    [[nodiscard]] std::array<size_t, 5> queue_depth() const {
        std::array<size_t, 5> depth{};
        std::lock_guard<std::mutex> lock(queue_mutex_);
        for (int i = 0; i < 5; ++i) {
            depth[i] = priority_queues_[i].size();
        }
        return depth;
    }

    /**
     * @brief 是否正在运行。
     */
    [[nodiscard]] bool is_running() const {
        return running_.load(std::memory_order_acquire);
    }

private:
    SchedulerConfig config_;
    SchedulerStats stats_;

    // 多级优先级队列
    mutable std::mutex queue_mutex_;
    std::array<std::deque<InferenceTaskPtr>, 5> priority_queues_;
    std::condition_variable queue_cv_;

    // 当前执行的任务（用于抢占检查）
    std::mutex running_mutex_;
    std::vector<InferenceTaskPtr> running_tasks_;

    // 执行单元
    std::vector<ExecutionUnit> exec_units_;
    std::mutex unit_mutex_;

    // 线程
    std::thread scheduler_thread_;
    std::vector<std::thread> worker_threads_;

    // 状态
    std::atomic<bool> running_{false};
    std::atomic<bool> stop_requested_{false};
    std::atomic<uint64_t> next_task_id_{1};

    // ── 内部方法 ────────────────────────────────────────────────────────

    void init_execution_units() {
        exec_units_.push_back({BackendType::NPU, "NPU_0", 1, 1});
        exec_units_.push_back({BackendType::GPU, "GPU_0", 1, 1});
        exec_units_.push_back({BackendType::CPU, "CPU_0", 4, 4});
        exec_units_.push_back({BackendType::CPU, "CPU_1", 4, 4});
    }

    std::chrono::microseconds get_default_timeout(TaskPriority p) {
        switch (p) {
            case TaskPriority::REALTIME: return std::chrono::microseconds{1000};  // 1ms
            case TaskPriority::HIGH:     return std::chrono::microseconds{16000}; // 16ms
            case TaskPriority::NORMAL:   return std::chrono::microseconds{100000};// 100ms
            case TaskPriority::LOW:      return std::chrono::microseconds{500000};// 500ms
            default:                     return config_.default_timeout;
        }
    }

    std::chrono::microseconds get_quantum(TaskPriority p) {
        switch (p) {
            case TaskPriority::REALTIME: return config_.realtime_quantum;
            case TaskPriority::HIGH:     return config_.high_quantum;
            case TaskPriority::NORMAL:   return config_.normal_quantum;
            case TaskPriority::LOW:      return config_.low_quantum;
            default:                     return config_.normal_quantum;
        }
    }

    static const char* priority_name(TaskPriority p) {
        switch (p) {
            case TaskPriority::REALTIME: return "realtime";
            case TaskPriority::HIGH:     return "high";
            case TaskPriority::NORMAL:   return "normal";
            case TaskPriority::LOW:      return "low";
            case TaskPriority::IDLE:     return "idle";
            default:                     return "unknown";
        }
    }

    /**
     * @brief 调度器主循环
     *
     * 实现固定优先级调度：
     *   1. 从最高优先级队列开始检查
     *   2. 若有高优先级任务到达，抢占当前低优先级任务
     *   3. 同一优先级内按 FIFO 顺序 + 时间片轮转
     */
    void scheduler_loop() {
        while (!stop_requested_.load(std::memory_order_acquire)) {
            InferenceTaskPtr next_task = nullptr;

            {
                std::unique_lock<std::mutex> lock(queue_mutex_);
                queue_cv_.wait_for(lock, std::chrono::microseconds{100},
                    [this] { return stop_requested_.load(std::memory_order_acquire) ||
                                    has_pending_tasks(); });

                if (stop_requested_.load(std::memory_order_acquire)) break;

                // 固定优先级调度：从高到低检查
                for (int p = static_cast<int>(TaskPriority::REALTIME);
                     p <= static_cast<int>(TaskPriority::IDLE); ++p) {

                    auto& pq = priority_queues_[p];
                    if (pq.empty()) continue;

                    // 取队首任务
                    next_task = pq.front();
                    pq.pop_front();

                    // 检查是否超时
                    if (next_task->missed_deadline()) {
                        next_task->state.store(TaskState::TIMEOUT, std::memory_order_release);
                        stats_.tasks_timeout.fetch_add(1, std::memory_order_relaxed);
                        stats_.per_priority[p].timeout.fetch_add(1, std::memory_order_relaxed);
                        stats_.deadline_misses.fetch_add(1, std::memory_order_relaxed);
                        if (next_task->callback) {
                            next_task->callback(Error<std::vector<Tensor>>(
                                ErrorCode::TIMEOUT, "Task deadline missed"));
                        }
                        next_task = nullptr;
                        continue;
                    }
                    break;
                }
            }

            if (next_task) {
                // 检查是否需要抢占
                if (config_.enable_preemption) {
                    check_preemption(next_task);
                }

                // 分配到执行单元
                dispatch_task(next_task);
            }
        }
    }

    /**
     * @brief 检查是否需要抢占低优先级任务。
     */
    void check_preemption(const InferenceTaskPtr& new_task) {
        std::lock_guard<std::mutex> lock(running_mutex_);

        for (auto& running : running_tasks_) {
            if (!running) continue;

            // 只有高优先级可以抢占低优先级
            if (new_task->priority < running->priority) {
                auto current_state = running->state.load(std::memory_order_acquire);
                if (current_state == TaskState::RUNNING) {
                    // 检查抢占次数限制
                    if (running->preempt_count < config_.max_preempt_count) {
                        running->state.store(TaskState::PREEMPTED, std::memory_order_release);
                        running->preempt_count++;
                        stats_.tasks_preempted.fetch_add(1, std::memory_order_relaxed);

                        auto p_idx = static_cast<size_t>(running->priority);
                        stats_.per_priority[p_idx].preempted.fetch_add(1, std::memory_order_relaxed);

                        // 将被抢占的任务重新入队（放在队首）
                        std::lock_guard<std::mutex> qlock(queue_mutex_);
                        auto& pq = priority_queues_[static_cast<size_t>(running->priority)];
                        pq.push_front(running);
                    }
                }
            }
        }
    }

    /**
     * @brief 将任务分配到可用的执行单元。
     */
    void dispatch_task(const InferenceTaskPtr& task) {
        // 查找可用的执行单元
        ExecutionUnit* unit = find_execution_unit(task->model_handle);
        if (!unit) {
            // 无可用单元，重新入队
            std::lock_guard<std::mutex> lock(queue_mutex_);
            auto& pq = priority_queues_[static_cast<size_t>(task->priority)];
            pq.push_front(task);
            return;
        }

        // 预留资源
        if (!unit->reserve()) {
            std::lock_guard<std::mutex> lock(queue_mutex_);
            auto& pq = priority_queues_[static_cast<size_t>(task->priority)];
            pq.push_front(task);
            return;
        }

        task->start_time = std::chrono::steady_clock::now();
        task->state.store(TaskState::RUNNING, std::memory_order_release);

        // 记录排队延迟
        auto queue_wait = std::chrono::duration_cast<std::chrono::microseconds>(
            task->start_time - task->enqueue_time);
        stats_.queue_wait_latency.record(queue_wait);

        {
            std::lock_guard<std::mutex> lock(running_mutex_);
            running_tasks_.push_back(task);
        }

        // 在工作线程中执行（通过条件变量通知）
        {
            std::lock_guard<std::mutex> lock(work_mutex_);
            work_queue_.push_back({task, unit});
        }
        work_cv_.notify_one();
    }

    ExecutionUnit* find_execution_unit(ModelHandle /*handle*/) {
        std::lock_guard<std::mutex> lock(unit_mutex_);
        // 优先 NPU → GPU → CPU
        for (auto& unit : exec_units_) {
            if (unit.can_accept()) return &unit;
        }
        return nullptr;
    }

    /**
     * @brief 工作线程循环
     */
    void worker_loop(size_t worker_id) {
        while (!stop_requested_.load(std::memory_order_acquire)) {
            WorkItem item;

            {
                std::unique_lock<std::mutex> lock(work_mutex_);
                work_cv_.wait_for(lock, std::chrono::microseconds{500},
                    [this] { return stop_requested_.load(std::memory_order_acquire) ||
                                    !work_queue_.empty(); });

                if (stop_requested_.load(std::memory_order_acquire)) break;
                if (work_queue_.empty()) continue;

                item = std::move(work_queue_.front());
                work_queue_.pop_front();
            }

            // 执行推理任务
            execute_task(item.task, item.unit, worker_id);
        }
    }

    void execute_task(const InferenceTaskPtr& task, ExecutionUnit* unit, size_t /*worker_id*/) {
        auto exec_start = std::chrono::steady_clock::now();

        // TODO: 实际调用 InferenceEngine::infer_multi_input()
        // 当前为骨架实现：模拟推理延迟
        std::chrono::microseconds sim_latency;
        switch (task->priority) {
            case TaskPriority::REALTIME: sim_latency = std::chrono::microseconds{500}; break;
            case TaskPriority::HIGH:     sim_latency = std::chrono::microseconds{5000}; break;
            case TaskPriority::NORMAL:   sim_latency = std::chrono::microseconds{30000}; break;
            default:                     sim_latency = std::chrono::microseconds{100000}; break;
        }

        // 时间片控制
        auto quantum = get_quantum(task->priority);
        if (sim_latency > quantum) {
            // 超时间片：模拟被抢占
            std::this_thread::sleep_for(quantum);
            // 如果还没完成，重新入队
            task->state.store(TaskState::PREEMPTED, std::memory_order_release);
            std::lock_guard<std::mutex> lock(queue_mutex_);
            priority_queues_[static_cast<size_t>(task->priority)].push_front(task);
            unit->release();
            return;
        }

        std::this_thread::sleep_for(sim_latency);

        auto exec_end = std::chrono::steady_clock::now();
        auto exec_time = std::chrono::duration_cast<std::chrono::microseconds>(
            exec_end - exec_start);
        task->actual_execution_time = exec_time;

        // 更新统计
        stats_.execution_latency.record(exec_time);
        auto end_to_end = std::chrono::duration_cast<std::chrono::microseconds>(
            exec_end - task->enqueue_time);
        stats_.end_to_end_latency.record(end_to_end);

        auto p_idx = static_cast<size_t>(task->priority);
        stats_.per_priority[p_idx].completed.fetch_add(1, std::memory_order_relaxed);
        stats_.tasks_completed.fetch_add(1, std::memory_order_relaxed);

        // 检查是否错过截止时间
        if (task->deadline != std::chrono::steady_clock::time_point{} &&
            exec_end > task->deadline) {
            stats_.deadline_misses.fetch_add(1, std::memory_order_relaxed);
        }

        // 完成回调
        task->state.store(TaskState::COMPLETED, std::memory_order_release);
        if (task->callback) {
            // 返回模拟输出
            std::vector<Tensor> dummy_outputs;
            task->callback(Ok(std::move(dummy_outputs)));
        }

        // 释放执行单元
        unit->release();
        unit->total_inferences.fetch_add(1, std::memory_order_relaxed);

        // 从运行列表中移除
        {
            std::lock_guard<std::mutex> lock(running_mutex_);
            auto it = std::find(running_tasks_.begin(), running_tasks_.end(), task);
            if (it != running_tasks_.end()) {
                running_tasks_.erase(it);
            }
        }
    }

    bool has_pending_tasks() const {
        for (const auto& pq : priority_queues_) {
            if (!pq.empty()) return true;
        }
        return false;
    }

    // 工作队列
    struct WorkItem {
        InferenceTaskPtr task;
        ExecutionUnit* unit{nullptr};
    };
    std::mutex work_mutex_;
    std::deque<WorkItem> work_queue_;
    std::condition_variable work_cv_;
};

// ═══════════════════════════════════════════════════════════════════════════════
// 全局调度器单例
// ═══════════════════════════════════════════════════════════════════════════════

static std::unique_ptr<RealtimeScheduler> g_scheduler;
static std::mutex g_scheduler_mutex;

RealtimeScheduler& global_scheduler() {
    std::lock_guard<std::mutex> lock(g_scheduler_mutex);
    if (!g_scheduler) {
        g_scheduler = std::make_unique<RealtimeScheduler>();
        g_scheduler->start(4);
    }
    return *g_scheduler;
}

void shutdown_global_scheduler() {
    std::lock_guard<std::mutex> lock(g_scheduler_mutex);
    if (g_scheduler) {
        g_scheduler->shutdown();
        g_scheduler.reset();
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// 流水线执行支持
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * @brief 推理流水线阶段
 *
 * 感知 → 认知 → 规划 的流水线并行执行。
 * 每帧数据流过三个推理阶段，前后帧可以 Overlap。
 */
class InferencePipeline {
public:
    struct PipelineStage {
        std::string name;                    ///< "perception" | "cognition" | "planning"
        ModelHandle model_handle;
        TaskPriority priority;
        std::chrono::microseconds expected_latency;
    };

    explicit InferencePipeline(const std::vector<PipelineStage>& stages)
        : stages_(stages) {}

    /**
     * @brief 推送一帧数据到流水线。
     *
     * 帧数据依次经过每个阶段，各阶段可并行处理不同帧。
     */
    void push_frame(std::vector<Tensor> frame_data) {
        auto& sched = global_scheduler();

        // 流水线深度限制
        {
            std::lock_guard<std::mutex> lock(pipeline_mutex_);
            if (in_flight_frames_.size() >= max_pipeline_depth_) {
                // 丢弃最旧帧（或阻塞等待，取决于配置）
                in_flight_frames_.pop_front();
            }
            in_flight_frames_.push_back(frame_count_++);
        }

        // 依次提交各阶段
        auto current_inputs = std::move(frame_data);
        for (size_t i = 0; i < stages_.size(); ++i) {
            const auto& stage = stages_[i];
            auto stage_inputs = current_inputs;  // 复制（实际应为引用/移动）

            sched.submit(
                stage.model_handle,
                stage_inputs,
                stage.priority,
                stage.expected_latency,
                [this, i, frame_id = frame_count_ - 1](
                    Result<std::vector<Tensor>> result) {
                    if (result.ok() && i + 1 < stages_.size()) {
                        // 结果传递给下一阶段
                        // 实际实现中应通过管道缓冲区传递
                    }
                    on_stage_complete(frame_id, i, result.ok());
                }
            );
        }
    }

    /**
     * @brief 获取流水线统计。
     */
    [[nodiscard]] double throughput_fps() const {
        return throughput_fps_.load(std::memory_order_relaxed);
    }

private:
    std::vector<PipelineStage> stages_;
    std::mutex pipeline_mutex_;
    std::deque<uint64_t> in_flight_frames_;
    uint32_t max_pipeline_depth_{3};
    uint64_t frame_count_{0};
    std::atomic<double> throughput_fps_{0.0};

    void on_stage_complete(uint64_t /*frame_id*/, size_t /*stage_idx*/, bool success) {
        if (!success) {
            // 处理流水线阶段失败
        }
        // 更新吞吐量统计
    }
};

} // namespace scheduler
} // namespace qoocore
