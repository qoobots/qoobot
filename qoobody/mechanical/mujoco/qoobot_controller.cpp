/*
============================================================================
QooBot Dynamics Control — Main Controller Implementation (Updated)
============================================================================
Integrates OpenLoong's MPC+WBC algorithm stack for QooBot biped control.

Updates in this version:
  - stepMPC() now truly calls QooBot_MPC
  - stepWBC() now truly calls QooBot_WBC
  - Added MuJoCo dynamics/Jacobian computation
  - MPC and WBC are no longer empty placeholders

Based on OpenLoong Dyn-Control, adapted for QooBot.
============================================================================
*/
#include "qoobot_controller.h"
#include <iostream>
#include <cmath>
#include <algorithm>

QooBotController::QooBotController(mjModel *m, mjData *d, const char *configPath)
    : mj_model(m), mj_data(d), timeStep(m->opt.timestep), stepCount(0)
{
    mjInterface = std::make_unique<MJ_Interface>(m, d);
    int nv = m->nv;  // total DOFs including free joint
    dataBus = std::make_unique<DataBus>(nv);

    const char *cfgPath = configPath ? configPath : "joint_ctrl_config.json";
    pvtCtr = std::make_unique<PVT_Ctr>(timeStep, cfgPath);

    // --- Instantiate MPC and WBC ---
    mpc = std::make_unique<QooBot_MPC>(timeStep);
    wbc = std::make_unique<QooBot_WBC>(nv, timeStep);

    // Set MPC weights (state tracking + control effort)
    Eigen::MatrixXd L_diag = Eigen::MatrixXd::Zero(1, QOO_MPC_NX);
    L_diag(0, 0) = 100;  L_diag(0, 1) = 100;  L_diag(0, 2) = 500;  // rpy
    L_diag(0, 3) = 500; L_diag(0, 4) = 500; L_diag(0, 5) = 1000; // pos
    L_diag(0, 6) = 10;  L_diag(0, 7) = 10;  L_diag(0, 8) = 50;   // ang_vel
    L_diag(0, 9) = 50;  L_diag(0, 10)= 50;  L_diag(0, 11)= 100;  // lin_vel
    Eigen::MatrixXd K_diag = Eigen::MatrixXd::Zero(1, QOO_MPC_NU * QOO_MPC_CH);
    for (int i = 0; i < QOO_MPC_NU * QOO_MPC_CH; i++) K_diag(0, i) = 1.0;
    mpc->setWeight(0.1, L_diag, K_diag);

    std::cout << "[QooBotController] Initialized with MPC+WBC" << std::endl;
    std::cout << "  - Timestep: " << timeStep << " s" << std::endl;
    std::cout << "  - Total DOFs: " << nv << std::endl;
    std::cout << "  - Actuated DOFs: " << (nv - 6) << std::endl;
}

QooBotController::~QooBotController() = default;

void QooBotController::init()
{
    // Read initial sensor values
    mjInterface->updateSensorValues();
    mjInterface->dataBusWrite(*dataBus);
    dataBus->updateQ();

    // Initialize gait state: start in double support
    dataBus->motionState = DataBus::Stand;
    dataBus->legState = DataBus::DSt;
    dataBus->legStateNext = DataBus::LSt;
    dataBus->leg_contact[0] = true;
    dataBus->leg_contact[1] = true;

    // Set initial desired values to current state
    dataBus->base_pos_des << dataBus->basePos[0], dataBus->basePos[1], dataBus->basePos[2];
    dataBus->base_rpy_des << dataBus->rpy[0], dataBus->rpy[1], dataBus->rpy[2];
    dataBus->base_vel_des.setZero();
    dataBus->base_omega_des.setZero();

    // Initialize desired joint positions to current
    for (int i = 0; i < mjInterface->jointNum; i++) {
        dataBus->motors_pos_des[i] = dataBus->motors_pos_cur[i];
        dataBus->motors_vel_des[i] = 0.0;
        dataBus->motors_tor_des[i] = 0.0;
    }

    // PVT: feed current positions to avoid jump
    pvtCtr->dataBusRead(*dataBus);

    // Gait parameters
    dataBus->tSwing = tSwing;
    dataBus->width_hips = 0.24;

    // Enable MPC
    mpc->enable();

    std::cout << "[QooBotController] Initialization complete (MPC+WBC enabled)" << std::endl;
}

