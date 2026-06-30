"""
QooBot C++ SDK — v1.6+

High-performance C++ API for real-time control and high-performance modules.
Provides the same capabilities as the Python SDK but with zero-overhead C++17
abstractions suitable for real-time control loops (< 1ms).

Features:
- Skill lifecycle (QooSkill base class with setup/run/cleanup hooks)
- Perception API (Camera, LiDAR, IMU with zero-copy access)
- Control API (JointController, Gripper, MobileBase with real-time safety)
- Communication API (Publisher, Subscriber with DDS/ROS2 backends)
- Logging (structured, async, multiple severity levels)
- Math utilities (SE(3), SO(3), kinematics)
- Real-time safety (priority inheritance, lock-free queues, memory preallocation)

Usage:
    #include <qoobot/sdk/qoobot.h>

    class MySkill : public qoobot::QooSkill {
    public:
        bool setup() override { ... }
        void run() override { ... }
        void cleanup() override { ... }
    };

    REGISTER_QOO_SKILL(MySkill)

Reference: Python SDK at qoobot-sdk/
"""

// This header file documents the C++ SDK API that is auto-generated
// by the CodeGenerator for C++ service projects.
//
// The C++ SDK header structure:
//   include/qoobot/sdk/
//     qoobot.h          — Main include (aggregates all)
//     skill.h            — QooSkill base class
//     perception.h       — Camera, LiDAR, IMU
//     control.h          — JointController, Gripper, MobileBase
//     communication.h    — Publisher, Subscriber
//     logging.h          — Structured logging
//     math.h             — SE(3), SO(3), kinematics
//     realtime.h         — Lock-free queues, priority inheritance

#pragma once

#include <string>
#include <memory>
#include <chrono>
#include <thread>
#include <atomic>
#include <functional>
#include <vector>
#include <map>

// ============================================================================
// Version
// ============================================================================

#define QOOBOT_SDK_VERSION_MAJOR 0
#define QOOBOT_SDK_VERSION_MINOR 1
#define QOOBOT_SDK_VERSION_PATCH 0
#define QOOBOT_SDK_VERSION "0.1.0"

// ============================================================================
// Skill Base Class
// ============================================================================

namespace qoobot {

/**
 * @brief Base class for QooBot skills (C++).
 *
 * Provides lifecycle management:
 *   setup()   — Called once when skill is loaded
 *   run()     — Main skill loop (called at configured frequency)
 *   cleanup() — Called when skill is unloaded
 *
 * Usage:
 *   class MySkill : public QooSkill {
 *   public:
 *       MySkill() : QooSkill("my_skill", "0.1.0") {}
 *       bool setup() override { return true; }
 *       void run() override { /* main loop */ }
 *       void cleanup() override {}
 *   };
 *   REGISTER_QOO_SKILL(MySkill)
 */
class QooSkill {
public:
    QooSkill(const std::string& name, const std::string& version = "0.1.0")
        : name_(name), version_(version) {}

    virtual ~QooSkill() = default;

    /** Called once when skill is loaded. Return false to abort loading. */
    virtual bool setup() { return true; }

    /** Main skill loop. Called at the configured frequency. */
    virtual void run() = 0;

    /** Called when skill is unloaded. Clean up resources. */
    virtual void cleanup() {}

    /** Get skill name. */
    const std::string& name() const { return name_; }

    /** Get skill version. */
    const std::string& version() const { return version_; }

    /** Check if skill is running. */
    bool isRunning() const { return running_.load(std::memory_order_acquire); }

protected:
    /** Start the skill (called by framework). */
    void start() {
        running_.store(true, std::memory_order_release);
        thread_ = std::make_unique<std::thread>([this]() {
            while (running_.load(std::memory_order_acquire)) {
                run();
                std::this_thread::sleep_for(period_);
            }
        });
    }

    /** Stop the skill (called by framework). */
    void stop() {
        running_.store(false, std::memory_order_release);
        if (thread_ && thread_->joinable()) {
            thread_->join();
        }
    }

    /** Set execution period. */
    void setPeriod(std::chrono::microseconds period) { period_ = period; }

private:
    std::string name_;
    std::string version_;
    std::atomic<bool> running_{false};
    std::unique_ptr<std::thread> thread_;
    std::chrono::microseconds period_{std::chrono::microseconds(10000)}; // 100 Hz default
};

} // namespace qoobot

/**
 * @brief Macro to register a QooBot skill with the skill loader.
 *
 * Creates a factory function that the skill loader can call to
 * instantiate the skill at runtime.
 *
 * Usage:
 *   REGISTER_QOO_SKILL(MySkill)
 */
