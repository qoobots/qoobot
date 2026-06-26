/*
============================================================================
QooBot Dynamics Control — Walk Demo (MPC + WBC)
============================================================================
Main simulation executable: loads QooBot MuJoCo model, runs MPC+WBC
controller, and renders the simulation with GLFW.

Usage:
  ./walk_mpc_wbc [model_path]

Default model: qoobot_float.xml

Controls:
  W/S      - Forward/Backward velocity
  A/D      - Left/Right velocity
  Q/E      - Yaw rotation
  Space    - Stand still
  Esc      - Exit

Based on OpenLoong Dyn-Control walk_mpc_wbc.cpp, adapted for QooBot.
============================================================================
*/
#include "qoobot_controller.h"
#include <mujoco/mujoco.h>
#include <GLFW/glfw3.h>
#include <iostream>
#include <string>
#include <chrono>
#include <thread>

// GLFW callbacks
static mjModel *g_model = nullptr;
static mjData *g_data = nullptr;
static QooBotController *g_controller = nullptr;
static bool g_paused = false;
static bool g_exit = false;

void keyboardCallback(GLFWwindow *window, int key, int scancode, int act, int mods)
{
    if (act == GLFW_PRESS || act == GLFW_REPEAT) {
        switch (key) {
        case GLFW_KEY_ESCAPE:
            g_exit = true;
            break;
        case GLFW_KEY_SPACE:
            g_controller->stand();
            std::cout << "[Control] Standing" << std::endl;
            break;
        case GLFW_KEY_W:
            g_controller->setDesiredVelocity(0.3, 0.0, 0.0);
            std::cout << "[Control] Walk forward 0.3 m/s" << std::endl;
            break;
        case GLFW_KEY_S:
            g_controller->setDesiredVelocity(-0.2, 0.0, 0.0);
            std::cout << "[Control] Walk backward 0.2 m/s" << std::endl;
            break;
        case GLFW_KEY_A:
            g_controller->setDesiredVelocity(0.0, 0.15, 0.0);
            std::cout << "[Control] Walk left 0.15 m/s" << std::endl;
            break;
        case GLFW_KEY_D:
            g_controller->setDesiredVelocity(0.0, -0.15, 0.0);
            std::cout << "[Control] Walk right 0.15 m/s" << std::endl;
            break;
        case GLFW_KEY_Q:
            g_controller->setDesiredVelocity(0.0, 0.0, 0.5);
            std::cout << "[Control] Turn left" << std::endl;
            break;
        case GLFW_KEY_E:
            g_controller->setDesiredVelocity(0.0, 0.0, -0.5);
            std::cout << "[Control] Turn right" << std::endl;
            break;
        case GLFW_KEY_P:
            g_paused = !g_paused;
            std::cout << "[Sim] " << (g_paused ? "Paused" : "Running") << std::endl;
            break;
        }
    }
}

