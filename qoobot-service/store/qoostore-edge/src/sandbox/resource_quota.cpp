/**
 * resource_quota.cpp — 资源配额管理
 * 使用 cgroups v2 实现 CPU、内存、IO 资源配额：
 *   - CPU: cpu.max (带宽控制)
 *   - Memory: memory.max + memory.high
 *   - IO: io.max (读写带宽和 IOPS 限制)
 *   - PIDs: pids.max (最大进程数)
 */
#include "qoostore/skill_types.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <filesystem>
#include <vector>
#include <string>
#include <algorithm>

namespace qoostore::edge {

namespace fs = std::filesystem;

class ResourceQuota {
public:
    struct QuotaConfig {
        std::string skill_id;
        std::string cgroup_path;            // /sys/fs/cgroup/qoostore/{skill_id}
        int cpu_max_percent = 30;           // CPU 最大百分比
        uint64_t memory_max_mb = 512;       // 最大内存 (MB)
        uint64_t memory_high_mb = 400;      // 内存高水位 (MB)
        uint64_t io_read_bps = 0;           // IO 读带宽限制 (bytes/s, 0=不限制)
        uint64_t io_write_bps = 0;          // IO 写带宽限制 (bytes/s, 0=不限制)
        int max_pids = 50;                  // 最大进程数
    };

    explicit ResourceQuota(const QuotaConfig& config)
        : config_(config) {}

    /**
     * 创建并配置 cgroup
     */
    bool setup() {
        std::cout << "[ResourceQuota] Setting up cgroup for: " << config_.skill_id << std::endl;

        if (!createCgroup()) {
            std::cerr << "[ResourceQuota] Failed to create cgroup" << std::endl;
            return false;
        }

        // 配置各控制器
        setupCpu();
        setupMemory();
        setupIO();
        setupPids();

        std::cout << "[ResourceQuota] Cgroup configured: "
                  << "cpu=" << config_.cpu_max_percent << "%, "
                  << "mem=" << config_.memory_max_mb << "MB, "
                  << "pids=" << config_.max_pids << std::endl;
        return true;
    }

    /**
     * 添加进程到 cgroup
     */
    bool addProcess(pid_t pid) {
        std::string procs_path = config_.cgroup_path + "/cgroup.procs";
        std::ofstream procs_file(procs_path);
        if (!procs_file.is_open()) {
            std::cerr << "[ResourceQuota] Failed to open cgroup.procs" << std::endl;
            return false;
        }
        procs_file << pid;
        procs_file.close();
        std::cout << "[ResourceQuota] Added pid " << pid << " to cgroup" << std::endl;
        return true;
    }

    /**
     * 删除 cgroup（当所有进程退出后）
     */
    bool teardown() {
        if (fs::exists(config_.cgroup_path)) {
            try {
                fs::remove(config_.cgroup_path);
                std::cout << "[ResourceQuota] Cgroup removed: " << config_.skill_id << std::endl;
            } catch (const std::exception& e) {
                std::cerr << "[ResourceQuota] Failed to remove cgroup: " << e.what() << std::endl;
                return false;
            }
        }
        return true;
    }

    /**
     * 更新 CPU 配额（运行时动态调整）
     */
    bool updateCpuLimit(int cpu_percent) {
        config_.cpu_max_percent = cpu_percent;
        return setupCpu();
    }

    /**
     * 更新内存配额
     */
    bool updateMemoryLimit(uint64_t memory_mb) {
        config_.memory_max_mb = memory_mb;
        config_.memory_high_mb = memory_mb * 4 / 5; // high = 80% of max
        return setupMemory();
    }

