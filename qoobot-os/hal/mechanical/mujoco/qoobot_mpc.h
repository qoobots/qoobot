/*
============================================================================
QooBot MPC — Model Predictive Control (SRBM-based)
============================================================================
QooBot 适配的 MPC 实现，基于 OpenLoong 算法，使用：
  - 单刚体模型 (SRBM) 离散化
  - qpOASES 求解约束 QP
  - 读取 QooBot DataBus 状态
  - 输出 Fr_ff (前馈地面反作用力)

机器人参数（与 OpenLoong 青龙相同）：
  - 质量: 77.35 kg
  - 转动惯量: 近似 OpenLoong
  - 足部接触尺寸: 近似 OpenLoong

License: Apache 2.0
============================================================================
*/
#pragma once

#include <Eigen/Dense>
#include "data_bus.h"
#include "useful_math.h"
#include <qpOASES.hpp>

const uint16_t QOO_MPC_N = 10;   // 预测时域
const uint16_t QOO_MPC_NX = 12;  // 状态维度: [rpy(3), pos(3), ang_vel(3), lin_vel(3)]
const uint16_t QOO_MPC_NU = 13;  // 控制维度: [f_xL,f_yL,f_zL,tau_xL,tau_yL,tau_zL, f_xR,f_yR,f_zR,tau_xR,tau_yR,tau_zR, f_z_total]
const uint16_t QOO_MPC_CH = 3;   // 滑动窗口大小

// 摩擦锥 & 力矩约束维度 (与 OpenLoong 一致)
const uint16_t QOO_NCFR_SINGLE = 4;
const uint16_t QOO_NCFR = QOO_NCFR_SINGLE * 2;           // 8
const uint16_t QOO_NCSTXY_A = 1;
const uint16_t QOO_NCSTXY_SINGLE = QOO_NCSTXY_A * 4;    // 4
const uint16_t QOO_NCSTXY = QOO_NCSTXY_SINGLE * 2;       // 8
const uint16_t QOO_NCSTZ_A = 2;
const uint16_t QOO_NCSTZ_SINGLE = QOO_NCSTZ_A * 4;      // 8
const uint16_t QOO_NCSTZ = QOO_NCSTZ_SINGLE * 2;         // 16
const uint16_t QOO_MPC_NC = QOO_NCFR + QOO_NCSTXY + QOO_NCSTZ; // 32 per step

class QooBot_MPC {
public:
    QooBot_MPC(double dtIn);
    ~QooBot_MPC() = default;

    // 设置 MPC 权重
    void setWeight(double u_weight, const Eigen::MatrixXd& L_diag, const Eigen::MatrixXd& K_diag);
    
    // 从 DataBus 读取状态
    void dataBusRead(const DataBus& data);
    
    // 求解 MPC QP
    void solve();
    
    // 写入 DataBus (Fr_ff, Xd, X_cur, etc.)
    void dataBusWrite(DataBus& data);
    
    // 启用/禁用 MPC
    void enable() { m_enabled = true; }
    void disable() { m_enabled = false; }
    bool isEnabled() const { return m_enabled; }

private:
    void buildSRBM();        // 构建单刚体模型离散化
    void buildQP();          // 构建 QP 问题
    void copyEigenToRealT(qpOASES::real_t* target, const Eigen::MatrixXd& source, int nRows, int nCols);

    bool m_enabled = false;
    double m_dt = 0.001;
    double m_alpha = 0.1;  // control effort weight
    
    // 机器人参数 (QooBot ≈ OpenLoong)
    double m_mass = 77.35;
    double m_gravity = -9.8;
    double m_miu = 0.5;   // 摩擦系数
    Eigen::Matrix3d m_Ic;  // CoM 转动惯量
    double m_deltaFoot[4];  // 足部接触尺寸 [dx+, dx-, dy+, dy-]
    double m_min[6], m_max[6];  // 力/力矩上下界
    
    // SRBM 状态空间矩阵
    Eigen::Matrix<double, QOO_MPC_NX, QOO_MPC_NX> m_Ac[QOO_MPC_N];
    Eigen::Matrix<double, QOO_MPC_NX, QOO_MPC_NU> m_Bc[QOO_MPC_N];
    Eigen::Matrix<double, QOO_MPC_NX, QOO_MPC_NX> m_A[QOO_MPC_N];
    Eigen::Matrix<double, QOO_MPC_NX, QOO_MPC_NU> m_B[QOO_MPC_N];
    
    // QP 矩阵
    Eigen::MatrixXd m_Aqp, m_Aqp1, m_Bqp1, m_Bqp, m_Cqp1, m_Cqp;
    Eigen::MatrixXd m_Xcur, m_Xdes, m_Xcal, m_dXcal;
    Eigen::VectorXd m_Ufe, m_Ufe_pre;
    
    // QP 权重
    Eigen::MatrixXd m_L, m_K, m_M;
    Eigen::MatrixXd m_H;
    Eigen::VectorXd m_c;
    
    // QP 约束
    Eigen::MatrixXd m_As;
    Eigen::VectorXd m_bs;
    Eigen::VectorXd m_uLow, m_uUpp;
    
    // qpOASES
    qpOASES::QProblem m_QP;
    static constexpr int QP_H_SIZE = QOO_MPC_NU * QOO_MPC_CH * QOO_MPC_NU * QOO_MPC_CH;
    static constexpr int QP_AS_SIZE = QOO_MPC_NC * QOO_MPC_CH * QOO_MPC_NU * QOO_MPC_CH;
    qpOASES::real_t m_qpH[QP_H_SIZE];
    qpOASES::real_t m_qpAs[QP_AS_SIZE];
    qpOASES::real_t m_qpc[QOO_MPC_NU * QOO_MPC_CH];
    qpOASES::real_t m_qplbA[QOO_MPC_NC * QOO_MPC_CH], m_qpubA[QOO_MPC_NC * QOO_MPC_CH];
    qpOASES::real_t m_qplu[QOO_MPC_NU * QOO_MPC_CH], m_qpuu[QOO_MPC_NU * QOO_MPC_CH];
    qpOASES::real_t m_xOptGuess[QOO_MPC_NU * QOO_MPC_CH];
    int m_nWSR = 100;
    qpOASES::real_t m_cpuTime = 0.001;
    int m_qpStatus = 0;
    
    // 步态状态
    DataBus::LegState m_legStateCur;
    DataBus::LegState m_legStateNext;
    DataBus::LegState m_legState[QOO_MPC_N];
    double m_phi = 0.0;
    
    // 足部位置 (世界坐标系)
    Eigen::Vector3d m_pCoM;
    Eigen::Matrix<double, 6, 1> m_pf2com, m_pf2comd;
    Eigen::Matrix<double, 6, 1> m_pe; // [fe_l(3); fe_r(3)]
    Eigen::Matrix3d m_Rcur, m_Rw2f, m_Rf2w;
    Eigen::Matrix3d m_Rcurz[QOO_MPC_N];
};
