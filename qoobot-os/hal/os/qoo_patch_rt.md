# PREEMPT_RT 实时补丁适配指南

> 适用内核: Linux 5.15 LTS / 6.1 LTS
> 最后更新: 2026-03-15

---

## 1. 概述

PREEMPT_RT（简称 RT）补丁将 Linux 内核改为**完全可抢占**，使内核代码路径的延迟从毫秒级降至**微秒级**，满足机器人运动控制的硬实时要求（< 50μs）。

---

## 2. 补丁获取

### 2.1 官方来源

| 内核版本 | RT 补丁版本 | 下载地址 |
|---------|-------------|---------|
| 5.15.x  | 5.15-rt    | `https://cdn.kernel.org/pub/linux/kernel/projects/rt/5.15/` |
| 6.1.x   | 6.1-rt     | `https://cdn.kernel.org/pub/linux/kernel/projects/rt/6.1/` |
| 6.6.x   | 6.6-rt     | `https://cdn.kernel.org/pub/linux/kernel/projects/rt/6.6/` |

### 2.2 下载示例（5.15 内核）

```bash
# 1. 下载主线内核源码
$ wget https://cdn.kernel.org/pub/linux/kernel/v5.x/linux-5.15.158.tar.xz
$ tar xf linux-5.15.158.tar.xz
$ cd linux-5.15.158

# 2. 下载对应的 RT 补丁
$ wget https://cdn.kernel.org/pub/linux/kernel/projects/rt/5.15/older/patch-5.15.158-rt78.patch.xz
$ xz -d patch-5.15.158-rt78.patch.xz
```

---

## 3. 补丁应用

### 3.1 打补丁

```bash
$ cd linux-5.15.158
$ patch -p1 < ../patch-5.15.158-rt78.patch
```

若使用 `git` 管理内核源码，推荐用 `git am`：

```bash
$ git am ../patch-5.15.158-rt78.patch
```

### 3.2 处理冲突

若 SoC 供应商的 BSP 内核与 RT 补丁有冲突：

```
1. 记录冲突文件 (git status 显示 both modified)
2. 手工合并冲突部分（通常较少）
3. git add <冲突文件>
4. git am --continue
```

典型冲突区域：`kernel/sched/`、`drivers/tty/`、`kernel/irq/`。

---

## 4. 内核配置（启用 RT）

### 4.1 加载参考配置

```bash
$ cp qoo_kernel_defconfig .config   # 使用本仓库提供的配置
$ make olddefconfig                      # 自动处理新配置项
```

### 4.2 关键配置项检查

```bash
$ make menuconfig
```

必须确认：

```
General setup  --->
  [*] Preemption Model (Fully Preemptible Kernel (Real-Time))  ← 选这个！

Processor type and features  --->
  [*] Enable Rwsem optimization for RT  (若可见)

Kernel hacking  --->
  [ ] Kernel debugging   ← 量产后禁用（开发阶段可保留）
```

### 4.3 生成配置文件

```bash
$ make -j$(nproc) vmlinux modules   # 编译内核和模块
$ make -j$(nproc) dtbs              # 编译设备树
```

---

## 5. 部署到目标板

### 5.1 安装内核

```bash
# x86_64 平台
$ sudo make modules_install
$ sudo make install

# ARM64 (交叉编译，安装到目标根文件系统)
$ export TARGET_ROOT=/mnt/rootfs
$ make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- modules_install INSTALL_MOD_PATH=$TARGET_ROOT
$ cp arch/arm64/boot/Image $TARGET_ROOT/boot/vmlinuz-5.15.158-rt78
$ cp arch/arm64/boot/dts/vendor/*.dtb $TARGET_ROOT/boot/dtbs/
```

### 5.2 更新 Bootloader

```bash
# U-Boot (ARM 嵌入式)
=> setenv bootargs 'console=ttyS0,115200 isolcpus=2,3 nohz_full=2,3 rcu_nocbs=2,3'
=> setenv bootcmd 'load mmc 0:1 ${loadaddr} Image; booti ${loadaddr}'
=> saveenv
=> boot
```

---

## 6. 实时性验证

### 6.1 cyclictest（标准工具）

```bash
# 安装 rt-tests 套件
$ sudo apt install rt-tests   # Ubuntu/Debian
$ sudo yum install rt-tests      # CentOS/RHEL

# 运行 cyclictest (5 线程，优先级 80，周期 1ms，运行 1 小时)
$ sudo cyclictest -t 5 -p 80 -n -i 1000 -D 1h -m -a 2-3
```

**输出解读：**

```
T: 0 (  80) P: 0 I:1000 C:  3600000 Min:     2 Act:    3 Avg:    3 Max:    28
T: 1 (  80) P: 0 I:1000 C:  3600000 Min:     2 Act:    3 Avg:    3 Max:    31
...
```

- `Min`: 最小延迟（μs）
- `Act`: 当前延迟（μs）
- `Avg`: 平均延迟（μs）
- `Max`: **最大延迟（μs）** ← 重点关注，应 < 50μs

### 6.2 压力测试下的 cyclictest

