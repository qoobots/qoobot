# =============================================================================
# QooBody — Yocto Image Recipe
# Description: qoobody-image.bb — QooBot hardware reference design OS image
# Usage: bitbake qoobody-image
# =============================================================================

SUMMARY = "QooBot Hardware Reference Design — OS Image"
DESCRIPTION = "Custom Linux OS image for QooBot compute platform. \
               Includes PREEMPT_RT kernel, QooBody HAL/drivers/firmware, \
               and runtime dependencies for QooBrain."

LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

# ---- Image Type -------------------------------------------------------------
inherit core-image

IMAGE_FEATURES += " \
    ssh-server-dropbear \
    hwcodecs \
    package-management \
    debug-tweaks \
"

# ---- Base Packages ----------------------------------------------------------
IMAGE_INSTALL:append = " \
    packagegroup-core-boot \
    packagegroup-base-wifi \
    packagegroup-base-bluetooth \
    packagegroup-base-usbhost \
    packagegroup-base-usbgadget \
"

# ---- QooBody Packages -------------------------------------------------------
IMAGE_INSTALL:append = " \
    qoobody-hal \
    qoobody-drivers \
    qoobody-compute \
    qoobody-power \
    qoo-kernel-rt \
"

# ---- Firmware Packages (if building for safety MCU) -------------------------
IMAGE_INSTALL:append = " \
    qoo-safety-fw \
    qoo-motor-ctrl \
"

# ---- Real-time & Control Dependencies ---------------------------------------
IMAGE_INSTALL:append = " \
    rt-tests \
    stress-ng \
    can-utils \
    ethtool \
    i2c-tools \
    spi-tools \
    iperf3 \
    tcpdump \
    gdb \
    strace \
    ltrace \
"

# ---- Network & Time Sync ----------------------------------------------------
IMAGE_INSTALL:append = " \
    linuxptp \
    chrony \
    avahi-daemon \
"

# ---- Security ---------------------------------------------------------------
IMAGE_INSTALL:append = " \
    op-tee \
    optee-client \
    optee-os \
    tpm2-tools \
    tpm2-tss \
    libtpm2-pkcs11 \
"

# ---- Development Tools (removed in production) ------------------------------
# IMAGE_INSTALL:append = " \
#     cmake \
#     git \
#     vim \
#     htop \
#     valgrind \
# "

# ---- Set root password (development only) -----------------------------------
# inherit extrausers
# EXTRA_USERS_PARAMS = "usermod -P qoobot root;"

# ---- Kernel command line ----------------------------------------------------
CMDLINE:append = " isolcpus=2,3 nohz_full=2,3 rcu_nocbs=2,3 quiet"
