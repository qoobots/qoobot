// utils/time_utils.h — Time measurement and conversion utilities
#pragma once

#include <chrono>
#include <string>
#include <vector>
#include <atomic>

namespace brain_core {

/// High-precision timer for performance measurement.
class Timer {
public:
    Timer();

    /// Start or reset the timer.
    void start();

    /// Get elapsed time since last start in seconds.
    double elapsedSec() const;

    /// Get elapsed time in milliseconds.
    double elapsedMs() const;

    /// Get elapsed time in microseconds.
    long long elapsedUs() const;

    /// Get current timestamp as ISO 8601 string.
    static std::string nowISO8601();

    /// Get current timestamp as Unix milliseconds.
    static long long nowUnixMs();

private:
    std::chrono::steady_clock::time_point _start;
};

/// Performance metrics accumulator.
class MetricsAccumulator {
public:
    MetricsAccumulator();

    /// Record a sample.
    void record(double value);

    /// Get statistics.
    double min()   const { return _min; }
    double max()   const { return _max; }
    double mean()  const;
    double p50()   const;  // median
    double p95()   const;
    double p99()   const;
    int    count() const { return _count; }

    /// Reset all accumulated data.
    void reset();

private:
    std::vector<double> _samples;
    double _min{0.0};
    double _max{0.0};
    double _sum{0.0};
    mutable std::mutex _mutex;
    std::atomic<int> _count{0};
};

} // namespace brain_core
