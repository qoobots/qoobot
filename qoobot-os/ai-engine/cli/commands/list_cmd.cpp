/**
 * @file list_cmd.cpp
 * @brief CLI "list" 子命令实现
 *
 * 用法：
 *   qoocore list backends
 *   qoocore list models
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include <spdlog/spdlog.h>

#include <iomanip>
#include <string>
#include <vector>

int cmd_list_backends(int argc, char** argv) {
    (void)argc; (void)argv;

    spdlog::info("Available backends:");
    spdlog::info("  NPU (Neural Processing Unit):");
    spdlog::info("    - npu_qnn   (Qualcomm Snapdragon, requires QNN SDK)");
    spdlog::info("    - npu_bpu   (Horizon Journey, requires BPU SDK) [planned]");
    spdlog::info("    - npu_rknn  (Rockchip RK3588, requires RKNN SDK) [planned]");
    spdlog::info("  GPU (Graphics Processing Unit):");
    spdlog::info("    - gpu_cuda  (NVIDIA Jetson, requires CUDA) [planned]");
    spdlog::info("    - gpu_opencl (OpenCL-compatible GPUs) [planned]");
    spdlog::info("  CPU (Central Processing Unit):");
    spdlog::info("    - cpu_neon  (ARM NEON, always available on ARM)");
    spdlog::info("    - cpu_avx512 (x86 AVX-512) [planned]");

    spdlog::info("\nNote: Backends with '[planned]' are not yet implemented.");
    spdlog::info("Compile with -DQOOCORE_ENABLE_QNN=ON to enable QNN backend.");

    return 0;
}

int cmd_list_models(int argc, char** argv) {
    (void)argc; (void)argv;

    spdlog::info("No models loaded. Use 'qoocore infer -m <model>' to load a model.");

    return 0;
}
