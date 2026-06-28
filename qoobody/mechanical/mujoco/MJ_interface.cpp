/*
============================================================================
QooBot Dynamics Control — MJ_Interface Implementation
============================================================================
Based on OpenLoong Dyn-Control, adapted for QooBot.
============================================================================
*/
#include "MJ_interface.h"
#include <iostream>
#include <cmath>

MJ_Interface::MJ_Interface(mjModel *mj_modelIn, mjData *mj_dataIn)
    : mj_model(mj_modelIn), mj_data(mj_dataIn)
{
    jointNum = JointName.size();
    motor_pos.assign(jointNum, 0);
    motor_pos_Old.assign(jointNum, 0);
    motor_vel.assign(jointNum, 0);

    // Get joint IDs
    for (int i = 0; i < jointNum; i++) {
        int jid = mj_name2id(mj_model, mjOBJ_JOINT, JointName[i].c_str());
        if (jid < 0) {
            std::cerr << "[MJ_Interface] ERROR: joint '" << JointName[i] << "' not found in model!" << std::endl;
        }
        jntId_qpos.push_back(mj_model->jnt_qposadr[jid]);
        jntId_qvel.push_back(mj_model->jnt_dofadr[jid]);
        int act_id = mj_name2id(mj_model, mjOBJ_ACTUATOR, ("M_" + JointName[i].substr(2)).c_str());
        // actuator_dynadr removed in newer MuJoCo; use actuator_trnid[0] for joint DOF address
        jntId_dctl.push_back(mj_model->jnt_dofadr[mj_model->actuator_trnid[2 * act_id]]);
    }

    // Get sensor IDs
    orientationSensorId = mj_name2id(mj_model, mjOBJ_SENSOR, orientationSensorName.c_str());
    velSensorId = mj_name2id(mj_model, mjOBJ_SENSOR, velSensorName.c_str());
    gyroSensorId = mj_name2id(mj_model, mjOBJ_SENSOR, gyroSensorName.c_str());
    accSensorId = mj_name2id(mj_model, mjOBJ_SENSOR, accSensorName.c_str());
    baseBodyId = mj_name2id(mj_model, mjOBJ_BODY, baseName.c_str());

    if (orientationSensorId < 0) std::cerr << "[MJ_Interface] WARNING: orientation sensor not found" << std::endl;
    if (velSensorId < 0) std::cerr << "[MJ_Interface] WARNING: velocity sensor not found" << std::endl;
    if (gyroSensorId < 0) std::cerr << "[MJ_Interface] WARNING: gyro sensor not found" << std::endl;
    if (accSensorId < 0) std::cerr << "[MJ_Interface] WARNING: accelerometer not found" << std::endl;

    std::cout << "[MJ_Interface] Initialized with " << jointNum << " joints" << std::endl;
}

