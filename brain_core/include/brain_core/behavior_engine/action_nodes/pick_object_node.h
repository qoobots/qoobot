// action_nodes/pick_object_node.h — Pick an object with the gripper
#pragma once

#include "brain_core/core_types.h"
#include <string>

namespace brain_core {

class PickObjectNode {
public:
    PickObjectNode();

    /// Set the target object label to pick.
    void setTarget(const std::string& object_label);

    /// Set grasp parameters.
    void setGraspParams(double approach_dist_m = 0.05,
                        double grasp_force_n = 20.0,
                        double lift_height_m = 0.1);

    /// Execute the pick action: approach → grasp → lift.
    /// Returns SUCCESS on successful grasp, FAILURE otherwise.
    BTNodeStatus execute();

    /// Cancel current pick action.
    void cancel();

    /// Check if object is currently grasped.
    bool hasGrasped() const { return _grasped; }

private:
    std::string _target_label;
    double _approach_dist{0.05};
    double _grasp_force{20.0};
    double _lift_height{0.1};
    bool _active{false};
    bool _grasped{false};
};

} // namespace brain_core