void QooBotController::controlCallback()
{
    stepCount++;

    // === Step 1: Read sensors ===
    mjInterface->updateSensorValues();
    mjInterface->dataBusWrite(*dataBus);
    dataBus->updateQ();

    // === Step 2: State Estimation ===
    stepStateEstimation();

    // === Step 3: Gait Scheduling ===
    stepGaitScheduler();

    // === Step 4: Foot Placement ===
    stepFootPlacement();

    // === Step 5: MPC (runs at 100Hz, every 10 steps) ===
    if (stepCount % 10 == 0) {
        stepMPC();
    }

    // === Step 6: WBC (runs every step) ===
    stepWBC();

    // === Step 7: PVT Joint Control ===
    stepPVTControl();

    // === Step 8: Send torques to MuJoCo ===
    mjInterface->setMotorsTorque(dataBus->motors_tor_out);
}

// === State Estimation (updated to fill DataBus properly) ===
void QooBotController::stepStateEstimation()
{
    dataBus->base_pos_est << dataBus->basePos[0], dataBus->basePos[1], dataBus->basePos[2];
    dataBus->base_vel_est << dataBus->baseLinVel[0], dataBus->baseLinVel[1], dataBus->baseLinVel[2];
    dataBus->eul_est << dataBus->rpy[0], dataBus->rpy[1], dataBus->rpy[2];
    dataBus->omegaW_est << dataBus->baseAngVel[0], dataBus->baseAngVel[1], dataBus->baseAngVel[2];

    // Detect foot contacts from force sensors
    dataBus->leg_contact[0] = (std::abs(dataBus->fL[2]) > 5.0);
    dataBus->leg_contact[1] = (std::abs(dataBus->fR[2]) > 5.0);
}

// === Gait Scheduler (unchanged) ===
void QooBotController::stepGaitScheduler()
{
    double t = stepCount * timeStep;
    double period = dataBus->tSwing + tStance;
    double phase = std::fmod(t, period);
    bool leftSwing = (phase < dataBus->tSwing);
    bool rightSwing = (phase >= period / 2.0) && (phase < period / 2.0 + dataBus->tSwing);

    if (dataBus->motionState == DataBus::Walk) {
        if (leftSwing && !rightSwing) {
            dataBus->legState = DataBus::RSt;
            dataBus->legStateNext = DataBus::LSt;
        } else if (rightSwing && !leftSwing) {
            dataBus->legState = DataBus::LSt;
            dataBus->legStateNext = DataBus::RSt;
        } else {
            dataBus->legState = DataBus::DSt;
        }
    } else {
        dataBus->legState = DataBus::DSt;
    }
}

// === Foot Placement (updated to fill DataBus) ===
void QooBotController::stepFootPlacement()
{
    if (dataBus->motionState != DataBus::Walk) return;

    double vx = dataBus->desV_W(0);
    double vy = dataBus->desV_W(1);
    double wz = dataBus->desWz_W;

    double k_vx = 0.5 * dataBus->tSwing;
    double k_vy = 0.3 * dataBus->tSwing;
    double k_wz = 0.2 * dataBus->tSwing;

    double halfStepX = vx * dataBus->tSwing * 0.5;
    double halfStepY = vy * dataBus->tSwing * 0.5;

    if (dataBus->legState == DataBus::RSt) {
        dataBus->swingDesPosFinal_W(0) = dataBus->posHip_W(0) + halfStepX;
        dataBus->swingDesPosFinal_W(1) = dataBus->posHip_W(1) + dataBus->width_hips / 2.0;
        dataBus->swingDesPosFinal_W(2) = 0.0;
    } else if (dataBus->legState == DataBus::LSt) {
        dataBus->swingDesPosFinal_W(0) = dataBus->posHip_W(0) + halfStepX;
        dataBus->swingDesPosFinal_W(1) = dataBus->posHip_W(1) - dataBus->width_hips / 2.0;
        dataBus->swingDesPosFinal_W(2) = 0.0;
    }

    // Update swing foot desired pos in DataBus
    dataBus->swing_fe_pos_des_W = dataBus->swingDesPosFinal_W;
}

// === MPC (NOW TRULY IMPLEMENTED) ===
void QooBotController::stepMPC()
{
    if (!mpc->isEnabled()) {
        dataBus->Fr_ff.setZero();
        return;
    }

    // --- Fill DataBus for MPC ---
    // (Already filled by updateQ() and stepFootPlacement())

    // Call MPC
    mpc->dataBusRead(*dataBus);
    mpc->solve();
    mpc->dataBusWrite(*dataBus);

    // Fr_ff is now set in DataBus
}

