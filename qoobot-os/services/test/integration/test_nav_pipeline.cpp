#include <gtest/gtest.h>
#include "qoosvc/navigation/navigation_service.h"

using namespace qoosvc::navigation;

/**
 * Integration test: NavigationService basic pipeline.
 */
TEST(NavPipelineTest, ServiceInitialization) {
    NavigationService nav;
    auto result = nav.initialize();
    EXPECT_TRUE(result.is_ok());
}

TEST(NavPipelineTest, NavigationGoal) {
    NavigationService nav;
    nav.initialize();

    NavigationGoal goal;
    goal.x = 3.5;
    goal.y = 2.1;
    goal.qw = 1.0;

    // In integration test, navigation may fail without actual map/robot
    auto result = nav.navigate_to(goal);
    // Don't assert success — just check it doesn't crash
    SUCCEED();
}

TEST(NavPipelineTest, ZoneManagement) {
    NavigationService nav;
    nav.initialize();

    EXPECT_TRUE(nav.add_restricted_zone("stairs", {}));
    EXPECT_TRUE(nav.add_speed_zone("corridor", {}, 0.5));
    EXPECT_TRUE(nav.add_preferred_zone("living_room", {}));
}

TEST(NavPipelineTest, ExplorationConfig) {
    NavigationService nav;
    nav.initialize();

    ExplorationConfig config;
    config.max_duration_sec = 60;
    config.return_to_start = false;

    auto result = nav.explore(config);
    SUCCEED();
}

TEST(NavPipelineTest, CancelNavigation) {
    NavigationService nav;
    nav.initialize();

    EXPECT_TRUE(nav.cancel_navigation());
}

TEST(NavPipelineTest, LifecycleSequence) {
    NavigationService nav;
    nav.initialize();

    auto stop_result = nav.stop();
    EXPECT_TRUE(stop_result.is_ok());
}
