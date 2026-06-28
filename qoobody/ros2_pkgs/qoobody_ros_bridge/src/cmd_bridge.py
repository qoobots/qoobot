#!/usr/bin/env python3
"""
============================================================================
QooBody Command Bridge — ROS 2 指令 → MuJoCo 控制 桥接
============================================================================

订阅:
  /cmd_vel               (geometry_msgs/Twist)        移动底盘速度指令
  /joint_commands        (trajectory_msgs/JointTrajectory)  关节轨迹指令
  /arm_r_controller/commands  (std_msgs/Float64MultiArray)  右臂指令
  /arm_l_controller/commands  (std_msgs/Float64MultiArray)  左臂指令

对标: unitree_ros-master unitree_controller/src/servo.cpp (MotorCmd 发布)
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from trajectory_msgs.msg import JointTrajectory
from std_msgs.msg import Float64MultiArray


class CmdBridge(Node):
    """指令桥接节点"""

    def __init__(self):
        super().__init__('cmd_bridge')

        # Subscribers
        self.cmd_vel_sub = self.create_subscription(
            Twist, '/cmd_vel', self.cmd_vel_callback, 10)
        self.joint_cmd_sub = self.create_subscription(
            JointTrajectory, '/joint_commands', self.joint_cmd_callback, 10)
        self.arm_r_sub = self.create_subscription(
            Float64MultiArray, '/arm_r_controller/commands', self.arm_r_callback, 10)
        self.arm_l_sub = self.create_subscription(
            Float64MultiArray, '/arm_l_controller/commands', self.arm_l_callback, 10)

        # Internal state
        self.cmd_vel = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]  # vx,vy,vz,wx,wy,wz
        self.joint_targets = {}

        self.get_logger().info('CmdBridge started')

    def cmd_vel_callback(self, msg: Twist):
        self.cmd_vel = [
            msg.linear.x, msg.linear.y, msg.linear.z,
            msg.angular.x, msg.angular.y, msg.angular.z
        ]

    def joint_cmd_callback(self, msg: JointTrajectory):
        for point in msg.points:
            for i, name in enumerate(msg.joint_names):
                if i < len(point.positions):
                    self.joint_targets[name] = point.positions[i]

    def arm_r_callback(self, msg: Float64MultiArray):
        # 7 DOF 右臂目标位置
        arm_joints = ['arm_r_01', 'arm_r_02', 'arm_r_03', 'arm_r_04',
                      'arm_r_05', 'arm_r_06', 'arm_r_07']
        for i, name in enumerate(arm_joints):
            if i < len(msg.data):
                self.joint_targets[name] = msg.data[i]

    def arm_l_callback(self, msg: Float64MultiArray):
        # 7 DOF 左臂目标位置
        arm_joints = ['arm_l_01', 'arm_l_02', 'arm_l_03', 'arm_l_04',
                      'arm_l_05', 'arm_l_06', 'arm_l_07']
        for i, name in enumerate(arm_joints):
            if i < len(msg.data):
                self.joint_targets[name] = msg.data[i]

    def get_cmd_vel(self):
        return self.cmd_vel

    def get_joint_targets(self):
        return dict(self.joint_targets)


def main(args=None):
    rclpy.init(args=args)
    node = CmdBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
