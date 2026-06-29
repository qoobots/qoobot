/*
============================================================================
QooBot WBC — Implementation (Complete qpOASES integration)
============================================================================
*/
#include "qoobot_wbc.h"
#include <iostream>
#include <cmath>

QooBot_WBC::QooBot_WBC(int model_nv_In, double dtIn)
    : m_modelNv(model_nv_In), m_dt(dtIn),
      m_QP(QOO_WBC_QP_NV, QOO_WBC_QP_NC)
{
    // 选取矩阵 Sf: 基座(6 DOF) → 全体速度
    m_Sf = Eigen::MatrixXd::Zero(6, m_modelNv);
    m_Sf.block<6, 6>(0, 0) = Eigen::Matrix<double, 6, 6>::Identity();
    m_St = Eigen::MatrixXd::Zero(m_modelNv, m_modelNv - 6);
    m_St.block(6, 0, m_modelNv - 6, m_modelNv - 6) = Eigen::MatrixXd::Identity(m_modelNv - 6, m_modelNv - 6);

    // 力/力矩上下界 (与 OpenLoong 一致)
    m_fzLow = 10.0;
    m_fzUpp = 1400.0;
    m_tauUppStand << 15, 30, 40;
    m_tauLowStand << -15, -30, -40;
    m_tauUppWalk  << 15, 40, 40;
    m_tauLowWalk  << -15, -40, -40;

    // qpOASES 配置
    qpOASES::Options options;
    options.setToMPC();
    options.printLevel = qpOASES::PL_LOW;
    m_QP.setOptions(options);

    m_ddqOpt = Eigen::VectorXd::Zero(m_modelNv);
    m_frOpt = Eigen::VectorXd::Zero(12);
    m_tauJointRes = Eigen::VectorXd::Zero(m_modelNv - 6);
    m_ddqFinal = Eigen::VectorXd::Zero(m_modelNv);
}

void QooBot_WBC::dataBusRead(const DataBus& data)
{
    // 读取动力学 (由控制器通过 MuJoCo 计算并填充)
    m_dynM = data.dyn_M;
    m_dynMinv = data.dyn_M_inv;
    m_dynAg = data.dyn_Ag;
    m_dyndAg = data.dyn_dAg;
    m_dynNon = data.dyn_Non;

    // 读取雅可比 (由控制器通过 MuJoCo 计算)
    m_Jbase = data.J_base;
    m_dJbase = data.dJ_base;
    m_Jfe = Eigen::MatrixXd::Zero(12, m_modelNv);
    m_Jfe.block(0, 0, 6, m_modelNv) = data.J_l;
    m_Jfe.block(6, 0, 6, m_modelNv) = data.J_r;
    m_dJfe = Eigen::MatrixXd::Zero(12, m_modelNv);
    m_dJfe.block(0, 0, 6, m_modelNv) = data.dJ_l;
    m_dJfe.block(6, 0, 6, m_modelNv) = data.dJ_r;

    // 根据步态状态选择接触/摆动脚雅可比
    m_legStateCur = data.legState;
    m_motionStateCur = data.motionState;
    if (m_legStateCur == DataBus::LSt) {
        m_Jc = data.J_l;
        m_dJc = data.dJ_l;
        m_Jsw = data.J_r;
        m_dJsw = data.dJ_r;
    } else {
        m_Jc = data.J_r;
        m_dJc = data.dJ_r;
        m_Jsw = data.J_l;
        m_dJsw = data.dJ_l;
    }

    m_Jcom = data.Jcom_W;
    m_pCoMCur = data.pCoM_W;

    // 读取前馈力
    m_FrFf = data.Fr_ff;

    // === 读取当前状态 (从 DataBus 传感器数据) ===
    m_baseRpyCur = data.base_rpy;
    m_basePosCur = data.base_pos;

    // 读取摆动脚当前位置
    if (m_legStateCur == DataBus::LSt)
        m_swingFePosCur = data.fe_r_pos_W;
    else if (m_legStateCur == DataBus::RSt)
        m_swingFePosCur = data.fe_l_pos_W;
    else
        m_swingFePosCur = data.fe_l_pos_W;  // DSt: 用左脚近似

    // 读取任务目标
    m_baseRpyDes = data.base_rpy_des;
    m_basePosDes = data.base_pos_des;
    m_desDdq = data.des_ddq;
    m_desDq = data.des_dq;
    m_desDeltaQ = data.des_delta_q;

    // 足部目标
    m_swingFePosDes = data.swing_fe_pos_des_W;
    m_swingFeRotDes = Eigen::Matrix3d::Identity();
}

