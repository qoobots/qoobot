/**
 * test_collision_checker.cpp — Unit tests for SafetyCollisionChecker proximity monitoring
 *
 * Tests cover: zone configuration, obstacle updates, proximity level
 * determination, zone counting, closest distance tracking.
 */

#include <gtest/gtest.h>
#include <vector>
#include <cmath>

#include "brain_core/safety_monitor/collision_checker.h"
#include "brain_core/core_types.h"

using brain_core::SafetyCollisionChecker;
using brain_core::SafetyZoneConfig;
using brain_core::ProximityLevel;
using brain_core::ObstacleInfo;

// ── Fixture ────────────────────────────────────────────────
class CollisionCheckerTest : public ::testing::Test {
protected:
    void SetUp() override {
        checker_ = std::make_unique<SafetyCollisionChecker>();
    }
    void TearDown() override {
        checker_.reset();
    }

    ObstacleInfo makeObstacle(double dist) {
        ObstacleInfo obs;
        obs.distance = dist;
        obs.label = "test_object";
        return obs;
    }

    std::unique_ptr<SafetyCollisionChecker> checker_;
};

// ── Constructor defaults ──────────────────────────────────
TEST_F(CollisionCheckerTest, ConstructorHasNoObstacles) {
    EXPECT_EQ(checker_->inCaution(), 0);
    EXPECT_EQ(checker_->inDanger(), 0);
    EXPECT_EQ(checker_->inCritical(), 0);
}

TEST_F(CollisionCheckerTest, DefaultClosestDistanceIsLarge) {
    EXPECT_GT(checker_->closestDistance(), 100.0);
}

// ── Zone configuration ────────────────────────────────────
TEST_F(CollisionCheckerTest, SetZonesUpdatesThresholds) {
    SafetyZoneConfig custom;
    custom.caution_radius = 0.5;
    custom.danger_radius = 0.2;
    custom.critical_radius = 0.05;
    EXPECT_NO_THROW(checker_->setZones(custom));
}

// ── Proximity level determination ─────────────────────────
TEST_F(CollisionCheckerTest, NoObstaclesReturnsSafe) {
    EXPECT_EQ(checker_->check(), ProximityLevel::SAFE);
}

TEST_F(CollisionCheckerTest, DistantObstacleReturnsSafe) {
    std::vector<ObstacleInfo> obs = {makeObstacle(5.0)};
    checker_->updateObstacles(obs);
    EXPECT_EQ(checker_->check(), ProximityLevel::SAFE);
}

TEST_F(CollisionCheckerTest, CautionZoneObstacle) {
    std::vector<ObstacleInfo> obs = {makeObstacle(0.25)};  // within default caution (0.3)
    checker_->updateObstacles(obs);
    EXPECT_EQ(checker_->check(), ProximityLevel::CAUTION);
}

TEST_F(CollisionCheckerTest, DangerZoneObstacle) {
    std::vector<ObstacleInfo> obs = {makeObstacle(0.10)};  // within default danger (0.15)
    checker_->updateObstacles(obs);
    EXPECT_EQ(checker_->check(), ProximityLevel::DANGER);
}

TEST_F(CollisionCheckerTest, CriticalZoneObstacle) {
    std::vector<ObstacleInfo> obs = {makeObstacle(0.02)};  // within default critical (0.05)
    checker_->updateObstacles(obs);
    EXPECT_EQ(checker_->check(), ProximityLevel::CRITICAL);
}

TEST_F(CollisionCheckerTest, WorstObstacleDeterminesLevel) {
    std::vector<ObstacleInfo> obs = {
        makeObstacle(5.0),   // SAFE
        makeObstacle(0.25),  // CAUTION
        makeObstacle(0.02),  // CRITICAL
    };
    checker_->updateObstacles(obs);
    EXPECT_EQ(checker_->check(), ProximityLevel::CRITICAL);
}

// ── Zone counting ─────────────────────────────────────────
TEST_F(CollisionCheckerTest, CountObstaclesPerZone) {
    std::vector<ObstacleInfo> obs = {
        makeObstacle(5.0),   // SAFE
        makeObstacle(0.28),  // CAUTION
        makeObstacle(0.26),  // CAUTION
        makeObstacle(0.10),  // DANGER
        makeObstacle(0.03),  // CRITICAL
    };
    checker_->updateObstacles(obs);
    checker_->check();

    EXPECT_EQ(checker_->inCaution(), 2);
    EXPECT_EQ(checker_->inDanger(), 1);
    EXPECT_EQ(checker_->inCritical(), 1);
}

// ── Closest distance tracking ─────────────────────────────
TEST_F(CollisionCheckerTest, ClosestDistanceIsMinimum) {
    std::vector<ObstacleInfo> obs = {
        makeObstacle(3.0),
        makeObstacle(0.5),
        makeObstacle(0.15),
    };
    checker_->updateObstacles(obs);
    checker_->check();
    EXPECT_NEAR(checker_->closestDistance(), 0.15, 0.001);
}

TEST_F(CollisionCheckerTest, ClosestDistanceWithNoObstacles) {
    checker_->check();
    EXPECT_GT(checker_->closestDistance(), 100.0);
}

// ── Empty update ──────────────────────────────────────────
TEST_F(CollisionCheckerTest, EmptyObstaclesResetsCounts) {
    std::vector<ObstacleInfo> obs = {makeObstacle(0.1)};
    checker_->updateObstacles(obs);
    checker_->check();
    EXPECT_GT(checker_->inDanger(), 0);

    // Clear obstacles
    checker_->updateObstacles({});
    checker_->check();
    EXPECT_EQ(checker_->inCaution(), 0);
    EXPECT_EQ(checker_->inDanger(), 0);
    EXPECT_EQ(checker_->inCritical(), 0);
}
