#!/usr/bin/env python3
"""
============================================================================
QooBody Teleop Keyboard — 键盘遥控节点
============================================================================

按键映射:
  W/S:        前进/后退 (linear.x)
  A/D:        左移/右移 (linear.y)
  Q/E:        左转/右转 (angular.z)
  R/F:        上升/下降 (linear.z)
  T/G:        俯仰 +/- (angular.y)
  Y/H:        翻滚 +/- (angular.x)
  SPACE:      急停 (全零)
  Ctrl+C:     退出

对标: unitree_ros-master unitree_controller/src/external_force.cpp
      (键盘遥控施加外力)
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import sys
import termios
import tty
import select


class TeleopKeyboard(Node):
    """键盘遥控节点"""

    # 速度增量
    LINEAR_STEP = 0.1   # m/s
    ANGULAR_STEP = 0.2  # rad/s

    # 按键映射
    KEY_MAP = {
        'w': (1, 0, 0, 0, 0, 0),    # 前进
        's': (-1, 0, 0, 0, 0, 0),   # 后退
        'a': (0, 1, 0, 0, 0, 0),    # 左移
        'd': (0, -1, 0, 0, 0, 0),   # 右移
        'q': (0, 0, 0, 0, 0, 1),    # 左转
        'e': (0, 0, 0, 0, 0, -1),   # 右转
        'r': (0, 0, 1, 0, 0, 0),    # 上升
        'f': (0, 0, -1, 0, 0, 0),   # 下降
        't': (0, 0, 0, 0, 1, 0),    # 俯仰+
        'g': (0, 0, 0, 0, -1, 0),   # 俯仰-
        'y': (0, 0, 0, 1, 0, 0),    # 翻滚+
        'h': (0, 0, 0, -1, 0, 0),   # 翻滚-
    }

    def __init__(self):
        super().__init__('teleop_keyboard')
        self.publisher = self.create_publisher(Twist, '/cmd_vel', 10)
        self.timer = self.create_timer(0.05, self.publish_cmd)  # 20 Hz

        # 当前速度
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0
        self.wx = 0.0
        self.wy = 0.0
        self.wz = 0.0

        self.get_logger().info(
            'TeleopKeyboard started.\n'
            '  W/S: fwd/back  A/D: left/right  Q/E: turn\n'
            '  R/F: up/down   T/G: pitch       Y/H: roll\n'
            '  SPACE: stop    Ctrl+C: quit'
        )

    def get_key(self):
        """非阻塞读取按键"""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
            if rlist:
                return sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return None

    def spin_once(self):
        key = self.get_key()
        if key is None:
            return

        if key == '\x03':  # Ctrl+C
            raise KeyboardInterrupt

        if key == ' ':
            self.vx = self.vy = self.vz = 0.0
            self.wx = self.wy = self.wz = 0.0
            self.get_logger().info('EMERGENCY STOP')
            return

        key = key.lower()
        if key in self.KEY_MAP:
            dvx, dvy, dvz, dwx, dwy, dwz = self.KEY_MAP[key]
            self.vx += dvx * self.LINEAR_STEP
            self.vy += dvy * self.LINEAR_STEP
            self.vz += dvz * self.LINEAR_STEP
            self.wx += dwx * self.ANGULAR_STEP
            self.wy += dwy * self.ANGULAR_STEP
            self.wz += dwz * self.ANGULAR_STEP
            self.get_logger().info(
                f'cmd_vel: [{self.vx:.1f}, {self.vy:.1f}, {self.vz:.1f}, '
                f'{self.wx:.1f}, {self.wy:.1f}, {self.wz:.1f}]'
            )

    def publish_cmd(self):
        msg = Twist()
        msg.linear.x = self.vx
        msg.linear.y = self.vy
        msg.linear.z = self.vz
        msg.angular.x = self.wx
        msg.angular.y = self.wy
        msg.angular.z = self.wz
        self.publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = TeleopKeyboard()
    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.01)
            node.spin_once()
    except KeyboardInterrupt:
        print('\nTeleopKeyboard stopped.')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
