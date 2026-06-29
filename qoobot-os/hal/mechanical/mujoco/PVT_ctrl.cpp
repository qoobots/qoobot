/*
============================================================================
QooBot Dynamics Control — PVT Controller Implementation
============================================================================
Joint-level PD controller implementation with:
- Low-pass filtered torque output
- Torque/velocity/position limit enforcement
- Optional feed-forward torque

Based on OpenLoong Dyn-Control, adapted for QooBot.
============================================================================
*/
#include "PVT_ctrl.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <algorithm>

PVT_Ctr::PVT_Ctr(double timeStepIn, const char *jsonPath)
{
    jointNum = motorName.size();
    motor_pos_cur.assign(jointNum, 0);
    motor_pos_des_old.assign(jointNum, 0);
    motor_vel.assign(jointNum, 0);
    motor_tor_out_link.assign(jointNum, 0);
    motor_tor_out_motor.assign(jointNum, 0);
    motor_pos_des.assign(jointNum, 0);
    motor_vel_des.assign(jointNum, 0);
    motor_tor_des.assign(jointNum, 0);

    pvt_Kp.assign(jointNum, 100.0);
    pvt_Kd.assign(jointNum, 10.0);
    maxTor.assign(jointNum, 50.0);
    maxVel.assign(jointNum, 10.0);
    maxPos.assign(jointNum, M_PI);
    minPos.assign(jointNum, -M_PI);
    gear.assign(jointNum, 1.0);

    PV_enable.assign(jointNum, 1);

    // Initialize LPFs
    for (int i = 0; i < jointNum; i++) {
        tau_out_lpf.emplace_back(20.0, timeStepIn);
    }

    // Load configuration from JSON if available
    if (jsonPath && strlen(jsonPath) > 0) {
        std::ifstream file(jsonPath);
        if (file.is_open()) {
            std::cout << "[PVT_Ctr] Loading config from: " << jsonPath << std::endl;
            std::string line;
            std::string jsonStr;
            while (std::getline(file, line)) {
                jsonStr += line;
            }
            file.close();

            // Simple JSON parsing for the known structure
            for (int i = 0; i < jointNum; i++) {
                const std::string &name = motorName[i];
                size_t pos = jsonStr.find("\"" + name + "\"");
                if (pos == std::string::npos) continue;

                auto findVal = [&](const std::string &key, double &val) {
                    size_t kp = jsonStr.find("\"" + key + "\"", pos);
                    if (kp != std::string::npos) {
                        size_t cp = jsonStr.find(":", kp);
                        if (cp != std::string::npos) {
                            std::string sub = jsonStr.substr(cp + 1);
                            std::stringstream ss(sub);
                            ss >> val;
                        }
                    }
                };

                findVal("kp", pvt_Kp[i]);
                findVal("kd", pvt_Kd[i]);
                findVal("maxTorque", maxTor[i]);
                findVal("maxSpeed", maxVel[i]);
                findVal("maxPos", maxPos[i]);
                findVal("minPos", minPos[i]);
                findVal("gear", gear[i]);
            }
            std::cout << "[PVT_Ctr] Configuration loaded for " << jointNum << " joints" << std::endl;
        } else {
            std::cout << "[PVT_Ctr] Config file not found, using defaults" << std::endl;
        }
    }
}

void PVT_Ctr::calMotorsPVT()
{
    for (int i = 0; i < jointNum; i++) {
        if (!PV_enable[i]) {
            motor_tor_out_link[i] = 0.0;
            motor_tor_out_motor[i] = 0.0;
            continue;
        }

        double tau;

        if (m_torqueFFMode) {
            // 力矩前馈模式: WBC 力矩作为主控制, PD 仅提供阻尼稳定
            double pos_err = motor_pos_des[i] - motor_pos_cur[i];
            double vel_err = motor_vel_des[i] - motor_vel[i];
            // 减小位置增益, 保留速度阻尼
            double dampKp = pvt_Kp[i] * 0.1;
            tau = dampKp * pos_err + pvt_Kd[i] * vel_err + motor_tor_des[i];
        } else {
            // 标准 PD + 力矩前馈模式
            double pos_err = motor_pos_des[i] - motor_pos_cur[i];
            double vel_err = motor_vel_des[i] - motor_vel[i];
            tau = pvt_Kp[i] * pos_err + pvt_Kd[i] * vel_err + motor_tor_des[i];
        }

        // Torque limiting
        tau = std::max(-maxTor[i], std::min(maxTor[i], tau));

        // Low-pass filter the torque output
        motor_tor_out_link[i] = tau_out_lpf[i].filter(tau);
        motor_tor_out_motor[i] = motor_tor_out_link[i] / gear[i];
    }

    // Store old desired positions for next cycle
    motor_pos_des_old = motor_pos_des;
}

void PVT_Ctr::calMotorsPVT(double deltaP_Lim)
{
    // Limit position change per timestep
    for (int i = 0; i < jointNum; i++) {
        double delta = motor_pos_des[i] - motor_pos_des_old[i];
        if (std::abs(delta) > deltaP_Lim) {
            motor_pos_des[i] = motor_pos_des_old[i] + sign(delta) * deltaP_Lim;
        }
    }
    calMotorsPVT();
}

void PVT_Ctr::enablePV() {
    std::fill(PV_enable.begin(), PV_enable.end(), 1);
}

void PVT_Ctr::disablePV() {
    std::fill(PV_enable.begin(), PV_enable.end(), 0);
}

void PVT_Ctr::enablePV(int jtId) {
    if (jtId >= 0 && jtId < jointNum) PV_enable[jtId] = 1;
}

void PVT_Ctr::disablePV(int jtId) {
    if (jtId >= 0 && jtId < jointNum) PV_enable[jtId] = 0;
}

void PVT_Ctr::setJointPD(double kp, double kd, const char *jointName) {
    for (int i = 0; i < jointNum; i++) {
        if (motorName[i] == jointName) {
            pvt_Kp[i] = kp;
            pvt_Kd[i] = kd;
            return;
        }
    }
}

void PVT_Ctr::dataBusRead(DataBus &busIn) {
    for (int i = 0; i < jointNum; i++) {
        motor_pos_cur[i] = busIn.motors_pos_cur[i];
        motor_vel[i] = busIn.motors_vel_cur[i];
        motor_pos_des[i] = busIn.motors_pos_des[i];
        motor_vel_des[i] = busIn.motors_vel_des[i];
        motor_tor_des[i] = busIn.motors_tor_des[i];
    }
}

void PVT_Ctr::dataBusWrite(DataBus &busIn) {
    for (int i = 0; i < jointNum; i++) {
        busIn.motors_tor_out[i] = motor_tor_out_link[i];
    }
}

void PVT_Ctr::setTorqueFeedforwardMode(bool enable) {
    m_torqueFFMode = enable;
}

double PVT_Ctr::sign(double in) {
    return (in > 0) ? 1.0 : ((in < 0) ? -1.0 : 0.0);
}