#define REGISTER_QOO_SKILL(SkillClass) \
    extern "C" { \
        qoobot::QooSkill* create_qoo_skill() { \
            return new SkillClass(); \
        } \
        void destroy_qoo_skill(qoobot::QooSkill* skill) { \
            delete skill; \
        } \
        const char* get_skill_name() { \
            static SkillClass _instance; \
            static std::string _name = _instance.name(); \
            return _name.c_str(); \
        } \
    }

// ============================================================================
// Perception API
// ============================================================================

namespace qoobot {

/** @brief Image data structure (zero-copy). */
struct Image {
    int width = 0;
    int height = 0;
    int channels = 3;
    uint64_t timestamp_ns = 0;
    std::string frame_id;
    std::vector<uint8_t> data;  // Row-major, interleaved (RGB)
};

/** @brief Point cloud data structure. */
struct PointCloud {
    uint64_t timestamp_ns = 0;
    std::string frame_id;
    std::vector<float> x, y, z;       // Point coordinates
    std::vector<float> intensity;     // Intensity values
    std::vector<uint32_t> ring;       // Laser ring ID
    size_t size() const { return x.size(); }
};

/** @brief IMU data structure. */
struct ImuData {
    uint64_t timestamp_ns = 0;
    std::string frame_id;
    double ax = 0, ay = 0, az = 0;    // Linear acceleration (m/s^2)
    double gx = 0, gy = 0, gz = 0;    // Angular velocity (rad/s)
    double qx = 0, qy = 0, qz = 0, qw = 1;  // Orientation quaternion
};

/**
 * @brief Camera interface for RGB/RGB-D image capture.
 */
class Camera {
public:
    explicit Camera(const std::string& topic);
    ~Camera();

    /** Capture the latest image (non-blocking). */
    Image capture();

    /** Capture with timeout (milliseconds). */
    std::optional<Image> captureTimeout(int timeout_ms);

    /** Get camera intrinsics. */
    void getIntrinsics(double& fx, double& fy, double& cx, double& cy) const;

private:
    class Impl;
    std::unique_ptr<Impl> impl_;
};

/**
 * @brief LiDAR interface for 3D point cloud capture.
 */
class LiDAR {
public:
    explicit LiDAR(const std::string& topic);
    ~LiDAR();

    /** Scan the latest point cloud (non-blocking). */
    PointCloud scan();

    /** Get LiDAR specs. */
    int numRings() const;
    double minRange() const;
    double maxRange() const;

private:
    class Impl;
    std::unique_ptr<Impl> impl_;
};

/**
 * @brief IMU interface for inertial measurements.
 */
class IMU {
public:
    explicit IMU(const std::string& topic);
    ~IMU();

    /** Read latest IMU data (non-blocking). */
    ImuData read();

private:
    class Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace qoobot

// ============================================================================
// Control API
// ============================================================================

namespace qoobot {

/** @brief Joint command. */
struct JointCommand {
    std::vector<std::string> joint_names;
    std::vector<double> positions;       // Target positions (rad)
    std::vector<double> velocities;      // Target velocities (rad/s)
    std::vector<double> torques;         // Feed-forward torques (Nm)
    std::vector<double> stiffness;       // Impedance stiffness
    std::vector<double> damping;         // Impedance damping
};

/** @brief Joint state. */
struct JointState {
    std::vector<std::string> joint_names;
    std::vector<double> positions;       // Current positions (rad)
    std::vector<double> velocities;      // Current velocities (rad/s)
    std::vector<double> torques;         // Measured torques (Nm)
};

/** @brief End-effector pose (SE(3)). */
struct Pose {
    double x = 0, y = 0, z = 0;         // Position (m)
    double qx = 0, qy = 0, qz = 0, qw = 1;  // Orientation (quaternion)
};

/**
 * @brief Joint-level controller for a robot arm.
 *
 * Supports position, velocity, and torque control modes with
 * impedance control parameters.
 */
class JointController {
public:
    explicit JointController(const std::string& group_name);
    ~JointController();

    /** Set target joint positions. */
    void setPositions(const std::vector<double>& positions);

    /** Set target joint velocities. */
    void setVelocities(const std::vector<double>& velocities);

    /** Set joint torques (direct torque control). */
    void setTorques(const std::vector<double>& torques);

    /** Set impedance parameters (stiffness + damping). */
    void setImpedance(const std::vector<double>& stiffness,
                      const std::vector<double>& damping);

