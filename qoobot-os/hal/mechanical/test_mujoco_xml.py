#!/usr/bin/env python3
"""
QooBot MuJoCo 双足仿生人模型 — 结构检查
==========================================
解析 qoobot_float.xml，验证：
  - XML 语法正确性
  - 运动学树完整性
  - Mesh 文件引用完整性
  - Joint/Actuator/Sensor 配置完整性
  - 与 joint_ctrl_config.json 的交叉一致性
"""

import xml.etree.ElementTree as ET
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MUJOCO_DIR = os.path.join(SCRIPT_DIR, "mujoco")
XML_PATH = os.path.join(MUJOCO_DIR, "qoobot_float.xml")
MESHES_DIR = os.path.join(MUJOCO_DIR, "meshes")
CONFIG_PATH = os.path.join(MUJOCO_DIR, "joint_ctrl_config.json")

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


def check_xml_syntax():
    """解析 XML 检查语法"""
    print("\n--- 1. XML 语法解析 ---")
    try:
        tree = ET.parse(XML_PATH)
        root = tree.getroot()
        info(f"根元素: <{root.tag}> model='{root.get('model', 'N/A')}'")
        return root
    except ET.ParseError as e:
        error(f"XML 解析失败: {e}")
        return None
    except FileNotFoundError:
        error(f"文件不存在: {XML_PATH}")
        return None


def check_meshes(root):
    """检查 mesh 资源引用完整性"""
    print("\n--- 2. Mesh 资源引用 ---")
    if root is None:
        return
    asset = root.find("asset")
    if asset is None:
        warning("未找到 <asset> 元素")
        return

    existing_meshes = set()
    if os.path.isdir(MESHES_DIR):
        for f in os.listdir(MESHES_DIR):
            if f.lower().endswith('.stl'):
                existing_meshes.add(f)
                # also add without extension for matching
                existing_meshes.add(os.path.splitext(f)[0])
    else:
        warning(f"Meshes 目录不存在: {MESHES_DIR}")

    declared_meshes = []
    missing_files = []
    for mesh_elem in asset.findall("mesh"):
        name = mesh_elem.get("name", "?")
        file = mesh_elem.get("file", "?")
        declared_meshes.append((name, file))
        # check file exists on disk
        full_path = os.path.join(MESHES_DIR, file)
        if not os.path.isfile(full_path):
            # try case-insensitive
            found = False
            if os.path.isdir(MESHES_DIR):
                for f in os.listdir(MESHES_DIR):
                    if f.lower() == file.lower():
                        found = True
                        break
            if not found:
                missing_files.append((name, file))

    info(f"声明 mesh 数量: {len(declared_meshes)}")
    info(f"meshes/ 目录下 STL 数量: {len([f for f in os.listdir(MESHES_DIR) if f.lower().endswith('.stl')]) if os.path.isdir(MESHES_DIR) else 0}")

    if missing_files:
        for name, file in missing_files:
            error(f"Mesh 文件缺失: {name} -> {file}")
    else:
        info("所有 mesh 文件引用有效 ✓")

    # check for unused STL files
    if os.path.isdir(MESHES_DIR):
        used_files = {m[1] for m in declared_meshes}
        for f in os.listdir(MESHES_DIR):
            if f.lower().endswith('.stl') and f not in used_files:
                warning(f"未使用的 STL 文件: {f}")

    return declared_meshes


def parse_kinematic_tree(root):
    """递归解析运动学树"""
    if root is None:
        return [], []

    worldbody = root.find("worldbody")
    if worldbody is None:
        error("未找到 <worldbody> 元素")
        return [], []

    bodies = []
    joints = []

    def walk(body_elem, parent_name="world", depth=0):
        name = body_elem.get("name", "unnamed")
        pos = body_elem.get("pos", "0 0 0")
        bodies.append({"name": name, "parent": parent_name, "depth": depth})

        for child in body_elem:
            if child.tag == "joint":
                jname = child.get("name", "?")
                jtype = child.get("type", child.tag)
                axis = child.get("axis", "?")
                limited = child.get("limited", "false")
                range_val = child.get("range", "?")
                joints.append({
                    "name": jname,
                    "parent_body": name,
                    "type": jtype,
                    "axis": axis,
                    "limited": limited == "true",
                    "range": range_val,
                })
            elif child.tag == "body":
                walk(child, name, depth + 1)

    for child in worldbody:
        if child.tag == "body":
            walk(child, "world", 0)

    return bodies, joints


