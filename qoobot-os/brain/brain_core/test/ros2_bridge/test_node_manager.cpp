/**
 * test_node_manager.cpp — Unit tests for NodeManager lifecycle management
 *
 * Tests cover: node creation/destruction, activation/deactivation,
 * duplicate handling, shutdown ordering, concurrent access safety.
 */

#include <gtest/gtest.h>
#include <vector>
#include <string>
#include <thread>

#include "brain_core/ros2_bridge/node_manager.h"

using brain_core::NodeManager;

// ── Fixture ────────────────────────────────────────────────
class NodeManagerTest : public ::testing::Test {
protected:
    void SetUp() override {
        mgr_ = std::make_unique<NodeManager>();
    }
    void TearDown() override {
        mgr_->shutdownAll();
        mgr_.reset();
    }
    std::unique_ptr<NodeManager> mgr_;
};

// ── Lifecycle: basic create / destroy ─────────────────────
TEST_F(NodeManagerTest, CreateSingleNode) {
    EXPECT_TRUE(mgr_->createNode("control"));
    EXPECT_EQ(mgr_->nodeCount(), 1);
    EXPECT_FALSE(mgr_->isActive("control"));  // not activated yet
}

TEST_F(NodeManagerTest, CreateNodeWithNamespace) {
    EXPECT_TRUE(mgr_->createNode("safety", "brain_core"));
    EXPECT_EQ(mgr_->nodeCount(), 1);
}

TEST_F(NodeManagerTest, CreateDuplicateNodeFails) {
    EXPECT_TRUE(mgr_->createNode("control"));
    EXPECT_FALSE(mgr_->createNode("control"));  // duplicate
    EXPECT_EQ(mgr_->nodeCount(), 1);
}

TEST_F(NodeManagerTest, CreateMultipleNodes) {
    std::vector<std::string> names = {"control", "safety", "perception", "behavior", "grpc"};
    for (const auto& n : names) {
        EXPECT_TRUE(mgr_->createNode(n)) << "Failed to create node: " + n;
    }
    EXPECT_EQ(mgr_->nodeCount(), names.size());
}

TEST_F(NodeManagerTest, DestroyNode) {
    mgr_->createNode("temp");
    EXPECT_EQ(mgr_->nodeCount(), 1);
    EXPECT_TRUE(mgr_->destroyNode("temp"));
    EXPECT_EQ(mgr_->nodeCount(), 0);
}

TEST_F(NodeManagerTest, DestroyNonexistentNodeReturnsFalse) {
    EXPECT_FALSE(mgr_->destroyNode("nonexistent"));
}

// ── Activation ────────────────────────────────────────────
TEST_F(NodeManagerTest, ActivateDeactivate) {
    mgr_->createNode("control");
    EXPECT_TRUE(mgr_->activateNode("control"));
    EXPECT_TRUE(mgr_->isActive("control"));
    EXPECT_TRUE(mgr_->deactivateNode("control"));
    EXPECT_FALSE(mgr_->isActive("control"));
}

TEST_F(NodeManagerTest, ActivateWithoutCreateFails) {
    EXPECT_FALSE(mgr_->activateNode("nonexistent"));
    EXPECT_FALSE(mgr_->deactivateNode("nonexistent"));
}

TEST_F(NodeManagerTest, DoubleActivate) {
    mgr_->createNode("control");
    EXPECT_TRUE(mgr_->activateNode("control"));
    EXPECT_TRUE(mgr_->activateNode("control"));  // idempotent
    EXPECT_TRUE(mgr_->isActive("control"));
}

// ── Query ─────────────────────────────────────────────────
TEST_F(NodeManagerTest, ListActiveNodes) {
    mgr_->createNode("a");
    mgr_->createNode("b");
    mgr_->createNode("c");
    mgr_->activateNode("a");
    mgr_->activateNode("c");

    auto active = mgr_->listActiveNodes();
    EXPECT_EQ(active.size(), 2);
    // Check that "a" and "c" are in the list
    bool has_a = std::find(active.begin(), active.end(), "a") != active.end();
    bool has_c = std::find(active.begin(), active.end(), "c") != active.end();
    EXPECT_TRUE(has_a);
    EXPECT_TRUE(has_c);
}

TEST_F(NodeManagerTest, EmptyManagerHasZeroNodes) {
    EXPECT_EQ(mgr_->nodeCount(), 0);
    EXPECT_TRUE(mgr_->listActiveNodes().empty());
}

// ── Shutdown ──────────────────────────────────────────────
TEST_F(NodeManagerTest, ShutdownAllClearsNodes) {
    mgr_->createNode("a");
    mgr_->createNode("b");
    mgr_->activateNode("a");
    mgr_->shutdownAll();
    EXPECT_EQ(mgr_->nodeCount(), 0);
}

// ── Concurrent safety (basic) ─────────────────────────────
TEST_F(NodeManagerTest, ConcurrentCreateFromMultipleThreads) {
    std::vector<std::thread> threads;
    for (int i = 0; i < 5; ++i) {
        threads.emplace_back([this, i]() {
            mgr_->createNode("node_" + std::to_string(i));
        });
    }
    for (auto& t : threads) t.join();
    EXPECT_EQ(mgr_->nodeCount(), 5);
}

// ── SpinOnce (no crash) ───────────────────────────────────
TEST_F(NodeManagerTest, SpinOnceWithNoNodesDoesNotCrash) {
    EXPECT_NO_THROW(mgr_->spinOnce());
}

TEST_F(NodeManagerTest, SpinOnceWithActiveNodesDoesNotCrash) {
    mgr_->createNode("a");
    mgr_->activateNode("a");
    EXPECT_NO_THROW(mgr_->spinOnce());
}
