/*
============================================================================
QooBot WBC — Whole-Body Control (QP-based)
============================================================================
QooBot 适配的 WBC 实现，基于 OpenLoong 算法，使用：
  - 任务优先级分解 (基于 null-space 投影)
  - qpOASES 求解约束 QP (力矩优化)
  - 读取 QooBot DataBus (Fr_ff, 动力学, 雅可比)
  - 输出 motors_tor_des (关节力矩指令)

与 OpenLoong 的差异：
  - 使用 MuJoCo 计算动力学和雅可比 (替代 Pinocchio)
  - 适配 QooBot 关节映射 (model_nv=37)
  - 定义适合 QooBot 的 WBC 任务集

License: Apache 2.0
============================================================================
*/
#pragma once

#include <Eigen/Dense>
#include "data_bus.h"
#include "useful_math.h"
#include <qpOASES.hpp>

// QooBot WBC QP 维度
// QP 变量: [ddq_base(6), Fr(12)] = 18
// QP 约束: [动力学等式(6), 摩擦金字塔约束(16)] = 22
const int QOO_WBC_QP_NV = 18;
const int QOO_WBC_QP_NC = 22;

class QooBot_WBC {
public:
    QooBot_WBC(int model_nv_In, double dtIn);
    ~QooBot_WBC() = default;

    // 从 DataBus 读取状态 (动力学, 雅可比, Fr_ff, 任务目标)
    void dataBusRead(const DataBus& data);
    
    // 计算期望加速度 (任务优先级分解)
    void computeDesAcc();
    
    // 求解 QP 得到关节力矩
    void computeTau();
    
    // 写入 DataBus (motors_tor_des, wbc_*)
    void dataBusWrite(DataBus& data);
    
    // 设置惯量补偿权重
    void setInertiaWeight(double w) { m_inertiaWeight = w; }

private:
    void copyEigenToRealT(qpOASES::real_t* target, const Eigen::MatrixXd& source, int nRows, int nCols);
    void copyEigenToRealT(qpOASES::real_t* target, const Eigen::VectorXd& source, int nRows);
    // 辅助读取
    Eigen::Vector3d dataBusReadRpy() const;
    Eigen::Vector3d dataBusReadPos() const;
    Eigen::Vector3d dataBusReadSwingFePos() const;
    void buildTaskForWalk();   // 行走模式任务
    void buildTaskForStand(); // 站立模式任务

    int m_modelNv;      // 总 DOF (QooBot: 37 = 6 float + 31 actuated)
    double m_dt = 0.001;
    double m_miu = 0.5;
    double m_inertiaWeight = 1.0;
    
    // 任务权重
    double m_fzLow = 10.0;
    double m_fzUpp = 1400.0;
    Eigen::Vector3d m_tauUppStand, m_tauLowStand;
    Eigen::Vector3d m_tauUppWalk, m_tauLowWalk;
    
    // 状态
    DataBus::LegState m_legStateCur;
    DataBus::MotionState m_motionStateCur;
    
    // 动力学
    Eigen::MatrixXd m_dynM, m_dynMinv, m_dynAg, m_dyndAg;
    Eigen::VectorXd m_dynNon;
    
    // 雅可比
    Eigen::MatrixXd m_Jc, m_dJc;   // 接触脚雅可比
    Eigen::MatrixXd m_Jsw, m_dJsw; // 摆动脚雅可比
    Eigen::MatrixXd m_Jfe, m_dJfe; // 双足雅可比
    Eigen::MatrixXd m_Jbase, m_dJbase;
    Eigen::MatrixXd m_Jcom;
    Eigen::Vector3d m_pCoMCur;
    
    // 任务目标
    Eigen::VectorXd m_desDdq, m_desDq, m_desDeltaQ, m_desQ;
    Eigen::Vector3d m_baseRpyDes, m_basePosDes;
    Eigen::Vector3d m_swingFePosDes, m_stanceFePosCur;
    Eigen::Matrix3d m_swingFeRotDes, m_stanceFeRotCur;
    
    // 前馈力
    Eigen::VectorXd m_FrFf;
    
    // 选取矩阵
    Eigen::MatrixXd m_Sf, m_St;
    
    // QP 求解结果
    Eigen::VectorXd m_ddqOpt, m_frOpt, m_tauJointRes;
    Eigen::VectorXd m_ddqFinal, m_desAccCache;
    
    // qpOASES
    qpOASES::QProblem m_QP;
    qpOASES::real_t m_qpH[QOO_WBC_QP_NV * QOO_WBC_QP_NV];
    qpOASES::real_t m_qpA[QOO_WBC_QP_NC * QOO_WBC_QP_NV];
    qpOASES::real_t m_qpg[QOO_WBC_QP_NV];
    qpOASES::real_t m_qplbA[QOO_WBC_QP_NC], m_qpubA[QOO_WBC_QP_NC];
    qpOASES::real_t m_xOptGuess[QOO_WBC_QP_NV];
    int m_nWSR = 200;
    qpOASES::real_t m_cpuTime = 0.001;
    int m_qpStatus = 0;
};