    /** Move to a Cartesian pose (inverse kinematics). */
    bool moveToPose(const Pose& target, double velocity_scaling = 1.0);

    /** Get current joint state. */
    JointState getState() const;

    /** Get end-effector pose (forward kinematics). */
    Pose getEndEffectorPose() const;

    /** Get joint names in this group. */
    std::vector<std::string> jointNames() const;

    /** Emergency stop — halt all joints. */
    void emergencyStop();

private:
    class Impl;
    std::unique_ptr<Impl> impl_;
};

/**
 * @brief Gripper/hand controller.
 */
class Gripper {
public:
    explicit Gripper(const std::string& name);
    ~Gripper();

    /** Open the gripper. */
    void open(double width = 0.1);

    /** Close the gripper with force limit. */
    void close(double force_limit = 10.0);

    /** Set gripper width (0 = closed, 1 = open). */
    void setWidth(double width);

    /** Get current gripper width. */
    double getWidth() const;

    /** Check if an object is grasped. */
    bool isGrasped() const;

private:
    class Impl;
    std::unique_ptr<Impl> impl_;
};

/**
 * @brief Mobile base controller (differential drive).
 */
class MobileBase {
public:
    explicit MobileBase(const std::string& name = "base");
    ~MobileBase();

    /** Set linear and angular velocity. */
    void setVelocity(double linear_x, double angular_z);

    /** Move to a target pose. */
    bool moveToTarget(double x, double y, double theta,
                      double velocity = 0.5);

    /** Stop the base. */
    void stop();

    /** Get current odometry. */
    void getOdometry(double& x, double& y, double& theta) const;

private:
    class Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace qoobot

// ============================================================================
// Communication API
// ============================================================================

namespace qoobot {

/**
 * @brief Typed publisher for sending messages on a topic.
 *
 * @tparam T Message type
 */
template <typename T>
class Publisher {
public:
    explicit Publisher(const std::string& topic, size_t queue_size = 10);
    ~Publisher();

    /** Publish a message. */
    void publish(const T& msg);

    /** Get topic name. */
    const std::string& topic() const;

    /** Get number of subscribers. */
    size_t subscriberCount() const;

private:
    class Impl;
    std::unique_ptr<Impl> impl_;
};

/**
 * @brief Typed subscriber for receiving messages from a topic.
 *
 * @tparam T Message type
 */
template <typename T>
class Subscriber {
public:
    using Callback = std::function<void(const T&)>;

    Subscriber(const std::string& topic, Callback callback, size_t queue_size = 10);
    ~Subscriber();

    /** Get topic name. */
    const std::string& topic() const;

private:
    class Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace qoobot

// ============================================================================
// Logging API
// ============================================================================

namespace qoobot {

enum class LogLevel {
    TRACE = 0,
    DEBUG = 1,
    INFO = 2,
    WARN = 3,
    ERROR = 4,
    FATAL = 5,
};

/**
 * @brief Structured logging with async backend.
 */
class Logger {
public:
    static Logger& instance();

    void log(LogLevel level, const std::string& message,
             const std::string& file = "", int line = 0);

    void setLevel(LogLevel level);
    LogLevel level() const;

    void setOutputFile(const std::string& path);

private:
    Logger();
    class Impl;
    std::unique_ptr<Impl> impl_;
};

// Convenience macros
#define QOOBOT_LOG_TRACE(msg) qoobot::Logger::instance().log(qoobot::LogLevel::TRACE, msg, __FILE__, __LINE__)
#define QOOBOT_LOG_DEBUG(msg) qoobot::Logger::instance().log(qoobot::LogLevel::DEBUG, msg, __FILE__, __LINE__)
#define QOOBOT_LOG_INFO(msg)  qoobot::Logger::instance().log(qoobot::LogLevel::INFO, msg, __FILE__, __LINE__)
#define QOOBOT_LOG_WARN(msg)  qoobot::Logger::instance().log(qoobot::LogLevel::WARN, msg, __FILE__, __LINE__)
#define QOOBOT_LOG_ERROR(msg) qoobot::Logger::instance().log(qoobot::LogLevel::ERROR, msg, __FILE__, __LINE__)
#define QOOBOT_LOG_FATAL(msg) qoobot::Logger::instance().log(qoobot::LogLevel::FATAL, msg, __FILE__, __LINE__)

} // namespace qoobot

// ============================================================================
// Math Utilities
// ============================================================================

namespace qoobot::math {

/**
 * @brief 3D vector.
 */
struct Vec3 {
    double x = 0, y = 0, z = 0;

    Vec3() = default;
    Vec3(double x, double y, double z) : x(x), y(y), z(z) {}