void MJ_Interface::updateSensorValues()
{
    // Read joint positions and velocities
    for (int i = 0; i < jointNum; i++) {
        motor_pos_Old[i] = motor_pos[i];
        motor_pos[i] = mj_data->qpos[jntId_qpos[i]];
        motor_vel[i] = mj_data->qvel[jntId_qvel[i]];
    }

    // Read base orientation from framequat sensor (MuJoCo order: w,x,y,z)
    if (orientationSensorId >= 0) {
        double *sensordata = mj_data->sensordata;
        int adr = mj_model->sensor_adr[orientationSensorId];
        double qw = sensordata[adr];
        double qx = sensordata[adr + 1];
        double qy = sensordata[adr + 2];
        double qz = sensordata[adr + 3];

        // Convert quaternion [w,x,y,z] to RPY
        double sinr_cosp = 2 * (qw * qx + qy * qz);
        double cosr_cosp = 1 - 2 * (qx * qx + qy * qy);
        rpy[0] = std::atan2(sinr_cosp, cosr_cosp);

        double sinp = 2 * (qw * qy - qz * qx);
        if (std::abs(sinp) >= 1)
            rpy[1] = std::copysign(M_PI / 2, sinp);
        else
            rpy[1] = std::asin(sinp);

        double siny_cosp = 2 * (qw * qz + qx * qy);
        double cosy_cosp = 1 - 2 * (qy * qy + qz * qz);
        rpy[2] = std::atan2(siny_cosp, cosy_cosp);

        // Store as [x,y,z,w] for downstream use
        baseQuat[0] = qx;
        baseQuat[1] = qy;
        baseQuat[2] = qz;
        baseQuat[3] = qw;
    }

    // Read base position
    if (baseBodyId >= 0) {
        basePos[0] = mj_data->xpos[3 * baseBodyId];
        basePos[1] = mj_data->xpos[3 * baseBodyId + 1];
        basePos[2] = mj_data->xpos[3 * baseBodyId + 2];
    }

    // Read base linear velocity (world frame)
    if (velSensorId >= 0) {
        int adr = mj_model->sensor_adr[velSensorId];
        baseLinVel[0] = mj_data->sensordata[adr];
        baseLinVel[1] = mj_data->sensordata[adr + 1];
        baseLinVel[2] = mj_data->sensordata[adr + 2];
    }

    // Read base angular velocity (body frame)
    if (gyroSensorId >= 0) {
        int adr = mj_model->sensor_adr[gyroSensorId];
        baseAngVel[0] = mj_data->sensordata[adr];
        baseAngVel[1] = mj_data->sensordata[adr + 1];
        baseAngVel[2] = mj_data->sensordata[adr + 2];
    }

    // Read base acceleration (body frame)
    if (accSensorId >= 0) {
        int adr = mj_model->sensor_adr[accSensorId];
        baseAcc[0] = mj_data->sensordata[adr];
        baseAcc[1] = mj_data->sensordata[adr + 1];
        baseAcc[2] = mj_data->sensordata[adr + 2];
    }

    // Read foot contact forces from touch sensors
    int lf_sensor_id = mj_name2id(mj_model, mjOBJ_SENSOR, "lf-touch");
    int rf_sensor_id = mj_name2id(mj_model, mjOBJ_SENSOR, "rf-touch");

    if (lf_sensor_id >= 0) {
        int adr = mj_model->sensor_adr[lf_sensor_id];
        f3d[0][0] = mj_data->sensordata[adr];     // left foot force Z
        f3d[1][0] = mj_data->sensordata[adr + 1]; // left foot force X (shear)
        f3d[2][0] = mj_data->sensordata[adr + 2]; // left foot force Y (shear)
    }
    if (rf_sensor_id >= 0) {
        int adr = mj_model->sensor_adr[rf_sensor_id];
        f3d[0][1] = mj_data->sensordata[adr];
        f3d[1][1] = mj_data->sensordata[adr + 1];
        f3d[2][1] = mj_data->sensordata[adr + 2];
    }

    // Read foot-end positions in world frame
    int lfBodyId = mj_name2id(mj_model, mjOBJ_BODY, "Link_ankle_l_pitch");
    int rfBodyId = mj_name2id(mj_model, mjOBJ_BODY, "Link_ankle_r_pitch");

    if (lfBodyId >= 0) {
        feLPosW[0] = mj_data->xpos[3 * lfBodyId];
        feLPosW[1] = mj_data->xpos[3 * lfBodyId + 1];
        feLPosW[2] = mj_data->xpos[3 * lfBodyId + 2];
        // Rotation matrix (row-major, 3x3)
        for (int i = 0; i < 9; i++)
            feLRotW[i] = mj_data->xmat[9 * lfBodyId + i];
    }
    if (rfBodyId >= 0) {
        feRPosW[0] = mj_data->xpos[3 * rfBodyId];
        feRPosW[1] = mj_data->xpos[3 * rfBodyId + 1];
        feRPosW[2] = mj_data->xpos[3 * rfBodyId + 2];
        for (int i = 0; i < 9; i++)
            feRRotW[i] = mj_data->xmat[9 * rfBodyId + i];
    }

    if (!isIni) {
        for (int i = 0; i < jointNum; i++) {
            motor_pos_Old[i] = motor_pos[i];
        }
        isIni = true;
    }
}

void MJ_Interface::setMotorsTorque(std::vector<double> &tauIn)
{
    for (int i = 0; i < jointNum; i++) {
        mj_data->ctrl[i] = tauIn[i];
    }
}

void MJ_Interface::dataBusWrite(DataBus &busIn)
{
    // Write sensor data to DataBus
    busIn.rpy[0] = rpy[0];
    busIn.rpy[1] = rpy[1];
    busIn.rpy[2] = rpy[2];

    busIn.basePos[0] = basePos[0];
    busIn.basePos[1] = basePos[1];
    busIn.basePos[2] = basePos[2];

    busIn.baseLinVel[0] = baseLinVel[0];
    busIn.baseLinVel[1] = baseLinVel[1];
    busIn.baseLinVel[2] = baseLinVel[2];

    busIn.baseAcc[0] = baseAcc[0];
    busIn.baseAcc[1] = baseAcc[1];
    busIn.baseAcc[2] = baseAcc[2];

    busIn.baseAngVel[0] = baseAngVel[0];
    busIn.baseAngVel[1] = baseAngVel[1];
    busIn.baseAngVel[2] = baseAngVel[2];

    busIn.fL[0] = f3d[0][0];
    busIn.fL[1] = f3d[1][0];
    busIn.fL[2] = f3d[2][0];
    busIn.fR[0] = f3d[0][1];
    busIn.fR[1] = f3d[1][1];
    busIn.fR[2] = f3d[2][1];

    // Write foot-end positions in world frame
    busIn.fe_l_pos_W = Eigen::Vector3d(feLPosW[0], feLPosW[1], feLPosW[2]);
    busIn.fe_r_pos_W = Eigen::Vector3d(feRPosW[0], feRPosW[1], feRPosW[2]);

    // Write foot-end rotation matrices (world frame)
    busIn.fe_l_rot_W = Eigen::Map<Eigen::Matrix<double, 3, 3, Eigen::RowMajor>>(feLRotW);
    busIn.fe_r_rot_W = Eigen::Map<Eigen::Matrix<double, 3, 3, Eigen::RowMajor>>(feRRotW);

    for (int i = 0; i < jointNum; i++) {
        busIn.motors_pos_cur[i] = motor_pos[i];
        busIn.motors_vel_cur[i] = motor_vel[i];
    }
}
