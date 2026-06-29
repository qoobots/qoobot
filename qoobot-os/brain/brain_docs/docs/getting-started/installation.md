# 安装指南

本指南将帮助你在本地环境中安装 QooBot Brain 的全部组件。

---

## 环境要求

| 组件 | 最低要求 | 推荐配置 |
|------|---------|---------|
| **操作系统** | Ubuntu 22.04 | Ubuntu 22.04 (Jammy) |
| **CPU** | x86_64, 4 核 | 8 核以上 |
| **内存** | 16 GB | 32 GB |
| **GPU** | NVIDIA GTX 1060 (6 GB VRAM) | RTX 3060 以上 (12 GB VRAM) |
| **磁盘** | 50 GB | 100 GB SSD |
| **Python** | 3.10+ | 3.11 |
| **Node.js** | 18+ | 22 LTS |

!!! note "Jetson Orin 支持"
    QooBot Brain 也支持 NVIDIA Jetson Orin 平台。请参考 [Jetson 部署指南](../development/modules.md#jetson-orin-部署)。

---

## 1. 安装系统依赖

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 基础工具链
sudo apt install -y build-essential cmake git curl wget

# Python 3.11 及虚拟环境
sudo apt install -y python3.11 python3.11-dev python3.11-venv

# 依赖库
sudo apt install -y \
    libprotobuf-dev protobuf-compiler \
    libgtest-dev libgoogle-glog-dev \
    libopencv-dev libeigen3-dev \
    libyaml-cpp-dev nlohmann-json3-dev
```

---

## 2. 安装 ROS 2 Humble

```bash
# 添加 ROS 2 仓库
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
    -o /usr/share/keyrings/ros-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
    http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | \
    sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# 安装
sudo apt update
sudo apt install -y ros-humble-desktop ros-humble-moveit2

# 初始化 rosdep
sudo rosdep init
rosdep update

# 添加到 shell 配置
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
```

---

## 3. 克隆仓库

```bash
git clone https://github.com/brain-os/brain_os.git
cd brain_os
```

---

## 4. 安装 Python 依赖

=== "虚拟环境 (推荐)"

    ```bash
    python3.11 -m venv venv
    source venv/bin/activate
    pip install -e brain_ai/
    pip install -e brain_sdk/
    pip install -r brain_docs/requirements.txt
    ```

=== "系统全局"

    ```bash
    pip install -e brain_ai/
    pip install -e brain_sdk/
    ```

---

## 5. 编译 C++ 组件

```bash
# 安装 ROS 2 构建工具
sudo apt install -y python3-colcon-common-extensions

# 构建 brain_core
cd brain_core
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)

# 运行测试
ctest --output-on-failure
```

---

## 6. 安装前端依赖

```bash
cd brain_viz
npm install        # 或 pnpm install
```

---

## 7. 安装模型文件

```bash
cd brain_models

# 如果使用 Git LFS（推荐）
git lfs pull

# 或手动下载模型文件并放置到 brain_models/ 目录
# - yolo11n.onnx (目标检测)
# - orb_vocab.fbow (ORB-SLAM3 词袋)
```

---

## 8. 生成 Protobuf 代码

```bash
cd brain_proto
pip install grpcio-tools protobuf
bash generate_proto.sh      # 生成 C++ 和 Python 代码
```

---

## 9. 验证安装

```bash
# 运行端到端集成测试
python tests/test_e2e_integration.py

# 运行性能基准
python scripts/benchmark.py -n 10

# 启动演示
python brain_sim/demo/e2e_demo.py --scenario pick_cup
```

!!! success "安装完成"
    如果上述所有步骤均无报错，说明 QooBot Brain 已成功安装。下一步请阅读 [快速上手](quickstart.md)。
