/*
============================================================================
QooBot MPC — Implementation (Complete qpOASES integration)
============================================================================
*/
#include "qoobot_mpc.h"
#include <iostream>
#include <cmath>

QooBot_MPC::QooBot_MPC(double dtIn)
    : m_dt(dtIn), m_QP(QOO_MPC_NU * QOO_MPC_CH, QOO_MPC_NC * QOO_MPC_CH)
{
    // 机器人参数 (QooBot ≈ OpenLoong 青龙)
    m_mass = 77.35;
    m_gravity = -9.8;
    m_miu = 0.5;

    // 足部接触尺寸 (近似 OpenLoong)
    m_deltaFoot[0] = 0.073;  // +x 半长
    m_deltaFoot[1] = 0.125;  // -x 半长
    m_deltaFoot[2] = 0.025;  // +y 半宽
    m_deltaFoot[3] = 0.025;  // -y 半宽

    // CoM 转动惯量 (近似 OpenLoong)
    m_Ic << 12.61, 0, 0.37,
              0, 11.15, 0.01,
              0.37, 0.01, 2.15;

    // 初始化 SRBM 矩阵
    for (int i = 0; i < QOO_MPC_N; i++) {
        m_Ac[i].setZero();
        m_Bc[i].setZero();
        m_A[i].setZero();
        m_B[i].setZero();
    }
    m_Aqp.setZero();
    m_Aqp1.setZero();
    m_Bqp1.setZero();
    m_Bqp.setZero();
    m_Cqp1.setZero();
    m_Cqp.setZero();

    m_Ufe.setZero();
    m_Ufe_pre.setZero();
    m_Xcur.setZero();
    m_Xcal.setZero();
    m_dXcal.setZero();

    m_L = Eigen::MatrixXd::Zero(QOO_MPC_NX * QOO_MPC_N, QOO_MPC_NX * QOO_MPC_N);
    m_K = Eigen::MatrixXd::Zero(QOO_MPC_NU * QOO_MPC_CH, QOO_MPC_NU * QOO_MPC_CH);
    m_H.setZero();
    m_c.setZero();

    m_uLow.setZero();
    m_uUpp.setZero();
    m_As.setZero();
    m_bs.setZero();

    // 力极限 (与 OpenLoong 一致)
    m_max[0] = 1000.0;  m_min[0] = -1000.0;
    m_max[1] = 1000.0;  m_min[1] = -1000.0;
    m_max[2] = -3.0 * m_mass * m_gravity;  m_min[2] = 0.0;
    m_max[3] = 20.0;   m_min[3] = -20.0;
    m_max[4] = 80.0;   m_min[4] = -80.0;
    m_max[5] = 100.0;  m_min[5] = -100.0;

    // qpOASES 配置
    qpOASES::Options options;
    options.printLevel = qpOASES::PL_LOW;
    m_QP.setOptions(options);
}

void QooBot_MPC::setWeight(double u_weight, const Eigen::MatrixXd& L_diag, const Eigen::MatrixXd& K_diag)
{
    m_alpha = u_weight;

    // 构造块对角权重矩阵
    m_L.setZero();
    m_K.setZero();

    for (int i = 0; i < QOO_MPC_N; i++) {
        for (int j = 0; j < QOO_MPC_NX; j++) {
            m_L(i * QOO_MPC_NX + j, i * QOO_MPC_NX + j) = L_diag(0, j);
        }
    }
    for (int i = 0; i < QOO_MPC_NU * QOO_MPC_CH; i++) {
        m_K(i, i) = K_diag(0, i);
    }

    // 旋转位置/速度权重到机体坐标系 (仅偏航)
    for (int i = 0; i < QOO_MPC_N; i++) {
        m_L.block<3, 3>(i * QOO_MPC_NX + 3, i * QOO_MPC_NX + 3) =
            m_Rcurz[i] * m_L.block<3, 3>(i * QOO_MPC_NX + 3, i * QOO_MPC_NX + 3) * m_Rcurz[i].transpose();
        m_L.block<3, 3>(i * QOO_MPC_NX + 6, i * QOO_MPC_NX + 6) =
            m_Rcurz[i] * m_L.block<3, 3>(i * QOO_MPC_NX + 6, i * QOO_MPC_NX + 6) * m_Rcurz[i].transpose();
        m_L.block<3, 3>(i * QOO_MPC_NX + 9, i * QOO_MPC_NX + 9) =
            m_Rcurz[i] * m_L.block<3, 3>(i * QOO_MPC_NX + 9, i * QOO_MPC_NX + 9) * m_Rcurz[i].transpose();
    }
}

