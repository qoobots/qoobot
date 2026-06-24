/**
 * test_topic_adapter.cpp — Unit tests for TopicAdapter pub/sub abstraction
 *
 * Tests cover: initialization, publisher creation/publishing,
 * subscriber creation/callbacks, topic listing, removal, global callbacks.
 */

#include <gtest/gtest.h>
#include <string>
#include <vector>

#include "brain_core/ros2_bridge/topic_adapter.h"

using brain_core::TopicAdapter;

// ── Fixture ────────────────────────────────────────────────
class TopicAdapterTest : public ::testing::Test {
protected:
    void SetUp() override {
        adapter_ = std::make_unique<TopicAdapter>();
    }
    void TearDown() override {
        adapter_.reset();
    }
    std::unique_ptr<TopicAdapter> adapter_;
};

// ── Initialization ────────────────────────────────────────
TEST_F(TopicAdapterTest, ConstructorIsNotInitialized) {
    EXPECT_EQ(adapter_->publisherCount(), 0);
    EXPECT_EQ(adapter_->subscriberCount(), 0);
}

TEST_F(TopicAdapterTest, InitializeWithNullHandleFails) {
    EXPECT_FALSE(adapter_->initialize(nullptr));
}

// ── Publisher API ─────────────────────────────────────────
TEST_F(TopicAdapterTest, CreatePublisher) {
    EXPECT_TRUE(adapter_->createPublisher("/joint_states", "sensor_msgs/JointState"));
    EXPECT_EQ(adapter_->publisherCount(), 1);
}

TEST_F(TopicAdapterTest, CreateDuplicatePublisherOverwrites) {
    EXPECT_TRUE(adapter_->createPublisher("/cmd_vel", "geometry_msgs/Twist"));
    EXPECT_TRUE(adapter_->createPublisher("/cmd_vel", "geometry_msgs/Twist"));
    EXPECT_EQ(adapter_->publisherCount(), 1);  // overwritten
}

TEST_F(TopicAdapterTest, CreateMultiplePublishers) {
    std::vector<std::string> topics = {"/topic_a", "/topic_b", "/topic_c"};
    for (const auto& t : topics) {
        EXPECT_TRUE(adapter_->createPublisher(t, "std_msgs/String"));
    }
    EXPECT_EQ(adapter_->publisherCount(), topics.size());
}

TEST_F(TopicAdapterTest, RemovePublisher) {
    adapter_->createPublisher("/to_remove", "std_msgs/String");
    EXPECT_EQ(adapter_->publisherCount(), 1);
    adapter_->removePublisher("/to_remove");
    EXPECT_EQ(adapter_->publisherCount(), 0);
}

TEST_F(TopicAdapterTest, RemoveNonexistentPublisherIsSafe) {
    EXPECT_NO_THROW(adapter_->removePublisher("/nonexistent"));
}

TEST_F(TopicAdapterTest, PublishWithoutInitializationIsSafe) {
    EXPECT_NO_THROW(adapter_->publish("/topic", "data"));
}

// ── Subscriber API ────────────────────────────────────────
TEST_F(TopicAdapterTest, CreateSubscription) {
    int call_count = 0;
    auto cb = [&call_count](const std::string& topic, const std::string& data) {
        call_count++;
    };
    EXPECT_TRUE(adapter_->createSubscription("/scan", "sensor_msgs/LaserScan", cb));
    EXPECT_EQ(adapter_->subscriberCount(), 1);
}

TEST_F(TopicAdapterTest, CreateSubscriptionWithNullCallbackSucceeds) {
    EXPECT_TRUE(adapter_->createSubscription("/scan", "sensor_msgs/LaserScan", nullptr));
    EXPECT_EQ(adapter_->subscriberCount(), 1);
}

TEST_F(TopicAdapterTest, RemoveSubscription) {
    adapter_->createSubscription("/scan", "sensor_msgs/LaserScan",
        [](const std::string&, const std::string&) {});
    EXPECT_EQ(adapter_->subscriberCount(), 1);
    adapter_->removeSubscription("/scan");
    EXPECT_EQ(adapter_->subscriberCount(), 0);
}

TEST_F(TopicAdapterTest, RemoveNonexistentSubscriptionIsSafe) {
    EXPECT_NO_THROW(adapter_->removeSubscription("/nonexistent"));
}

// ── Topic listing ─────────────────────────────────────────
TEST_F(TopicAdapterTest, ListTopicsReturnsAll) {
    adapter_->createPublisher("/pub_a", "std_msgs/String");
    adapter_->createPublisher("/pub_b", "std_msgs/String");
    adapter_->createSubscription("/sub_a", "std_msgs/String",
        [](const std::string&, const std::string&) {});

    auto topics = adapter_->listTopics();
    EXPECT_EQ(topics.size(), 3);
}

// ── Global callback ───────────────────────────────────────
TEST_F(TopicAdapterTest, SetGlobalCallback) {
    bool called = false;
    adapter_->setGlobalCallback([&called](const std::string&, const std::string&) {
        called = true;
    });
    // Global callback is stored but not invoked here without actual ROS
    // Just verify setter works:
    EXPECT_NO_THROW(adapter_->setGlobalCallback(nullptr));
}
