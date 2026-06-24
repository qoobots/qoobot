// action_nodes/place_object_node.h — Place an object at a target location
#pragma once

#include "brain_core/core_types.h"
#include <string>

namespace brain_core {

class PlaceObjectNode {
public:
    PlaceObjectNode();

    /// Set target placement position in world coordinates.
    void setTarget(double x, double y, double z);

    /// Set placement surface height (e.g., tabletop z=0.05).
    void setSurfaceHeight(double z);

    /// Execute the place action: approach → lower → release → retract.
    /// Returns SUCCESS on successful placement, FAILURE otherwise.
    BTNodeStatus execute();

    /// Cancel current place action.
    void cancel();

    /// Check if object has been released.
    bool hasReleased() const { return _released; }

private:
    double _target_x{0.0}, _target_y{0.0}, _target_z{0.0};
    double _surface_z{0.05};
    double _approach_height{0.15};  // hover above target
    bool _active{false};
    bool _released{false};
};

} // namespace brain_core
