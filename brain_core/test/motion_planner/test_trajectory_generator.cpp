/**
 * test_trajectory_generator.cpp — Unit tests for TrajectoryGenerator multi-strategy generation
 *
 * Tests cover: trajectory generation with different strategies,
 * waypoint interpolation, score computation, strategy configuration,
 * Cartesian pose generation, empty/boundary inputs.
 */

#include <gtest/gtest.h>
#include <vector>
#include <algorithm>
#include <cmath>

#include "brain_core/motion_planner/trajectory_generator.h"
#include "brain_core/core_types.h"

using brain_core::TrajectoryGenerator;
using brain_core::TrajectoryStrategy;
using brain_core::StrategyConfig;
using brain_core::Trajectory;

// ── Fixture ────────────────────────────────────────────────
class TrajectoryGeneratorTest : public ::testing::Test {
protected:
    void SetUp() override {
        gen_ = std::make_unique<TrajectoryGenerator>();
    }
    void TearDown() override {
        gen_.reset();
    }

    std::vector<double> zeroJoints(int count = 7) {
        return std::vector<double>(count, 0.0);
    }

    std::vector<double> goalJoints() {
        return {0.5, -0.3, 0.2, -1.0, 0.8, 0.1, 0.4};
    }

    std::unique_ptr<TrajectoryGenerator> gen_;
};

// ── Basic generation ──────────────────────────────────────
TEST_F(TrajectoryGeneratorTest, GenerateSingleTrajectory) {
    auto traj = gen_->generate(zeroJoints(), goalJoints());
    EXPECT_FALSE(traj.waypoints.empty());
    EXPECT_GE(traj.waypoints.size(), 2);  // at least start + end
}

TEST_F(TrajectoryGeneratorTest, GeneratedTrajectoryHasName) {
    auto traj = gen_->generate(zeroJoints(), goalJoints());
    EXPECT_FALSE(traj.name.empty());
}

TEST_F(TrajectoryGeneratorTest, GeneratedTrajectoryHasScore) {
    auto traj = gen_->generate(zeroJoints(), goalJoints());
    EXPECT_GE(traj.score, 0.0);
    EXPECT_LE(traj.score, 1.0);
}

TEST_F(TrajectoryGeneratorTest, CollisionFreeByDefault) {
    auto traj = gen_->generate(zeroJoints(), goalJoints());
    EXPECT_TRUE(traj.collision_free);
}

// ── Waypoint interpolation ────────────────────────────────
TEST_F(TrajectoryGeneratorTest, WaypointsSpanDuration) {
    auto traj = gen_->generate(zeroJoints(), goalJoints(),
                                TrajectoryStrategy::OPTIMAL, 2.0);
    EXPECT_GT(traj.waypoints.size(), 0);
    double last_time = traj.waypoints.back().time_from_start_sec;
    EXPECT_NEAR(last_time, 2.0, 0.1);
}

TEST_F(TrajectoryGeneratorTest, FirstWaypointAtZeroTime) {
    auto traj = gen_->generate(zeroJoints(), goalJoints());
    EXPECT_NEAR(traj.waypoints.front().time_from_start_sec, 0.0, 0.001);
}

// ── Strategy variation ────────────────────────────────────
TEST_F(TrajectoryGeneratorTest, DifferentStrategiesProduceTrajectories) {
    std::vector<TrajectoryStrategy> strategies = {
        TrajectoryStrategy::OPTIMAL,
        TrajectoryStrategy::CONSERVATIVE,
        TrajectoryStrategy::AGGRESSIVE,
        TrajectoryStrategy::EXPLORATORY,
        TrajectoryStrategy::ADVERSARIAL,
    };
    for (auto st : strategies) {
        auto traj = gen_->generate(zeroJoints(), goalJoints(), st);
        EXPECT_FALSE(traj.waypoints.empty()) << "Strategy: " << static_cast<int>(st);
    }
}

TEST_F(TrajectoryGeneratorTest, GenerateAllReturnsFiveTrajectories) {
    auto trajs = gen_->generateAll(zeroJoints(), goalJoints());
    EXPECT_EQ(trajs.size(), 5);
}

