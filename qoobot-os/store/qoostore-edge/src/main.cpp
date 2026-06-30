/**
 * main.cpp — qoostore-edge 守护进程入口
 *
 * qoostore-daemon 是 QooBot 机器人端的技能运行环境守护进程。
 * 它在后台运行，管理所有已安装技能的安装、卸载、更新、沙箱隔离和运行时监控。
 *
 * 启动方式：
 *   qoostore-daemon [--config /path/to/qoostore.yaml]
 *
 * 生命周期：
 *   1. 加载配置
 *   2. 初始化各子系统（技能管理器/沙箱/权限/监控/IPC/依赖解析）
 *   3. 加载已安装技能列表
 *   4. 启动运行时监控循环
 *   5. 进入主事件循环
 *   6. 捕获 SIGTERM/SIGINT → 优雅关闭
 */

#include "qoostore/skill_manager.h"
#include "qoostore/sandbox_engine.h"
#include "qoostore/permission_manager.h"
#include "qoostore/runtime_monitor.h"
#include "qoostore/skill_ipc.h"
#include "qoostore/skill_downloader.h"
#include "qoostore/skill_resolver.h"
#include "json_utils.hpp"

#include <iostream>
#include <string>
#include <thread>
#include <atomic>
#include <csignal>
#include <chrono>
#include <fstream>
#include <sstream>

// ============================================================================
// 工厂函数声明（定义在各模块的 .cpp 文件中）
// ============================================================================

namespace qoostore::edge {

std::unique_ptr<SkillManager> createSkillManager();
std::unique_ptr<SandboxEngine> createSandboxEngine();
std::unique_ptr<PermissionManager> createPermissionManager();
std::unique_ptr<RuntimeMonitor> createRuntimeMonitor();
std::unique_ptr<SkillIPC> createSkillIPC();
std::unique_ptr<SkillDownloader> createSkillDownloader();
std::unique_ptr<SkillResolver> createSkillResolver();

} // namespace qoostore::edge

// ============================================================================
// 全局状态
// ============================================================================

