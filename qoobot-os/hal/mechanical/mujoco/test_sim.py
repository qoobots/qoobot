"""
QooBot MuJoCo 仿真测试脚本 (带行走控制器)
加载 qoobot_float.xml 模型，运行 MPC+WBC 闭环行走控制，GLFW 渲染可视化。
"""
import os
import sys
import time
import mujoco
import glfw
import numpy as np

# 切换到脚本所在目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qoobot_walking_controller import QooBotWalkingController

MODEL_PATH = "qoobot_float.xml"


def load_model():
    """加载 MuJoCo 模型"""
    if not os.path.exists(MODEL_PATH):
        print(f"[ERROR] 模型文件不存在: {MODEL_PATH}")
        return None, None
    print(f"[INFO] 加载模型: {MODEL_PATH}")
    model = mujoco.MjModel.from_xml_path(MODEL_PATH)
    data = mujoco.MjData(model)
    return model, data


def print_model_info(model):
    """打印模型信息"""
    print("=" * 60)
    print("  QooBot 双足仿生人 - MuJoCo 模型信息")
    print("=" * 60)
    print(f"  - 刚体数量 (nbody):     {model.nbody}")
    print(f"  - 关节数量 (njnt):      {model.njnt}")
    print(f"  - 自由度 (nv):          {model.nv}")
    print(f"  - 执行器数量 (nu):      {model.nu}")
    print(f"  - 时间步长 (timestep):  {model.opt.timestep:.4f} s")
    print(f"  - 重力:                 {model.opt.gravity}")
    print()


