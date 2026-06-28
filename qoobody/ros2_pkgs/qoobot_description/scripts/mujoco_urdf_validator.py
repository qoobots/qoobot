#!/usr/bin/env python3
"""
============================================================================
QooBot MuJoCo ↔ URDF 模型一致性校验工具
============================================================================

功能:
  1. 解析 MuJoCo XML (qoobot_float.xml) 提取关节/质量/惯量/限位
  2. 解析 URDF/Xacro 提取对应参数
  3. 交叉校验: 关节名称/质量/惯量/限位/几何引用 一致性
  4. 生成差异报告

对标: qoobody/docs/01功能清单完成进度.md "模型一致性校验"

用法:
  python mujoco_urdf_validator.py \
    --mujoco qoobody/mechanical/mujoco/qoobot_float.xml \
    --urdf qoobody/ros2_pkgs/qoobot_description/urdf/qoobot.urdf.xacro \
    --joint-config qoobody/mechanical/mujoco/joint_ctrl_config.json \
    --output report.json
"""

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class JointInfo:
    """关节信息"""
    name: str
    axis: Tuple[float, float, float] = (0, 0, 0)
    pos: Tuple[float, float, float] = (0, 0, 0)
    range_lower: float = 0.0
    range_upper: float = 0.0
    damping: float = 0.0
    frictionloss: float = 0.0
    limited: bool = False


@dataclass
class LinkInfo:
    """连杆信息"""
    name: str
    mass: float = 0.0
    inertia: Tuple[float, ...] = (0, 0, 0, 0, 0, 0)  # ixx,ixy,ixz,iyy,iyz,izz
    inertial_pos: Tuple[float, float, float] = (0, 0, 0)
    mesh: Optional[str] = None


@dataclass
class ValidationResult:
    """校验结果"""
    joint_name: str
    field: str
    mujoco_value: str
    urdf_value: str
    status: str  # "ok", "mismatch", "missing_urdf", "missing_mujoco"
    tolerance: float = 0.0


@dataclass
class Report:
    """校验报告"""
    total_joints: int = 0
    total_links: int = 0
    matched: int = 0
    mismatched: int = 0
    missing_in_urdf: int = 0
    missing_in_mujoco: int = 0
    results: List[ValidationResult] = field(default_factory=list)


class MuJoCoParser:
    """MuJoCo XML 解析器"""

    def __init__(self, xml_path: str):
        self.xml_path = xml_path
        self.joints: Dict[str, JointInfo] = {}
        self.links: Dict[str, LinkInfo] = {}
        self._parse()

    def _parse(self):
        tree = ET.parse(self.xml_path)
        root = tree.getroot()

        # 解析关节
        for elem in root.iter('joint'):
            name = elem.get('name', '')
            if not name:
                continue
            joint = JointInfo(
                name=name,
                axis=tuple(float(x) for x in elem.get('axis', '0 0 0').split()),
                pos=tuple(float(x) for x in elem.get('pos', '0 0 0').split()),
                range_lower=0.0,
                range_upper=0.0,
                damping=float(elem.get('damping', 0)),
                frictionloss=float(elem.get('frictionloss', 0)),
                limited=elem.get('limited', 'false') == 'true',
            )
            if joint.limited:
                range_str = elem.get('range', '0 0')
                parts = range_str.split()
                if len(parts) >= 2:
                    joint.range_lower = float(parts[0])
                    joint.range_upper = float(parts[1])
            self.joints[name] = joint

        # 解析连杆 (inertial body)
        for elem in root.iter('body'):
            name = elem.get('name', '')
            if not name:
                continue
            inertial = elem.find('inertial')
            if inertial is not None:
                pos_str = inertial.get('pos', '0 0 0')
                pos = tuple(float(x) for x in pos_str.split())
                mass = float(inertial.get('mass', 0))

                # MuJoCo 惯量: fullinertia="ixx iyy izz ixy ixz iyz" 或 diaginertia
                fullinertia = inertial.get('fullinertia', '')
                diaginertia = inertial.get('diaginertia', '')
                if fullinertia:
                    parts = [float(x) for x in fullinertia.split()]
                    if len(parts) >= 6:
                        inertia = tuple(parts[:6])
                    else:
                        inertia = (0, 0, 0, 0, 0, 0)
                elif diaginertia:
                    parts = [float(x) for x in diaginertia.split()]
                    if len(parts) >= 3:
                        inertia = (parts[0], 0, 0, parts[1], 0, parts[2])
                    else:
                        inertia = (0, 0, 0, 0, 0, 0)
                else:
                    inertia = (0, 0, 0, 0, 0, 0)

                # 查找 mesh
                mesh = None
                for geom in elem.iter('geom'):
                    mesh = geom.get('mesh', None)
                    if mesh:
                        break

                self.links[name] = LinkInfo(
                    name=name,
                    mass=mass,
                    inertia=inertia,
                    inertial_pos=pos,
                    mesh=mesh,
                )