    /**
     * 获取当前资源使用情况
     */
    ResourceUsage getCurrentUsage() const {
        ResourceUsage usage = {};

        // 读取 memory.current
        std::string mem_current_path = config_.cgroup_path + "/memory.current";
        std::ifstream mem_file(mem_current_path);
        if (mem_file.is_open()) {
            uint64_t mem_bytes;
            mem_file >> mem_bytes;
            usage.memory_mb = mem_bytes / (1024 * 1024);
        }

        // 读取 cpu.stat
        std::string cpu_stat_path = config_.cgroup_path + "/cpu.stat";
        std::ifstream cpu_file(cpu_stat_path);
        if (cpu_file.is_open()) {
            std::string line;
            while (std::getline(cpu_file, line)) {
                if (line.starts_with("usage_usec ")) {
                    // usage_percent = usage_usec / period_usec * 100
                    // Simplified
                    usage.cpu_percent = 10.0; // stub
                }
            }
        }

        return usage;
    }

private:
    QuotaConfig config_;

    bool createCgroup() {
        try {
            fs::create_directories(config_.cgroup_path);
            return true;
        } catch (const std::exception& e) {
            std::cerr << "[ResourceQuota] Create cgroup failed: " << e.what() << std::endl;
            return false;
        }
    }

    /**
     * 配置 CPU 控制器
     * cgroups v2: cpu.max = "$MAX $PERIOD"
     * 例如：cpu_max_percent=30, period=100000 -> "30000 100000"
     */
    bool setupCpu() {
        std::string cpu_max_path = config_.cgroup_path + "/cpu.max";
        std::ofstream cpu_file(cpu_max_path);
        if (!cpu_file.is_open()) return false;

        int period = 100000; // 100ms
        int quota = (config_.cpu_max_percent * period) / 100;
        cpu_file << quota << " " << period;
        cpu_file.close();
        return true;
    }

    /**
     * 配置内存控制器
     * cgroups v2: memory.max, memory.high, memory.swap.max
     */
    bool setupMemory() {
        // memory.max — 硬限制（触发 OOM）
        std::string mem_max_path = config_.cgroup_path + "/memory.max";
        std::ofstream mem_max_file(mem_max_path);
        if (mem_max_file.is_open()) {
            mem_max_file << (config_.memory_max_mb * 1024 * 1024);
            mem_max_file.close();
        }

        // memory.high — 软限制（触发回收，不 OOM）
        std::string mem_high_path = config_.cgroup_path + "/memory.high";
        std::ofstream mem_high_file(mem_high_path);
        if (mem_high_file.is_open()) {
            mem_high_file << (config_.memory_high_mb * 1024 * 1024);
            mem_high_file.close();
        }

        // memory.swap.max — 禁用 swap（防止内存压力）
        std::string swap_path = config_.cgroup_path + "/memory.swap.max";
        std::ofstream swap_file(swap_path);
        if (swap_file.is_open()) {
            swap_file << "0";
            swap_file.close();
        }

        return true;
    }

    /**
     * 配置 IO 控制器
     * cgroups v2: io.max = "device rbps wbps riops wiops"
     */
    bool setupIO() {
        if (config_.io_read_bps == 0 && config_.io_write_bps == 0) {
            return true; // 不限制 IO
        }

        std::string io_max_path = config_.cgroup_path + "/io.max";
        std::ofstream io_file(io_max_path);
        if (!io_file.is_open()) return false;

        // 限制主要块设备 (简化：使用设备号 8:0 = sda)
        io_file << "8:0"
                << " rbps=" << config_.io_read_bps
                << " wbps=" << config_.io_write_bps
                << std::endl;
        io_file.close();
        return true;
    }

    /**
     * 配置进程数限制
     */
    bool setupPids() {
        std::string pids_max_path = config_.cgroup_path + "/pids.max";
        std::ofstream pids_file(pids_max_path);
        if (!pids_file.is_open()) return false;

        pids_file << config_.max_pids;
        pids_file.close();
        return true;
    }
};

std::unique_ptr<ResourceQuota> createResourceQuota(
        const ResourceQuota::QuotaConfig& config) {
    return std::make_unique<ResourceQuota>(config);
}

} // namespace qoostore::edge