int main(int argc, char **argv)
{
    std::cout << "==================================================" << std::endl;
    std::cout << "  QooBot Dynamics Control - Walk Demo" << std::endl;
    std::cout << "  MPC + WBC Biped Locomotion" << std::endl;
    std::cout << "  Based on OpenLoong Dyn-Control" << std::endl;
    std::cout << "==================================================" << std::endl;

    // Load model
    std::string modelPath = "qoobot_float.xml";
    if (argc > 1) modelPath = argv[1];

    char error[1000] = "";
    mjModel *m = mj_loadXML(modelPath.c_str(), nullptr, error, 1000);
    if (!m) {
        std::cerr << "[ERROR] Failed to load model: " << error << std::endl;
        return 1;
    }
    g_model = m;

    mjData *d = mj_makeData(m);
    if (!d) {
        std::cerr << "[ERROR] Failed to create data" << std::endl;
        mj_deleteModel(m);
        return 1;
    }
    g_data = d;

    std::cout << "[Model] Loaded: " << modelPath << std::endl;
    std::cout << "  - Bodies: " << m->nbody << std::endl;
    std::cout << "  - Joints: " << m->njnt << std::endl;
    std::cout << "  - DOFs: " << m->nv << std::endl;
    std::cout << "  - Actuators: " << m->nu << std::endl;

    // Initialize GLFW
    if (!glfwInit()) {
        std::cerr << "[ERROR] Failed to initialize GLFW" << std::endl;
        mj_deleteData(d);
        mj_deleteModel(m);
        return 1;
    }

    GLFWwindow *window = glfwCreateWindow(1200, 900, "QooBot - MPC+WBC Walk Demo", nullptr, nullptr);
    if (!window) {
        std::cerr << "[ERROR] Failed to create GLFW window" << std::endl;
        glfwTerminate();
        mj_deleteData(d);
        mj_deleteModel(m);
        return 1;
    }

    glfwMakeContextCurrent(window);
    glfwSetKeyCallback(window, keyboardCallback);

    // Initialize MuJoCo visualization
    mjvCamera cam;
    mjvOption opt;
    mjvScene scn;
    mjrContext con;

    mjv_defaultCamera(&cam);
    mjv_defaultOption(&opt);
    mjv_defaultScene(&scn);
    mjr_defaultContext(&con);

    mjv_makeScene(m, &scn, 2000);
    mjr_makeContext(m, &con, mjFONTSCALE_150);

    cam.distance = 3.0;
    cam.lookat[0] = 0.0;
    cam.lookat[1] = 0.0;
    cam.lookat[2] = 1.0;
    cam.elevation = -15;
    cam.azimuth = 160;

    // Initialize controller
    QooBotController controller(m, d);
    g_controller = &controller;
    controller.init();

    std::cout << std::endl;
    std::cout << "Controls:" << std::endl;
    std::cout << "  W/S     - Forward/Backward" << std::endl;
    std::cout << "  A/D     - Left/Right" << std::endl;
    std::cout << "  Q/E     - Turn Left/Right" << std::endl;
    std::cout << "  Space   - Stand still" << std::endl;
    std::cout << "  P       - Pause/Resume" << std::endl;
    std::cout << "  Esc     - Exit" << std::endl;
    std::cout << std::endl;

    // Main simulation loop
    double simTime = 0.0;
    auto lastPrint = std::chrono::steady_clock::now();

    while (!glfwWindowShouldClose(window) && !g_exit) {
        // Physics step
        if (!g_paused) {
            controller.controlCallback();
            mj_step(m, d);
            simTime += m->opt.timestep;
        }

        // Periodic status print
        auto now = std::chrono::steady_clock::now();
        if (std::chrono::duration_cast<std::chrono::seconds>(now - lastPrint).count() >= 1) {
            lastPrint = now;
            const auto &bus = controller.getDataBus();
            std::cout << "\r[Time: " << std::fixed << std::setprecision(2) << simTime
                      << "s] BasePos: (" << std::setprecision(3) << bus.basePos[0]
                      << ", " << bus.basePos[1] << ", " << bus.basePos[2]
                      << ") RPY: (" << bus.rpy[0] << ", " << bus.rpy[1] << ", " << bus.rpy[2]
                      << ")  " << std::flush;
        }

        // Render
        mjv_updateScene(m, d, &opt, nullptr, &cam, mjCAT_ALL, &scn);
        mjrRect viewport = {0, 0, 0, 0};
        glfwGetFramebufferSize(window, &viewport.width, &viewport.height);
        mjr_render(viewport, &scn, &con);

        glfwSwapBuffers(window);
        glfwPollEvents();
    }

    std::cout << std::endl << "[Sim] Shutting down..." << std::endl;

    // Cleanup
    mjv_freeScene(&scn);
    mjr_freeContext(&con);
    mj_deleteData(d);
    mj_deleteModel(m);
    glfwDestroyWindow(window);
    glfwTerminate();

    return 0;
}
