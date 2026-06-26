/*
============================================================================
QooBot Dynamics Control — Data Bus
============================================================================
Central data structure shared across all control modules:
MJ_Interface -> DataBus -> MPC -> WBC -> PVT_Ctr -> MJ_Interface

Based on OpenLoong Dyn-Control, adapted for QooBot.
============================================================================
*/
#pragma once

#include <Eigen/Dense>
#include <iostream>
#include <vector>
#include <iomanip>

struct DataBus
{
    const int model_nv;  // number of degrees of freedom (nv = nq - 1 for free joint)

    // Frame offset matrices (identity for matching frames)
    const Eigen::Matrix3d fe_L_rot_L_off = Eigen::Matrix3d::Identity();
    const Eigen::Matrix3d fe_R_rot_L_off = Eigen::Matrix3d::Identity();

    // === Sensors & State Feedback ===
    double rpy[3];
    double fL[3], fR[3];
    double basePos[3];
    double baseLinVel[3];
    double baseAcc[3];
    double baseAngVel[3];
    std::vector<double> motors_pos_cur;
    std::vector<double> motors_vel_cur;
    std::vector<double> motors_tor_cur;
    Eigen::VectorXd FL_est, FR_est;
    bool isdqIni;

    // === PVT Control Targets ===
    std::vector<double> motors_pos_des;
    std::vector<double> motors_vel_des;
    std::vector<double> motors_tor_des;
    std::vector<double> motors_tor_out;

    // === Kinematics & Dynamics ===
    Eigen::VectorXd q, dq, ddq;
    Eigen::VectorXd qOld;
    Eigen::MatrixXd J_base, J_l, J_r;
    Eigen::MatrixXd dJ_base, dJ_l, dJ_r;
    Eigen::MatrixXd Jcom_W;                    // CoM Jacobian in world frame
    Eigen::Vector3d pCoM_W;
    Eigen::Vector3d fe_r_pos_W, fe_l_pos_W, base_pos, base_vel;
    Eigen::Matrix3d fe_r_rot_W, fe_l_rot_W, base_rot;
    Eigen::Vector3d fe_r_pos_L, fe_l_pos_L;
    Eigen::Vector3d fe_r_vel_L, fe_l_vel_L;
    Eigen::Vector3d hip_link_pos;
    Eigen::Matrix3d fe_r_rot_L, fe_l_rot_L;
    Eigen::Matrix3d hip_link_rot;
    Eigen::Vector3d fe_r_pos_L_cmd, fe_l_pos_L_cmd;
    Eigen::Matrix3d fe_r_rot_L_cmd, fe_l_rot_L_cmd;
    Eigen::Vector3d hip_l_pos_W, hip_r_pos_W;  // hip positions in world frame

    Eigen::VectorXd qCmd, dqCmd;
    Eigen::VectorXd tauJointCmd;
    Eigen::MatrixXd dyn_M, dyn_M_inv, dyn_C, dyn_Ag, dyn_dAg;
    Eigen::VectorXd dyn_G, dyn_Non;
    Eigen::Vector3d base_omega_L, base_omega_W, base_rpy;

    // === State Estimation ===
    Eigen::Matrix<double, 3, 1> base_pos_est, base_vel_est;
    Eigen::Matrix<double, 3, 1> eul_est, omegaW_est;
    Eigen::Matrix<double, 3, 1> fe_l_pos_W_est, fe_r_pos_W_est;
    Eigen::Vector3d delta_acc;            // accelerometer bias estimate
    Eigen::Vector3d freeAcc;              // free acceleration (gravity-compensated)
    Eigen::Matrix<double, 15, 1> AX;      // A * X (state prediction)
    Eigen::Matrix<double, 15, 1> BU;      // B * u (input)
    Eigen::Matrix<double, 6, 1> CX;       // C * X (observation)
    Eigen::Matrix<double, 6, 1> Y;        // measurement
    Eigen::Matrix<double, 3, 1> pbW;      // base position in world (reshaped)

    // === Joystick Commands ===
    Eigen::Vector3d js_eul_des;
    Eigen::Vector3d js_pos_des;
    Eigen::Vector3d js_omega_des;
    Eigen::Vector3d js_vel_des;

    // === MPC Variables ===
    Eigen::Vector3d slop{Eigen::Vector3d::Zero()}; // terrain slope estimation [roll,pitch,yaw]
    Eigen::VectorXd Xd;
    Eigen::VectorXd X_cur;
    Eigen::VectorXd X_cal;
    Eigen::VectorXd dX_cal;
    Eigen::VectorXd fe_react_tau_cmd;
    int qp_nWSR_MPC;
    double qp_cpuTime_MPC;
    int qpStatus_MPC;

    // === WBC Variables ===
    Eigen::Vector3d base_rpy_des;
    Eigen::Vector3d base_pos_des;
    Eigen::Vector3d base_vel_des;
    Eigen::Vector3d base_omega_des;
    Eigen::VectorXd des_ddq, des_dq, des_delta_q, des_q;
    Eigen::Vector3d swing_fe_pos_des_W;
    Eigen::Vector3d swing_fe_rpy_des_W;
    Eigen::Vector3d stance_fe_pos_cur_W;
    Eigen::Matrix3d stance_fe_rot_cur_W;
    Eigen::VectorXd wbc_delta_q_final, wbc_dq_final, wbc_ddq_final;
    Eigen::VectorXd wbc_tauJointRes;
    Eigen::VectorXd wbc_FrRes;
    Eigen::VectorXd Fr_ff;
    int qp_nWSR;
    double qp_cpuTime;
    int qp_status;