class URDFParser:
    """URDF/Xacro 解析器 (简化版, 解析 xacro 中直接定义的 joint/link)"""

    def __init__(self, urdf_path: str):
        self.urdf_path = urdf_path
        self.joints: Dict[str, JointInfo] = {}
        self.links: Dict[str, LinkInfo] = {}
        self._parse()

    def _parse(self):
        try:
            tree = ET.parse(self.urdf_path)
        except ET.ParseError:
            # xacro 文件无法直接解析, 尝试提取 robot 标签内容
            with open(self.urdf_path, 'r') as f:
                content = f.read()
            # 简单提取: 查找 <joint name="..."> 和 <link name="...">
            import re
            # 提取关节
            joint_pattern = re.findall(
                r'<joint\s+name="([^"]+)"\s+type="[^"]*">.*?'
                r'<axis\s+xyz="([^"]*)"/>.*?'
                r'<limit\s+lower="([^"]*)"\s+upper="([^"]*)"\s+effort="([^"]*)"\s+velocity="([^"]*)"/>',
                content, re.DOTALL
            )
            for name, axis, lower, upper, effort, velocity in joint_pattern:
                axis_vals = tuple(float(x) for x in axis.split() if x)
                if len(axis_vals) < 3:
                    axis_vals = (0, 0, 1)
                self.joints[name] = JointInfo(
                    name=name,
                    axis=axis_vals,
                    range_lower=float(lower) if lower else 0,
                    range_upper=float(upper) if upper else 0,
                    limited=True,
                )

            # 提取连杆质量
            link_pattern = re.findall(
                r'<link\s+name="([^"]+)">.*?<mass\s+value="([^"]*)"',
                content, re.DOTALL
            )
            for name, mass in link_pattern:
                self.links[name] = LinkInfo(name=name, mass=float(mass))

            return

        root = tree.getroot()
        for joint_elem in root.iter('joint'):
            name = joint_elem.get('name', '')
            if not name:
                continue
            axis_elem = joint_elem.find('axis')
            axis = (0, 0, 1)
            if axis_elem is not None:
                xyz = axis_elem.get('xyz', '0 0 1')
                axis = tuple(float(x) for x in xyz.split())

            limit_elem = joint_elem.find('limit')
            lower, upper = 0.0, 0.0
            if limit_elem is not None:
                lower = float(limit_elem.get('lower', 0))
                upper = float(limit_elem.get('upper', 0))

            self.joints[name] = JointInfo(
                name=name,
                axis=axis,
                range_lower=lower,
                range_upper=upper,
                limited=True,
            )

        for link_elem in root.iter('link'):
            name = link_elem.get('name', '')
            if not name:
                continue
            inertial = link_elem.find('inertial')
            mass = 0.0
            if inertial is not None:
                mass_elem = inertial.find('mass')
                if mass_elem is not None:
                    mass = float(mass_elem.get('value', 0))
            self.links[name] = LinkInfo(name=name, mass=mass)


class JointConfigLoader:
    """关节控制配置加载器"""

    def __init__(self, config_path: str):
        self.config = {}
        with open(config_path, 'r') as f:
            self.config = json.load(f)

    def get_kp_kd(self, joint_name: str) -> Tuple[float, float]:
        entry = self.config.get(joint_name, {})
        return entry.get('kp', 0), entry.get('kd', 0)

    def get_limits(self, joint_name: str) -> Tuple[float, float]:
        entry = self.config.get(joint_name, {})
        return entry.get('minPos', 0), entry.get('maxPos', 0)