namespace {

std::atomic<bool> g_running{true};
std::unique_ptr<qoostore::edge::SkillManager> g_skill_manager;
std::unique_ptr<qoostore::edge::SandboxEngine> g_sandbox_engine;
std::unique_ptr<qoostore::edge::PermissionManager> g_permission_manager;
std::unique_ptr<qoostore::edge::RuntimeMonitor> g_runtime_monitor;
std::unique_ptr<qoostore::edge::SkillIPC> g_skill_ipc;
std::unique_ptr<qoostore::edge::SkillDownloader> g_skill_downloader;
std::unique_ptr<qoostore::edge::SkillResolver> g_skill_resolver;

struct DaemonConfig {
    std::string skills_root = "/data/qoostore/skills";
    std::string config_path = "/etc/qoostore/daemon.yaml";
    int monitor_interval_sec = 5;
    bool auto_start_skills = true;
};

DaemonConfig g_config;

// ============================================================================
// 信号处理
// ============================================================================

void signalHandler(int sig) {
    std::cout << "\n[qoostore-daemon] Received signal " << sig << ", shutting down..." << std::endl;
    g_running.store(false);
}

void installSignalHandlers() {
    std::signal(SIGINT, signalHandler);
    std::signal(SIGTERM, signalHandler);
#ifndef _WIN32
    std::signal(SIGHUP, signalHandler);
    std::signal(SIGQUIT, signalHandler);
#endif
}

// ============================================================================
// 配置加载
// ============================================================================

DaemonConfig loadConfig(const std::string& config_path) {
    DaemonConfig config;
    std::ifstream file(config_path);
    if (!file.is_open()) {
        std::cout << "[qoostore-daemon] Config file not found, using defaults" << std::endl;
        return config;
    }

    std::stringstream buffer;
    buffer << file.rdbuf();

    try {
        auto root = qoostore::edge::json::parse(buffer.str());
        config.skills_root = root.get_string("skills_root", config.skills_root);
        config.monitor_interval_sec = static_cast<int>(root.get_int("monitor_interval_sec", 5));
        config.auto_start_skills = root.get_bool("auto_start_skills", true);
    } catch (const std::exception& e) {
        std::cerr << "[qoostore-daemon] Failed to parse config: " << e.what() << std::endl;
    }

    return config;
}

// ============================================================================
// 子系统初始化
// ============================================================================

bool initializeSubsystems() {
    std::cout << "[qoostore-daemon] Initializing subsystems..." << std::endl;

    // 1. 技能管理器
    g_skill_manager = qoostore::edge::createSkillManager();
    std::cout << "[qoostore-daemon]   SkillManager: OK" << std::endl;

    // 2. 沙箱引擎
    g_sandbox_engine = qoostore::edge::createSandboxEngine();
    std::cout << "[qoostore-daemon]   SandboxEngine: OK" << std::endl;

    // 3. 权限管理器
    g_permission_manager = qoostore::edge::createPermissionManager();
    g_permission_manager->loadPermissions();
    std::cout << "[qoostore-daemon]   PermissionManager: OK" << std::endl;

    // 4. 运行时监控
    g_runtime_monitor = qoostore::edge::createRuntimeMonitor();
    g_runtime_monitor->onCrash([](const qoostore::edge::CrashReport& report) {
        std::cerr << "[qoostore-daemon] CRASH: " << report.skill_id
                  << " v" << report.version
                  << " signal=" << report.signal << std::endl;
    });
    std::cout << "[qoostore-daemon]   RuntimeMonitor: OK" << std::endl;

    // 5. 技能间 IPC
    g_skill_ipc = qoostore::edge::createSkillIPC();
    std::cout << "[qoostore-daemon]   SkillIPC: OK" << std::endl;

    // 6. 技能下载器
    g_skill_downloader = qoostore::edge::createSkillDownloader();
    std::cout << "[qoostore-daemon]   SkillDownloader: OK" << std::endl;

    // 7. 依赖解析器
    g_skill_resolver = qoostore::edge::createSkillResolver();
    std::cout << "[qoostore-daemon]   SkillResolver: OK" << std::endl;

    return true;
}

// ============================================================================
// 主循环
// ============================================================================

void daemonLoop() {
    std::cout << "[qoostore-daemon] Entering main loop..." << std::endl;

    // 加载已安装技能列表
    auto installed = g_skill_manager->listInstalled();
    std::cout << "[qoostore-daemon] Loaded " << installed.size() << " installed skills" << std::endl;

    // 注册已安装技能到依赖解析器
    for (const auto& skill : installed) {
        g_skill_resolver->registerInstalled(skill.skill_id, skill.version);
        if (g_config.auto_start_skills) {
            g_runtime_monitor->startMonitoring(skill.skill_id);
        }
    }

    // 主事件循环
    while (g_running.load()) {
        std::this_thread::sleep_for(std::chrono::seconds(g_config.monitor_interval_sec));

        // 定期检查更新
        g_skill_manager->checkForUpdates();

        // 刷新监控统计
        g_runtime_monitor->flushStats();
    }
}

// ============================================================================
// 优雅关闭
// ============================================================================

void shutdown() {
    std::cout << "[qoostore-daemon] Shutting down..." << std::endl;

    g_runtime_monitor->stopMonitoringAll();
    g_runtime_monitor->flushStats();

    // 停止所有运行中的技能
    for (const auto& skill : g_skill_manager->listInstalled()) {
        g_sandbox_engine->stopSandbox(skill.skill_id);
    }

    std::cout << "[qoostore-daemon] Shutdown complete." << std::endl;
}

} // anonymous namespace

// ============================================================================
// 主入口
// ============================================================================

int main(int argc, char* argv[]) {
    std::cout << "qoostore-daemon v0.2.0 — QooBot 机器人端技能运行环境" << std::endl;

    // 解析命令行参数
    std::string config_path = "/etc/qoostore/daemon.yaml";
    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "--config" && i + 1 < argc) {
            config_path = argv[++i];
        } else if (arg == "--help" || arg == "-h") {
            std::cout << "Usage: qoostore-daemon [OPTIONS]" << std::endl;
            std::cout << "  --config PATH   Path to daemon config file" << std::endl;
            std::cout << "  --help, -h      Show this help message" << std::endl;
            return 0;
        }
    }

    // 安装信号处理
    installSignalHandlers();

    // 加载配置
    g_config = loadConfig(config_path);
    std::cout << "[qoostore-daemon] Skills root: " << g_config.skills_root << std::endl;

    // 初始化子系统
    if (!initializeSubsystems()) {
        std::cerr << "[qoostore-daemon] Failed to initialize subsystems" << std::endl;
        return 1;
    }

    std::cout << "[qoostore-daemon] All subsystems initialized. Daemon is running." << std::endl;

    // 进入主循环
    daemonLoop();

    // 优雅关闭
    shutdown();

    return 0;
}
