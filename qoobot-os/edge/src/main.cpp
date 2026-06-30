/**
 * main.cpp — qooedge-daemon 边缘计算守护进程入口
 *
 * qooedge-daemon 是 QooBot 的边缘计算层守护进程。
 * 它在机器人端运行，管理系统与云端之间的推理卸载、数据同步和 Mesh 网络。
 *
 * 启动方式：
 *   qooedge-daemon [--config /path/to/edge.yaml]
 */

#include "qooedge/edge_types.h"
#include "qooedge/edge_runtime.h"
#include "qooedge/edge_offload.h"
#include "qooedge/edge_sync.h"
#include "qooedge/edge_mesh.h"

#include <iostream>
#include <string>
#include <thread>
#include <atomic>
#include <csignal>
#include <chrono>
#include <fstream>
#include <sstream>

// ============================================================================
// 全局状态
// ============================================================================

namespace {

std::atomic<bool> g_running{true};
std::unique_ptr<qooedge::EdgeRuntime> g_runtime;
std::unique_ptr<qooedge::EdgeOffload> g_offload;
std::unique_ptr<qooedge::EdgeSync> g_sync;
std::unique_ptr<qooedge::EdgeMesh> g_mesh;

struct EdgeConfig {
    std::string cloud_endpoint = "https://cloud.qoobot.io";
    std::string device_id = "qoobot-edge-001";
    std::string model_registry = "/data/qooedge/models";
    bool wifi_only = true;
    bool charging_only = true;
    uint16_t mesh_port = 9000;
};

EdgeConfig g_config;

void signalHandler(int sig) {
    std::cout << "\n[qooedge-daemon] Received signal " << sig << ", shutting down..." << std::endl;
    g_running.store(false);
}

void installSignalHandlers() {
    std::signal(SIGINT, signalHandler);
    std::signal(SIGTERM, signalHandler);
}

bool initializeSubsystems() {
    std::cout << "[qooedge-daemon] Initializing edge computing subsystems..." << std::endl;

    // 1. 边缘推理运行时
    g_runtime = qooedge::createEdgeRuntime();
    g_runtime->initialize(g_config.model_registry);
    std::cout << "[qooedge-daemon]   EdgeRuntime: OK" << std::endl;

    // 2. 任务卸载引擎
    g_offload = qooedge::createEdgeOffload();
    g_offload->initialize("/etc/qooedge/offload.yaml");
    std::cout << "[qooedge-daemon]   EdgeOffload: OK" << std::endl;

    // 3. 端-云同步引擎
    g_sync = qooedge::createEdgeSync();
    g_sync->initialize(g_config.cloud_endpoint, g_config.device_id);
    g_sync->setNetworkConstraints(g_config.wifi_only, g_config.charging_only);
    std::cout << "[qooedge-daemon]   EdgeSync: OK" << std::endl;

    // 4. Mesh 网络
    g_mesh = qooedge::createEdgeMesh();
    g_mesh->initialize("edge-" + g_config.device_id, g_config.device_id, g_config.mesh_port);
    g_mesh->join();
    std::cout << "[qooedge-daemon]   EdgeMesh: OK" << std::endl;

    return true;
}

void daemonLoop() {
    std::cout << "[qooedge-daemon] Entering main loop..." << std::endl;

    while (g_running.load()) {
        std::this_thread::sleep_for(std::chrono::seconds(10));

        // 定期心跳
        g_mesh->heartbeat();

        // 打印统计
        std::cout << "[qooedge-daemon] Runtime: " << g_runtime->getStatistics()
                  << " Offload: " << g_offload->getDecisionStats() << std::endl;
    }
}

void shutdown() {
    std::cout << "[qooedge-daemon] Shutting down..." << std::endl;

    g_runtime->shutdown();
    g_mesh->leave();

    std::cout << "[qooedge-daemon] Shutdown complete." << std::endl;
}

} // anonymous namespace

int main(int argc, char* argv[]) {
    std::cout << "qooedge-daemon v0.1.0 — QooBot 边缘计算层" << std::endl;

    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "--help" || arg == "-h") {
            std::cout << "Usage: qooedge-daemon [OPTIONS]\n";
            std::cout << "  --config PATH  Path to edge config file\n";
            std::cout << "  --help, -h     Show this help message\n";
            return 0;
        }
    }

    installSignalHandlers();

    if (!initializeSubsystems()) {
        std::cerr << "[qooedge-daemon] Failed to initialize" << std::endl;
        return 1;
    }

    std::cout << "[qooedge-daemon] All subsystems initialized. Daemon is running." << std::endl;

    daemonLoop();
    shutdown();

    return 0;
}