    // === Foot Placement ===
    Eigen::Vector3d swingStartPos_W;
    Eigen::Vector3d swingDesPosCur_W;
    Eigen::Vector3d swingDesPosCur_L;
    Eigen::Vector3d swingDesPosFinal_W;
    Eigen::Vector3d stanceDesPos_W;
    Eigen::Vector3d posHip_W, posST_W;
    Eigen::Vector3d desV_W;
    double desWz_W;
    double theta0;
    double width_hips;
    double tSwing;
    double phi;

    // === Gait State Machine ===
    enum MotionState { Stand, Walk, Walk2Stand };
    enum LegState { LSt, RSt, DSt };

    bool leg_contact[2];
    double thetaZ_des{0};
    LegState legState{DataBus::DSt};
    LegState legStateNext{DataBus::DSt};
    MotionState motionState{DataBus::Stand};

    // === Jump State ===
    Eigen::Vector3d base_pos_stand;
    Eigen::Matrix<double, 6, 1> pfeW_stand, pfeW0;

    DataBus(int model_nvIn) : model_nv(model_nvIn)
    {
        int nact = model_nv - 6;  // actuator count = nv - 6 (free joint DOFs)
        motors_pos_cur.assign(nact, 0);
        motors_vel_cur.assign(nact, 0);
        motors_tor_out.assign(nact, 0);
        motors_tor_cur.assign(nact, 0);
        motors_tor_des.assign(nact, 0);
        motors_vel_des.assign(nact, 0);
        motors_pos_des.assign(nact, 0);

        q = Eigen::VectorXd::Zero(model_nv + 1);
        qOld = Eigen::VectorXd::Zero(model_nv + 1);
        dq = Eigen::VectorXd::Zero(model_nv);
        ddq = Eigen::VectorXd::Zero(model_nv);
        qCmd = Eigen::VectorXd::Zero(model_nv + 1);
        dqCmd = Eigen::VectorXd::Zero(model_nv);
        tauJointCmd = Eigen::VectorXd::Zero(nact);

        FL_est = Eigen::VectorXd::Zero(6);
        FR_est = Eigen::VectorXd::Zero(6);

        Xd = Eigen::VectorXd::Zero(12 * 10);
        X_cur = Eigen::VectorXd::Zero(12);
        X_cal = Eigen::VectorXd::Zero(12);
        dX_cal = Eigen::VectorXd::Zero(12);
        fe_react_tau_cmd = Eigen::VectorXd::Zero(13 * 3);
        Fr_ff = Eigen::VectorXd::Zero(12);

        des_ddq = Eigen::VectorXd::Zero(model_nv);
        des_dq = Eigen::VectorXd::Zero(model_nv);
        des_delta_q = Eigen::VectorXd::Zero(model_nv);

        base_rpy_des.setZero();
        base_pos_des.setZero();
        base_vel_des.setZero();
        base_omega_des.setZero();

        js_eul_des.setZero();
        js_pos_des.setZero();
        js_omega_des.setZero();
        js_vel_des.setZero();

        motionState = Stand;
        base_vel << 0, 0, 0;
    }

    // Update generalized coordinates from sensor values
    void updateQ()
    {
        base_omega_W << baseAngVel[0], baseAngVel[1], baseAngVel[2];
        auto Rcur = eul2Rot(rpy[0], rpy[1], rpy[2]);
        base_omega_W = Rcur * base_omega_W;

        auto quatNow = eul2quat(rpy[0], rpy[1], rpy[2]);
        q(0) = basePos[0];
        q(1) = basePos[1];
        q(2) = basePos[2];
        q(3) = quatNow.x();
        q(4) = quatNow.y();
        q(5) = quatNow.z();
        q(6) = quatNow.w();

        for (int i = 0; i < model_nv - 6; i++)
            q(i + 7) = motors_pos_cur[i];

        Eigen::Vector3d vCoM_W;
        vCoM_W << baseLinVel[0], baseLinVel[1], baseLinVel[2];
        dq.block<3, 1>(0, 0) = vCoM_W;
        dq.block<3, 1>(3, 0) << base_omega_W[0], base_omega_W[1], base_omega_W[2];

        for (int i = 0; i < model_nv - 6; i++)
            dq(i + 6) = motors_vel_cur[i];

        base_pos << q(0), q(1), q(2);
        base_rpy << rpy[0], rpy[1], rpy[2];
        base_rot = Rcur;
        qOld = q;
    }

    // === Math Utilities ===
    static Eigen::Matrix3d eul2Rot(double roll, double pitch, double yaw)
    {
        Eigen::Matrix3d Rx, Ry, Rz;
        Rz << cos(yaw), -sin(yaw), 0,
              sin(yaw),  cos(yaw), 0,
              0,          0,        1;
        Ry << cos(pitch), 0, sin(pitch),
              0,          1, 0,
             -sin(pitch), 0, cos(pitch);
        Rx << 1, 0,           0,
              0, cos(roll), -sin(roll),
              0, sin(roll),  cos(roll);
        return Rz * Ry * Rx;
    }

    static Eigen::Quaterniond eul2quat(double roll, double pitch, double yaw)
    {
        Eigen::Matrix3d R = eul2Rot(roll, pitch, yaw);
        return Eigen::Quaterniond(R);
    }
};
