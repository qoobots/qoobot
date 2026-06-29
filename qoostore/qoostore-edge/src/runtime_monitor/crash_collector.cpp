/**
 * crash_collector.cpp — 崩溃收集器
 * 职责：捕获技能崩溃信号、收集堆栈回溯、生成崩溃报告
 */
#include "qoostore/skill_types.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <filesystem>
#include <vector>
#include <string>
#include <chrono>
#include <csignal>
#include <execinfo.h>
#include <cxxabi.h>
#include <unistd.h>
#include <sys/wait.h>

namespace qoostore::edge {

namespace fs = std::filesystem;

class CrashCollector {
public:
    struct CollectorConfig {
        std::string crash_log_dir = "/data/qoostore/crashes";
        int max_crash_logs = 100;       // 最大保留崩溃日志数
        int stack_trace_depth = 32;     // 堆栈回溯深度
        bool enable_core_dump = false;  // 是否生成 core dump
    };

    explicit CrashCollector(const CollectorConfig& config)
        : config_(config) {
        fs::create_directories(config_.crash_log_dir);
        registerSignalHandlers();
    }

    ~CrashCollector() {
        // 恢复默认信号处理
    }

    /**
     * 收集指定技能的崩溃信息
     */
    CrashReport collectCrash(const std::string& skill_id, const std::string& version,
                              int signal, pid_t pid) {
        CrashReport report;
        report.skill_id = skill_id;
        report.version = version;
        report.signal = signal;
        report.timestamp = std::chrono::system_clock::now();

        // 收集堆栈回溯
        report.backtrace = captureBacktrace(pid);

        // 收集进程状态
        report.context["pid"] = std::to_string(pid);
        report.context["signal_name"] = signalName(signal);

        // 保存崩溃报告
        saveCrashReport(report);

        std::cerr << "[CrashCollector] Skill crashed: " << skill_id
                  << " v" << version << " signal=" << signal << std::endl;

        return report;
    }

    /**
     * 获取最近的崩溃报告
     */
    std::vector<CrashReport> getRecentCrashes(const std::string& skill_id, int limit = 10) {
        std::vector<CrashReport> reports;

        for (const auto& entry : fs::directory_iterator(config_.crash_log_dir)) {
            if (!entry.is_regular_file()) continue;
            std::string filename = entry.path().filename().string();
            if (!skill_id.empty() && filename.find(skill_id) == std::string::npos) continue;

            // 读取崩溃报告文件
            std::ifstream file(entry.path());
            if (!file.is_open()) continue;

            CrashReport report;
            std::string line;
            while (std::getline(file, line)) {
                if (line.starts_with("skill_id=")) report.skill_id = line.substr(9);
                else if (line.starts_with("version=")) report.version = line.substr(8);
                else if (line.starts_with("signal=")) report.signal = std::stoi(line.substr(7));
                else if (line.starts_with("backtrace=")) report.backtrace = line.substr(10);
            }

            reports.push_back(report);
            if (reports.size() >= static_cast<size_t>(limit)) break;
        }

        return reports;
    }

    /**
     * 清理旧崩溃日志
     */
    void cleanup() {
        std::vector<fs::directory_entry> entries;
        for (const auto& entry : fs::directory_iterator(config_.crash_log_dir)) {
            if (entry.is_regular_file()) {
                entries.push_back(entry);
            }
        }

        // 按修改时间排序
        std::sort(entries.begin(), entries.end(),
                  [](const auto& a, const auto& b) {
                      return a.last_write_time() > b.last_write_time();
                  });

        // 删除超出限制的旧日志
        for (size_t i = config_.max_crash_logs; i < entries.size(); i++) {
            fs::remove(entries[i].path());
        }
    }

private:
    CollectorConfig config_;

