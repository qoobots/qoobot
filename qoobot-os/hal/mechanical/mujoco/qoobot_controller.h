/*
============================================================================
QooBot Dynamics Control — Main Controller
============================================================================
Top-level controller orchestrating:
  MJ_Interface (sensors) -> DataBus -> StateEst -> MPC -> WBC -> PVT_Ctr -> MJ_Interface (actuators)

This controller wraps OpenLoong's MPC+WBC algorithm stack and adapts it
for the QooBot biped humanoid robot.

Control Pipeline:
  1. MJ_Interface reads sensor data from MuJoCo
  2. DataBus centralizes all state information
  3. StateEst estimates base pose/velocity
  4. JoystickInterpreter translates user commands
  5. GaitScheduler manages LSt/RSt/DSt state machine
  6. FootPlacement plans swing foot trajectories
  7. MPC computes optimal ground reaction forces
  8. WBC maps forces to joint torques via task prioritization
  9. PVT_Ctr applies PD control + torque limiting
  10. MJ_Interface sends torques back to MuJoCo

Based on OpenLoong Dyn-Control, adapted for QooBot.
============================================================================
*/
#pragma once

#include "MJ_interface.h"
#include "data_bus.h"
#include "PVT_ctrl.h"
#include "qoobot_mpc.h"
#include "qoobot_wbc.h"
#include <mujoco/mujoco.h>
#include <memory>

class QooBotController {
public:
    QooBotController(mjModel *m, mjData *d, const char *configPath = nullptr);
    ~QooBotController();

    // Main control loop callback (called every simulation step)
    void controlCallback();

    // Initialize controller state
    void init();

    // Set desired walking velocity (m/s forward, rad/s yaw)
    void setDesiredVelocity(double vx, double vy, double wz);

    // Set standing mode
    void stand();

    // Get current state for monitoring
    const DataBus &getDataBus() const { return *dataBus; }

private:
    mjModel *mj_model;
    mjData *mj_data;

    std::unique_ptr<MJ_Interface> mjInterface;
    std::unique_ptr<DataBus> dataBus;
    std::unique_ptr<PVT_Ctr> pvtCtr;

    double timeStep;
    int stepCount;

    // MPC & WBC algorithm instances
    std::unique_ptr<QooBot_MPC> mpc;
    std::unique_ptr<QooBot_WBC> wbc;

    // Control pipeline steps
    void stepStateEstimation();
    void stepGaitScheduler();
    void stepFootPlacement();
    void stepMPC();
    void stepWBC();
    void stepPVTControl();

    // MuJoCo dynamics & Jacobian computation
    void computeDynamics();
    void computeJacobians();

    // Gait parameters
    double tSwing{0.3};      // swing phase duration (s)
    double tStance{0.5};     // stance phase duration (s)
    double stepHeight{0.08}; // max foot clearance (m)
    double stepLength{0.15}; // step length (m)
};