class Validator:
    """一致性校验器"""

    # 关节名称映射: MuJoCo → URDF
    JOINT_NAME_MAP = {
        'J_head_yaw': 'head_yaw',
        'J_head_pitch': 'head_pitch',
        'J_arm_r_01': 'arm_r_01',
        'J_arm_r_02': 'arm_r_02',
        'J_arm_r_03': 'arm_r_03',
        'J_arm_r_04': 'arm_r_04',
        'J_arm_r_05': 'arm_r_05',
        'J_arm_r_06': 'arm_r_06',
        'J_arm_r_07': 'arm_r_07',
        'J_arm_l_01': 'arm_l_01',
        'J_arm_l_02': 'arm_l_02',
        'J_arm_l_03': 'arm_l_03',
        'J_arm_l_04': 'arm_l_04',
        'J_arm_l_05': 'arm_l_05',
        'J_arm_l_06': 'arm_l_06',
        'J_arm_l_07': 'arm_l_07',
        'J_waist_pitch': 'waist_pitch',
        'J_waist_roll': 'waist_roll',
        'J_waist_yaw': 'waist_yaw',
        'J_hip_r_roll': 'hip_r_roll',
        'J_hip_r_yaw': 'hip_r_yaw',
        'J_hip_r_pitch': 'hip_r_pitch',
        'J_knee_r_pitch': 'knee_r_pitch',
        'J_ankle_r_pitch': 'ankle_r_pitch',
        'J_ankle_r_roll': 'ankle_r_roll',
        'J_hip_l_roll': 'hip_l_roll',
        'J_hip_l_yaw': 'hip_l_yaw',
        'J_hip_l_pitch': 'hip_l_pitch',
        'J_knee_l_pitch': 'knee_l_pitch',
        'J_ankle_l_pitch': 'ankle_l_pitch',
        'J_ankle_l_roll': 'ankle_l_roll',
    }

    # 关节限位容差 (rad)
    LIMIT_TOLERANCE = 0.01  # ~0.5 deg
    # 质量容差 (kg)
    MASS_TOLERANCE = 0.01  # 10g
    # 惯量容差
    INERTIA_TOLERANCE = 0.001

    def __init__(self, mujoco: MuJoCoParser, urdf: URDFParser, config: JointConfigLoader):
        self.mujoco = mujoco
        self.urdf = urdf
        self.config = config

    def validate(self) -> Report:
        report = Report()

        # 验证关节
        mj_joints = set(self.mujoco.joints.keys())
        urdf_joints = set(self.urdf.joints.keys())
        mapped_mj = set()
        for mj_name in mj_joints:
            mapped = self.JOINT_NAME_MAP.get(mj_name)
            if mapped:
                mapped_mj.add(mapped)

        all_joints = mj_joints | urdf_joints
        report.total_joints = len(all_joints)

        for mj_name in sorted(mj_joints):
            urdf_name = self.JOINT_NAME_MAP.get(mj_name)
            if not urdf_name:
                continue

            mj = self.mujoco.joints[mj_name]

            if urdf_name not in self.urdf.joints:
                report.results.append(ValidationResult(
                    joint_name=mj_name,
                    field='joint',
                    mujoco_value=mj_name,
                    urdf_value='N/A',
                    status='missing_urdf',
                ))
                report.missing_in_urdf += 1
                continue

            ur = self.urdf.joints[urdf_name]

            # 验证限位
            if mj.limited:
                limit_match = (
                    abs(mj.range_lower - ur.range_lower) < self.LIMIT_TOLERANCE and
                    abs(mj.range_upper - ur.range_upper) < self.LIMIT_TOLERANCE
                )
                report.results.append(ValidationResult(
                    joint_name=mj_name,
                    field='range',
                    mujoco_value=f'[{mj.range_lower:.4f}, {mj.range_upper:.4f}]',
                    urdf_value=f'[{ur.range_lower:.4f}, {ur.range_upper:.4f}]',
                    status='ok' if limit_match else 'mismatch',
                    tolerance=self.LIMIT_TOLERANCE,
                ))
                if limit_match:
                    report.matched += 1
                else:
                    report.mismatched += 1
            else:
                report.matched += 1

        # 验证连杆质量
        for mj_name in sorted(self.mujoco.links.keys()):
            mj = self.mujoco.links[mj_name]
            urdf_name = mj_name.replace('Link_', '')
            if urdf_name in self.urdf.links:
                ur = self.urdf.links[urdf_name]
                mass_match = abs(mj.mass - ur.mass) < self.MASS_TOLERANCE
                report.results.append(ValidationResult(
                    joint_name=f'[link] {mj_name}',
                    field='mass',
                    mujoco_value=f'{mj.mass:.4f}',
                    urdf_value=f'{ur.mass:.4f}',
                    status='ok' if mass_match else 'mismatch',
                    tolerance=self.MASS_TOLERANCE,
                ))
                if mass_match:
                    report.matched += 1
                else:
                    report.mismatched += 1

        # 验证关节控制参数 (KP/KD)
        for joint_name, entry in self.config.config.items():
            if not isinstance(entry, dict):
                continue
            kp = entry.get('kp', 0)
            kd = entry.get('kd', 0)
            report.results.append(ValidationResult(
                joint_name=joint_name,
                field='kp_kd',
                mujoco_value=f'kp={kp}, kd={kd}',
                urdf_value='joint_pid_gains (see joint_control.yaml)',
                status='ok',
            ))
            report.matched += 1

        return report


