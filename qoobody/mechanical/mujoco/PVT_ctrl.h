/*
============================================================================
QooBot Dynamics Control — PVT (Position-Velocity-Torque) Controller
============================================================================
Joint-level PD controller with low-pass filtering and torque limiting.
Configuration is loaded from joint_ctrl_config.json.

Based on OpenLoong Dyn-Control, adapted for QooBot.
============================================================================
*/
#pragma once

#include <fstream>
#include <string>
#include <vector>
#include <cmath>
#include "data_bus.h"

// Simple first-order low-pass filter
class LPF_Fst {
public:
    LPF_Fst() : fc(20), Ts(0.001), alpha(1.0), y_prev(0.0) {}
    LPF_Fst(double fcIn, double TsIn)
        : fc(fcIn), Ts(TsIn), alpha(1.0), y_prev(0.0)
    {
        double tau = 1.0 / (2.0 * M_PI * fc);
        alpha = Ts / (Ts + tau);
    }
    double filter(double u) {
        y_prev = alpha * u + (1.0 - alpha) * y_prev;
        return y_prev;
    }
    void reset() { y_prev = 0.0; }

private:
    double fc, Ts, alpha, y_prev;
};

class PVT_Ctr {
public:
    int jointNum;
    std::vector<double> motor_pos_cur;
    std::vector<double> motor_pos_des_old;
    std::vector<double> motor_vel;
    std::vector<double> motor_tor_out_link;
    std::vector<double> motor_tor_out_motor;

    std::vector<double> motor_pos_des;
    std::vector<double> motor_vel_des;
    std::vector<double> motor_tor_des;

    std::vector<double> pvt_Kp;
    std::vector<double> pvt_Kd;
    std::vector<double> maxTor;
    std::vector<double> maxVel;
    std::vector<double> maxPos;
    std::vector<double> minPos;
    std::vector<double> gear;

    PVT_Ctr(double timeStepIn, const char *jsonPath);
    void calMotorsPVT();
    void calMotorsPVT(double deltaP_Lim);
    void enablePV();
    void disablePV();
    void enablePV(int jtId);
    void disablePV(int jtId);
    void setJointPD(double kp, double kd, const char *jointName);
    void dataBusRead(DataBus &busIn);
    void dataBusWrite(DataBus &busIn);

private:
    std::vector<LPF_Fst> tau_out_lpf;
    std::vector<int> PV_enable;
    double sign(double in);

    // QooBot joint names matching qoobot_float.xml
    const std::vector<std::string> motorName = {
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
};
