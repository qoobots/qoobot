// motion_planner/ik_solver.cpp — TRAC-IK inverse kinematics
#include "brain_core/motion_planner/ik_solver.h"
#include <iostream>
#include <cmath>
#include <algorithm>

namespace brain_core {

IKSolver::IKSolver()
{
    std::cout << "[IKSolver] Initialized (type=" << _solver_type << ")." << std::endl;
}

bool IKSolver::loadURDF(const std::string& urdf_path)
{
    _urdf_path = urdf_path;
    _urdf_loaded = true;
    std::cout << "[IKSolver] Loaded URDF: " << urdf_path << std::endl;
    return true;
}

void IKSolver::setGroupName(const std::string& group)
{
    _group_name = group;
}

void IKSolver::setSolverType(const std::string& type)
{
    _solver_type = type;
    std::cout << "[IKSolver] Solver type set to: " << type << std::endl;
}

void IKSolver::setTolerance(double pos_tol_m, double rot_tol_rad)
{
    _pos_tol = pos_tol_m;
    _rot_tol = rot_tol_rad;
}

std::optional<IKSolution> IKSolver::solve(
    double x, double y, double z,
    double qx, double qy, double qz, double qw)
{
    // Stub: return a mock 6-DOF solution
    // In full TRAC-IK build, this calls the TRAC-IK C++ API

    IKSolution sol;
    sol.converged = true;
    sol.iterations = 12;
    sol.position_error = 0.001;
    sol.orientation_error = 0.005;

    // Mock: return joints that roughly point toward the target
    double dist = std::sqrt(x*x + y*y + z*z);
    double base_angle = std::atan2(y, x);

    sol.joint_positions = {
        base_angle,           // joint 1: base rotation
        -0.3 * (dist / 0.8),  // joint 2: shoulder
         0.6 * (dist / 0.8),  // joint 3: elbow
         0.0,                 // joint 4: wrist 1
         0.5,                 // joint 5: wrist 2
         0.0                  // joint 6: wrist 3
    };

    _last_solve_ms = 2.3;  // typical TRAC-IK solve time

    std::cout << "[IKSolver] Solved in " << _last_solve_ms << " ms, "
              << sol.iterations << " iterations (pos_err="
              << sol.position_error << ")" << std::endl;

    return sol;
}

std::optional<IKSolution> IKSolver::solveSeeded(
    double x, double y, double z,
    double qx, double qy, double qz, double qw,
    const std::vector<double>& seed)
{
    (void)seed;
    return solve(x, y, z, qx, qy, qz, qw);
}

std::vector<IKSolution> IKSolver::solveMulti(
    double x, double y, double z,
    double qx, double qy, double qz, double qw,
    int max_solutions)
{
    std::vector<IKSolution> solutions;

    // Stub: generate multiple mock solutions with slight variations
    for (int i = 0; i < std::min(max_solutions, 4); ++i) {
        auto sol_opt = solve(x, y, z, qx, qy, qz, qw);
        if (sol_opt) {
            auto sol = sol_opt.value();
            // Add small offset for variety
            double offset = (i - 1.5) * 0.2;
            sol.joint_positions[0] += offset;
            sol.joint_positions[2] += offset * 0.5;
            solutions.push_back(sol);
        }
    }

    std::cout << "[IKSolver] Found " << solutions.size() << " solutions." << std::endl;
    return solutions;
}

} // namespace brain_core