// === WBC (NOW TRULY IMPLEMENTED) ===
void QooBotController::stepWBC()
{
    // --- Compute dynamics and Jacobians using MuJoCo ---
    computeDynamics();
    computeJacobians();

    // --- Call WBC ---
    wbc->dataBusRead(*dataBus);
    wbc->computeDesAcc();
    wbc->computeTau();
    wbc->dataBusWrite(*dataBus);

    // motors_tor_des is now set in DataBus
    // Copy to motors_tor_out (with PVT filtering)
}

// === MuJoCo Dynamics Computation ===
void QooBotController::computeDynamics()
{
    // 使用 MuJoCo 前动力学计算:
    //   M = 质量矩阵, Non = C(q,dq)*dq + G(q) (科里奥利 + 重力)
    // 方法: 设 qacc=0, 调用 mj_inverse() → qfrc_inverse = Non
    int nv = mj_model->nv;

    // 1. 计算质量矩阵 M (mj_forward 会填充 d->qM)
    mj_forward(mj_model, mj_data);

    // 2. 将 MuJoCo 稀疏 M 转为稠密 Eigen 矩阵
    //    d->qM 是稠密格式 (mj_forward 后填充)
    Eigen::Map<Eigen::Matrix<double, -1, -1, Eigen::RowMajor>> M_map(
        mj_data->qM, nv, nv);
    dataBus->dyn_M = M_map.cast<double>();

    // 3. 计算 M_inv
    dataBus->dyn_M_inv = dataBus->dyn_M.inverse();

    // 4. 计算 Non = C*dq + G:
    //    设 qacc=0, 调用 mj_inverse() → qfrc_inverse = Non
    Eigen::VectorXd qacc_save = Eigen::Map<Eigen::VectorXd>(mj_data->qacc, nv);
    Eigen::Map<Eigen::VectorXd>(mj_data->qacc, nv).setZero();
    mj_inverse(mj_model, mj_data);
    dataBus->dyn_Non = Eigen::Map<Eigen::VectorXd>(mj_data->qfrc_inverse, nv).cast<double>();

    // 5. 恢复 qacc
    Eigen::Map<Eigen::VectorXd>(mj_data->qacc, nv) = qacc_save;

    // 6. dyn_Ag = C*dq (科里奥利项, 不含重力)
    //    Non = dyn_Ag + G, 但 MuJoCo 不分开存储, 这里省略 dyn_Ag
    //    WBC 中仅使用 dyn_M 和 dyn_Non, 故足够
}

