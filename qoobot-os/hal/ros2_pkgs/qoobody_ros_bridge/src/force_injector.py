#!/usr/bin/env python3
"""
============================================================================
QooBody Force Injector — 外力注入调试工具
============================================================================

功能:
  - 对机器人指定连杆施加外部力/力矩脉冲
  - 支持持续力和单次脉冲两种模式
  - 用于测试控制器鲁棒性和碰撞检测

对标: unitree_ros-master unitree_controller/src/external_force.cpp
      (键盘遥控施加外力: 脉冲/连续两种模式)
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import WrenchStamped
from std_msgs.msg import Header


class ForceInjector(Node):
    """外力注入节点"""

    # 可施加外力的连杆
    TARGET_LINKS = [
        'base_link',
        'Link_arm_r_07', 'Link_arm_l_07',
        'Link_ankle_r_roll', 'Link_ankle_l_roll',
    ]

    def __init__(self):
        super().__init__('force_injector')

        # Publishers (每连杆一个外力话题)
        self.force_pubs = {}
        for link in self.TARGET_LINKS:
            self.force_pubs[link] = self.create_publisher(
                WrenchStamped, f'/force_inject/{link}', 10)

        # 外力参数
        self.active_forces = {}  # link -> (fx,fy,fz,tx,ty,tz,duration)
        self.impulse_queue = []  # 脉冲队列

        # Timer
        self.timer = self.create_timer(0.01, self.publish_forces)  # 100 Hz

        self.get_logger().info(
            f'ForceInjector started. Targets: {self.TARGET_LINKS}'
        )

    def apply_force(self, link: str, fx=0.0, fy=0.0, fz=0.0,
                    tx=0.0, ty=0.0, tz=0.0, duration=-1.0):
        """
        施加外力

        Args:
            link: 目标连杆名称
            fx,fy,fz: 力分量 (N)
            tx,ty,tz: 力矩分量 (N·m)
            duration: 持续时间 (秒), -1 表示持续
        """
        if link not in self.TARGET_LINKS:
            self.get_logger().error(f'Unknown link: {link}')
            return
        self.active_forces[link] = (fx, fy, fz, tx, ty, tz, duration)
        self.get_logger().info(
            f'Force on {link}: F=({fx:.1f},{fy:.1f},{fz:.1f})N, '
            f'T=({tx:.1f},{ty:.1f},{tz:.1f})Nm, dur={duration}s'
        )

    def apply_impulse(self, link: str, fx=0.0, fy=0.0, fz=0.0,
                      tx=0.0, ty=0.0, tz=0.0, duration=0.1):
        """施加脉冲力 (对标 unitree external_force 脉冲模式)"""
        self.impulse_queue.append((link, fx, fy, fz, tx, ty, tz, duration))

    def clear_forces(self):
        """清除所有外力"""
        self.active_forces.clear()
        self.impulse_queue.clear()
        self.get_logger().info('All forces cleared')

    def publish_forces(self):
        now = self.get_clock().now().to_msg()

        # 处理脉冲队列
        remaining = []
        for item in self.impulse_queue:
            link, fx, fy, fz, tx, ty, tz, duration = item
            remaining_time = duration - 0.01
            if remaining_time > 0:
                remaining.append((link, fx, fy, fz, tx, ty, tz, remaining_time))
                self._publish_wrench(link, fx, fy, fz, tx, ty, tz, now)
        self.impulse_queue = remaining

        # 处理持续力
        expired = []
        for link, (fx, fy, fz, tx, ty, tz, duration) in self.active_forces.items():
            if duration > 0:
                new_dur = duration - 0.01
                if new_dur <= 0:
                    expired.append(link)
                    continue
                self.active_forces[link] = (fx, fy, fz, tx, ty, tz, new_dur)
            self._publish_wrench(link, fx, fy, fz, tx, ty, tz, now)

        for link in expired:
            del self.active_forces[link]
            self.get_logger().info(f'Force on {link} expired')

    def _publish_wrench(self, link, fx, fy, fz, tx, ty, tz, stamp):
        msg = WrenchStamped()
        msg.header = Header()
        msg.header.stamp = stamp
        msg.header.frame_id = link
        msg.wrench.force.x = fx
        msg.wrench.force.y = fy
        msg.wrench.force.z = fz
        msg.wrench.torque.x = tx
        msg.wrench.torque.y = ty
        msg.wrench.torque.z = tz
        if link in self.force_pubs:
            self.force_pubs[link].publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = ForceInjector()

    # 演示: 对右脚踝施加持续力 (模拟外力干扰)
    node.apply_force(
        'Link_ankle_r_roll',
        fx=5.0, fz=-10.0,  # 向右 + 向下 10N
        duration=2.0
    )

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
