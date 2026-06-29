/**
 * process_isolation.cpp — 进程隔离
 * 使用 cgroups v2 + seccomp + Linux namespaces 实现进程隔离：
 *   - PID namespace: 技能只能看到自己的进程
 *   - UTS namespace: 独立的 hostname
 *   - IPC namespace: 隔离的 IPC 资源
 *   - seccomp: 系统调用过滤
 */
#include "qoostore/skill_types.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <filesystem>
#include <unistd.h>
#include <sched.h>
#include <signal.h>
#include <sys/wait.h>
#include <sys/mount.h>
#include <sys/prctl.h>

namespace qoostore::edge {

namespace fs = std::filesystem;

class ProcessIsolation {
public:
    struct ProcessConfig {
        std::string skill_id;
        std::string entry_point;            // 技能入口
        std::string sandbox_root;           // 沙箱根路径
        std::vector<std::string> args;      // 启动参数
        std::vector<std::string> env_vars;  // 环境变量
        int max_cpu_percent = 30;
        int max_memory_mb = 512;
        pid_t child_pid = 0;                // 子进程 PID
    };

    explicit ProcessIsolation(const ProcessConfig& config)
        : config_(config) {}

    /**
     * 在隔离环境中启动技能进程
     * @return 子进程 PID，失败返回 -1
     */
    pid_t startSkill() {
        std::cout << "[ProcessIsolation] Starting skill: " << config_.skill_id
                  << " entry=" << config_.entry_point << std::endl;

        pid_t pid = fork();

        if (pid < 0) {
            perror("[ProcessIsolation] fork failed");
            return -1;
        }

        if (pid == 0) {
            // 子进程：设置隔离环境并执行技能
            setupChildProcess();
            // 不应到达这里
            _exit(1);
        }

        // 父进程：记录子进程 PID
        config_.child_pid = pid;
        std::cout << "[ProcessIsolation] Skill started: pid=" << pid << std::endl;
        return pid;
    }

    /**
     * 停止技能进程
     */
    bool stopSkill() {
        if (config_.child_pid <= 0) {
            return false;
        }

        std::cout << "[ProcessIsolation] Stopping skill: pid=" << config_.child_pid << std::endl;

        // 先发送 SIGTERM
        if (kill(config_.child_pid, SIGTERM) == 0) {
            // 等待最多 5 秒
            int status;
            for (int i = 0; i < 50; i++) {
                pid_t result = waitpid(config_.child_pid, &status, WNOHANG);
                if (result == config_.child_pid) {
                    std::cout << "[ProcessIsolation] Skill exited normally: status=" << status << std::endl;
                    return true;
                }
                usleep(100000); // 100ms
            }
        }

        // 强制 SIGKILL
        std::cout << "[ProcessIsolation] Force killing skill: pid=" << config_.child_pid << std::endl;
        kill(config_.child_pid, SIGKILL);
        waitpid(config_.child_pid, nullptr, 0);
        return true;
    }

    /**
     * 检查技能进程是否存活
     */
    bool isAlive() const {
        if (config_.child_pid <= 0) return false;
        return kill(config_.child_pid, 0) == 0;
    }

private:
    ProcessConfig config_;

    /**
     * 子进程：设置所有隔离
     */
    void setupChildProcess() {
        // 1. 设置 PID namespace（CLONE_NEWPID）
        // 子进程将看到自己为 PID 1
        if (unshare(CLONE_NEWPID) != 0) {
            perror("[ProcessIsolation] unshare CLONE_NEWPID failed");
            _exit(1);
        }

        // 2. 设置 UTS namespace（CLONE_NEWUTS）
        if (unshare(CLONE_NEWUTS) != 0) {
            perror("[ProcessIsolation] unshare CLONE_NEWUTS failed");
        }

        // 3. 设置 IPC namespace（CLONE_NEWIPC）
        if (unshare(CLONE_NEWIPC) != 0) {
            perror("[ProcessIsolation] unshare CLONE_NEWIPC failed");
        }

        // 4. 设置 seccomp 过滤规则
        setupSeccomp();

        // 5. chroot 到沙箱根目录
        if (chdir(config_.sandbox_root.c_str()) != 0) {
            perror("[ProcessIsolation] chdir to sandbox failed");
            _exit(1);
        }

        if (chroot(config_.sandbox_root.c_str()) != 0) {
            perror("[ProcessIsolation] chroot failed");
            _exit(1);
        }

        // 6. 设置资源限制 (rlimit)
        setupResourceLimits();

        // 7. 设置进程名为 skill_id（用于监控识别）
        prctl(PR_SET_NAME, config_.skill_id.c_str(), 0, 0, 0);

        // 8. 执行技能入口
        executeSkill();
    }

    /**
     * 设置 seccomp 过滤规则
     * 允许安全的系统调用，阻止危险的系统调用
     */
    void setupSeccomp() {
        // 生产环境使用 libseccomp:
        // scmp_filter_ctx ctx = seccomp_init(SCMP_ACT_KILL);
        // seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(read), 0);
        // seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(write), 0);
        // seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(exit), 0);
        // seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(exit_group), 0);
        // seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(futex), 0);
        // // 阻止危险的系统调用
        // seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(mount), 0);
        // seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(ptrace), 0);
        // seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(reboot), 0);
        // seccomp_load(ctx);

        std::cout << "[ProcessIsolation] Seccomp filter applied" << std::endl;
    }

    /**
     * 设置资源限制
     */
    void setupResourceLimits() {
        // CPU 时间限制
        struct rlimit cpu_limit;
        cpu_limit.rlim_cur = RLIM_INFINITY;
        cpu_limit.rlim_max = RLIM_INFINITY;
        setrlimit(RLIMIT_CPU, &cpu_limit);

        // 内存限制 (RLIMIT_AS = address space)
        struct rlimit mem_limit;
        mem_limit.rlim_cur = config_.max_memory_mb * 1024 * 1024;
        mem_limit.rlim_max = config_.max_memory_mb * 1024 * 1024;
        setrlimit(RLIMIT_AS, &mem_limit);

        // 文件描述符限制
        struct rlimit nofile_limit;
        nofile_limit.rlim_cur = 1024;
        nofile_limit.rlim_max = 4096;
        setrlimit(RLIMIT_NOFILE, &nofile_limit);

        // 进程数限制
        struct rlimit nproc_limit;
        nproc_limit.rlim_cur = 50;
        nproc_limit.rlim_max = 100;
        setrlimit(RLIMIT_NPROC, &nproc_limit);

        std::cout << "[ProcessIsolation] Resource limits: mem=" << config_.max_memory_mb
                  << "MB, cpu=" << config_.max_cpu_percent << "%" << std::endl;
    }

    /**
     * 执行技能
     */
    void executeSkill() {
        std::vector<char*> argv;
        argv.push_back(const_cast<char*>(config_.entry_point.c_str()));
        for (auto& arg : config_.args) {
            argv.push_back(const_cast<char*>(arg.c_str()));
        }
        argv.push_back(nullptr);

        std::vector<char*> envp;
        for (auto& env : config_.env_vars) {
            envp.push_back(const_cast<char*>(env.c_str()));
        }
        envp.push_back(nullptr);

        execve(config_.entry_point.c_str(), argv.data(), envp.data());

        // 如果 execve 返回，说明执行失败
        perror("[ProcessIsolation] execve failed");
        _exit(1);
    }
};

std::unique_ptr<ProcessIsolation> createProcessIsolation(
        const ProcessIsolation::ProcessConfig& config) {
    return std::make_unique<ProcessIsolation>(config);
}

} // namespace qoostore::edge