void QooBot_WBC::computeDesAcc()
{
    // === 任务优先级分解 (PD 控制) ===
    // 层级 1: 接触约束 (最高优先级, 由 QP 保证)
    // 层级 2: 基座姿态/位置跟踪
    // 层级 3: 摆动脚轨迹跟踪

    m_ddqFinal = Eigen::VectorXd::Zero(m_modelNv);

    // --- 基座任务: 姿态 + 位置 ---
    // 使用从 DataBus 读取的当前状态
    Eigen::Vector3d errRpy = m_baseRpyDes - m_baseRpyCur;
    Eigen::Vector3d errPos = m_basePosDes - m_basePosCur;

    // 基座 PD 增益
    double kpBase = 500.0, kdBase = 50.0;
    Eigen::VectorXd accBase = Eigen::VectorXd::Zero(6);
    accBase.block<3, 1>(0, 0) = kpBase * errRpy - kdBase * m_dynAg.block<3, 1>(0, 0);
    accBase.block<3, 1>(3, 0) = kpBase * errPos - kdBase * m_dynAg.block<3, 1>(3, 0);

    // 写入 ddq_final 的基座部分
    m_ddqFinal.block<6, 1>(0, 0) = accBase;

    // --- 摆动脚任务 ---
    if (m_motionStateCur == DataBus::Walk) {
        Eigen::Vector3d errSwing = m_swingFePosDes - m_swingFePosCur;
        double kpSwing = 500.0, kdSwing = 50.0;
        Eigen::VectorXd accSwing = Eigen::VectorXd::Zero(6);
        accSwing.block<3, 1>(0, 0) = kpSwing * errSwing - kdSwing * Eigen::Vector3d::Zero();
        // 摆动脚加速度映射到关节空间 (雅可比伪逆)
        Eigen::MatrixXd Jsw_pinv = m_Jsw.transpose() * (m_Jsw * m_Jsw.transpose() + 1e-6 * Eigen::MatrixXd::Identity(6, 6)).inverse();
        m_ddqFinal += Jsw_pinv * accSwing;
    }

    // 保存用于 QP
    m_desAccCache = m_ddqFinal;
}