void QooBot_MPC::dataBusRead(const DataBus& data)
{
    // 读取状态: X_cur = [rpy(3); pos(3); ang_vel(3); lin_vel(3)]
    m_Xcur.block<3, 1>(0, 0) = data.base_rpy;
    m_Xcur.block<3, 1>(3, 0) = data.base_pos;
    m_Xcur.block<3, 1>(6, 0) = data.dq.block<3, 1>(3, 0);  // 角速度
    m_Xcur.block<3, 1>(9, 0) = data.dq.block<3, 1>(0, 0);  // 线速度

    // 读取期望轨迹 Xd (从 joystick 指令生成)
    if (m_enabled) {
        for (int i = 0; i < QOO_MPC_N - 1; i++) {
            m_Xdes.block<QOO_MPC_NX, 1>(QOO_MPC_NX * i, 0) =
                m_Xdes.block<QOO_MPC_NX, 1>(QOO_MPC_NX * (i + 1), 0);
        }
        // 最后一个时刻的期望值从 joystick 指令来
        for (int j = 0; j < 3; j++) {
            m_Xdes(QOO_MPC_NX * (QOO_MPC_N - 1) + j) = data.js_eul_des(j);
            m_Xdes(QOO_MPC_NX * (QOO_MPC_N - 1) + 3 + j) = data.js_pos_des(j);
        }
    } else {
        for (int i = 0; i < QOO_MPC_N; i++) {
            m_Xdes.block<QOO_MPC_NX, 1>(QOO_MPC_NX * i, 0) = m_Xcur;
        }
    }

    // 足部位置
    m_pe.block<3, 1>(0, 0) = data.fe_l_pos_W;
    m_pe.block<3, 1>(3, 0) = data.fe_r_pos_W;
    m_pCoM = m_Xcur.block<3, 1>(3, 0);
    m_pf2com.block<3, 1>(0, 0) = m_pe.block<3, 1>(0, 0) - m_pCoM;
    m_pf2com.block<3, 1>(3, 0) = m_pe.block<3, 1>(3, 0) - m_pCoM;

    // 旋转矩阵
    m_Rcur = eul2Rot(data.base_rpy(0), data.base_rpy(1), data.base_rpy(2));
    for (int i = 0; i < QOO_MPC_N; i++) {
        m_Rcurz[i] = Rz3(m_Xcur(2));  // 仅偏航角
    }

    // 步态状态
    m_legStateCur = data.legState;
    m_legStateNext = data.legStateNext;
    m_phi = data.phi;

    // 预测步态状态
    for (int i = 0; i < QOO_MPC_N; i++) {
        double aa = i * m_dt / 0.4;
        double phip = m_phi + aa;
        if (phip > 1.0)
            m_legState[i] = m_legStateNext;
        else
            m_legState[i] = m_legStateCur;
    }

    // 机体到足部坐标系旋转
    if (m_legStateCur == DataBus::RSt)
        m_Rf2w = data.fe_r_rot_W;
    else if (m_legStateCur == DataBus::LSt)
        m_Rf2w = data.fe_l_rot_W;
    else
        m_Rf2w = Eigen::Matrix3d::Identity();
    m_Rw2f = m_Rf2w.transpose();
}

