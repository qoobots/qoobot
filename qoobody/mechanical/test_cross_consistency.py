#!/usr/bin/env python3
"""
QooBot 双足机器人模型一致性检查
===================================
验证：
  1. joint_ctrl_config.json 与 qoobot_float.xml 关节名一致性
  2. STL mesh 文件是否全部被 XML 引用
  3. 执行器力矩参数与 QJ 系列模组规格对照
"""

import xml.etree.ElementTree as ET
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MUJOCO_DIR = os.path.join(SCRIPT_DIR, "mujoco")
XML_PATH = os.path.join(MUJOCO_DIR, "qoobot_float.xml")
CONFIG_PATH = os.path.join(MUJOCO_DIR, "joint_ctrl_config.json")
MESHES_DIR = os.path.join(MUJOCO_DIR, "meshes")

ERRORS = []
WARNINGS = []


def error(msg):
    ERRORS.append(msg)
    print(f"  [ERROR] {msg}")


def warning(msg):
    WARNINGS.append(msg)
    print(f"  [WARN]  {msg}")


def info(msg):
    print(f"  [INFO]  {msg}")


def check_config_vs_xml():
    """检查 joint_ctrl_config.json 与 MuJoCo XML 的关节一致性"""
    print("\n--- 1. joint_ctrl_config.json ↔ qoobot_float.xml ---")

    if not os.path.exists(CONFIG_PATH):
        error(f"配置文件不存在: {CONFIG_PATH}")
        return None, None
    if not os.path.exists(XML_PATH):
        error(f"XML 文件不存在: {XML_PATH}")
        return None, None

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    tree = ET.parse(XML_PATH)
    root = tree.getroot()

    # 收集 XML 中所有关节
    xml_joints = set()
    for elem in root.iter("joint"):
        name = elem.get("name")
        if name:
            xml_joints.add(name)

    # 收集 XML 中所有电机
    xml_motors = set()
    for elem in root.iter("motor"):
        joint = elem.get("joint")
        if joint:
            xml_motors.add(joint)

    config_joints = set(config.keys())

    info(f"config.json 关节数: {len(config_joints)}")
    info(f"MuJoCo XML 关节数: {len(xml_joints)}")
    info(f"MuJoCo XML 电机数: {len(xml_motors)}")

    # 交叉对比
    only_config = config_joints - xml_joints
    only_xml = xml_joints - config_joints
    config_no_motor = config_joints - xml_motors
    motor_no_config = xml_motors - config_joints

    if only_config:
        error(f"config 中有但 XML 中无对应关节: {only_config}")
    else:
        info("config.json → XML 关节: 完全匹配 ✓")

    if config_no_motor:
        warning(f"config 中有但 XML 中无对应电机: {config_no_motor}")
    else:
        info("config.json → XML 电机: 完全匹配 ✓")

    if motor_no_config:
        warning(f"XML 中有电机但 config 中无配置: {motor_no_config}")

    if only_xml:
        info(f"XML 中无 config 配置的关节 (含 freejoint/被动等): {only_xml}")

    return config, root


def check_mesh_usage(root):
    """检查 STL mesh 文件使用情况"""
    print("\n--- 2. STL Mesh 文件引用完整性 ---")
    if root is None:
        return

    # 收集 XML 中引用的所有 mesh 文件
    xml_meshes = set()
    for elem in root.iter("mesh"):
        file = elem.get("file")
        if file:
            xml_meshes.add(file)

    info(f"XML 中引用的 mesh: {len(xml_meshes)}")

    # 检查 meshes/ 目录
    if not os.path.isdir(MESHES_DIR):
        warning(f"Meshes 目录不存在: {MESHES_DIR}")
        return

    stl_files = [f for f in os.listdir(MESHES_DIR) if f.lower().endswith('.stl')]
    info(f"meshes/ 目录 STL 文件: {len(stl_files)}")

    # 缺失引用
    missing = []
    for mesh_file in xml_meshes:
        full = os.path.join(MESHES_DIR, mesh_file)
        if not os.path.isfile(full):
            # 大小写不敏感匹配
            found = False
            for stl in stl_files:
                if stl.lower() == mesh_file.lower():
                    found = True
                    break
            if not found:
                missing.append(mesh_file)

    # 未使用文件
    unused = [f for f in stl_files if f not in xml_meshes]

    if missing:
        for m in missing:
            error(f"XML 引用但文件缺失: {m}")
    else:
        info("所有 XML 引用的 mesh 文件均存在 ✓")

    if unused:
        for u in unused:
            warning(f"未使用的 STL 文件: {u}")


def check_torque_vs_modules():
    """检查执行器力矩与 QJ 系列模组规格对照"""
    print("\n--- 3. 电机力矩 vs QJ 模组规格 ---")

    QJ_SPECS = {
        "QJ-05":  {"torque": 5,    "mass": 0.3,  "diameter": 45,  "use": "手指/腕部"},
        "QJ-20":  {"torque": 20,   "mass": 0.8,  "diameter": 65,  "use": "肘部"},
        "QJ-50":  {"torque": 50,   "mass": 1.5,  "diameter": 85,  "use": "肩部横滚/偏航"},
        "QJ-100": {"torque": 100,  "mass": 3.0,  "diameter": 110, "use": "肩部俯仰/腰部"},
        "QJ-200": {"torque": 200,  "mass": 5.5,  "diameter": 140, "use": "髋部/膝部"},
    }

    if not os.path.exists(XML_PATH):
        return

    tree = ET.parse(XML_PATH)
    root = tree.getroot()

    motors = []
    for m in root.iter("motor"):
        name = m.get("name", "?")
        joint = m.get("joint", "?")
        ctrlrange_str = m.get("ctrlrange", "0 0")
        try:
            parts = ctrlrange_str.split()
            max_torque = max(abs(float(parts[0])), abs(float(parts[1])))
        except (ValueError, IndexError):
            max_torque = 0
        motors.append((name, joint, max_torque))

    info(f"电机总数: {len(motors)}")

    for name, joint, torque in sorted(motors, key=lambda x: -x[2]):
        # 找到匹配的 QJ 规格
        best_match = None
        for qj_name, spec in sorted(QJ_SPECS.items(), key=lambda x: -x[1]["torque"]):
            if torque <= spec["torque"] * 1.2:  # 20% 余量
                best_match = (qj_name, spec)

        if best_match:
            qj_name, spec = best_match
            ratio = torque / spec["torque"] * 100
            print(f"  {joint:25s}  {torque:6.1f} Nm → {qj_name} ({spec['torque']} Nm, {ratio:.0f}% 利用率, {spec['use']})")
        else:
            print(f"  {joint:25s}  {torque:6.1f} Nm → 超出 QJ-200 规格，需定制")


def main():
    print("=" * 60)
    print("  QooBot 双足机器人一致性检查")
    print("=" * 60)

    config, xml_root = check_config_vs_xml()
    check_mesh_usage(xml_root)
    check_torque_vs_modules()

    print(f"\n{'=' * 60}")
    print(f"  检查结果: {len(ERRORS)} 错误, {len(WARNINGS)} 警告")
    print(f"{'=' * 60}")
    if ERRORS:
        print("\n错误列表:")
        for e in ERRORS:
            print(f"  ✗ {e}")
    if WARNINGS:
        print("\n警告列表:")
        for w in WARNINGS:
            print(f"  ⚠ {w}")

    if ERRORS:
        return 1
    print("  ✓ 交叉一致性检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
