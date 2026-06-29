# =============================================================================
# QooBody — Yocto Security Baseline Append
# Description: qoo-security.bbappend — Security hardening for QooBot OS
# =============================================================================

FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"

# ---- OP-TEE Integration -----------------------------------------------------
# If the SoC supports ARM TrustZone:
IMAGE_INSTALL:append = " \
    optee-os \
    optee-client \
    optee-examples \
    optee-test \
"

# ---- Secure Boot Signing Tools ----------------------------------------------
SRC_URI:append = " \
    file://qoobody-security/secure-boot-keys/ \
"

do_install:append() {
    # Install secure boot public key for kernel module verification
    install -d ${D}${sysconfdir}/secure-boot
    install -m 0400 ${WORKDIR}/qoobody-security/secure-boot-keys/qoobot_sb_pub.pem \
        ${D}${sysconfdir}/secure-boot/qoobot_sb_pub.pem
}

# ---- Firewall Rules (iptables / nftables) -----------------------------------
# IMAGE_INSTALL:append = " iptables"
#
# do_install:append() {
#     install -d ${D}${sysconfdir}/iptables
#     install -m 0644 ${WORKDIR}/qoobody-security/rules.v4 \
#         ${D}${sysconfdir}/iptables/rules.v4
# }

# ---- Read-Only Root Filesystem ----------------------------------------------
# IMAGE_FEATURES += "read-only-rootfs"

# ---- Password policy (pam) --------------------------------------------------
# IMAGE_INSTALL:append = " libpam-pwquality cracklib"

# ---- Audit daemon -----------------------------------------------------------
# IMAGE_INSTALL:append = " auditd audispd-plugins"

# ---- Disable root login via SSH ---------------------------------------------
ROOTFS_POSTPROCESS_COMMAND:append = " qoo_disable_root_ssh;"

qoo_disable_root_ssh() {
    if [ -f ${IMAGE_ROOTFS}${sysconfdir}/ssh/sshd_config ]; then
        sed -i 's/^#PermitRootLogin.*/PermitRootLogin no/' \
            ${IMAGE_ROOTFS}${sysconfdir}/ssh/sshd_config
    fi
}
