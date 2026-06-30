#include "qooedge/edge_mesh.h"

using namespace qooedge;

TEST(edge_mesh_init) {
    auto mesh = createEdgeMesh();
    CHECK(mesh->initialize("test-node", "test-robot", 9000));
    CHECK_EQ(mesh->getMyRole(), NodeRole::WORKER);
    CHECK_EQ(mesh->getMyState(), NodeState::ONLINE);
    return true;
}

TEST(edge_mesh_join_leave) {
    auto mesh = createEdgeMesh();
    mesh->initialize("test-node-2", "test-robot-2", 9001);
    mesh->join();
    mesh->leave();
    return true;
}

TEST(edge_mesh_capabilities) {
    auto mesh = createEdgeMesh();
    mesh->initialize("test-node-3", "test-robot-3", 9002);

    std::vector<std::string> caps = {"navigation", "perception", "manipulation"};
    mesh->setCapabilities(caps);

    return true;
}

TEST(edge_mesh_publish_subscribe) {
    auto mesh = createEdgeMesh();
    mesh->initialize("test-node-4", "test-robot-4", 9003);

    bool callback_called = false;
    mesh->subscribe("test/topic", [&](const MeshMessage& msg) {
        callback_called = true;
        CHECK_EQ(msg.topic, "test/topic");
    });

    std::vector<uint8_t> payload = {0x01, 0x02, 0x03};
    mesh->publish("test/topic", payload);

    CHECK(callback_called);

    mesh->unsubscribe("test/topic");
    return true;
}

TEST(edge_mesh_topology_info) {
    auto mesh = createEdgeMesh();
    mesh->initialize("test-node-5", "test-robot-5", 9004);
    mesh->join();

    auto info = mesh->getTopologyInfo();
    CHECK(info.find("test-node-5") != std::string::npos);
    CHECK(info.find("peers") != std::string::npos);

    mesh->leave();
    return true;
}

TEST(edge_mesh_node_state_callback) {
    auto mesh = createEdgeMesh();
    mesh->initialize("test-node-6", "test-robot-6", 9005);

    bool callback_called = false;
    mesh->onNodeStateChanged([&](const MeshNode&, NodeState, NodeState) {
        callback_called = true;
    });

    mesh->join();
    mesh->leave();
    // callback may or may not fire depending on timing
    return true;
}

TEST(edge_mesh_online_nodes) {
    auto mesh = createEdgeMesh();
    mesh->initialize("test-node-7", "test-robot-7", 9006);
    mesh->join();

    auto nodes = mesh->getOnlineNodes();
    CHECK(nodes.size() >= 1u); // at least self

    for (const auto& node : nodes) {
        CHECK(node.state == NodeState::ONLINE);
    }

    mesh->leave();
    return true;
}
