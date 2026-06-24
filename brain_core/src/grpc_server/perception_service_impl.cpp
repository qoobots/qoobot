// grpc_server/perception_service_impl.cpp — PerceptionService gRPC
#include "brain_core/grpc_server/perception_service_impl.h"
#include <iostream>

namespace brain_core {

PerceptionServiceImpl::PerceptionServiceImpl()
{
    std::cout << "[PerceptionServiceImpl] Initialized." << std::endl;
}

std::string PerceptionServiceImpl::getSceneGraph() const
{
    // Stub: return a mock JSON scene description
    std::cout << "[PerceptionServiceImpl] GetSceneGraph called." << std::endl;
    return R"({"objects":[{"label":"cup","confidence":0.92,"pos":[0.3,0.4,0.05]},{"label":"bottle","confidence":0.88,"pos":[0.6,0.5,0.08]}]})";
}

void PerceptionServiceImpl::getLocalization(double& x, double& y, double& z,
                                              double& qx, double& qy, double& qz, double& qw) const
{
    x = _pose_x;
    y = _pose_y;
    z = _pose_z;
    qx = _pose_qx;
    qy = _pose_qy;
    qz = _pose_qz;
    qw = _pose_qw;
}

std::vector<std::string> PerceptionServiceImpl::queryObjects(
    const std::string& label_filter) const
{
    std::cout << "[PerceptionServiceImpl] QueryObjects: \"" << label_filter << "\"" << std::endl;

    // Stub: return matching object IDs
    if (label_filter == "cup" || label_filter.empty()) {
        return {"obj_001_cup"};
    }
    if (label_filter == "bottle") {
        return {"obj_002_bottle"};
    }
    return {};
}

} // namespace brain_core
