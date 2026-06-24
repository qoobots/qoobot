// grpc_server/perception_service_impl.h — PerceptionService gRPC (C++ side)
#pragma once

#include "brain_core/core_types.h"
#include <string>
#include <vector>

namespace brain_core {

/// Implements the PerceptionService gRPC service on the C++ side.
/// Acts as proxy from gRPC → onboard perception modules.
class PerceptionServiceImpl {
public:
    PerceptionServiceImpl();

    /// Get the latest scene graph from perception.
    std::string getSceneGraph() const;

    /// Get current robot localization (odometry/slam).
    void getLocalization(double& x, double& y, double& z,
                          double& qx, double& qy, double& qz, double& qw) const;

    /// Query objects by label/class.
    std::vector<std::string> queryObjects(const std::string& label_filter) const;

private:
    double _pose_x{0.0}, _pose_y{0.0}, _pose_z{0.0};
    double _pose_qx{0.0}, _pose_qy{0.0}, _pose_qz{0.0}, _pose_qw{1.0};
};

} // namespace brain_core
