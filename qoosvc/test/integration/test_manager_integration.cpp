#include <gtest/gtest.h>
#include "qoosvc/manager/service_manager.h"
#include "qoosvc/voice/voice_service.h"
#include "qoosvc/diagnostics/diagnostics_service.h"

using namespace qoosvc;
using namespace qoosvc::manager;

/**
 * Integration test: ServiceManager orchestrating multiple real services.
 */
class ManagerIntegrationTest : public ::testing::Test {
protected:
    void SetUp() override {
        mgr.register_service(std::make_unique<voice::VoiceService>(), {"svc_voice"});
        mgr.register_service(std::make_unique<diagnostics::DiagnosticsService>(), {"svc_diagnostics"});
    }

    ServiceManager mgr;
};

TEST_F(ManagerIntegrationTest, InitializeAndStartAll) {
    auto init_result = mgr.initialize_all();
    EXPECT_TRUE(init_result.is_ok());

    auto start_result = mgr.start_all();
    EXPECT_TRUE(start_result.is_ok());

    auto services = mgr.list_services();
    EXPECT_EQ(services.size(), 2);

    for (const auto& svc : services) {
        EXPECT_EQ(svc.state, ServiceState::RUNNING);
    }
}

TEST_F(ManagerIntegrationTest, HealthCheckAll) {
    mgr.initialize_all();
    mgr.start_all();

    auto health = mgr.check_all_health();
    EXPECT_EQ(health.size(), 2);

    for (const auto& [name, healthy] : health) {
        EXPECT_TRUE(healthy) << "Service " << name << " should be healthy";
    }
}

TEST_F(ManagerIntegrationTest, StopAllServices) {
    mgr.initialize_all();
    mgr.start_all();

    auto stop_result = mgr.stop_all();
    EXPECT_TRUE(stop_result.is_ok());

    auto services = mgr.list_services();
    for (const auto& svc : services) {
        EXPECT_EQ(svc.state, ServiceState::STOPPED);
    }
}

TEST_F(ManagerIntegrationTest, PauseAndResumeSingleService) {
    mgr.initialize_all();
    mgr.start_all();

    auto pause_result = mgr.pause_service("svc_voice");
    EXPECT_TRUE(pause_result.is_ok());

    auto info = mgr.get_service_info("svc_voice");
    EXPECT_TRUE(info.is_ok());
    EXPECT_EQ(info->state, ServiceState::PAUSED);

    auto resume_result = mgr.resume_service("svc_voice");
    EXPECT_TRUE(resume_result.is_ok());
}

TEST_F(ManagerIntegrationTest, RestartService) {
    mgr.initialize_all();
    mgr.start_all();

    auto restart_result = mgr.restart_service("svc_diagnostics");
    EXPECT_TRUE(restart_result.is_ok());
}

TEST_F(ManagerIntegrationTest, GetServicePointer) {
    mgr.initialize_all();

    auto* voice = mgr.get_service("svc_voice");
    EXPECT_NE(voice, nullptr);
    EXPECT_EQ(voice->name(), "svc_voice");

    auto* diag = mgr.get_service("svc_diagnostics");
    EXPECT_NE(diag, nullptr);
    EXPECT_EQ(diag->name(), "svc_diagnostics");
}