    double norm() const;
    Vec3 normalized() const;
    Vec3 cross(const Vec3& other) const;
    double dot(const Vec3& other) const;

    Vec3 operator+(const Vec3& o) const { return {x + o.x, y + o.y, z + o.z}; }
    Vec3 operator-(const Vec3& o) const { return {x - o.x, y - o.y, z - o.z}; }
    Vec3 operator*(double s) const { return {x * s, y * s, z * s}; }
};

/**
 * @brief Rotation matrix (SO(3)).
 */
struct SO3 {
    double R[3][3] = {{1, 0, 0}, {0, 1, 0}, {0, 0, 1}};

    SO3() = default;

    /** Create from quaternion. */
    static SO3 fromQuaternion(double qx, double qy, double qz, double qw);

    /** Create from axis-angle. */
    static SO3 fromAxisAngle(const Vec3& axis, double angle);

    /** Create from Euler angles (ZYX intrinsic). */
    static SO3 fromEuler(double roll, double pitch, double yaw);

    /** Convert to quaternion. */
    void toQuaternion(double& qx, double& qy, double& qz, double& qw) const;

    /** Rotate a vector. */
    Vec3 rotate(const Vec3& v) const;

    /** Inverse (transpose). */
    SO3 inverse() const;

    /** Compose rotations. */
    SO3 operator*(const SO3& other) const;
};

/**
 * @brief Rigid transformation (SE(3)).
 */
struct SE3 {
    SO3 rotation;
    Vec3 translation;

    SE3() = default;
    SE3(const SO3& R, const Vec3& t) : rotation(R), translation(t) {}

    /** Identity transformation. */
    static SE3 identity();

    /** Transform a point. */
    Vec3 transform(const Vec3& point) const;

    /** Inverse transformation. */
    SE3 inverse() const;

    /** Compose transformations. */
    SE3 operator*(const SE3& other) const;
};

} // namespace qoobot::math

// ============================================================================
// Real-time Safety
// ============================================================================

namespace qoobot::realtime {

/**
 * @brief Lock-free single-producer single-consumer queue.
 *
 * Safe for use in real-time threads (no dynamic allocation, no locks).
 *
 * @tparam T Element type
 * @tparam Capacity Queue capacity (must be power of 2)
 */
template <typename T, size_t Capacity = 256>
class SPSCQueue {
    static_assert((Capacity & (Capacity - 1)) == 0, "Capacity must be power of 2");

public:
    SPSCQueue() = default;

    /** Try to push an element. Returns false if queue is full. */
    bool tryPush(const T& item);

    /** Try to pop an element. Returns false if queue is empty. */
    bool tryPop(T& item);

    /** Check if queue is empty. */
    bool empty() const;

    /** Get number of elements in queue. */
    size_t size() const;

private:
    alignas(64) std::atomic<size_t> write_idx_{0};
    alignas(64) std::atomic<size_t> read_idx_{0};
    alignas(64) T buffer_[Capacity];
};

/**
 * @brief Real-time memory pool (preallocated).
 *
 * Allocates memory upfront to avoid dynamic allocation in real-time threads.
 *
 * @tparam T Element type
 * @tparam PoolSize Number of preallocated elements
 */
template <typename T, size_t PoolSize = 1024>
class MemoryPool {
public:
    MemoryPool();

    /** Allocate an element. Returns nullptr if pool is exhausted. */
    T* allocate();

    /** Deallocate an element. */
    void deallocate(T* ptr);

    /** Get available elements. */
    size_t available() const;

private:
    std::array<T, PoolSize> pool_;
    SPSCQueue<T*, PoolSize * 2> free_list_;
};

} // namespace qoobot::realtime

// ============================================================================
// Service Registration (same pattern as skills)
// ============================================================================

namespace qoobot {

class QooService {
public:
    QooService(const std::string& name) : name_(name) {}
    virtual ~QooService() = default;

    virtual bool init() { return true; }
    virtual void run() = 0;
    virtual void cleanup() {}

    const std::string& name() const { return name_; }
    double frequency() const { return frequency_; }

protected:
    void setFrequency(double hz) { frequency_ = hz; }

private:
    std::string name_;
    double frequency_ = 100.0;
};

} // namespace qoobot

#define REGISTER_QOO_SERVICE(ServiceClass) \
    extern "C" { \
        qoobot::QooService* create_qoo_service() { \
            return new ServiceClass(); \
        } \
        void destroy_qoo_service(qoobot::QooService* service) { \
            delete service; \
        } \
    }