// === MuJoCo Jacobian Computation ===
void QooBotController::computeJacobians()
{
    int nv = mj_model->nv;

    // --- 左/右足踝关节 ID ---
    int bodyIdL = mj_name2id(mj_model, mjOBJ_BODY, "Link_ankle_l_pitch");
    int bodyIdR = mj_name2id(mj_model, mjOBJ_BODY, "Link_ankle_r_pitch");
    if (bodyIdL < 0) std::cerr << "[WBC] Warning: left ankle body not found!" << std::endl;
    if (bodyIdR < 0) std::cerr << "[WBC] Warning: right ankle body not found!" << std::endl;

    // --- 足端雅可比 J_l, J_r (6 x nv) ---
    if (bodyIdL >= 0) {
        Eigen::VectorXd jacp = Eigen::VectorXd::Zero(3 * nv);
        Eigen::VectorXd jacr = Eigen::VectorXd::Zero(3 * nv);
        double point[3] = {0, 0, 0};
        mj_jac(mj_model, mj_data,
               jacp.data(), jacr.data(),
               point, bodyIdL);
        // 组合为 6 x nv: 前3行=位置, 后3行=旋转
        Eigen::Map<Eigen::Matrix<double, 3, -1, Eigen::RowMajor>> Jp_map(jacp.data(), 3, nv);
        Eigen::Map<Eigen::Matrix<double, 3, -1, Eigen::RowMajor>> Jr_map(jacr.data(), 3, nv);
        dataBus->J_l = Eigen::MatrixXd::Zero(6, nv);
        dataBus->J_l.block<3, -1>(0, 0) = Jp_map.cast<double>();
        dataBus->J_l.block<3, -1>(3, 0) = Jr_map.cast<double>();
    }
    if (bodyIdR >= 0) {
        Eigen::VectorXd jacp = Eigen::VectorXd::Zero(3 * nv);
        Eigen::VectorXd jacr = Eigen::VectorXd::Zero(3 * nv);
        double point[3] = {0, 0, 0};
        mj_jac(mj_model, mj_data,
               jacp.data(), jacr.data(),
               point, bodyIdR);
        Eigen::Map<Eigen::Matrix<double, 3, -1, Eigen::RowMajor>> Jp_map(jacp.data(), 3, nv);
        Eigen::Map<Eigen::Matrix<double, 3, -1, Eigen::RowMajor>> Jr_map(jacr.data(), 3, nv);
        dataBus->J_r = Eigen::MatrixXd::Zero(6, nv);
        dataBus->J_r.block<3, -1>(0, 0) = Jp_map.cast<double>();
        dataBus->J_r.block<3, -1>(3, 0) = Jr_map.cast<double>();
    }

    // --- 雅可比时间导数 dJ_l, dJ_r ---
    if (bodyIdL >= 0) {
        Eigen::VectorXd djacp = Eigen::VectorXd::Zero(3 * nv);
        Eigen::VectorXd djacr = Eigen::VectorXd::Zero(3 * nv);
        double point[3] = {0, 0, 0};
        mj_jacDot(mj_model, mj_data,
                   djacp.data(), djacr.data(),
                   point, bodyIdL);
        Eigen::Map<Eigen::Matrix<double, 3, -1, Eigen::RowMajor>> dJp_map(djacp.data(), 3, nv);
        Eigen::Map<Eigen::Matrix<double, 3, -1, Eigen::RowMajor>> dJr_map(djacr.data(), 3, nv);
        dataBus->dJ_l = Eigen::MatrixXd::Zero(6, nv);
        dataBus->dJ_l.block<3, -1>(0, 0) = dJp_map.cast<double>();
        dataBus->dJ_l.block<3, -1>(3, 0) = dJr_map.cast<double>();
    }
    if (bodyIdR >= 0) {
        Eigen::VectorXd djacp = Eigen::VectorXd::Zero(3 * nv);
        Eigen::VectorXd djacr = Eigen::VectorXd::Zero(3 * nv);
        double point[3] = {0, 0, 0};
        mj_jacDot(mj_model, mj_data,
                   djacp.data(), djacr.data(),
                   point, bodyIdR);
        Eigen::Map<Eigen::Matrix<double, 3, -1, Eigen::RowMajor>> dJp_map(djacp.data(), 3, nv);
        Eigen::Map<Eigen::Matrix<double, 3, -1, Eigen::RowMajor>> dJr_map(djacr.data(), 3, nv);
        dataBus->dJ_r = Eigen::MatrixXd::Zero(6, nv);
        dataBus->dJ_r.block<3, -1>(0, 0) = dJp_map.cast<double>();
        dataBus->dJ_r.block<3, -1>(3, 0) = dJr_map.cast<double>();
    }

    // --- 基座雅可比 J_base = [I6x6, 0] ---
    dataBus->J_base = Eigen::MatrixXd::Zero(6, nv);
    dataBus->J_base.block<6, 6>(0, 0) = Eigen::Matrix<double, 6, 6>::Identity();
    dataBus->dJ_base = Eigen::MatrixXd::Zero(6, nv);  // 浮动基座 dJ_base ≈ 0

    // --- CoM 雅可比 (mj_jacCom removed in newer MuJoCo; approximate via subtree_com) ---
    dataBus->Jcom_W = Eigen::MatrixXd::Zero(3, nv);
    dataBus->Jcom_W.block<3, 3>(0, 0) = Eigen::Matrix3d::Identity();  // base lin vel ≈ CoM vel
    dataBus->pCoM_W = Eigen::Vector3d(
        mj_data->subtree_com[0],
        mj_data->subtree_com[1],
        mj_data->subtree_com[2]);
}

// === PVT Control (unchanged) ===
void QooBotController::stepPVTControl()
{
    pvtCtr->dataBusRead(*dataBus);
    pvtCtr->calMotorsPVT();
    pvtCtr->dataBusWrite(*dataBus);
}

void QooBotController::setDesiredVelocity(double vx, double vy, double wz)
{
    dataBus->desV_W << vx, vy, 0;
    dataBus->desWz_W = wz;
    if (std::abs(vx) > 0.01 || std::abs(vy) > 0.01 || std::abs(wz) > 0.01) {
        dataBus->motionState = DataBus::Walk;
    } else {
        dataBus->motionState = DataBus::Stand;
    }
}

void QooBotController::stand()
{
    dataBus->motionState = DataBus::Stand;
    dataBus->desV_W.setZero();
    dataBus->desWz_W = 0.0;
}
