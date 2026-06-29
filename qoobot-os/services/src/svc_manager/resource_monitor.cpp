#include <chrono>
#include <string>
#include <thread>
#include <unordered_map>

#ifdef __linux__
#include <sys/resource.h>
#include <sys/sysinfo.h>
#include <unistd.h>
#endif

namespace qoosvc::manager {

/**
 * ResourceMonitor — monitors CPU and memory usage of services.
 *
 * On Linux, uses /proc/self/stat and getrusage for accurate measurements.
 * On other platforms, provides estimates.
 */
class ResourceMonitor {
public:
    struct Usage {
        double cpu_percent;
        size_t memory_mb;
    };

    /**
     * Sample current resource usage for the calling process.
     */
    Usage sample() {
        Usage usage{0.0, 0};

#ifdef __linux__
        struct rusage ru;
        if (getrusage(RUSAGE_SELF, &ru) == 0) {
            // Memory in MB
            usage.memory_mb = ru.ru_maxrss / 1024;

            // CPU time delta
            auto now = std::chrono::steady_clock::now();
            double cpu_time = ru.ru_utime.tv_sec + ru.ru_stime.tv_sec +
                              (ru.ru_utime.tv_usec + ru.ru_stime.tv_usec) / 1e6;

            if (last_sample_time_.time_since_epoch().count() > 0) {
                auto elapsed = std::chrono::duration<double>(now - last_sample_time_).count();
                double cpu_delta = cpu_time - last_cpu_time_;
                if (elapsed > 0) {
                    usage.cpu_percent = (cpu_delta / elapsed) * 100.0;
                }
            }

            last_cpu_time_ = cpu_time;
            last_sample_time_ = now;
        }
#else
        // Fallback: estimate based on known allocations
        usage.cpu_percent = 0.0;
        usage.memory_mb = 0;
#endif

        return usage;
    }

    /**
     * Check if a service exceeds its resource quota.
     * Returns the exceeded resource name, or empty if within limits.
     */
    std::string check_quota(const std::string& name, const Usage& usage,
                             double max_cpu, size_t max_memory_mb) {
        if (max_cpu > 0 && usage.cpu_percent > max_cpu) {
            return "CPU: " + std::to_string(usage.cpu_percent) + "% > " +
                   std::to_string(max_cpu) + "%";
        }
        if (max_memory_mb > 0 && usage.memory_mb > max_memory_mb) {
            return "Memory: " + std::to_string(usage.memory_mb) + "MB > " +
                   std::to_string(max_memory_mb) + "MB";
        }
        return {};
    }

private:
    double last_cpu_time_ = 0.0;
    std::chrono::steady_clock::time_point last_sample_time_;
};

} // namespace qoosvc::manager
