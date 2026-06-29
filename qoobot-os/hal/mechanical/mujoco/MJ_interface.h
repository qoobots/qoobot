/*
============================================================================
QooBot Dynamics Control — MuJoCo Simulation Interface
============================================================================
Based on OpenLoong Dyn-Control, adapted for QooBot biped humanoid robot.
License: Apache 2.0

This module provides the bridge between MuJoCo physics engine and
the QooBot MPC+WBC control stack.
============================================================================
*/
#pragma once

#include <mujoco/mujoco.h>
#include "data_bus.h"
#include <string>
#include <vector>

class MJ_Interface {
public:
    int jointNum{0};
    std::vector<double> motor_pos;
    std::vector<double> motor_pos_Old;
    std::vector<double> motor_vel;
    double rpy[3]{0};           // roll, pitch, yaw of base_link
    double baseQuat[4]{0};      // [x,y,z,w] order
    double f3d[3][2]{0};        // 3D foot-end contact force [axis][L/R]
    double basePos[3]{0};       // base_link position in world frame
    double baseAcc[3]{0};       // base_link acceleration in body frame
    double baseAngVel[3]{0};    // base_link angular velocity in body frame
    double baseLinVel[3]{0};    // base_link linear velocity in body frame
    double feLPosW[3]{0};       // left foot-end position in world frame
    double feRPosW[3]{0};       // right foot-end position in world frame
    double feLRotW[9]{0};       // left foot-end rotation matrix (row-major)
    double feRRotW[9]{0};       // right foot-end rotation matrix (row-major)

    // QooBot joint names (matching qoobot_float.xml)
    const std::vector<std::string> JointName = {
        "J_arm_l_01", "J_arm_l_02", "J_arm_l_03", "J_arm_l_04", "J_arm_l_05",
        "J_arm_l_06", "J_arm_l_07",
        "J_arm_r_01", "J_arm_r_02", "J_arm_r_03", "J_arm_r_04", "J_arm_r_05",
        "J_arm_r_06", "J_arm_r_07",
        "J_head_yaw", "J_head_pitch",
        "J_waist_pitch", "J_waist_roll", "J_waist_yaw",
        "J_hip_l_roll", "J_hip_l_yaw", "J_hip_l_pitch", "J_knee_l_pitch",
        "J_ankle_l_pitch", "J_ankle_l_roll",
        "J_hip_r_roll", "J_hip_r_yaw", "J_hip_r_pitch", "J_knee_r_pitch",
        "J_ankle_r_pitch", "J_ankle_r_roll"
    };

    const std::string baseName = "base_link";
    const std::string orientationSensorName = "baselink-quat";
    const std::string velSensorName = "baselink-velocity";
    const std::string gyroSensorName = "baselink-gyro";
    const std::string accSensorName = "baselink-baseAcc";

    MJ_Interface(mjModel *mj_modelIn, mjData *mj_dataIn);
    void updateSensorValues();
    void setMotorsTorque(std::vector<double> &tauIn);
    void dataBusWrite(DataBus &busIn);

private:
    mjModel *mj_model;
    mjData *mj_data;
    std::vector<int> jntId_qpos, jntId_qvel, jntId_dctl;

    int orientationSensorId;
    int velSensorId;
    int gyroSensorId;
    int accSensorId;
    int baseBodyId;

    double timeStep{0.001};
    bool isIni{false};
};
