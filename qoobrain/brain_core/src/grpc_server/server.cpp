// grpc_server/server.cpp — C++ gRPC server
#include "brain_core/grpc_server/server.h"
#include <iostream>

namespace brain_core {

GRPCServer::GRPCServer()
{
    std::cout << "[GRPCServer] Initialized." << std::endl;
}

bool GRPCServer::start(const std::string& address)
{
    _address = address;
    _running = true;

    // In full build:
    //   grpc::ServerBuilder builder;
    //   builder.AddListeningPort(address, grpc::InsecureServerCredentials());
    //   registerServices();
    //   _server_impl = builder.BuildAndStart();

    std::cout << "[GRPCServer] Started on " << address
              << " (stub — full gRPC requires protobuf linking)." << std::endl;
    return true;
}

void GRPCServer::stop()
{
    _running = false;
    std::cout << "[GRPCServer] Stopped." << std::endl;
}

void GRPCServer::registerServices()
{
    // In full build:
    //   builder.RegisterService(&control_service_);
    //   builder.RegisterService(&perception_service_);
    //   builder.RegisterService(&safety_service_);
    std::cout << "[GRPCServer] Services registered (Control, Perception, Safety)." << std::endl;
}

} // namespace brain_core
