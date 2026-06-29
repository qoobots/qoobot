#include <gtest/gtest.h>
#include "qoosvc/common/service_base.h"

using namespace qoosvc;

class TestService : public ServiceBase {
public:
    TestService() : ServiceBase("test_svc") {}
    bool init_called = false;
    bool start_called = false;
    bool stop_called = false;

protected:
    Result<void> on_initialize() override {
        init_called = true;
        return Result<void>::ok();
    }
    Result<void> on_start() override {
        start_called = true;
        return Result<void>::ok();
    }
    Result<void> on_stop() override {
        stop_called = true;
        return Result<void>::ok();
    }
};

TEST(ServiceBaseTest, InitialState) {
    TestService svc;
    EXPECT_EQ(svc.name(), "test_svc");
    EXPECT_EQ(svc.state(), ServiceState::UNINITIALIZED);
    EXPECT_FALSE(svc.is_running());
}

TEST(ServiceBaseTest, Initialize) {
    TestService svc;
    auto result = svc.initialize();
    EXPECT_TRUE(result.is_ok());
    EXPECT_EQ(svc.state(), ServiceState::RUNNING);
    EXPECT_TRUE(svc.is_running());
    EXPECT_TRUE(svc.init_called);
}

TEST(ServiceBaseTest, DoubleInitializeFails) {
    TestService svc;
    svc.initialize();
    auto result = svc.initialize();
    EXPECT_TRUE(result.is_err());
    EXPECT_EQ(result.error_code(), ErrorCode::INVALID_ARGUMENT);
}

TEST(ServiceBaseTest, LifecycleSequence) {
    TestService svc;
    svc.initialize();
    EXPECT_EQ(svc.state(), ServiceState::RUNNING);

    auto pause_result = svc.pause();
    EXPECT_TRUE(pause_result.is_ok());
    EXPECT_EQ(svc.state(), ServiceState::PAUSED);

    auto resume_result = svc.resume();
    EXPECT_TRUE(resume_result.is_ok());
    EXPECT_EQ(svc.state(), ServiceState::RUNNING);

    auto stop_result = svc.stop();
    EXPECT_TRUE(stop_result.is_ok());
    EXPECT_EQ(svc.state(), ServiceState::STOPPED);
}

TEST(ServiceBaseTest, HealthCheck) {
    TestService svc;
    EXPECT_TRUE(svc.health_check());  // RUNNING or PAUSED

    svc.initialize();
    EXPECT_TRUE(svc.health_check());

    svc.pause();
    EXPECT_TRUE(svc.health_check());

    svc.resume();
    svc.stop();
    EXPECT_FALSE(svc.health_check());
}
