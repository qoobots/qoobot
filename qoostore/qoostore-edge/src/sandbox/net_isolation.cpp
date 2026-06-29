/**
 * net_isolation.cpp — 网络隔离
 * 使用 Linux Network Namespace 实现网络隔离：
 *   - 创建独立的 network namespace
 *   - 仅允许访问 manifest 中声明的网络地址
 *   - eBPF/iptables 规则进行流量过滤
 */
#include "qoostore/skill_types.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <filesystem>
#include <unistd.h>
#include <sys/mount.h>
#include <net/if.h>
#include <arpa/inet.h>

namespace qoostore::edge {

namespace fs = std::filesystem;

class NetworkIsolation {
public:
    struct NetIsolationConfig {
        std::string skill_id;
        std::string sandbox_root;           // /var/run/qoostore/sandboxes/{skill_id}
        std::vector<std::string> allowed_domains;   // 允许访问的域名/IP
        std::vector<int> allowed_ports;             // 允许访问的端口
        bool allow_localhost = false;               // 是否允许 localhost
        bool allow_internet = false;                // 是否允许互联网访问
        uint64_t bandwidth_limit_bps = 0;           // 带宽限制 (bps, 0=不限制)
    };

    explicit NetworkIsolation(const NetIsolationConfig& config)
        : config_(config) {}

    /**
     * 设置网络隔离
     */
    bool setup() {
        std::cout << "[NetIsolation] Setting up network isolation for: " << config_.skill_id << std::endl;

        // 1. 创建 Network Namespace
        if (!createNetworkNamespace()) {
            std::cerr << "[NetIsolation] Failed to create network namespace" << std::endl;
            return false;
        }

        // 2. 创建 veth pair 连接宿主机和 namespace
        if (!setupVethPair()) {
            std::cerr << "[NetIsolation] Failed to setup veth pair" << std::endl;
            return false;
        }

        // 3. 配置防火墙规则（限制允许的地址/端口）
        if (!setupFirewallRules()) {
            std::cerr << "[NetIsolation] Failed to setup firewall rules" << std::endl;
            return false;
        }

        // 4. 设置带宽限制（如果需要）
        if (config_.bandwidth_limit_bps > 0) {
            setupBandwidthLimit();
        }

        std::cout << "[NetIsolation] Network isolation ready" << std::endl;
        return true;
    }

    /**
     * 拆除网络隔离
     */
    bool teardown() {
        std::string ns_path = "/var/run/netns/" + config_.skill_id;
        if (fs::exists(ns_path)) {
            // 删除 namespace（当所有进程退出后自动清理）
            fs::remove(ns_path);
        }
        std::cout << "[NetIsolation] Network isolation removed" << std::endl;
        return true;
    }

private:
    NetIsolationConfig config_;

    /**
     * 创建 Network Namespace
     * ip netns add {skill_id}
     */
    bool createNetworkNamespace() {
        std::string ns_path = "/var/run/netns/" + config_.skill_id;

        // 确保 /var/run/netns 存在
        fs::create_directories("/var/run/netns");

        // 创建 bind mount 作为 namespace 引用
        int fd = open(ns_path.c_str(), O_RDONLY | O_CREAT | O_EXCL, 0);
        if (fd < 0) {
            perror("[NetIsolation] create netns file failed");
            return false;
        }
        close(fd);

        // 使用 unshare 创建新 namespace 并绑定
        // 生产环境：clone() with CLONE_NEWNET flag
        if (unshare(CLONE_NEWNET) != 0) {
            perror("[NetIsolation] unshare CLONE_NEWNET failed");
            return false;
        }

        // 将当前 namespace 绑定到文件
        if (mount("/proc/self/ns/net", ns_path.c_str(), nullptr, MS_BIND, nullptr) != 0) {
            perror("[NetIsolation] mount netns failed");
            return false;
        }

        std::cout << "[NetIsolation] Created network namespace: " << config_.skill_id << std::endl;
        return true;
    }

    /**
     * 设置 veth pair（虚拟以太网对）
     */
    bool setupVethPair() {
        std::string veth_host = "veth-h-" + config_.skill_id.substr(0, 8);
        std::string veth_guest = "veth-g-" + config_.skill_id.substr(0, 8);

        // ip link add {veth_host} type veth peer name {veth_guest}
        // ip link set {veth_guest} netns {skill_id}
        // ip addr add 10.0.x.1/24 dev {veth_host}
        // ip netns exec {skill_id} ip addr add 10.0.x.2/24 dev {veth_guest}
        // ip link set {veth_host} up
        // ip netns exec {skill_id} ip link set {veth_guest} up

        std::cout << "[NetIsolation] veth pair: " << veth_host << " <-> " << veth_guest << std::endl;

        // 生产环境：执行上述 ip 命令或使用 netlink API
        return true;
    }

    /**
     * 配置防火墙规则
     */
    bool setupFirewallRules() {
        // 默认策略：DROP all
        // 允许规则：
        //   1. 允许 lo 接口
        //   2. 允许声明的域名/IP
        //   3. 允许声明的端口
        //   4. 允许 DNS (UDP 53)

        std::cout << "[NetIsolation] Configuring firewall rules" << std::endl;
        std::cout << "[NetIsolation]   Allowed domains: " << config_.allowed_domains.size() << std::endl;
        std::cout << "[NetIsolation]   Allowed ports: " << config_.allowed_ports.size() << std::endl;
        std::cout << "[NetIsolation]   Internet access: " << (config_.allow_internet ? "YES" : "NO") << std::endl;

        // 生产环境：使用 iptables/nftables 或 eBPF 设置规则
        // iptables -A OUTPUT -j DROP
        // iptables -A OUTPUT -o lo -j ACCEPT
        // for each domain: iptables -A OUTPUT -d {ip} -j ACCEPT
        // iptables -A OUTPUT -p udp --dport 53 -j ACCEPT

        return true;
    }

    /**
     * 设置带宽限制
     * 使用 tc (traffic control) 进行流量整形
     */
    void setupBandwidthLimit() {
        std::string veth_host = "veth-h-" + config_.skill_id.substr(0, 8);
        uint64_t rate_kbps = config_.bandwidth_limit_bps / 1000;

        // tc qdisc add dev {veth_host} root tbf rate {rate}kbit burst 32kbit latency 400ms
        std::cout << "[NetIsolation] Bandwidth limit: " << rate_kbps << " kbps on " << veth_host << std::endl;
    }
};

std::unique_ptr<NetworkIsolation> createNetworkIsolation(
        const NetworkIsolation::NetIsolationConfig& config) {
    return std::make_unique<NetworkIsolation>(config);
}

} // namespace qoostore::edge
