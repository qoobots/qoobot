// motion_planner/trajectory_follower.cpp — Real-time trajectory execution
#include "brain_core/motion_planner/trajectory_follower.h"
#include <iostream>

namespace brain_core {

TrajectoryFollower::TrajectoryFollower()
{
    std::cout << "[TrajectoryFollower] Initialized." << std::endl;
}

void TrajectoryFollower::loadTrajectory(const Trajectory& traj)
{
    _trajectory = traj;
    _current_wp = 0;
    _state = FollowState::IDLE;
    std::cout << "[TrajectoryFollower] Loaded trajectory: " << traj.name
              << " (" << traj.waypoints.size() << " waypoints)" << std::endl;
}

bool TrajectoryFollower::start()
{
    if (_trajectory.waypoints.empty()) {
        std::cerr << "[TrajectoryFollower] No trajectory loaded!" << std::endl;
        return false;
    }

    _current_wp = 0;
    _state = FollowState::MOVING;

    std::cout << "[TrajectoryFollower] Started following." << std::endl;

    if (_state_cb) _state_cb(FollowState::MOVING);
    return true;
}

void TrajectoryFollower::pause()
{
    if (_state == FollowState::MOVING) {
        _state = FollowState::PAUSED;
        std::cout << "[TrajectoryFollower] Paused at waypoint "
                  << _current_wp << "." << std::endl;
        if (_state_cb) _state_cb(FollowState::PAUSED);
    }
}

void TrajectoryFollower::resume()
{
    if (_state == FollowState::PAUSED) {
        _state = FollowState::MOVING;
        std::cout << "[TrajectoryFollower] Resumed." << std::endl;
        if (_state_cb) _state_cb(FollowState::MOVING);
    }
}

void TrajectoryFollower::emergencyStop()
{
    _state = FollowState::STOPPED;
    std::cout << "[TrajectoryFollower] EMERGENCY STOP!" << std::endl;
    if (_state_cb) _state_cb(FollowState::STOPPED);
}

FollowProgress TrajectoryFollower::progress() const
{
    FollowProgress prog;
    prog.state = _state;
    prog.current_waypoint = _current_wp;
    prog.total_waypoints = static_cast<int>(_trajectory.waypoints.size());

    if (prog.total_waypoints > 0) {
        prog.completion_pct = 100.0 * _current_wp / prog.total_waypoints;
    }

    // Stub: mock tracking error
    prog.position_error = (_state == FollowState::MOVING) ? 0.002 : 0.0;
    prog.velocity = (_state == FollowState::MOVING) ? 0.15 : 0.0;

    return prog;
}

void TrajectoryFollower::onProgress(ProgressCallback cb)
{
    _progress_cb = std::move(cb);
}

void TrajectoryFollower::onStateChange(StateCallback cb)
{
    _state_cb = std::move(cb);
}

} // namespace brain_core