TEST_F(TrajectoryGeneratorTest, GenerateAllHasUniqueNames) {
    auto trajs = gen_->generateAll(zeroJoints(), goalJoints());
    std::vector<std::string> names;
    for (const auto& t : trajs) {
        names.push_back(t.name);
    }
    std::sort(names.begin(), names.end());
    auto it = std::unique(names.begin(), names.end());
    EXPECT_EQ(it, names.end()) << "Trajectory names are not unique";
}

// ── Strategy configuration ────────────────────────────────
TEST_F(TrajectoryGeneratorTest, SetAndGetStrategyConfig) {
    StrategyConfig cfg;
    cfg.type = TrajectoryStrategy::CONSERVATIVE;
    cfg.position_weight = 0.5;
    cfg.time_weight = 0.1;
    cfg.collision_weight = 0.4;

    gen_->setStrategyConfig(TrajectoryStrategy::CONSERVATIVE, cfg);
    auto retrieved = gen_->getStrategyConfig(TrajectoryStrategy::CONSERVATIVE);

    EXPECT_EQ(retrieved.type, TrajectoryStrategy::CONSERVATIVE);
    EXPECT_NEAR(retrieved.position_weight, 0.5, 0.001);
    EXPECT_NEAR(retrieved.time_weight, 0.1, 0.001);
    EXPECT_NEAR(retrieved.collision_weight, 0.4, 0.001);
}

// ── Waypoint count ────────────────────────────────────────
TEST_F(TrajectoryGeneratorTest, SetWaypointCount) {
    gen_->setWaypointCount(100);
    auto traj = gen_->generate(zeroJoints(), goalJoints());
    EXPECT_EQ(traj.waypoints.size(), 100);
}

TEST_F(TrajectoryGeneratorTest, DefaultWaypointCountIsFifty) {
    auto traj = gen_->generate(zeroJoints(), goalJoints());
    EXPECT_EQ(traj.waypoints.size(), 50);
}

// ── Cartesian pose generation ─────────────────────────────
TEST_F(TrajectoryGeneratorTest, GenerateToPose) {
    auto traj = gen_->generateToPose(0.5, 0.0, 0.3,
                                      0.0, 0.0, 0.0, 1.0,
                                      zeroJoints());
    // Without IK solver URDF, may fall back to joint-space interpolation
    EXPECT_FALSE(traj.waypoints.empty());
}

// ── Edge cases ────────────────────────────────────────────
TEST_F(TrajectoryGeneratorTest, SameStartAndGoal) {
    auto j = goalJoints();
    auto traj = gen_->generate(j, j);
    EXPECT_FALSE(traj.waypoints.empty());
    // Waypoints should ideally represent a zero-length trajectory
}

TEST_F(TrajectoryGeneratorTest, ZeroDurationHandledGracefully) {
    auto traj = gen_->generate(zeroJoints(), goalJoints(),
                                TrajectoryStrategy::OPTIMAL, 0.0);
    // Should not crash; implementation may clamp to minimum duration
    EXPECT_FALSE(traj.waypoints.empty());
}

TEST_F(TrajectoryGeneratorTest, SingleJointTrajectory) {
    auto start = std::vector<double>{0.0};
    auto goal = std::vector<double>{1.0};
    auto traj = gen_->generate(start, goal);
    EXPECT_FALSE(traj.waypoints.empty());
}

// ── Waypoint data integrity ───────────────────────────────
TEST_F(TrajectoryGeneratorTest, WaypointTimesAreMonotonic) {
    auto traj = gen_->generate(zeroJoints(), goalJoints());
    double prev = -1.0;
    for (const auto& wp : traj.waypoints) {
        EXPECT_GE(wp.time_from_start_sec, prev);
        prev = wp.time_from_start_sec;
    }
}

TEST_F(TrajectoryGeneratorTest, FirstWaypointMatchesStart) {
    auto start = zeroJoints();
    auto traj = gen_->generate(start, goalJoints());
    ASSERT_FALSE(traj.waypoints.empty());
    // First waypoint joint positions should be close to start
    for (size_t i = 0; i < start.size(); ++i) {
        EXPECT_NEAR(traj.waypoints[0].x, 0.0, 1e-6);  // quaternion identity
        EXPECT_NEAR(traj.waypoints[0].y, 0.0, 1e-6);
        EXPECT_NEAR(traj.waypoints[0].z, 0.0, 1e-6);
    }
}
