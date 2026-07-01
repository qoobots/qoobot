#pragma once

#include "edge_types.h"
#include <memory>
#include <string>
#include <vector>
#include <functional>

namespace qooedge {

/**
 * EdgeMesh — 多机器人 Mesh 网络
 *
 * 管理本地局域网/Ad-Hoc 网络中的多机器人发现、通信和协同。
 * 支持节点自动发现、拓扑维护、消息路由和群组管理。
 *
 * 网络架构：
 *   - 物理层：Wi-Fi 6E / BLE 5.3 / UWB / 5G D2D
 *   - 协议层：mDNS 服务发现 + gRPC 消息通道
 *   - 拓扑层：Mesh + Star 混合拓扑
 *   - 路由层：自适应路由（支持多跳）
 *
 * 对标：ROS 2 DDS Discovery + AWS IoT FleetWise
 */
class EdgeMesh {
public:
    virtual ~EdgeMesh() = default;

    /**
     * 初始化 Mesh 网络
     * @param node_id 本节点 ID
     * @param robot_id 关联机器人 ID
     * @param listen_port 监听端口
     */
    virtual bool initialize(const std::string& node_id,
                             const std::string& robot_id,
                             uint16_t listen_port) = 0;

    /**
     * 加入 Mesh 网络
     * @param discovery_endpoint 发现服务地址（mDNS 或手动指定）
     */
    virtual bool join(const std::string& discovery_endpoint = "") = 0;

    /**
     * 离开 Mesh 网络
     */
    virtual void leave() = 0;

    /**
     * 发送消息到指定节点
     */
    virtual bool sendTo(const std::string& target_node,
                         const MeshMessage& message) = 0;

    /**
     * 广播消息到所有节点
     */
    virtual void broadcast(const MeshMessage& message) = 0;

    /**
     * 按话题发布消息
     */
    virtual void publish(const std::string& topic,
                          const std::vector<uint8_t>& payload) = 0;

    /**
     * 订阅话题
     */
    virtual void subscribe(const std::string& topic,
                            MeshCallback callback) = 0;

    /**
     * 取消订阅
     */
    virtual void unsubscribe(const std::string& topic) = 0;

    /**
     * 获取在线节点列表
     */
    virtual std::vector<MeshNode> getOnlineNodes() const = 0;

    /**
     * 获取指定节点信息
     */
    virtual MeshNode getNode(const std::string& node_id) const = 0;

    /**
     * 注册节点状态变化回调
     */
    virtual void onNodeStateChanged(NodeCallback callback) = 0;

    /**
     * 查看本节点角色
     */
    virtual NodeRole getMyRole() const = 0;

    /**
     * 查看本节点状态
     */
    virtual NodeState getMyState() const = 0;

    /**
     * 设置本节点能力声明
     */
    virtual void setCapabilities(const std::vector<std::string>& capabilities) = 0;

    /**
     * 获取网络拓扑信息
     */
    virtual std::string getTopologyInfo() const = 0;

    /**
     * 发送心跳包
     */
    virtual void heartbeat() = 0;
};

// 工厂函数
std::unique_ptr<EdgeMesh> createEdgeMesh();

} // namespace qooedge
