/**
 * test_tree_executor.cpp — Unit tests for TreeExecutor lifecycle & execution
 *
 * Tests cover: load/halt/reset, tick status transitions,
 * load from file, state queries, empty tree handling.
 */

#include <gtest/gtest.h>
#include <string>
#include <fstream>
#include <cstdio>

#include "brain_core/behavior_engine/tree_executor.h"
#include "brain_core/core_types.h"

using brain_core::TreeExecutor;
using brain_core::BTNodeStatus;

// Minimal valid BT XML
static const char* MINIMAL_BT_XML = R"(<?xml version="1.0"?>
<root BTCPP_format="4">
  <BehaviorTree ID="minimal">
    <Sequence>
      <Wait duration="1.0"/>
    </Sequence>
  </BehaviorTree>
</root>)";

// ── Fixture ────────────────────────────────────────────────
class TreeExecutorTest : public ::testing::Test {
protected:
    void SetUp() override {
        exec_ = std::make_unique<TreeExecutor>();
    }
    void TearDown() override {
        exec_->halt();
        exec_.reset();
    }

    std::string writeTempFile(const std::string& content) {
        std::string path = "bt_exec_test_" + std::to_string(fc_++) + ".xml";
        std::ofstream ofs(path);
        ofs << content;
        ofs.close();
        return path;
    }

    std::unique_ptr<TreeExecutor> exec_;
    int fc_ = 0;
};

// ── Initial state ─────────────────────────────────────────
TEST_F(TreeExecutorTest, ConstructorIsUnloaded) {
    EXPECT_FALSE(exec_->isLoaded());
    EXPECT_EQ(exec_->status(), BTNodeStatus::IDLE);
    EXPECT_TRUE(exec_->currentXML().empty());
}

// ── Load tree ─────────────────────────────────────────────
TEST_F(TreeExecutorTest, LoadValidXML) {
    EXPECT_TRUE(exec_->loadTree(MINIMAL_BT_XML));
    EXPECT_TRUE(exec_->isLoaded());
    EXPECT_FALSE(exec_->currentXML().empty());
}

TEST_F(TreeExecutorTest, LoadInvalidXMLFails) {
    EXPECT_FALSE(exec_->loadTree("not valid xml <<<"));
    EXPECT_FALSE(exec_->isLoaded());
}

TEST_F(TreeExecutorTest, LoadEmptyXMLFails) {
    EXPECT_FALSE(exec_->loadTree(""));
    EXPECT_FALSE(exec_->isLoaded());
}

TEST_F(TreeExecutorTest, LoadThenReload) {
    EXPECT_TRUE(exec_->loadTree(MINIMAL_BT_XML));
    std::string new_xml = R"(<?xml version="1.0"?>
<root BTCPP_format="4">
  <BehaviorTree ID="v2">
    <Sequence>
      <NavigateTo goal="1,0,0"/>
    </Sequence>
  </BehaviorTree>
</root>)";
    EXPECT_TRUE(exec_->loadTree(new_xml));
    EXPECT_NE(exec_->currentXML().find("NavigateTo"), std::string::npos);
}

// ── Load from file ────────────────────────────────────────
TEST_F(TreeExecutorTest, LoadFromFile) {
    auto path = writeTempFile(MINIMAL_BT_XML);
    EXPECT_TRUE(exec_->loadTreeFromFile(path));
    EXPECT_TRUE(exec_->isLoaded());
    std::remove(path.c_str());
}

TEST_F(TreeExecutorTest, LoadFromNonexistentFileFails) {
    EXPECT_FALSE(exec_->loadTreeFromFile("nonexistent_tree.xml"));
    EXPECT_FALSE(exec_->isLoaded());
}

// ── Tick execution ────────────────────────────────────────
TEST_F(TreeExecutorTest, TickWithoutLoadedTreeReturnsIdle) {
    auto status = exec_->tick();
    EXPECT_EQ(status, BTNodeStatus::IDLE);
}

TEST_F(TreeExecutorTest, TickWithLoadedTree) {
    exec_->loadTree(MINIMAL_BT_XML);
    auto status = exec_->tick();
    // Tree should be either RUNNING (if Wait is ticking) or SUCCESS (if completed)
    bool valid = (status == BTNodeStatus::RUNNING || status == BTNodeStatus::SUCCESS);
    EXPECT_TRUE(valid) << "Unexpected status after tick";
}

// ── Halt ──────────────────────────────────────────────────
TEST_F(TreeExecutorTest, HaltOnLoadedTree) {
    exec_->loadTree(MINIMAL_BT_XML);
    exec_->tick();
    EXPECT_NO_THROW(exec_->halt());
}

TEST_F(TreeExecutorTest, HaltOnUnloadedTreeIsSafe) {
    EXPECT_NO_THROW(exec_->halt());
}

// ── Reset ─────────────────────────────────────────────────
TEST_F(TreeExecutorTest, ResetClearsState) {
    exec_->loadTree(MINIMAL_BT_XML);
    exec_->tick();
    exec_->reset();
    EXPECT_FALSE(exec_->isLoaded());
    EXPECT_EQ(exec_->status(), BTNodeStatus::IDLE);
    EXPECT_TRUE(exec_->currentXML().empty());
}

// ── Status transitions ────────────────────────────────────
TEST_F(TreeExecutorTest, StatusAfterLoad) {
    EXPECT_EQ(exec_->status(), BTNodeStatus::IDLE);
    exec_->loadTree(MINIMAL_BT_XML);
    // After load, status may still be IDLE until first tick
    // This is implementation-defined; we only verify no crash
    EXPECT_NO_THROW(exec_->tick());
}