def run_simulation(model, data):
    """运行物理仿真，集成行走控制器"""
    # 初始化 GLFW
    if not glfw.init():
        print("[ERROR] GLFW 初始化失败")
        return

    window = glfw.create_window(1200, 900, "QooBot - MPC+WBC 行走仿真", None, None)
    if not window:
        print("[ERROR] GLFW 窗口创建失败")
        glfw.terminate()
        return

    glfw.make_context_current(window)
    glfw.swap_interval(1)

    # 初始化 MuJoCo 渲染
    scene = mujoco.MjvScene(model, maxgeom=2000)
    context = mujoco.MjrContext(model, mujoco.mjtFontScale.mjFONTSCALE_150)
    camera = mujoco.MjvCamera()
    option = mujoco.MjvOption()

    mujoco.mjv_defaultCamera(camera)
    mujoco.mjv_defaultOption(option)

    camera.distance = 3.0
    camera.lookat[:] = [0.0, 0.0, 1.0]
    camera.elevation = -15
    camera.azimuth = 160

    # ── 鼠标交互 ──
    button_left = False
    button_middle = False
    button_right = False
    last_x = 0
    last_y = 0
    scroll_y = 0.0

    def mouse_button_callback(window, button, action, mods):
        nonlocal button_left, button_middle, button_right, last_x, last_y
        is_press = (action == glfw.PRESS)
        if button == glfw.MOUSE_BUTTON_LEFT:
            button_left = is_press
        elif button == glfw.MOUSE_BUTTON_MIDDLE:
            button_middle = is_press
        elif button == glfw.MOUSE_BUTTON_RIGHT:
            button_right = is_press
        last_x, last_y = glfw.get_cursor_pos(window)

    def mouse_move_callback(window, x, y):
        nonlocal last_x, last_y
        dx = x - last_x
        dy = y - last_y
        last_x, last_y = x, y
        if not (button_left or button_middle or button_right):
            return
        width, height = glfw.get_framebuffer_size(window)
        if width <= 0 or height <= 0:
            return
        mod_shift = (glfw.get_key(window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS or
                     glfw.get_key(window, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS)
        mod_ctrl = (glfw.get_key(window, glfw.KEY_LEFT_CONTROL) == glfw.PRESS or
                    glfw.get_key(window, glfw.KEY_RIGHT_CONTROL) == glfw.PRESS)
        if button_right:
            action_type = mujoco.mjtMouse.mjMOUSE_MOVE_V if mod_shift else mujoco.mjtMouse.mjMOUSE_MOVE_H
        elif button_middle or (button_left and mod_ctrl):
            action_type = mujoco.mjtMouse.mjMOUSE_ZOOM
        elif button_left:
            action_type = mujoco.mjtMouse.mjMOUSE_ROTATE_V if mod_shift else mujoco.mjtMouse.mjMOUSE_ROTATE_H
        else:
            return
        mujoco.mjv_moveCamera(model, action_type, dx / width, dy / height, scene, camera)

    def scroll_callback(window, xoffset, yoffset):
        nonlocal scroll_y
        scroll_y = yoffset

    glfw.set_mouse_button_callback(window, mouse_button_callback)
    glfw.set_cursor_pos_callback(window, mouse_move_callback)
    glfw.set_scroll_callback(window, scroll_callback)

    # ── 行走控制器 ──
    controller = QooBotWalkingController(model, data)
    controller.control_mode = 'position'

    # ── 仿真状态 ──
    paused = False
    sim_time = 0.0
    step_count = 0
    last_print = time.time()
    space_pressed_prev = False
    w_pressed_prev = False
    s_pressed_prev = False
    key1_pressed_prev = False

    print()
    print("=" * 60)
    print("  QooBot MPC+WBC 行走仿真")
    print("  鼠标左键拖拽: 旋转  |  滚轮: 缩放  |  右键拖拽: 平移")
    print("  [W] 前进  [S] 停止  [A/D] 转向")
    print("  [1] 切换 position/torque 模式")
    print("  [Space] 暂停/恢复  [Esc] 退出")
    print("=" * 60)
    print()

    # 设置初始站立姿态
    print("[INFO] 初始化站立姿态...")
    from qoobot_robot_params import STAND_POSE
    for jname, angle in STAND_POSE.items():
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
        if jid >= 0:
            qpos_addr = model.jnt_qposadr[jid]
            if qpos_addr >= 0:
                data.qpos[qpos_addr] = angle

    data.qpos[2] = 1.0  # 基座高度

    # 初始化接触稳定
    print("[INFO] 初始化接触稳定...")
    for _ in range(200):
        controller.step()
        mujoco.mj_step(model, data)

    controller.stop()

    while not glfw.window_should_close(window):
        # 滚轮缩放
        if scroll_y != 0.0:
            mujoco.mjv_moveCamera(model, mujoco.mjtMouse.mjMOUSE_ZOOM,
                                  0.0, -0.05 * scroll_y, scene, camera)
            scroll_y = 0.0

        # ── 键盘处理 ──
        space_pressed = (glfw.get_key(window, glfw.KEY_SPACE) == glfw.PRESS)
        if space_pressed and not space_pressed_prev:
            paused = not paused
            print(f"[Sim] {'暂停' if paused else '运行中'}")
        space_pressed_prev = space_pressed

        if glfw.get_key(window, glfw.KEY_ESCAPE) == glfw.PRESS:
            break

        # W/S: 前进/停止
        w_pressed = (glfw.get_key(window, glfw.KEY_W) == glfw.PRESS)
        if w_pressed and not w_pressed_prev:
            print("[Cmd] 前进 0.3 m/s")
            controller.set_velocity(0.3, 0.0, 0.0)
        w_pressed_prev = w_pressed

        s_pressed = (glfw.get_key(window, glfw.KEY_S) == glfw.PRESS)
        if s_pressed and not s_pressed_prev:
            print("[Cmd] 停止")
            controller.stop()
        s_pressed_prev = s_pressed

        # A/D: 转向
        if glfw.get_key(window, glfw.KEY_A) == glfw.PRESS:
            controller.set_velocity(0.1, 0.0, 0.3)
        if glfw.get_key(window, glfw.KEY_D) == glfw.PRESS:
            controller.set_velocity(0.1, 0.0, -0.3)

        # 1: 切换控制模式
        key_1 = (glfw.get_key(window, glfw.KEY_1) == glfw.PRESS)
        if key_1 and not key1_pressed_prev:
            new_mode = controller.toggle_control_mode()
            print(f"[Ctrl] 切换到 {new_mode} 模式")
        key1_pressed_prev = key_1

        if not paused:
            # ── 控制器 ──
            controller.step()

            # ── 物理仿真 ──
            mujoco.mj_step(model, data)
            sim_time += model.opt.timestep
            step_count += 1

        # 每秒打印状态
        now = time.time()
        if now - last_print >= 1.0:
            last_print = now
            base_pos = data.qpos[0:3]
            base_quat = data.qpos[3:7]
            rpy = np.zeros(3)
            mujoco.mju_quat2Vel(rpy, base_quat, 1.0)

            try:
                lf_touch = data.sensor("lf-touch").data[0]
                rf_touch = data.sensor("rf-touch").data[0]
            except Exception:
                lf_touch = rf_touch = 0.0

            gait = controller.gait
            mode_str = controller.control_mode
            print(f"\r[Time: {sim_time:6.2f}s | {mode_str} | {gait.leg_state} phi={gait.phi:.2f}] "
                  f"H: {base_pos[2]:.3f} "
                  f"LF:{lf_touch:.0f} RF:{rf_touch:.0f}",
                  end="", flush=True)

        # 渲染
        viewport = mujoco.MjrRect(0, 0, 0, 0)
        viewport.width, viewport.height = glfw.get_framebuffer_size(window)
        mujoco.mjv_updateScene(model, data, option, None, camera,
                               mujoco.mjtCatBit.mjCAT_ALL, scene)
        mujoco.mjr_render(viewport, scene, context)
        glfw.swap_buffers(window)
        glfw.poll_events()

    print(f"\n[Sim] 仿真结束。总时间: {sim_time:.2f}s, 总步数: {step_count}")
    glfw.terminate()


def main():
    print("╔" + "═" * 58 + "╗")
    print("║" + "  QooBot MPC+WBC Walking Simulation              ".center(56) + "║")
    print("║" + "  双足仿生人 (30 DOF) 闭环行走控制              ".center(56) + "║")
    print("╚" + "═" * 58 + "╝")
    print()

    model, data = load_model()
    if model is None:
        return 1

    print_model_info(model)

    try:
        run_simulation(model, data)
    except KeyboardInterrupt:
        print("\n[Sim] 用户中断")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
