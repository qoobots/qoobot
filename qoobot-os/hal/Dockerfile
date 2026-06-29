# =============================================================================
# QooBody — Docker Development Environment
#
# Build:
#   docker build -t qoobot/qoobody-dev:latest .
#
# Run (with mounted source for live development):
#   docker run -it --rm -v $(pwd):/workspace qoobot/qoobody-dev:latest
#
# Run HIL simulation:
#   docker run -it --rm --network host --privileged qoobot/qoobody-dev:latest hil-test
#
# Multi-stage: dev → build → test → deploy
# =============================================================================

# ---- Stage 1: Development Environment ---------------------------------------
FROM ubuntu:24.04 AS qoobody-dev

LABEL org.qoobot.image="qoobody-dev"
LABEL org.qoobot.description="QooBody Hardware Reference Design — Development"

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Install build toolchain
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    ninja-build \
    gdb \
    git \
    pkg-config \
    # Cross-compilers
    gcc-aarch64-linux-gnu \
    g++-aarch64-linux-gnu \
    gcc-arm-none-eabi \
    binutils-arm-none-eabi \
    # Analysis & formatting
    clang-format-17 \
    clang-tidy-17 \
    valgrind \
    # Real-time test tools
    rt-tests \
    stress-ng \
    # Utilities
    can-utils \
    i2c-tools \
    ethtool \
    tcpdump \
    vim \
    less \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
CMD ["/bin/bash"]

# ---- Stage 2: Build (x86_64 HIL) -------------------------------------------
FROM qoobody-dev AS qoobody-build-hil

COPY . /workspace/qoobody
WORKDIR /workspace/qoobody

RUN cmake -B build \
    -G Ninja \
    -DPLATFORM=x86_64 \
    -DCMAKE_BUILD_TYPE=Release \
    -DQOOBODY_BUILD_TESTS=ON \
    -DQOOBODY_BUILD_FIRMWARE=OFF \
    && cmake --build build --parallel $(nproc)

# ---- Stage 3: Build (aarch64 Jetson Orin) ----------------------------------
FROM qoobody-dev AS qoobody-build-jetson

COPY . /workspace/qoobody
WORKDIR /workspace/qoobody

RUN cmake -B build-aarch64 \
    -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE=cmake/toolchains/aarch64-linux-gnu.cmake \
    -DPLATFORM=jetson_orin \
    -DCMAKE_BUILD_TYPE=Release \
    -DQOOBODY_BUILD_FIRMWARE=OFF \
    -DQOOBODY_BUILD_TESTS=OFF \
    && cmake --build build-aarch64 --parallel $(nproc)

# ---- Stage 4: Test Runner ---------------------------------------------------
FROM qoobody-build-hil AS qoobody-test

WORKDIR /workspace/qoobody/build
CMD ["ctest", "--output-on-failure", "-j", "$(nproc)"]

# ---- Stage 5: HIL Simulation Runtime ----------------------------------------
FROM ubuntu:24.04 AS qoobody-hil-runtime

LABEL org.qoobot.image="qoobody-hil"
LABEL org.qoobot.description="QooBody HIL Simulation Runtime"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libc6 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=qoobody-build-hil /workspace/qoobody/build/qoo_* /usr/local/bin/

ENTRYPOINT ["/usr/local/bin/qoo_hil_test"]
