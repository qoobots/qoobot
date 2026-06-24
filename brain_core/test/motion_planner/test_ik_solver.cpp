/**
 * test_ik_solver.cpp — Unit tests for IKSolver inverse kinematics
 *
 * Tests cover: URDF loading, solver configuration, solve/seeded/multi
 * API, tolerance settings, timing, no-solution handling.
 */

#include <gtest/gtest.h>
#include <string>
#include <vector>
#include <cmath>

#include "brain_core/motion_planner/ik_solver.h"

using brain_core::IKSolver;
using brain_core::IKSolution;

// ── Fixture ────────────────────────────────────────────────
class IKSolverTest : public ::testing::Test {
protected:
    void SetUp() override {
        solver_ = std::make_unique<IKSolver>();
    }
    void TearDown() override {
        solver_.reset();
    }
    std::unique_ptr<IKSolver> solver_;
};

// ── Constructor defaults ──────────────────────────────────
TEST_F(IKSolverTest, ConstructorDefaults) {
    EXPECT_FALSE_NE(solver_->lastSolveTimeMs(), -1.0);  // initialized
}

// ── URDF loading ──────────────────────────────────────────
TEST_F(IKSolverTest, LoadNonexistentURDFFails) {
    EXPECT_FALSE(solver_->loadURDF("nonexistent.urdf"));
}

// ── Configuration ─────────────────────────────────────────
TEST_F(IKSolverTest, SetGroupName) {
    EXPECT_NO_THROW(solver_->setGroupName("arm"));
    EXPECT_NO_THROW(solver_->setGroupName("gripper"));
}

TEST_F(IKSolverTest, SetSolverType) {
    EXPECT_NO_THROW(solver_->setSolverType("trac_ik"));
    EXPECT_NO_THROW(solver_->setSolverType("kdl"));
    EXPECT_NO_THROW(solver_->setSolverType("lma"));
}

TEST_F(IKSolverTest, SetInvalidSolverTypeIsAccepted) {
    // Implementation may accept any string and defer validation
    EXPECT_NO_THROW(solver_->setSolverType("nonexistent_solver"));
}

TEST_F(IKSolverTest, SetTolerance) {
    EXPECT_NO_THROW(solver_->setTolerance(0.01, 0.02));
}

// ── Solve (without URDF loaded) ───────────────────────────
TEST_F(IKSolverTest, SolveWithoutURDFReturnsNullopt) {
    auto result = solver_->solve(0.5, 0.0, 0.3, 0.0, 0.0, 0.0, 1.0);
    EXPECT_FALSE(result.has_value());
}

TEST_F(IKSolverTest, SolveSeededWithoutURDFReturnsNullopt) {
    std::vector<double> seed = {0, 0, 0, 0, 0, 0, 0};
    auto result = solver_->solveSeeded(0.5, 0.0, 0.3, 0.0, 0.0, 0.0, 1.0, seed);
    EXPECT_FALSE(result.has_value());
}

TEST_F(IKSolverTest, SolveMultiWithoutURDFReturnsEmpty) {
    auto results = solver_->solveMulti(0.5, 0.0, 0.3, 0.0, 0.0, 0.0, 1.0, 8);
    EXPECT_TRUE(results.empty());
}

// ── Pose out of reach ─────────────────────────────────────
TEST_F(IKSolverTest, FarAwayPoseReturnNullopt) {
    // Even without URDF, these should handle gracefully
    auto result = solver_->solve(10.0, 10.0, 10.0, 0.0, 0.0, 0.0, 1.0);
    EXPECT_FALSE(result.has_value());
}

// ── Timing ────────────────────────────────────────────────
TEST_F(IKSolverTest, SolveTimeInitializedToZero) {
    EXPECT_NEAR(solver_->lastSolveTimeMs(), 0.0, 0.001);
}

// ── IKSolution struct sanity ──────────────────────────────
TEST_F(IKSolverTest, IKSolutionDefaultValues) {
    IKSolution sol;
    EXPECT_TRUE(sol.joint_positions.empty());
    EXPECT_NEAR(sol.position_error, 0.0, 1e-9);
    EXPECT_NEAR(sol.orientation_error, 0.0, 1e-9);
    EXPECT_EQ(sol.iterations, 0);
    EXPECT_FALSE(sol.converged);
}

// ── Multiple solve calls ──────────────────────────────────
TEST_F(IKSolverTest, RepeatedCallsWithoutURDFDoNotCrash) {
    for (int i = 0; i < 10; ++i) {
        auto r = solver_->solve(0.5, 0.1 * i, 0.3, 0, 0, 0, 1);
        EXPECT_FALSE(r.has_value());
    }
}
