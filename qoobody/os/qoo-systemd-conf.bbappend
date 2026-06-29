# =============================================================================
# QooBody — Yocto Systemd Configuration Append
# Description: qoo-systemd-conf.bbappend — System services for QooBot OS
# =============================================================================

FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"

# ---- RT Tuning Service ------------------------------------------------------
# Ensures real-time kernel parameters are set on every boot
SRC_URI:append = " \
    file://qoobody-systemd/99-qoobot-rt.conf \
    file://qoobody-systemd/qoobot-rt-tune.service \
"

do_install:append() {
    # Install sysctl configuration for real-time tuning
    install -d ${D}${sysconfdir}/sysctl.d
    install -m 0644 ${WORKDIR}/qoobody-systemd/99-qoobot-rt.conf \
        ${D}${sysconfdir}/sysctl.d/99-qoobot-rt.conf

    # Install systemd service for RT tuning
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${WORKDIR}/qoobody-systemd/qoobot-rt-tune.service \
        ${D}${systemd_system_unitdir}/qoobot-rt-tune.service
}

# ---- System Tuning (sysctl) -------------------------------------------------
# Content would be:
# vm.swappiness = 0
# kernel.sched_rt_runtime_us = 950000
# kernel.sched_rt_period_us = 1000000

# ---- Disable unnecessary services for embedded ------------------------------
SYSTEMD_AUTO_ENABLE:${PN}-sshd = "enable"
SYSTEMD_AUTO_ENABLE:${PN}-avahi-daemon = "disable"
SYSTEMD_AUTO_ENABLE:${PN}-bluetooth = "enable"

# ---- Set hostname -----------------------------------------------------------
hostname_pn-base-files = "qoobot"
