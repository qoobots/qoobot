// cli/commands/info_cmd.cpp
// QooCore CLI — info 子命令实现

#include "qoocore/engine.h"
#include "qoocore/hardware/hardware_probe.h"
#include <iostream>
#include <fstream>

// config_generated.h 由 CMake 生成，位于 build 目录
#ifndef QOOCORE_VERSION_STRING
#define QOOCORE_VERSION_STRING "0.1.0-dev"
#endif

int cmd_info(const InfoOptions& opts) {
    if (opts.target.empty() || opts.target == "system") {
        std::cout << "========== System Info ==========" << std::endl;
        std::cout << "QooCore version: " << QOOCORE_VERSION_STRING << std::endl;
        std::cout << "构建时间:     " << __DATE__ << " " << __TIME__ << std::endl;

        // 硬件探测
        qoocore::hardware::HardwareProfile profile;
        qoocore::hardware::HardwareProber::probe(profile);
        std::cout << "\n---------- 硬件 ----------" << std::endl;
        std::cout << "NPU 数量:  " << profile.npu_candidates.size() << std::endl;
        for (size_t i = 0; i < profile.npu_candidates.size(); ++i) {
            const auto& npu = profile.npu_candidates[i];
            std::cout << "  [" << i << "] " << npu.vendor << " " << npu.chip
                      << " (算力: " << npu.topo_tops << " TOPS)" << std::endl;
        }
        std::cout << "GPU 数量:  " << profile.gpu_candidates.size() << std::endl;
        std::cout << "总内存:     " << profile.total_memory_mb << " MB" << std::endl;
        return 0;
    }

    // 否则视为模型路径
    std::ifstream ifs(opts.target, std::ios::binary);
    if (!ifs) {
        std::cerr << "[ERROR] 无法打开文件: " << opts.target << std::endl;
        return 1;
    }

    // 尝试读取 .qoomodel 文件头
    char magic[8];
    ifs.read(magic, 8);
    if (ifs && std::memcmp(magic, "QMD\1\2\3\4\5", 8) == 0) {
        std::cout << "文件格式: .qoomodel" << std::endl;
        std::cout << "文件:     " << opts.target << std::endl;
        // TODO: 解析完整 header，打印模型信息
        std::cout << "[INFO] 使用 `qoocore-cli infer -m " << opts.target << " --dry-run` 查看详情" << std::endl;
    } else {
        std::cerr << "[ERROR] 未知文件格式: " << opts.target << std::endl;
        return 1;
    }

    return 0;
}
