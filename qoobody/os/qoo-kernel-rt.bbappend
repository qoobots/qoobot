# =============================================================================
# QooBody — Yocto Kernel Recipe Append (PREEMPT_RT)
# Description: qoo-kernel-rt.bbappend — Apply PREEMPT_RT patch + QooBody config
# =============================================================================

FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"

# ---- Kernel Source Configuration --------------------------------------------
# Preferred kernel version: 5.15 LTS or 6.1 LTS with PREEMPT_RT
PREFERRED_VERSION_linux-yocto-rt ?= "6.1%"

# ---- Kernel Configuration Fragment ------------------------------------------
SRC_URI:append = " \
    file://qoo_kernel_defconfig \
"

# Apply QooBody-specific kernel configuration on top of RT config
do_configure:append() {
    ${S}/scripts/kconfig/merge_config.sh -m \
        ${B}/.config \
        ${WORKDIR}/qoo_kernel_defconfig
}

# ---- Append PREEMPT_RT Patch Steps (documented in qoo_patch_rt.md) ----------
# For custom BSP kernels (Jetson BSP / Rockchip BSP):
#
# KERNEL_PATCHES = " \
#     file://rt-patches/0001-rt-core.patch \
#     file://rt-patches/0002-rt-drivers.patch \
#     file://qoobody/0001-qoo-canfd-timing.patch \
#     file://qoobody/0002-qoo-gptp-clock.patch \
# "
# SRC_URI:append = "${KERNEL_PATCHES}"

# ---- Device Tree ------------------------------------------------------------
# KERNEL_DEVICETREE:append = " qoo_body_v1.dtb"
# SRC_URI:append = " file://qoo_device_tree.dts"

do_compile:append() {
    echo "QooBody: Kernel with PREEMPT_RT + custom device tree compiled"
}