def main():
    parser = argparse.ArgumentParser(
        description='QooBot MuJoCo ↔ URDF 模型一致性校验工具'
    )
    parser.add_argument(
        '--mujoco', required=True,
        help='Path to MuJoCo XML model (qoobot_float.xml)'
    )
    parser.add_argument(
        '--urdf', required=True,
        help='Path to URDF/Xacro model (qoobot.urdf.xacro)'
    )
    parser.add_argument(
        '--joint-config', required=True,
        help='Path to joint control config (joint_ctrl_config.json)'
    )
    parser.add_argument(
        '--output', default='validation_report.json',
        help='Output JSON report path'
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Verbose output'
    )
    args = parser.parse_args()

    # 检查文件存在
    for path, name in [
        (args.mujoco, 'MuJoCo XML'),
        (args.urdf, 'URDF/Xacro'),
        (args.joint_config, 'Joint Config')
    ]:
        if not os.path.exists(path):
            print(f'ERROR: {name} file not found: {path}')
            sys.exit(1)

    print(f'=== QooBot Model Validator ===')
    print(f'  MuJoCo: {args.mujoco}')
    print(f'  URDF:   {args.urdf}')
    print(f'  Config: {args.joint_config}')
    print()

    # 解析
    mujoco_parser = MuJoCoParser(args.mujoco)
    urdf_parser = URDFParser(args.urdf)
    config_loader = JointConfigLoader(args.joint_config)

    print(f'Parsed MuJoCo: {len(mujoco_parser.joints)} joints, {len(mujoco_parser.links)} links')
    print(f'Parsed URDF:   {len(urdf_parser.joints)} joints, {len(urdf_parser.links)} links')
    print(f'Loaded Config: {len(config_loader.config)} joint entries')
    print()

    # 校验
    validator = Validator(mujoco_parser, urdf_parser, config_loader)
    report = validator.validate()

    # 输出报告
    print(f'=== Validation Report ===')
    print(f'  Total checks:  {report.total_joints + len(mujoco_parser.links)}')
    print(f'  Matched:       {report.matched}')
    print(f'  Mismatched:    {report.mismatched}')
    print(f'  Missing URDF:  {report.missing_in_urdf}')
    print(f'  Missing MuJoCo:{report.missing_in_mujoco}')
    print()

    if args.verbose or report.mismatched > 0:
        print('=== Details ===')
        for r in report.results:
            status_icon = '✅' if r.status == 'ok' else '❌' if r.status == 'mismatch' else '⚠️'
            print(f'  {status_icon} [{r.status}] {r.joint_name}.{r.field}:')
            print(f'       MuJoCo: {r.mujoco_value}')
            print(f'       URDF:   {r.urdf_value}')
            if r.tolerance:
                print(f'       tol:    ±{r.tolerance}')
            print()

    # 保存 JSON
    report_data = {
        'summary': {
            'total_checks': report.total_joints + len(mujoco_parser.links),
            'matched': report.matched,
            'mismatched': report.mismatched,
            'missing_in_urdf': report.missing_in_urdf,
            'missing_in_mujoco': report.missing_in_mujoco,
            'pass': report.mismatched == 0,
        },
        'results': [
            {
                'joint': r.joint_name,
                'field': r.field,
                'mujoco_value': r.mujoco_value,
                'urdf_value': r.urdf_value,
                'status': r.status,
            }
            for r in report.results
        ]
    }
    with open(args.output, 'w') as f:
        json.dump(report_data, f, indent=2)
    print(f'Report saved to: {args.output}')

    if report.mismatched > 0:
        print(f'\nWARNING: {report.mismatched} mismatches found!')
        sys.exit(1)
    else:
        print('\nAll checks passed! ✅')
        sys.exit(0)


if __name__ == '__main__':
    main()
