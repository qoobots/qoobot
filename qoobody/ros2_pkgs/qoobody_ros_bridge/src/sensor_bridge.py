#!/usr/bin/env python3
"""
============================================================================
QooBody Sensor Bridge — MuJoCo 传感器数据 → ROS 2 Topic 桥接
============================================================================

发布:
  /joint_states          (sensor_msgs/JointState)
  /imu/data              (sensor_msgs/Imu)
  /camera/rgb/image_raw  (sensor_msgs/Image)
  /camera/depth/points   (sensor_msgs/PointCloud2)
  /lidar/points          (sensor_msgs/PointCloud2)
  /tf                    (tf2_msgs/TFMessage)

对标: unitree_ros-master unitree_controller/src/servo.cpp
      (订阅关节状态 + IMU + 足端力)
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState, Imu, Image, PointCloud2
from geometry_msgs.msg import TransformStamped
from std_msgs.msg import Header
import numpy as np


class SensorBridge(Node):
    """传感器数据桥接节点"""

    # QooBot 30 个关节 (不含浮动基座)
    JOINT_NAMES = [
        'waist_pitch', 'waist_roll', 'waist_yaw',
        'head_yaw', 'head_pitch',
        'arm_r_01', 'arm_r_02', 'arm_r_03', 'arm_r_04',
        'arm_r_05', 'arm_r_06', 'arm_r_07',
        'arm_l_01', 'arm_l_02', 'arm_l_03', 'arm_l_04',
        'arm_l_05', 'arm_l_06', 'arm_l_07',
        'hip_r_roll', 'hip_r_yaw', 'hip_r_pitch',
        'knee_r_pitch', 'ankle_r_pitch', 'ankle_r_roll',
        'hip_l_roll', 'hip_l_yaw', 'hip_l_pitch',
        'knee_l_pitch', 'ankle_l_pitch', 'ankle_l_roll',
    ]

    def __init__(self):
        super().__init__('sensor_bridge')

        # Publishers
        self.joint_pub = self.create_publisher(JointState, '/joint_states', 10)
        self.imu_pub = self.create_publisher(Imu, '/imu/data', 10)

        # Timers
        self.joint_timer = self.create_timer(0.005, self.publish_joint_states)  # 200 Hz
        self.imu_timer = self.create_timer(0.005, self.publish_imu)  # 200 Hz

        # Internal state (mock for now — real data from MuJoCo interface)
        self.joint_positions = np.zeros(len(self.JOINT_NAMES))
        self.joint_velocities = np.zeros(len(self.JOINT_NAMES))
        self.joint_efforts = np.zeros(len(self.JOINT_NAMES))

        self.get_logger().info(
            f'SensorBridge started: {len(self.JOINT_NAMES)} joints, '
            f'publishing at 200Hz'
        )

    def update_joint_state(self, positions, velocities=None, efforts=None):
        """外部接口: 从 MuJoCo 更新关节状态"""
        self.joint_positions = np.array(positions)
        if velocities is not None:
            self.joint_velocities = np.array(velocities)
        if efforts is not None:
            self.joint_efforts = np.array(efforts)

    def publish_joint_states(self):
        msg = JointState()
        msg.header = Header()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = ''
        msg.name = list(self.JOINT_NAMES)
        msg.position = self.joint_positions.tolist()
        msg.velocity = self.joint_velocities.tolist()
        msg.effort = self.joint_efforts.tolist()
        self.joint_pub.publish(msg)

    def publish_imu(self):
        msg = Imu()
        msg.header = Header()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'imu_link'
        # Mock values — real data from MuJoCo sensor callback
        msg.angular_velocity.x = 0.0
        msg.angular_velocity.y = 0.0
        msg.angular_velocity.z = 0.0
        msg.linear_acceleration.x = 0.0
        msg.linear_acceleration.y = 0.0
        msg.linear_acceleration.z = -9.81
        msg.orientation.w = 1.0
        self.imu_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = SensorBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
