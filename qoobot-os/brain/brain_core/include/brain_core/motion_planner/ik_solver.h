// motion_planner/ik_solver.h — TRAC-IK inverse kinematics solver
#pragma once

#include "brain_core/core_types.h"
#include <vector>
#include <string>
#include <optional>

namespace brain_core {

/// IK solution with quality metrics.
struct IKSolution {
    std::vector<double> joint_positions;
    double position_error{0.0};    // m
    double orientation_error{0.0}; // rad
    int    iterations{0};
    bool   converged{false};
};

class IKSolver {
public:
    IKSolver();

    /// Load robot URDF for kinematic chain definition.
    bool loadURDF(const std::string& urdf_path);

    /// Set the planning group (e.g., "arm", "gripper").
    void setGroupName(const std::string& group);

    /// Set the IK solver type: "trac_ik", "kdl", "lma".
    void setSolverType(const std::string& type);

    /// Solve inverse kinematics for a target pose.
    /// Returns nullopt if no solution found.
    std::optional<IKSolution> solve(double x, double y, double z,
                                     double qx, double qy, double qz, double qw);

    /// Solve with seed configuration for consistency.
    std::optional<IKSolution> solveSeeded(
        double x, double y, double z,
        double qx, double qy, double qz, double qw,
        const std::vector<double>& seed);

    /// Solve for multiple IK solutions (return up to N).
    std::vector<IKSolution> solveMulti(
        double x, double y, double z,
        double qx, double qy, double qz, double qw,
        int max_solutions = 8);

    /// Get the last solution timing in milliseconds.
    double lastSolveTimeMs() const { return _last_solve_ms; }

    /// Set position/rotation tolerance.
    void setTolerance(double pos_tol_m, double rot_tol_rad);

private:
    std::string _urdf_path;
    std::string _group_name{"arm"};
    std::string _solver_type{"trac_ik"};
    double _pos_tol{0.005};   // 5 mm
    double _rot_tol{0.01};    // ~0.6 deg
    double _last_solve_ms{0.0};
    bool _urdf_loaded{false};
};

} // namespace brain_core
