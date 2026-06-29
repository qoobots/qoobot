// utils/time_utils.cpp — Time measurement utilities
#include "brain_core/utils/time_utils.h"
#include <algorithm>
#include <iomanip>
#include <sstream>

namespace brain_core {

Timer::Timer()
{
    _start = std::chrono::steady_clock::now();
}

void Timer::start()
{
    _start = std::chrono::steady_clock::now();
}

double Timer::elapsedSec() const
{
    auto now = std::chrono::steady_clock::now();
    return std::chrono::duration_cast<std::chrono::duration<double>>(
        now - _start).count();
}

double Timer::elapsedMs() const
{
    return elapsedSec() * 1000.0;
}

long long Timer::elapsedUs() const
{
    auto now = std::chrono::steady_clock::now();
    return std::chrono::duration_cast<std::chrono::microseconds>(
        now - _start).count();
}

std::string Timer::nowISO8601()
{
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        now.time_since_epoch()) % 1000;

    std::stringstream ss;
    ss << std::put_time(std::gmtime(&time_t), "%Y-%m-%dT%H:%M:%S");
    ss << "." << std::setw(3) << std::setfill('0') << ms.count() << "Z";
    return ss.str();
}

long long Timer::nowUnixMs()
{
    auto now = std::chrono::system_clock::now();
    return std::chrono::duration_cast<std::chrono::milliseconds>(
        now.time_since_epoch()).count();
}

// MetricsAccumulator
MetricsAccumulator::MetricsAccumulator()
{
    _min = std::numeric_limits<double>::max();
    _max = std::numeric_limits<double>::lowest();
}

void MetricsAccumulator::record(double value)
{
    std::lock_guard<std::mutex> lock(_mutex);
    _samples.push_back(value);
    _sum += value;
    _min = std::min(_min, value);
    _max = std::max(_max, value);
    _count++;
}

double MetricsAccumulator::mean() const
{
    std::lock_guard<std::mutex> lock(_mutex);
    return (_count > 0) ? (_sum / _count) : 0.0;
}

double MetricsAccumulator::p50() const
{
    std::lock_guard<std::mutex> lock(_mutex);
    if (_samples.empty()) return 0.0;
    auto sorted = _samples;
    std::sort(sorted.begin(), sorted.end());
    return sorted[sorted.size() / 2];
}

double MetricsAccumulator::p95() const
{
    std::lock_guard<std::mutex> lock(_mutex);
    if (_samples.empty()) return 0.0;
    auto sorted = _samples;
    std::sort(sorted.begin(), sorted.end());
    return sorted[static_cast<size_t>(sorted.size() * 0.95)];
}

double MetricsAccumulator::p99() const
{
    std::lock_guard<std::mutex> lock(_mutex);
    if (_samples.empty()) return 0.0;
    auto sorted = _samples;
    std::sort(sorted.begin(), sorted.end());
    return sorted[static_cast<size_t>(sorted.size() * 0.99)];
}

void MetricsAccumulator::reset()
{
    std::lock_guard<std::mutex> lock(_mutex);
    _samples.clear();
    _min = std::numeric_limits<double>::max();
    _max = std::numeric_limits<double>::lowest();
    _sum = 0.0;
    _count = 0;
}

} // namespace brain_core
