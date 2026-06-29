#include <gtest/gtest.h>
#include "qoosvc/manager/service_manager.h"

using namespace qoosvc;
using namespace qoosvc::manager;

class TestService : public ServiceBase {
public:
    TestService(const std::string& name) : ServiceBase(name) {}
    bool init_called = false;
protected:
    Result<void> on_initialize() override {
        init_called = true;
        return Result<void>::ok();
    }
};

TEST(ServiceManagerTest, RegisterService) {
    ServiceManager mgr;
    auto svc = std::make_unique<TestService>("test_svc");
    auto result = mgr.register_service(std::move(svc));
    EXPECT_TRUE(result.is_ok());

    auto info = mgr.get_service_info("test_svc");
    EXPECT_TRUE(info.is_ok());
    EXPECT_EQ(info->name, "test_svc");
}

TEST(ServiceManagerTest, RegisterDuplicateFails) {
    ServiceManager mgr;
    mgr.register_service(std::make_unique<TestService>("test_svc"));
    auto result = mgr.register_service(std::make_unique<TestService>("test_svc"));
    EXPECT_TRUE(result.is_err());
}

TEST(ServiceManagerTest, RegisterNullFails) {
    ServiceManager mgr;
    auto result = mgr.register_service(nullptr);
    EXPECT_TRUE(result.is_err());
}

TEST(ServiceManagerTest, UnregisterService) {
    ServiceManager mgr;
    mgr.register_service(std::make_unique<TestService>("test_svc"));
    auto result = mgr.unregister_service("test_svc");
    EXPECT_TRUE(result.is_ok());

    auto info = mgr.get_service_info("test_svc");
    EXPECT_TRUE(info.is_err());
}

TEST(ServiceManagerTest, UnregisterNonExistentFails) {
    ServiceManager mgr;
    auto result = mgr.unregister_service("nonexistent");
    EXPECT_TRUE(result.is_err());
}

TEST(ServiceManagerTest, ListServices) {
    ServiceManager mgr;
    mgr.register_service(std::make_unique<TestService>("svc_a"));
    mgr.register_service(std::make_unique<TestService>("svc_b"));

    auto services = mgr.list_services();
    EXPECT_EQ(services.size(), 2);
}

TEST(ServiceManagerTest, InitializeAll) {
    ServiceManager mgr;
    auto svc1 = std::make_unique<TestService>("svc_a");
    auto svc2 = std::make_unique<TestService>("svc_b");

    TestService* raw1 = svc1.get();
    TestService* raw2 = svc2.get();

    mgr.register_service(std::move(svc1));
    mgr.register_service(std::move(svc2));

    auto result = mgr.initialize_all();
    EXPECT_TRUE(result.is_ok());
    EXPECT_TRUE(raw1->init_called);
    EXPECT_TRUE(raw2->init_called);
}

TEST(ServiceManagerTest, DependencyOrder) {
    ServiceManager mgr;
    mgr.register_service(std::make_unique<TestService>("svc_a"));
    mgr.register_service(std::make_unique<TestService>("svc_b"));
    mgr.register_service(std::make_unique<TestService>("svc_c"));

    // svc_c depends on svc_b, svc_b depends on svc_a
    auto r1 = mgr.add_dependency("svc_b", "svc_a");
    EXPECT_TRUE(r1.is_ok());
    auto r2 = mgr.add_dependency("svc_c", "svc_b");
    EXPECT_TRUE(r2.is_ok());

    // Circular dependency should be rejected
    auto r3 = mgr.add_dependency("svc_a", "svc_c");
    EXPECT_TRUE(r3.is_err());
}

TEST(ServiceManagerTest, StartStopService) {
    ServiceManager mgr;
    mgr.register_service(std::make_unique<TestService>("test_svc"));

    auto start_result = mgr.start_service("test_svc");
    EXPECT_TRUE(start_result.is_ok());

    auto stop_result = mgr.stop_service("test_svc");
    EXPECT_TRUE(stop_result.is_ok());
}

TEST(ServiceManagerTest, GetService) {
    ServiceManager mgr;
    auto svc = std::make_unique<TestService>("test_svc");
    TestService* raw = svc.get();
    mgr.register_service(std::move(svc));

    auto* found = mgr.get_service("test_svc");
    EXPECT_EQ(found, raw);

    auto* not_found = mgr.get_service("nonexistent");
    EXPECT_EQ(not_found, nullptr);
}

TEST(ServiceManagerTest, PauseResumeService) {
    ServiceManager mgr;
    mgr.register_service(std::make_unique<TestService>("test_svc"));
    mgr.initialize_all();

    auto pause_result = mgr.pause_service("test_svc");
    EXPECT_TRUE(pause_result.is_ok());

    auto resume_result = mgr.resume_service("test_svc");
    EXPECT_TRUE(resume_result.is_ok());
}

TEST(ServiceManagerTest, ResourceQuota) {
    ServiceManager mgr;
    mgr.register_service(std::make_unique<TestService>("test_svc"));
    ResourceQuota quota{50.0, 512, 1024, 10};
    auto result = mgr.set_resource_quota("test_svc", quota);
    EXPECT_TRUE(result.is_ok());

    auto usage = mgr.get_resource_usage();
    EXPECT_EQ(usage.size(), 1);
    EXPECT_EQ(usage[0].name, "test_svc");
}
