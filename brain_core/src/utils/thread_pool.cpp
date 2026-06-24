// utils/thread_pool.cpp
#include "brain_core/utils/thread_pool.h"
#include <iostream>

namespace brain_core {

ThreadPool::ThreadPool(size_t num_threads)
{
    std::cout << "[ThreadPool] Initialized with " << num_threads << " threads." << std::endl;

    for (size_t i = 0; i < num_threads; ++i) {
        _threads.emplace_back(&ThreadPool::_workerLoop, this);
    }
}

ThreadPool::~ThreadPool()
{
    shutdown();
}

void ThreadPool::_workerLoop()
{
    while (true) {
        std::function<void()> task;
        {
            std::unique_lock<std::mutex> lock(_mutex);
            _cv.wait(lock, [this] {
                return !_running || !_tasks.empty();
            });
            if (!_running && _tasks.empty()) return;
            task = std::move(_tasks.front());
            _tasks.pop();
        }
        task();
    }
}

size_t ThreadPool::queueSize() const
{
    std::lock_guard<std::mutex> lock(_mutex);
    return _tasks.size();
}

void ThreadPool::shutdown()
{
    if (!_running) return;

    _running = false;
    _cv.notify_all();

    for (auto& t : _threads) {
        if (t.joinable()) t.join();
    }
    _threads.clear();
}

} // namespace brain_core
