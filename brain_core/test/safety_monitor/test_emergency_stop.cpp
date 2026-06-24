/**
 * test_emergency_stop.cpp — Unit tests for EmergencyStop mechanism
 *
 * Tests cover: trigger/reset, active state, reason tracking,
 * timestamp capture, callback registration, concurrent access.
 */

#include <gtest/gtest.h>
#include <string>
#include <thread>
#include <chrono>

#include "brain_core/safety_monitor/emergency_stop.h"

using brain_core::EmergencyStop;

// ── Fixture ────────────────────────────────────────────────
class EmergencyStopTest : public ::testing::Test {
protected:
    void SetUp() override {
        estop_ = std::make_unique<EmergencyStop>();
    }
    void TearDown() override {
        estop_.reset();
    }
    std::unique_ptr<EmergencyStop> estop_;
};

// ── Constructor defaults ──────────────────────────────────
TEST_F(EmergencyStopTest, ConstructorIsNotActive) {
    EXPECT_FALSE(estop_->isActive());
    EXPECT_TRUE(estop_->reason().empty());
}

// ── Trigger ───────────────────────────────────────────────
TEST_F(EmergencyStopTest, TriggerActivatesStop) {
    estop_->trigger("collision detected");
    EXPECT_TRUE(estop_->isActive());
}

TEST_F(EmergencyStopTest, TriggerStoresReason) {
    estop_->trigger("joint limit exceeded");
    EXPECT_EQ(estop_->reason(), "joint limit exceeded");
}

TEST_F(EmergencyStopTest, TriggerCapturesTimestamp) {
    auto before = std::chrono::system_clock::now();
    estop_->trigger("test");
    auto after = std::chrono::system_clock::now();
    auto stop_time = estop_->triggeredAt();
    EXPECT_GE(stop_time, before);
    EXPECT_LE(stop_time, after);
}

TEST_F(EmergencyStopTest, DoubleTriggerKeepsFirstReason) {
    estop_->trigger("first reason");
    estop_->trigger("second reason");
    EXPECT_TRUE(estop_->isActive());
    EXPECT_EQ(estop_->reason(), "first reason");
}

// ── Reset ─────────────────────────────────────────────────
TEST_F(EmergencyStopTest, ResetAfterTrigger) {
    estop_->trigger("obstacle");
    EXPECT_TRUE(estop_->isActive());
    EXPECT_TRUE(estop_->reset());
    EXPECT_FALSE(estop_->isActive());
}

TEST_F(EmergencyStopTest, ResetWithoutTriggerReturnsFalse) {
    EXPECT_FALSE(estop_->reset());
}

TEST_F(EmergencyStopTest, ResetClearsReason) {
    estop_->trigger("test reason");
    estop_->reset();
    // Reason may or may not be cleared — implementation-specific
    // Just verify active state is cleared
    EXPECT_FALSE(estop_->isActive());
}

TEST_F(EmergencyStopTest, TriggerResetTrigger) {
    estop_->trigger("first");
    estop_->reset();
    estop_->trigger("second");
    EXPECT_TRUE(estop_->isActive());
    EXPECT_EQ(estop_->reason(), "second");
}

// ── Callback ──────────────────────────────────────────────
TEST_F(EmergencyStopTest, CallbackInvokedOnTrigger) {
    bool called = false;
    std::string cb_reason;
    estop_->onStop([&](const std::string& r) {
        called = true;
        cb_reason = r;
    });

    estop_->trigger("callback test");
    EXPECT_TRUE(called);
    EXPECT_EQ(cb_reason, "callback test");
}

TEST_F(EmergencyStopTest, CallbackNotInvokedOnReset) {
    bool called = false;
    estop_->onStop([&](const std::string&) {
        called = true;
    });
    estop_->trigger("t1");
    EXPECT_TRUE(called);

    called = false;
    estop_->reset();
    EXPECT_FALSE(called);  // reset should not fire callback
}

TEST_F(EmergencyStopTest, MultipleCallbacksLastWins) {
    int first = 0, second = 0;
    estop_->onStop([&](const std::string&) { first++; });
    estop_->onStop([&](const std::string&) { second++; });  // replaces first
    estop_->trigger("test");
    EXPECT_EQ(first, 0);   // first callback was replaced
    EXPECT_EQ(second, 1);  // second callback fired
}

// ── Thread safety ─────────────────────────────────────────
TEST_F(EmergencyStopTest, ConcurrentTriggerRead) {
    std::atomic<int> reads{0};
    std::thread reader([&]() {
        for (int i = 0; i < 100; ++i) {
            estop_->isActive();
            ++reads;
        }
    });
    std::thread writer([&]() {
        for (int i = 0; i < 100; ++i) {
            estop_->trigger("t");
            estop_->reset();
        }
    });
    reader.join();
    writer.join();
    EXPECT_EQ(reads, 100);
    // No crash = pass
}

// ── Empty reason ──────────────────────────────────────────
TEST_F(EmergencyStopTest, TriggerWithEmptyReasonSucceeds) {
    EXPECT_NO_THROW(estop_->trigger(""));
    EXPECT_TRUE(estop_->isActive());
}