```bash
# 终端 1: 运行 cyclictest
$ sudo cyclictest -t 5 -p 80 -n -i 1000 -D 1h -m -a 2-3

# 终端 2: 施加系统压力
$ stress-ng --cpu 4 --io 2 --vm 1 --vm-bytes 512M --hdd 1 --hdd-bytes 1G &
$ sudo dd if=/dev/zero of=/tmp/testfile bs=1M count=10000 &
```

实时系统在高压下 `Max` 延迟仍应 < 100μs。

---

## 7. 常见问题排查

### 7.1 最大延迟超标（> 100μs）

| 原因 | 排查方法 | 解决方案 |
|------|---------|---------|
| CPU 频率调节 | `cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor` | 设为 `performance` |
| 透明大页 | `cat /sys/kernel/mm/transparent_hugepage/enabled` | 设为 `never` |
| 内核调试选项 | `grep CONFIG_DEBUG /boot/config-$(uname -r)` | 禁用所有 `CONFIG_DEBUG_*` |
| 中断亲和性 | `cat /proc/irq/*/smp_affinity` | 将中断绑定到非实时核心 |
| C-state 深度休眠 | `cat /sys/devices/system/cpu/cpu*/cpuidle/state*/disable` | 禁用 C-state > C1 |

### 7.2 实时线程仍然被抢占

```bash
# 检查线程优先级
$ chrt -p $(pidof my_rt_thread)
# 输出应显示: policy: SCHED_FIFO, priority: 80

# 检查是否有更高优先级线程
$ ps -eo pid,cls,rtprio,comm | grep -E 'FF|RR' | sort -k3 -rn
# 确保内核线程 (migration/N, watchdog/N) 优先级 < 用户线程
```

### 7.3 应用层无法锁定内存

```bash
# 错误: mlockall() 返回 -EPERM
# 解决: 修改 ulimit
$ sudo cp /etc/security/limits.conf /etc/security/limits.conf.bak
$ echo "@real-time soft memlock unlimited" | sudo tee -a /etc/security/limits.conf
$ echo "@real-time hard memlock unlimited" | sudo tee -a /etc/security/limits.conf
$ sudo usermod -aG real-time $USER
# 重新登录后生效
```

---

## 8. 量产检查清单

- [ ] `cyclictest` Max < 50μs（无压力）/ < 100μs（满压力）
- [ ] 所有 `CONFIG_DEBUG_*` 已禁用
- [ ] 透明大页已禁用
- [ ] CPU 调频器设为 `performance`
- [ ] C-state 深度休眠已禁用（或限制到 C1）
- [ ] 实时线程优先级 > 内核线程优先级
- [ ]  applications 调用 `mlockall()`
- [ ] `isolcpus=` 和 `nohz_full=` 已配置
- [ ] 内核启动参数包含 `nosoftlockup` 和 `nowatchdog`

---

## 附录: 快速验证脚本

```bash
#!/bin/bash
# os/verify_rt.sh - 快速验证 RT 环境

echo "=== PREEMPT_RT 验证脚本 ==="
echo ""

# 1. 检查内核是否启用 RT
if [ -f /sys/kernel/realtime ]; then
    echo "[OK] PREEMPT_RT 已启用"
else
    echo "[FAIL] PREEMPT_RT 未启用（检查 CONFIG_PREEMPT_RT）"
    exit 1
fi

# 2. 检查内核配置
if [ -f /boot/config-$(uname -r) ]; then
    if zgrep CONFIG_PREEMPT_RT=y /boot/config-$(uname -r); then
        echo "[OK] 内核配置启用 CONFIG_PREEMPT_RT"
    else
        echo "[FAIL] 内核配置未启用 CONFIG_PREEMPT_RT"
    fi
else
    echo "[WARN] 无法读取内核配置文件"
fi

# 3. 检查 CPU 调频器
GOV=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo "unknown")
if [ "$GOV" = "performance" ]; then
    echo "[OK] CPU 调频器: performance"
else
    echo "[WARN] CPU 调频器: $GOV (建议设为 performance)"
fi

# 4. 检查透明大页
THP=$(cat /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null || echo "unknown")
if echo "$THP" | grep -q "\[never\]"; then
    echo "[OK] 透明大页: 已禁用"
else
    echo "[WARN] 透明大页: $THP (建议设为 never)"
fi

# 5. 运行短时 cyclictest
if command -v cyclictest &>/dev/null; then
    echo ""
    echo "运行 cyclictest (10 秒)..."
    cyclictest -t 3 -p 80 -n -i 1000 -D 10s -q
else
    echo "[WARN] cyclictest 未安装 (apt install rt-tests)"
fi

echo ""
echo "=== 验证完成 ==="
```

---

## 参考链接

- PREEMPT_RT 官方网站: `https://wiki.linuxfoundation.org/realtime/`
- RT 补丁下载: `https://cdn.kernel.org/pub/linux/kernel/projects/rt/`
- `cyclictest` 手册: `man cyclictest` 或 `https://man7.org/linux/man-pages/man8/cyclictest.8.html`
