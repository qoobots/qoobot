# C++ SDK 示例 — 自主导航技能
# 演示 qoobot-sdk C++ API 的完整用法

#include <qoobot/sdk/qoobot.h>
#include <qoobot/sdk/logging.h>
#include <memory>
#include <cmath>

using namespace qoobot;
using namespace std::chrono_literals;

class AutonomousNavigation : public QooSkill {
public:
    AutonomousNavigation()
        : QooSkill("autonomous_navigation", "0.1.0")
        , lidar_("os1_64")
        , base_("base")
    {}

    bool setup() override {
        QOOBOT_LOG_INFO("AutonomousNavigation initializing");

        // Configure control frequency
        setPeriod(std::chrono::microseconds(10000)); // 100 Hz

        // Initialize LiDAR subscriber
        // lidar_sub_ = std::make_unique<Subscriber<PointCloud>>(
        //     "/qoobot/lidar",
        //     [this](const PointCloud& cloud) { this->onLidar(cloud); }
        // );

        QOOBOT_LOG_INFO("AutonomousNavigation initialized");
        return true;
    }

    void run() override {
        // 1. Perception — get latest LiDAR scan
        auto cloud = lidar_.scan();

        // 2. Planning — simple obstacle avoidance
        double linear_x = 0.3;   // Forward velocity (m/s)
        double angular_z = 0.0;  // Turn rate (rad/s)

        // Check for obstacles in front
        bool obstacle_detected = false;
        for (size_t i = 0; i < cloud.size(); ++i) {
            // Check points within 1 meter ahead
            if (cloud.x[i] > 0 && cloud.x[i] < 1.0 && std::abs(cloud.y[i]) < 0.5) {
                if (cloud.z[i] > -0.2 && cloud.z[i] < 1.0) {
                    obstacle_detected = true;
                    break;
                }
            }
        }

        if (obstacle_detected) {
            // Turn to avoid obstacle
            QOOBOT_LOG_DEBUG("Obstacle detected — turning");
            linear_x = 0.0;
            angular_z = 0.5;
        }

        // 3. Control — send velocity commands
        base_.setVelocity(linear_x, angular_z);
    }

    void cleanup() override {
        QOOBOT_LOG_INFO("AutonomousNavigation stopped");
        base_.stop();
    }

private:
    LiDAR lidar_;
    MobileBase base_;
};

REGISTER_QOO_SKILL(AutonomousNavigation)
