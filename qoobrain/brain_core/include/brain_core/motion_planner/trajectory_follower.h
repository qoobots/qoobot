// motion_planner/trajectory_follower.h — Real-time trajectory execution & monitoring
#pragma once

#include "brain_core/core_types.h"
#include <vector>
#include <atomic>
#include <functional>

namespace brain_core {

/// Trajectory following state.
enum class FollowState {
    IDLE,
    MOVING,
    PAUSED,
    COMPLETED,
    ERROR,
    STOPPED,  // emergency stop
};

/// Trajectory following progress.
struct FollowProgress {
    FollowState state{FollowState::IDLE};
    int    current_waypoint{0};
    int    total_waypoints{0};
    double completion_pct{0.0};   // 0.0–100.0
    double position_error{0.0};   // current tracking error (m)
    double velocity{0.0};         // current end-effector velocity (m/s)
};

class TrajectoryFollower {
public:
    using ProgressCallback = std::function<void(const FollowProgress&)>;
    using StateCallback     = std::function<void(FollowState)>;

    TrajectoryFollower();

    /// Load a trajectory for following.
    void loadTrajectory(const Trajectory& traj);

    /// Start following the loaded trajectory.
    /// Returns false if no trajectory is loaded.
    bool start();

    /// Pause execution (decelerate to stop).
    void pause();

    /// Resume paused execution.
    void resume();

    /// Emergency stop (immediate halt).
    void emergencyStop();

    /// Get current follow progress.
    FollowProgress progress() const;

    /// Register progress callback (called at ~50 Hz).
    void onProgress(ProgressCallback cb);

    /// Register state change callback.
    void onStateChange(StateCallback cb);

    /// Check if currently following.
    bool isActive() const { return _state != FollowState::IDLE; }

private:
    Trajectory _trajectory;
    std::atomic<FollowState> _state{FollowState::IDLE};
    int _current_wp{0};
    ProgressCallback _progress_cb;
    StateCallback     _state_cb;
};

} // namespace brain_core