    /**
     * 捕获堆栈回溯
     */
    std::string captureBacktrace(pid_t pid) {
        // 读取 /proc/{pid}/maps 获取内存映射
        // 读取 /proc/{pid}/stack 获取内核栈

        std::stringstream result;

        // 方法1：从 /proc/{pid}/cmdline 获取命令行
        std::string cmdline_path = "/proc/" + std::to_string(pid) + "/cmdline";
        std::ifstream cmdline_file(cmdline_path);
        if (cmdline_file.is_open()) {
            std::string cmdline;
            std::getline(cmdline_file, cmdline, '\0');
            result << "Command: " << cmdline << "\n";
        }

        // 方法2：使用 libunwind 或 backtrace() 获取堆栈
        void* buffer[32];
        int nptrs = backtrace(buffer, config_.stack_trace_depth);
        char** strings = backtrace_symbols(buffer, nptrs);

        if (strings != nullptr) {
            result << "Backtrace (" << nptrs << " frames):\n";
            for (int i = 0; i < nptrs; i++) {
                result << "  #" << i << " " << demangle(strings[i]) << "\n";
            }
            free(strings);
        }

        return result.str();
    }

    /**
     * C++ 符号 demangle
     */
    std::string demangle(const char* symbol) {
        std::string sym(symbol);
        // 提取括号中的 mangled name
        size_t begin = sym.find('(');
        size_t end = sym.find('+');
        if (begin == std::string::npos || end == std::string::npos) return sym;

        std::string mangled = sym.substr(begin + 1, end - begin - 1);
        int status;
        char* demangled = abi::__cxa_demangle(mangled.c_str(), nullptr, nullptr, &status);

        if (status == 0 && demangled != nullptr) {
            std::string result = sym.substr(0, begin + 1) + demangled + sym.substr(end);
            free(demangled);
            return result;
        }

        return sym;
    }

    /**
     * 信号名称映射
     */
    std::string signalName(int sig) {
        switch (sig) {
            case SIGSEGV: return "SIGSEGV (Segmentation fault)";
            case SIGABRT: return "SIGABRT (Aborted)";
            case SIGFPE:  return "SIGFPE (Floating point exception)";
            case SIGILL:  return "SIGILL (Illegal instruction)";
            case SIGBUS:  return "SIGBUS (Bus error)";
            case SIGTERM: return "SIGTERM (Terminated)";
            case SIGKILL: return "SIGKILL (Killed)";
            case SIGSYS:  return "SIGSYS (Bad system call)";
            default:      return "SIGNAL " + std::to_string(sig);
        }
    }

    /**
     * 保存崩溃报告到文件
     */
    void saveCrashReport(const CrashReport& report) {
        auto now = std::chrono::system_clock::now();
        auto time_t = std::chrono::system_clock::to_time_t(now);
        std::stringstream filename;
        filename << config_.crash_log_dir << "/crash_"
                 << report.skill_id << "_"
                 << time_t << ".log";

        std::ofstream file(filename.str());
        if (!file.is_open()) return;

        file << "skill_id=" << report.skill_id << "\n";
        file << "version=" << report.version << "\n";
        file << "signal=" << report.signal << "\n";
        file << "timestamp=" << time_t << "\n";
        file << "backtrace=" << report.backtrace << "\n";
        file.close();

        // 清理旧日志
        cleanup();
    }

    /**
     * 注册信号处理器
     */
    void registerSignalHandlers() {
        // 在监控进程中注册信号处理器
        struct sigaction sa;
        sa.sa_flags = SA_SIGINFO | SA_NOCLDWAIT;
        sigemptyset(&sa.sa_mask);

        // SIGCHLD 用于检测子进程崩溃
        sa.sa_sigaction = [](int sig, siginfo_t* info, void* context) {
            if (sig == SIGCHLD && info->si_code == CLD_KILLED) {
                int status;
                pid_t pid = waitpid(info->si_pid, &status, WNOHANG);
                if (pid > 0 && WIFSIGNALED(status)) {
                    int term_sig = WTERMSIG(status);
                    std::cerr << "[CrashCollector] Child process " << pid
                              << " killed by signal " << term_sig << std::endl;
                }
            }
        };
        sigaction(SIGCHLD, &sa, nullptr);
    }
};

std::unique_ptr<CrashCollector> createCrashCollector(
        const CrashCollector::CollectorConfig& config) {
    return std::make_unique<CrashCollector>(config);
}

} // namespace qoostore::edge
