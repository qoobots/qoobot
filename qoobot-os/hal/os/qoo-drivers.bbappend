# =============================================================================
# QooBody — Yocto Drivers Recipe Append
# Description: qoo-drivers.bbappend — Build & install QooBody reference drivers
# =============================================================================

FILESEXTRAPATHS:prepend := "${THISDIR}/${PN}:"

# ---- Driver Sources ---------------------------------------------------------
# QooBody reference drivers are built by CMake; this append compiles them
# within the Yocto build as kernel out-of-tree modules or user-space drivers.

SRC_URI:append = " \
    file://qoobody-drivers.tar.gz \
"

do_compile() {
    cd ${WORKDIR}/qoobody-drivers
    cmake -B build \
        -DCMAKE_BUILD_TYPE=Release \
        -DQOOBODY_BUILD_DRIVERS=ON \
        -DQOOBODY_BUILD_HAL=ON \
        -DQOOBODY_BUILD_COMPUTE=ON \
        -DQOOBODY_BUILD_POWER=ON
    cmake --build build --parallel ${@oe.utils.cpu_count()}
}

do_install() {
    install -d ${D}${libdir}/qoobody
    install -d ${D}${includedir}/qoobody

    # Install HAL headers
    cp -r ${WORKDIR}/qoobody-drivers/hal/*.h ${D}${includedir}/qoobody/

    # Install static libraries
    cp ${WORKDIR}/qoobody-drivers/build/libqoobody_*.a ${D}${libdir}/qoobody/

    # Install driver utilities
    install -d ${D}${bindir}
    cp ${WORKDIR}/qoobody-drivers/build/qoo_drv_test ${D}${bindir}/ || true
}

# ---- Ensure driver modules are loaded at boot -------------------------------
FILES:${PN} += " \
    ${libdir}/qoobody/*.a \
    ${includedir}/qoobody/*.h \
"
