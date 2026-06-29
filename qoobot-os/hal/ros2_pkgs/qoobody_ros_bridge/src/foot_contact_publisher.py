#!/usr/bin/env python3
"""
============================================================================
QooBody Foot Contact Publisher — 足端接触力 → ROS 2 发布
============================================================================

发布:
  /foot_contact/right   (geometry_msgs/WrenchStamped)
  /foot_contact/left    (geometry_msgs/WrenchStamped)

对标: unitree_ros-master unitree_gazebo/plugin/foot_contact_plugin.cc
      (ContactSensor → /visual/{name}_foot_contact/the_force)
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import WrenchStamped
from std_msgs.msg import Header


class FootContactPublisher(Node):
    """足端接触力发布节点"""

    FOOT_LINKS = ['right_foot', 'left_foot']

    def __init__(self):
        super().__init__('foot_contact_publisher')

        # Publishers (100 Hz — 对标 unitree)
        self.foot_pubs = {}
        for foot in self.FOOT_LINKS:
            self.foot_pubs[foot] = self.create_publisher(
                WrenchStamped, f'/foot_contact/{foot}', 10)

        # Timer
        self.timer = self.create_timer(0.01, self.publish_foot_contact)  # 100 Hz

        # Contact state
        self.contact_forces = {foot: [0.0, 0.0, 0.0] for foot in self.FOOT_LINKS}
        self.contact_torques = {foot: [0.0, 0.0, 0.0] for foot in self.FOOT_LINKS}

        self.get_logger().info('FootContactPublisher started at 100Hz')

    def update_contact(self, foot: str, force, torque=None):
        """外部接口: 从 MuJoCo 足端力传感器更新"""
        if foot in self.contact_forces:
            self.contact_forces[foot] = list(force)
            if torque is not None:
                self.contact_torques[foot] = list(torque)

    def publish_foot_contact(self):
        now = self.get_clock().now().to_msg()
        for foot in self.FOOT_LINKS:
            msg = WrenchStamped()
            msg.header = Header()
            msg.header.stamp = now
            msg.header.frame_id = f'{foot}_link'
            msg.wrench.force.x = self.contact_forces[foot][0]
            msg.wrench.force.y = self.contact_forces[foot][1]
            msg.wrench.force.z = self.contact_forces[foot][2]
            msg.wrench.torque.x = self.contact_torques[foot][0]
            msg.wrench.torque.y = self.contact_torques[foot][1]
            msg.wrench.torque.z = self.contact_torques[foot][2]
            self.foot_pubs[foot].publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = FootContactPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
