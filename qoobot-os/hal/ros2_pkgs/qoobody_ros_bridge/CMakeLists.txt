cmake_minimum_required(VERSION 3.8)
project(qoobody_ros_bridge)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

ament_python_install_package(${PROJECT_NAME})

install(
  DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  src/sensor_bridge.py
  src/cmd_bridge.py
  src/foot_contact_publisher.py
  src/teleop_keyboard.py
  src/force_injector.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