void QooBot_WBC::computeTau()
{
    // === 构建 WBC QP 问题 ===
    // 变量: x = [ddq_base(6); Fr_delta(12)]  (18 维)
    // 等式约束: M_s * ddq + Non_s = J_s^T * (Fr_ff + Fr_delta)   (6 维)
    // 不等式约束: 摩擦金字塔  (16 维)

    // --- 提取基座自由度对应的动力学 ---
    Eigen::MatrixXd M_s = m_dynM.block(0, 0, 6, m_modelNv);  // 6 x nv
    Eigen::VectorXd Non_s = m_dynNon.block<6, 1>(0, 0);       // 6 x 1
    Eigen::MatrixXd JcT_s = m_Jfe.transpose().block(0, 0, 6, 12); // 6 x 12 (基座行)

    // --- QP 矩阵 ---
    Eigen::MatrixXd H = Eigen::MatrixXd::Zero(QOO_WBC_QP_NV, QOO_WBC_QP_NV);
    Eigen::VectorXd g = Eigen::VectorXd::Zero(QOO_WBC_QP_NV);

    // 权重: 优先满足接触约束, 其次最小化基座加速度和力偏差
    H.block<6, 6>(0, 0) = Eigen::MatrixXd::Identity(6, 6) * 1e7;   // ddq_base 权重
    H.block<12, 12>(6, 6) = Eigen::MatrixXd::Identity(12, 12) * 1e1; // Fr_delta 权重

    // --- 等式约束: M_s * (Sf*ddq_base + St*ddq_joint) + Non_s = JcT_s^T * (Fr_ff + Fr_delta) ---
    // 简化: 假设 ddq_joint = m_ddqFinal(6:end), 仅优化 ddq_base 和 Fr_delta
    Eigen::MatrixXd A_eq = Eigen::MatrixXd::Zero(6, QOO_WBC_QP_NV);
    Eigen::VectorXd b_eq = Eigen::VectorXd::Zero(6);

    A_eq.block<6, 6>(0, 0) = M_s * m_Sf;                       // ddq_base 系数
    A_eq.block<6, 12>(0, 6) = -JcT_s.transpose().block(0, 0, 6, 12); // Fr_delta 系数 (转置调整)

    b_eq = -M_s * m_St * m_ddqFinal.block(6, 0, m_modelNv - 6, 1) - Non_s + JcT_s.transpose() * m_FrFf;

    // --- 摩擦金字塔约束 ---
    // |f_x| <= miu * f_z,  |f_y| <= miu * f_z  (每足 4 个不等式, 共 16)
    Eigen::MatrixXd A_fr = Eigen::MatrixXd::Zero(16, 12);
    // 左足摩擦锥 (6 DOF: f_xL, f_yL, f_zL, tau_xL, tau_yL, tau_zL 中的 f_xL, f_yL, f_zL)
    A_fr(0, 0) = -1.0;  A_fr(0, 2) = -m_miu;   // -f_xL - miu*f_zL <= 0
    A_fr(1, 0) =  1.0;  A_fr(1, 2) = -m_miu;   //  f_xL - miu*f_zL <= 0
    A_fr(2, 1) = -1.0;  A_fr(2, 2) = -m_miu;   // -f_yL - miu*f_zL <= 0
    A_fr(3, 1) =  1.0;  A_fr(3, 2) = -m_miu;   //  f_yL - miu*f_zL <= 0
    // 右足摩擦锥
    A_fr(4, 6) = -1.0;  A_fr(4, 8) = -m_miu;
    A_fr(5, 6) =  1.0;  A_fr(5, 8) = -m_miu;
    A_fr(6, 7) = -1.0;  A_fr(6, 8) = -m_miu;
    A_fr(7, 7) =  1.0;  A_fr(7, 8) = -m_miu;

    // 扩展到 Fr_delta (QP 变量 6:12 是 Fr_delta)
    Eigen::MatrixXd A_ineq = Eigen::MatrixXd::Zero(16, QOO_WBC_QP_NV);
    A_ineq.block(0, 6, 16, 12) = A_fr;

    Eigen::VectorXd lbA_ineq = Eigen::VectorXd::Constant(16, -1e15);
    Eigen::VectorXd ubA_ineq = Eigen::VectorXd::Zero(16);  // Fr 在摩擦锥内: A*Fr <= 0

    // --- 力 Z 方向范围约束 ---
    Eigen::MatrixXd A_fz = Eigen::MatrixXd::Zero(4, QOO_WBC_QP_NV);
    Eigen::VectorXd lbA_fz = Eigen::VectorXd::Zero(4);
    Eigen::VectorXd ubA_fz = Eigen::VectorXd::Zero(4);
    // f_zL >= m_fzLow, f_zL <= m_fzUpp
    A_fz(0, 6 + 2) = 1.0;   lbA_fz(0) = m_fzLow;  ubA_fz(0) = m_fzUpp;
    // f_zR >= m_fzLow, f_zR <= m_fzUpp
    A_fz(1, 6 + 8) = 1.0; lbA_fz(1) = m_fzLow;  ubA_fz(1) = m_fzUpp;
    // -f_zL <= -m_fzLow  (即 f_zL >= m_fzLow, 已包含在上述)
    A_fz(2, 6 + 2) = -1.0; lbA_fz(2) = -m_fzUpp; ubA_fz(2) = -m_fzLow;
    A_fz(3, 6 + 8) = -1.0; lbA_fz(3) = -m_fzUpp; ubA_fz(3) = -m_fzLow;

    // --- 组总约束矩阵 ---
    Eigen::MatrixXd A_total = Eigen::MatrixXd::Zero(6 + 16 + 4, QOO_WBC_QP_NV);
    Eigen::VectorXd lbA_total = Eigen::VectorXd::Zero(6 + 16 + 4);
    Eigen::VectorXd ubA_total = Eigen::VectorXd::Zero(6 + 16 + 4);

    A_total.block(0, 0, 6, QOO_WBC_QP_NV) = A_eq;
    lbA_total.block<6, 1>(0, 0) = b_eq;
    ubA_total.block<6, 1>(0, 0) = b_eq;  // 等式约束: lbA = ubA = b

    A_total.block(6, 0, 16, QOO_WBC_QP_NV) = A_ineq;
    lbA_total.block<16, 1>(6, 0) = lbA_ineq;
    ubA_total.block<16, 1>(6, 0) = ubA_ineq;

    A_total.block(22, 0, 4, QOO_WBC_QP_NV) = A_fz;
    lbA_total.block<4, 1>(22, 0) = lbA_fz;
    ubA_total.block<4, 1>(22, 0) = ubA_fz;

    // --- 变量上下界 ---
    Eigen::VectorXd lb = Eigen::VectorXd::Constant(QOO_WBC_QP_NV, -1e15);
    Eigen::VectorXd ub = Eigen::VectorXd::Constant(QOO_WBC_QP_NV,  1e15);
    // Fr_delta 的 f_z 分量有下限 (避免拉力过大)
    lb(6 + 2) = -m_fzUpp;  ub(6 + 2) = -m_fzLow;   // 左足 f_z 是推力, 故为负
    lb(6 + 8) = -m_fzUpp;  ub(6 + 8) = -m_fzLow;   // 右足同上

    // === 调用 qpOASES ===
    copyEigenToRealT(m_qpH, H, QOO_WBC_QP_NV, QOO_WBC_QP_NV);
    copyEigenToRealT(m_qpg, g, QOO_WBC_QP_NV, 1);
    copyEigenToRealT(m_qpA, A_total, 6 + 16 + 4, QOO_WBC_QP_NV);
    copyEigenToRealT(m_qplbA, lbA_total, 6 + 16 + 4, 1);
    copyEigenToRealT(m_qpubA, ubA_total, 6 + 16 + 4, 1);

    int nWSR = 200;
    qpOASES::real_t cpuTime = m_dt;
    qpOASES::returnValue res;
    res = m_QP.init(m_qpH, m_qpg, m_qpA, NULL, NULL, m_qplbA, m_qpubA, nWSR, &cpuTime, m_xOptGuess);

    m_qpStatus = qpOASES::getSimpleStatus(res);
    if (res != qpOASES::SUCCESSFUL_RETURN) {
        std::cerr << "[WBC] QP solve failed! status=" << m_qpStatus << std::endl;
        // 降级: 使用 ddq_final 和 Fr_ff 直接计算力矩
        m_tauJointRes = m_dynM * m_ddqFinal + m_dynNon - m_Jfe.transpose() * m_FrFf;
        m_tauJointRes = m_tauJointRes.block(6, 0, m_modelNv - 6, 1);
        m_QP.reset();
        return;
    }

    qpOASES::real_t xOpt[QOO_WBC_QP_NV];
    m_QP.getPrimalSolution(xOpt);

    Eigen::VectorXd ddqBaseOpt(6), frDelta(12);
    for (int i = 0; i < 6; i++)  ddqBaseOpt(i) = xOpt[i];
    for (int i = 0; i < 12; i++) frDelta(i) = xOpt[6 + i];

    // --- 组最终加速度和接触力 ---
    m_ddqOpt = m_ddqFinal;
    m_ddqOpt.block<6, 1>(0, 0) += ddqBaseOpt;
    m_frOpt = m_FrFf + frDelta;

    // --- 计算关节力矩 ---
    Eigen::VectorXd tauRes = m_dynM * m_ddqOpt + m_dynNon - m_Jfe.transpose() * m_frOpt;
    m_tauJointRes = tauRes.block(6, 0, m_modelNv - 6, 1);

    m_QP.reset();
}

void QooBot_WBC::dataBusWrite(DataBus& data)
{
    data.wbc_ddq_final = m_ddqFinal;
    data.wbc_tauJointRes = m_tauJointRes;
    data.wbc_FrRes = m_frOpt;

    // 写入关节力矩指令
    int nAct = m_modelNv - 6;
    for (int i = 0; i < nAct; i++) {
        data.motors_tor_des[i] = m_tauJointRes(i);
    }
}

// === 辅助函数 ===
void QooBot_WBC::copyEigenToRealT(qpOASES::real_t* target, const Eigen::MatrixXd& source, int nRows, int nCols)
{
    int count = 0;
    for (int i = 0; i < nRows; i++) {
        for (int j = 0; j < nCols; j++) {
            target[count++] = source(i, j);
        }
    }
}

void QooBot_WBC::copyEigenToRealT(qpOASES::real_t* target, const Eigen::VectorXd& source, int nRows)
{
    for (int i = 0; i < nRows; i++) {
        target[i] = source(i);
    }
}
