// action_nodes/observe_node.h — Scene observation & perception trigger
#pragma once

#include "brain_core/core_types.h"
#include <string>
#include <vector>

namespace brain_core {

/// Observed scene snapshot from perception.
struct ObservationResult {
    SensorFrame frame;
    std::string scene_description;  // e.g., "table with 3 objects"
    int num_objects{0};
};

class ObserveNode {
public:
    ObserveNode();

    /// Set observation mode: "once" or "continuous".
    void setMode(const std::string& mode);

    /// Set which sensor to observe from (e.g., "rgbd_camera").
    void setSensor(const std::string& sensor_id);

    /// Execute observation. Returns SUCCESS with observation data,
    /// RUNNING during continuous observation.
    BTNodeStatus execute();

    /// Get the latest observation result.
    ObservationResult result() const;

    /// Cancel observation.
    void cancel();

private:
    std::string _mode{"once"};
    std::string _sensor_id{"rgbd_camera"};
    ObservationResult _result;
    bool _active{false};
};

} // namespace brain_core