def check_kinematic_tree(root):
    """检查运动学树完整性"""
    print("\n--- 3. 运动学树 ---")
    if root is None:
        return

    bodies, joints = parse_kinematic_tree(root)
    body_names = {b["name"] for b in bodies}
    joint_names = {j["name"] for j in joints}

    info(f"Body 数量: {len(bodies)}")
    info(f"Joint 数量: {len(joints)}")

    # 检查是否有孤立 body
    for b in bodies:
        if b["parent"] != "world" and b["parent"] not in body_names:
            error(f"孤立 body: {b['name']} (parent '{b['parent']}' 不存在)")

    # 检查 freejoint
    freejoint_count = sum(1 for j in joints if j.get("type") == "freejoint")
    info(f"浮动基座 (freejoint): {freejoint_count}")

    # 运动 DOF 计算: freejoint 贡献 6, 其他各贡献 1
    dof = freejoint_count * 6 + (len(joints) - freejoint_count)
    info(f"总自由度 (DOF): {dof}")

    # 树结构深度
    max_depth = max(b["depth"] for b in bodies) if bodies else 0
    info(f"运动学树最大深度: {max_depth}")

    # 打印树结构
    print("\n  运动学树结构:")
    for b in bodies:
        indent = "  " * (b["depth"] + 1)
        body_joints = [j for j in joints if j["parent_body"] == b["name"]]
        joint_str = ""
        if body_joints:
            jnames = [j["name"] for j in body_joints]
            joint_str = f" [{', '.join(jnames)}]"
        print(f"  {indent}└── {b['name']}{joint_str}")

    return bodies, joints


def check_actuators(root):
    """检查执行器配置"""
    print("\n--- 4. 执行器 (Actuators) ---")
    if root is None:
        return

    actuator = root.find("actuator")
    if actuator is None:
        warning("未找到 <actuator> 元素")
        return

    motors = actuator.findall("motor")
    info(f"电机数量: {len(motors)}")

    for m in motors:
        name = m.get("name", "?")
        joint = m.get("joint", "?")
        ctrlrange = m.get("ctrlrange", "?")
        if joint == "?":
            warning(f"电机 {name} 缺少 joint 属性")
        if ctrlrange == "?":
            warning(f"电机 {name} 缺少 ctrlrange")

    # 检查 joint_ctrl_config.json 一致性
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        config_joints = set(config.keys())
        motor_joints = {m.get("joint") for m in motors}
        motor_joints.discard("?")

        only_in_config = config_joints - motor_joints
        only_in_motor = motor_joints - config_joints

        if only_in_config:
            warning(f"joint_ctrl_config.json 中有但 MuJoCo 中无电机的关节: {only_in_config}")
        if only_in_motor:
            warning(f"MuJoCo 中有电机但 joint_ctrl_config.json 中无配置的关节: {only_in_motor}")
        if not only_in_config and not only_in_motor:
            info("joint_ctrl_config.json 与 MuJoCo 电机配置完全一致 ✓")

    return motors


def check_sensors(root):
    """检查传感器配置"""
    print("\n--- 5. 传感器 (Sensors) ---")
    if root is None:
        return

    sensor = root.find("sensor")
    if sensor is None:
        warning("未找到 <sensor> 元素")
        return

    sensor_types = {}
    for s in sensor:
        tag = s.tag
        sensor_types[tag] = sensor_types.get(tag, 0) + 1

    info(f"传感器总数: {sum(sensor_types.values())}")
    for st, count in sensor_types.items():
        info(f"  {st}: {count}")

    return sensor


def check_contact_exclusions(root):
    """检查碰撞排除"""
    print("\n--- 6. 碰撞排除 (Contact Exclusions) ---")
    if root is None:
        return

    contact = root.find("contact")
    if contact is None:
        warning("未找到 <contact> 元素")
        return

    excludes = contact.findall("exclude")
    info(f"碰撞排除对数量: {len(excludes)}")


def main():
    print("=" * 60)
    print("  QooBot MuJoCo 双足模型 — 结构检查")
    print("=" * 60)

    root = check_xml_syntax()
    meshes = check_meshes(root)
    bodies, joints = check_kinematic_tree(root)
    check_actuators(root)
    check_sensors(root)
    check_contact_exclusions(root)

    # 汇总
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
    print("  ✓ MuJoCo 模型检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
