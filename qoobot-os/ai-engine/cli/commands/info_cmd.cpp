// cli/commands/info_cmd.cpp
// QooCore CLI — info 子命令实现

#include "qoocore/engine.h"
#include "qoocore/hardware/hardware_probe.h"
#include "cli_parser.h"
#include <iostream>
#include <fstream>
#include <cstring>

using namespace qoocore;
using namespace qoocore::cli;

int cmd_info(int argc, char** argv) {
    InfoOptions opts;
    for (int i = 0; i < argc; ++i) {
        std::string arg = argv[i];
        if (i + 1 < argc && arg[0] != '-') {
            opts.target = arg;
        }
    }

    if (opts.target.empty() || opts.target == "system") {
        std::cout << "========== System Info ==========" << std::endl;
        std::cout << "QooCore version: " << QOOCORE_VERSION_STRING << std::endl;
        std::cout << "构建时间:     " << __DATE__ << " " << __TIME__ << std::endl;

        // 硬件探测
        auto probe_result = hardware::HardwareProber::probe();
        if (probe_result.ok()) {
            const auto& profile = probe_result.value();
            std::cout << "\n---------- 硬件 ----------" << std::endl;
            std::cout << "NPU 数量:  " << profile.npu_candidates.size() << std::endl;
            for (std::size_t i = 0; i < profile.npu_candidates.size(); ++i) {
                const auto& npu = profile.npu_candidates[i];
                std::cout << "  [" << i << "] " << npu.vendor << " "
                          << npu.chip_model << std::endl;
            }
            std::cout << "GPU 数量:  " << profile.gpu_candidates.size() << std::endl;
            std::cout << "总内存:     "
                      << profile.total_memory_bytes / (1024 * 1024) << " MB" << std::endl;
        } else {
            std::cerr << "[WARN] 硬件探测失败: " << probe_result.error().message << std::endl;
        }
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
        std::cout << "[INFO] 使用 `qoocore-cli infer -m " << opts.target
                  << " --dry-run` 查看详情" << std::endl;
    } else {
        std::cerr << "[ERROR] 未知文件格式: " << opts.target << std::endl;
        return 1;
    }

    return 0;
}
