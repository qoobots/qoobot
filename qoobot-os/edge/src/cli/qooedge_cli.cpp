/**
 * qooedge_cli.cpp — qooedge 命令行管理工具
 *
 * 提供对边缘计算层的命令行管理接口：
 *   qooedge-cli status         系统状态
 *   qooedge-cli runtime [stats] 运行时统计
 *   qooedge-cli offload [stats] 卸载决策统计
 *   qooedge-cli mesh [nodes]    Mesh 网络拓扑
 *   qooedge-cli help            帮助信息
 */

#include "qooedge/edge_types.h"
#include "qooedge/edge_runtime.h"
#include "qooedge/edge_offload.h"
#include "qooedge/edge_mesh.h"

#include <iostream>
#include <iomanip>
#include <string>

void printUsage() {
    std::cout << "qooedge-cli — QooEdge CLI v0.1.0\n\n";
    std::cout << "Usage: qooedge-cli <command> [options]\n\n";
    std::cout << "Commands:\n";
    std::cout << "  status              Show edge layer status\n";
    std::cout << "  runtime stats       Show inference runtime statistics\n";
    std::cout << "  offload stats       Show offload decision statistics\n";
    std::cout << "  mesh nodes          List mesh network nodes\n";
    std::cout << "  mesh topology       Show mesh network topology\n";
    std::cout << "  help                Show this help\n";
}

void cmdStatus() {
    auto runtime = qooedge::createEdgeRuntime();
    auto offload = qooedge::createEdgeOffload();
    auto mesh = qooedge::createEdgeMesh();

    runtime->initialize("/data/qooedge/models");
    offload->initialize("/etc/qooedge/offload.yaml");
    mesh->initialize("cli-node", "cli", 0);

    std::cout << "QooEdge Status\n";
    std::cout << "  Runtime Queue Depth:  " << runtime->getQueueDepth() << "\n";
    std::cout << "  Loaded Models:        " << runtime->listLoadedModels().size() << "\n";
    std::cout << "  Offload Offline Mode: " << (offload->isOfflineMode() ? "ON" : "OFF") << "\n";

    auto online_nodes = mesh->getOnlineNodes();
    std::cout << "  Mesh Online Nodes:    " << online_nodes.size() << "\n";
}

void cmdRuntimeStats() {
    auto runtime = qooedge::createEdgeRuntime();
    runtime->initialize("/data/qooedge/models");
    std::cout << runtime->getStatistics() << std::endl;
}

void cmdOffloadStats() {
    auto offload = qooedge::createEdgeOffload();
    offload->initialize("/etc/qooedge/offload.yaml");
    std::cout << offload->getDecisionStats() << std::endl;
}

void cmdMeshNodes() {
    auto mesh = qooedge::createEdgeMesh();
    mesh->initialize("cli-node", "cli", 0);
    mesh->join();

    auto nodes = mesh->getOnlineNodes();
    std::cout << std::left << std::setw(20) << "Node ID"
              << std::setw(20) << "Robot ID"
              << std::setw(10) << "Role"
              << std::setw(18) << "IP"
              << "\n";
    std::cout << std::string(68, '-') << "\n";

    for (const auto& node : nodes) {
        std::string role_str;
        switch (node.role) {
            case qooedge::NodeRole::LEADER: role_str = "LEADER"; break;
            case qooedge::NodeRole::WORKER: role_str = "WORKER"; break;
            case qooedge::NodeRole::RELAY: role_str = "RELAY"; break;
            case qooedge::NodeRole::OBSERVER: role_str = "OBSERVER"; break;
        }

        std::cout << std::left << std::setw(20) << node.node_id
                  << std::setw(20) << node.robot_id
                  << std::setw(10) << role_str
                  << std::setw(18) << node.ip_address
                  << "\n";
    }
}

void cmdMeshTopology() {
    auto mesh = qooedge::createEdgeMesh();
    mesh->initialize("cli-node", "cli", 0);
    mesh->join();
    std::cout << mesh->getTopologyInfo() << std::endl;
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        printUsage();
        return 1;
    }

    std::string cmd1 = argv[1];

    if (cmd1 == "help" || cmd1 == "--help" || cmd1 == "-h") {
        printUsage();
    } else if (cmd1 == "status") {
        cmdStatus();
    } else if (cmd1 == "runtime" && argc >= 3 && std::string(argv[2]) == "stats") {
        cmdRuntimeStats();
    } else if (cmd1 == "offload" && argc >= 3 && std::string(argv[2]) == "stats") {
        cmdOffloadStats();
    } else if (cmd1 == "mesh" && argc >= 3 && std::string(argv[2]) == "nodes") {
        cmdMeshNodes();
    } else if (cmd1 == "mesh" && argc >= 3 && std::string(argv[2]) == "topology") {
        cmdMeshTopology();
    } else {
        std::cerr << "Unknown command: " << cmd1 << "\n";
        printUsage();
        return 1;
    }

    return 0;
}
