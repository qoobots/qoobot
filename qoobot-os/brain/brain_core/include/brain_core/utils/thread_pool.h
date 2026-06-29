// utils/thread_pool.h — Thread pool for parallel task execution
#pragma once

#include <vector>
#include <queue>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <functional>
#include <atomic>
#include <future>

namespace brain_core {

/// Simple fixed-size thread pool for parallel computation.
/// Used by TrajectoryGenerator for parallel strategy generation.
class ThreadPool {
public:
    explicit ThreadPool(size_t num_threads = 4);
    ~ThreadPool();

    /// Submit a task and get a future for the result.
    template<typename F, typename... Args>
    auto submit(F&& f, Args&&... args)
        -> std::future<typename std::invoke_result<F, Args...>::type>;

    /// Get number of threads in the pool.
    size_t threadCount() const { return _threads.size(); }

    /// Get number of queued tasks.
    size_t queueSize() const;

    /// Shut down the pool (waits for all tasks to complete).
    void shutdown();

private:
    void _workerLoop();

    std::vector<std::thread> _threads;
    std::queue<std::function<void()>> _tasks;
    std::mutex _mutex;
    std::condition_variable _cv;
    std::atomic<bool> _running{true};
};

// Template implementation
template<typename F, typename... Args>
auto ThreadPool::submit(F&& f, Args&&... args)
    -> std::future<typename std::invoke_result<F, Args...>::type>
{
    using ReturnType = typename std::invoke_result<F, Args...>::type;

    auto task = std::make_shared<std::packaged_task<ReturnType()>>(
        std::bind(std::forward<F>(f), std::forward<Args>(args)...));

    std::future<ReturnType> result = task->get_future();

    {
        std::lock_guard<std::mutex> lock(_mutex);
        _tasks.emplace([task]() { (*task)(); });
    }

    _cv.notify_one();
    return result;
}

} // namespace brain_core