void QooBot_MPC::solve()
{
    if (!m_enabled) {
        m_Ufe.setZero();
        m_Ufe(2) = -0.5 * m_mass * m_gravity;
        m_Ufe(8) = -0.5 * m_mass * m_gravity;
        m_Ufe(12) = m_mass * m_gravity;
        return;
    }

    // === 构建 SRBM 离散化 ===
    for (int i = 0; i < QOO_MPC_N; i++) {
        m_Ac[i].block<3, 3>(0, 6) = m_Rcurz[i].transpose();
        m_A[i] = Eigen::Matrix<double, QOO_MPC_NX, QOO_MPC_NX>::Identity() + m_dt * m_Ac[i];
    }
    for (int i = 0; i < QOO_MPC_N; i++) {
        Eigen::Matrix3d Ic_W_inv = (m_Rcurz[i] * m_Ic * m_Rcurz[i].transpose()).inverse();
        m_Bc[i].block<3, 3>(6, 0) = Ic_W_inv * CrossProduct_A(m_pf2com.block<3, 1>(0, 0));
        m_Bc[i].block<3, 3>(6, 3) = Ic_W_inv;
        m_Bc[i].block<3, 3>(6, 6) = Ic_W_inv * CrossProduct_A(m_pf2com.block<3, 1>(3, 0));
        m_Bc[i].block<3, 3>(6, 9) = Ic_W_inv;
        m_Bc[i].block<3, 3>(9, 0) = Eigen::Matrix3d::Identity() / m_mass;
        m_Bc[i].block<3, 3>(9, 6) = Eigen::Matrix3d::Identity() / m_mass;
        m_Bc[i](QOO_MPC_NX - 1, QOO_MPC_NU - 1) = 1.0 / m_mass;
        m_B[i] = m_dt * m_Bc[i];
    }

    // === 构建 QP 矩阵 Aqp, Bqp ===
    for (int i = 0; i < QOO_MPC_N; i++)
        m_Aqp.block<QOO_MPC_NX, QOO_MPC_NX>(i * QOO_MPC_NX, 0) =
            Eigen::Matrix<double, QOO_MPC_NX, QOO_MPC_NX>::Identity();
    for (int i = 0; i < QOO_MPC_N; i++)
        for (int j = 0; j < i + 1; j++)
            m_Aqp.block<QOO_MPC_NX, QOO_MPC_NX>(i * QOO_MPC_NX, 0) =
                m_A[j] * m_Aqp.block<QOO_MPC_NX, QOO_MPC_NX>(i * QOO_MPC_NX, 0);

    for (int i = 0; i < QOO_MPC_N; i++)
        m_Aqp1.block<QOO_MPC_NX, QOO_MPC_NX>(i * QOO_MPC_NX, i * QOO_MPC_NX) =
            Eigen::Matrix<double, QOO_MPC_NX, QOO_MPC_NX>::Identity();
    for (int i = 1; i < QOO_MPC_N; i++)
        for (int j = 0; j < i; j++)
            for (int k = j + 1; k < i + 1; k++)
                m_Aqp1.block<QOO_MPC_NX, QOO_MPC_NX>(i * QOO_MPC_NX, j * QOO_MPC_NX) =
                    m_A[k] * m_Aqp1.block<QOO_MPC_NX, QOO_MPC_NX>(i * QOO_MPC_NX, j * QOO_MPC_NX);

    for (int i = 0; i < QOO_MPC_N; i++)
        m_Bqp1.block<QOO_MPC_NX, QOO_MPC_NU>(i * QOO_MPC_NX, i * QOO_MPC_NU) = m_B[i];

    Eigen::MatrixXd Bqp11 = Eigen::MatrixXd::Zero(QOO_MPC_NU * QOO_MPC_N, QOO_MPC_NU * QOO_MPC_CH);
    Bqp11.block<QOO_MPC_NU * QOO_MPC_CH, QOO_MPC_NU * QOO_MPC_CH>(0, 0) =
        Eigen::MatrixXd::Identity(QOO_MPC_NU * QOO_MPC_CH, QOO_MPC_NU * QOO_MPC_CH);
    for (int i = 0; i < (QOO_MPC_N - QOO_MPC_CH); i++)
        Bqp11.block<QOO_MPC_NU, QOO_MPC_NU>(QOO_MPC_NU * QOO_MPC_CH + i * QOO_MPC_NU, QOO_MPC_NU * (QOO_MPC_CH - 1)) =
            Eigen::MatrixXd::Identity(QOO_MPC_NU, QOO_MPC_NU);

    Eigen::MatrixXd B_tmp = Eigen::MatrixXd::Zero(QOO_MPC_NX * QOO_MPC_N, QOO_MPC_NU * QOO_MPC_CH);
    B_tmp = m_Bqp1 * Bqp11;
    m_Bqp = m_Aqp1 * B_tmp;

    // === 期望控制增量 (重力补偿基准) ===
    Eigen::Matrix<double, QOO_MPC_NU * QOO_MPC_CH, 1> delta_U;
    delta_U.setZero();
    for (int i = 0; i < QOO_MPC_CH; i++) {
        if (m_legState[i] == DataBus::LSt) {
            delta_U(QOO_MPC_NU * i + 2) = m_mass * m_gravity;
        } else if (m_legState[i] == DataBus::RSt) {
            delta_U(QOO_MPC_NU * i + 8) = m_mass * m_gravity;
        } else {
            delta_U(QOO_MPC_NU * i + 2) = 0.5 * m_mass * m_gravity;
            delta_U(QOO_MPC_NU * i + 8) = 0.5 * m_mass * m_gravity;
        }
    }

    m_H = 2.0 * (m_Bqp.transpose() * m_L * m_Bqp + m_alpha * m_K) + 1e-10 * Eigen::MatrixXd::Identity(QOO_MPC_NU * QOO_MPC_CH, QOO_MPC_NU * QOO_MPC_CH);
    m_c = 2.0 * m_Bqp.transpose() * m_L * (m_Aqp * m_Xcur - m_Xdes) + 2.0 * m_alpha * m_K * delta_U;

    // === 构建约束矩阵 ===
    // 1. 摩擦金字塔约束
    Eigen::Matrix<double, QOO_NCFR_SINGLE, 3> Asfr111, Asfr11;
    Eigen::Matrix<double, QOO_NCFR_SINGLE, QOO_MPC_NU / 2> Asfr1_single;
    Eigen::Matrix<double, QOO_NCFR, QOO_MPC_NU> Asfr;
    Asfr111 << -1.0, 0.0, -1.0 / sqrt(2.0) * m_miu,
                1.0, 0.0, -1.0 / sqrt(2.0) * m_miu,
                0.0, -1.0, -1.0 / sqrt(2.0) * m_miu,
                0.0,  1.0, -1.0 / sqrt(2.0) * m_miu;
    Asfr11 = Asfr111 * m_Rw2f;
    Asfr1_single.setZero();
    Asfr1_single.block<QOO_NCFR_SINGLE, 3>(0, 0) = Asfr11;
    Asfr1_single.block<QOO_NCFR_SINGLE, 3>(0, 6) = Asfr11;
    Asfr.setZero();
    for (int i = 0; i < QOO_MPC_CH; i++)
        Asfr.block<QOO_NCFR, QOO_MPC_NU>(QOO_NCFR * i, i * QOO_MPC_NU) = Asfr1_single;

    // 2. XY 力矩约束
    double sign_xy[4] = {1.0, -1.0, -1.0, 1.0};
    Eigen::Matrix<double, 3, 1> gxyz[4];
    gxyz[0] << 0.0, 1.0, 0.0;
    gxyz[1] << 0.0, 1.0, 0.0;
    gxyz[2] << 1.0, 0.0, 0.0;
    gxyz[3] << 1.0, 0.0, 0.0;
    Eigen::Matrix<double, 3, 1> r[4], p[4];
    r[0] << 0.0, 1.0, 0.0;  r[1] << 0.0, 1.0, 0.0;
    r[2] << 1.0, 0.0, 0.0;  r[3] << 1.0, 0.0, 0.0;
    p[0] << m_deltaFoot[0], 0.0, 0.0;  p[1] << -m_deltaFoot[1], 0.0, 0.0;
    p[2] << 0.0, m_deltaFoot[2], 0.0;  p[3] << 0.0, -m_deltaFoot[3], 0.0;

    Eigen::Matrix<double, QOO_NCSTXY_A, 6> Astxy_r[4];
    Eigen::Matrix<double, QOO_NCSTXY_SINGLE, 6> Astxy11;
    Eigen::Matrix<double, QOO_NCSTXY, QOO_MPC_NU> Astxy1;
    Eigen::Matrix<double, QOO_NCSTXY * QOO_MPC_CH, QOO_MPC_NU * QOO_MPC_CH> Astxy;
    Astxy11.setZero(); Astxy1.setZero(); Astxy.setZero();
    for (int i = 0; i < 4; i++) {
        Astxy_r[i].setZero();
        Astxy_r[i].block<1, 3>(0, 0) =
            sign_xy[i] * gxyz[i].transpose() * m_Rw2f * m_Rf2w * r[i] * (m_Rf2w * r[i]).transpose() *
            CrossProduct_A(m_Rf2w * p[i]);
        Astxy_r[i].block<1, 3>(0, 3) = sign_xy[i] * gxyz[i].transpose() * m_Rw2f;
        Astxy11.block<QOO_NCSTXY_A, 6>(i * QOO_NCSTXY_A, 0) = Astxy_r[i];
    }
    Astxy1.block<QOO_NCSTXY_SINGLE, 6>(0, 0) = Astxy11;
    Astxy1.block<QOO_NCSTXY_SINGLE, 6>(QOO_NCSTXY_SINGLE, 6) = Astxy11;
    for (int i = 0; i < QOO_MPC_CH; i++)
        Astxy.block<QOO_NCSTXY, QOO_MPC_NU>(QOO_NCSTXY * i, i * QOO_MPC_NU) = Astxy1;

    // 3. Z 力矩约束
    Eigen::Matrix<double, QOO_NCSTZ_A, 6> Astz_r[4];
    Eigen::Matrix<double, QOO_NCSTZ_SINGLE, 6> Astz11;
    Eigen::Matrix<double, QOO_NCSTZ, QOO_MPC_NU> Astz1;
    Eigen::Matrix<double, QOO_NCSTZ * QOO_MPC_CH, QOO_MPC_NU * QOO_MPC_CH> Astz;
    Astz11.setZero(); Astz1.setZero(); Astz.setZero();
    for (int i = 0; i < 4; i++) {
        Astz_r[i].setZero();
        Astz_r[i].block<1, 3>(0, 0) = -sqrt(p[i](0)*p[i](0) + p[i](1)*p[i](1) + p[i](2)*p[i](2)) * m_miu *
                                          Eigen::Matrix<double, 1, 3>(0.0, 0.0, 1.0) * m_Rw2f;
        Astz_r[i].block<1, 3>(0, 3) = Eigen::Matrix<double, 1, 3>(0.0, 0.0, 1.0) * m_Rw2f;
        Astz_r[i].block<1, 3>(1, 0) = Astz_r[i].block<1, 3>(0, 0);
        Astz_r[i].block<1, 3>(1, 3) = -1.0 * Astz_r[i].block<1, 3>(0, 3);
        Astz11.block<QOO_NCSTZ_A, 6>(i * QOO_NCSTZ_A, 0) = Astz_r[i];
    }
    Astz1.block<QOO_NCSTZ_SINGLE, 6>(0, 0) = Astz11;
    Astz1.block<QOO_NCSTZ_SINGLE, 6>(QOO_NCSTZ_SINGLE, 6) = Astz11;
    for (int i = 0; i < QOO_MPC_CH; i++)
        Astz.block<QOO_NCSTZ, QOO_MPC_NU>(QOO_NCSTZ * i, i * QOO_MPC_NU) = Astz1;

    // 合成为总约束矩阵
    m_As.setZero();
    m_As.block<QOO_NCFR * QOO_MPC_CH, QOO_MPC_NU * QOO_MPC_CH>(0, 0) = Asfr;
    m_As.block<QOO_NCSTXY * QOO_MPC_CH, QOO_MPC_NU * QOO_MPC_CH>(QOO_NCFR * QOO_MPC_CH, 0) = Astxy;
    m_As.block<QOO_NCSTZ * QOO_MPC_CH, QOO_MPC_NU * QOO_MPC_CH>(QOO_NCFR * QOO_MPC_CH + QOO_NCSTXY * QOO_MPC_CH, 0) = Astz;

    m_bs.setZero();

    // === 设置变量上下界 ===
    Eigen::Matrix<double, QOO_MPC_NU * QOO_MPC_CH, 1> Guess_value;
    Guess_value.setZero();
    for (int i = 0; i < QOO_MPC_CH; i++) {
        if (m_legState[i] == DataBus::DSt) {
            Guess_value(i * QOO_MPC_NU + 2) = -0.5 * m_mass * m_gravity;
            Guess_value(i * QOO_MPC_NU + 8) = -0.5 * m_mass * m_gravity;
            Guess_value(i * QOO_MPC_NU + 12) = m_mass * m_gravity;
            for (int j = 0; j < 6; j++) {
                m_uLow(i * QOO_MPC_NU + j) = m_min[j];
                m_uLow(i * QOO_MPC_NU + j + 6) = m_min[j];
                m_uUpp(i * QOO_MPC_NU + j) = m_max[j];
                m_uUpp(i * QOO_MPC_NU + j + 6) = m_max[j];
            }
            m_uLow(i * QOO_MPC_NU + 12) = m_mass * m_gravity;
            m_uUpp(i * QOO_MPC_NU + 12) = m_mass * m_gravity;
        } else if (m_legState[i] == DataBus::LSt) {
            Guess_value(i * QOO_MPC_NU + 2) = -m_mass * m_gravity;
            Guess_value(i * QOO_MPC_NU + 8) = 0.0;
            Guess_value(i * QOO_MPC_NU + 12) = m_mass * m_gravity;
            for (int j = 0; j < 6; j++) {
                m_uLow(i * QOO_MPC_NU + j) = m_min[j];
                m_uLow(i * QOO_MPC_NU + j + QOO_MPC_NU / 2) = 0.0;
                m_uUpp(i * QOO_MPC_NU + j) = m_max[j];
                m_uUpp(i * QOO_MPC_NU + j + QOO_MPC_NU / 2) = 0.0;
            }
            m_uLow(i * QOO_MPC_NU + 12) = m_mass * m_gravity;
            m_uUpp(i * QOO_MPC_NU + 12) = m_mass * m_gravity;
        } else if (m_legState[i] == DataBus::RSt) {
            Guess_value(i * QOO_MPC_NU + 2) = 0.0;
            Guess_value(i * QOO_MPC_NU + 8) = -m_mass * m_gravity;
            Guess_value(i * QOO_MPC_NU + 12) = m_mass * m_gravity;
            for (int j = 0; j < 6; j++) {
                m_uLow(i * QOO_MPC_NU + j) = 0.0;
                m_uLow(i * QOO_MPC_NU + j + QOO_MPC_NU / 2) = m_min[j];
                m_uUpp(i * QOO_MPC_NU + j) = 0.0;
                m_uUpp(i * QOO_MPC_NU + j + QOO_MPC_NU / 2) = m_max[j];
            }
            m_uLow(i * QOO_MPC_NU + 12) = m_mass * m_gravity;
            m_uUpp(i * QOO_MPC_NU + 12) = m_mass * m_gravity;
        }
    }

    // === 设置约束上下界 ===
    Eigen::Matrix<double, QOO_MPC_NC * QOO_MPC_CH, 1> lbA, ubA, one_ch;
    one_ch.setOnes();
    lbA = -1e7 * one_ch;
    ubA = 1e7 * one_ch;
    for (int i = 0; i < QOO_MPC_CH; i++) {
        if (m_legState[i] == DataBus::DSt) {
            ubA.block<QOO_NCFR, 1>(QOO_NCFR * i, 0).setZero();
            ubA.block<QOO_NCSTXY, 1>(QOO_NCFR * QOO_MPC_CH + QOO_NCSTXY * i, 0).setZero();
            ubA.block<QOO_NCSTZ, 1>(QOO_NCFR * QOO_MPC_CH + QOO_NCSTXY * QOO_MPC_CH + QOO_NCSTZ * i, 0).setZero();
        } else if (m_legState[i] == DataBus::LSt) {
            ubA.block<QOO_NCFR_SINGLE, 1>(QOO_NCFR * i, 0).setZero();
            ubA.block<QOO_NCSTXY_SINGLE, 1>(QOO_NCFR * QOO_MPC_CH + QOO_NCSTXY * i, 0).setZero();
            ubA.block<QOO_NCSTZ_SINGLE, 1>(QOO_NCFR * QOO_MPC_CH + QOO_NCSTXY * QOO_MPC_CH + QOO_NCSTZ * i, 0).setZero();
        } else if (m_legState[i] == DataBus::RSt) {
            ubA.block<QOO_NCFR_SINGLE, 1>(QOO_NCFR * i + QOO_NCFR_SINGLE, 0).setZero();
            ubA.block<QOO_NCSTXY_SINGLE, 1>(QOO_NCFR * QOO_MPC_CH + QOO_NCSTXY * i + QOO_NCSTXY_SINGLE, 0).setZero();
            ubA.block<QOO_NCSTZ_SINGLE, 1>(QOO_NCFR * QOO_MPC_CH + QOO_NCSTXY * QOO_MPC_CH + QOO_NCSTZ * i + QOO_NCSTZ_SINGLE, 0).setZero();
        }
    }

    // === 调用 qpOASES ===
    copyEigenToRealT(m_qpH, m_H, QOO_MPC_NU * QOO_MPC_CH, QOO_MPC_NU * QOO_MPC_CH);
    copyEigenToRealT(m_qpc, m_c, QOO_MPC_NU * QOO_MPC_CH, 1);
    copyEigenToRealT(m_qpAs, m_As, QOO_MPC_NC * QOO_MPC_CH, QOO_MPC_NU * QOO_MPC_CH);
    copyEigenToRealT(m_qplbA, lbA, QOO_MPC_NC * QOO_MPC_CH, 1);
    copyEigenToRealT(m_qpubA, ubA, QOO_MPC_NC * QOO_MPC_CH, 1);
    copyEigenToRealT(m_qplu, m_uLow, QOO_MPC_NU * QOO_MPC_CH, 1);
    copyEigenToRealT(m_qpuu, m_uUpp, QOO_MPC_NU * QOO_MPC_CH, 1);
    copyEigenToRealT(m_xOptGuess, Guess_value, QOO_MPC_NU * QOO_MPC_CH, 1);

    int nWSR = 100000;
    qpOASES::real_t cpuTime = m_dt;
    qpOASES::returnValue res;
    res = m_QP.init(m_qpH, m_qpc, m_qpAs, m_qplu, m_qpuu, m_qplbA, m_qpubA, nWSR, &cpuTime, m_xOptGuess);

    m_qpStatus = qpOASES::getSimpleStatus(res);
    if (res != qpOASES::SUCCESSFUL_RETURN) {
        std::cerr << "[MPC] QP solve failed! status=" << m_qpStatus << std::endl;
        // 降级: 使用重力补偿
        m_Ufe.setZero();
        if (m_legStateCur == DataBus::DSt) {
            m_Ufe(2) = -0.5 * m_mass * m_gravity;
            m_Ufe(8) = -0.5 * m_mass * m_gravity;
        } else if (m_legStateCur == DataBus::LSt) {
            m_Ufe(2) = -m_mass * m_gravity;
        } else {
            m_Ufe(8) = -m_mass * m_gravity;
        }
        m_Ufe(12) = m_mass * m_gravity;
        m_QP.reset();
        return;
    }

    qpOASES::real_t xOpt[QOO_MPC_NU * QOO_MPC_CH];
    m_QP.getPrimalSolution(xOpt);
    for (int i = 0; i < QOO_MPC_NU * QOO_MPC_CH; i++)
        m_Ufe(i) = xOpt[i];

    // 计算预测状态
    m_dXcal = m_Ac[0] * m_Xcur + m_Bc[0] * m_Ufe.block<QOO_MPC_NU, 1>(0, 0);
    Eigen::Matrix<double, QOO_MPC_NX, 1> delta_X;
    delta_X.setZero();
    for (int i = 0; i < 3; i++) {
        delta_X(i) = 0.5 * m_dXcal(i + 6) * m_dt * m_dt;
        delta_X(i + 3) = 0.5 * m_dXcal(i + 9) * m_dt * m_dt;
        delta_X(i + 6) = m_dXcal(i + 6) * m_dt;
        delta_X(i + 9) = m_dXcal(i + 9) * m_dt;
    }
    m_Xcal = (m_Aqp * m_Xcur + m_Bqp * m_Ufe).block<QOO_MPC_NX, 1>(QOO_MPC_NX * 0, 0) + delta_X;
    m_Ufe_pre = m_Ufe.block<QOO_MPC_NU, 1>(0, 0);

    m_QP.reset();
}

void QooBot_MPC::dataBusWrite(DataBus& data)
{
    data.Fr_ff = m_Ufe.block<12, 1>(0, 0);
    // 写入期望加速度 (用于 WBC)
    data.des_ddq.block<2, 1>(0, 0) << m_dXcal(9), m_dXcal(10);
    data.des_dq.block<3, 1>(0, 0) << m_Xdes(9), m_Xdes(10), m_Xdes(11);
    data.base_rpy_des << 0.0, 0.0, m_Xdes(2);
    data.base_pos_des << m_Xdes(3), m_Xdes(4), m_Xdes(5);
}

void QooBot_MPC::copyEigenToRealT(qpOASES::real_t* target, const Eigen::MatrixXd& source, int nRows, int nCols)
{
    int count = 0;
    for (int i = 0; i < nRows; i++) {
        for (int j = 0; j < nCols; j++) {
            target[count++] = source(i, j);
        }
    }
}
