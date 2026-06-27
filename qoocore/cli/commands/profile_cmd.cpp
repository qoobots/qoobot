// cli/commands/profile_cmd.cpp
// QooCore CLI — profile 子命令实现

#include "qoocore/engine.h"
#include "qoocore/tensor.h"
#include "cli_parser.h"
#include <iostream>
#include <fstream>
#include <chrono>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace qoocore;
using namespace qoocore::cli;

int cmd_profile(int argc, char** argv) {
    ProfileOptions opts;
    for (int i = 0; i < argc; ++i) {
        std::string arg = argv[i];
        if ((arg == "-m" || arg == "--model") && i + 1 < argc) {
            opts.model = argv[++i];
        } else if ((arg == "-o" || arg == "--output") && i + 1 < argc) {
            opts.output = argv[++i];
        } else if (arg == "--repeats" && i + 1 < argc) {
            opts.repeats = std::stoi(argv[++i]);
        }
    }

    if (opts.model.empty()) {
        std::cerr << "[ERROR] 未指定模型路径 (-m / --model)" << std::endl;
        return 1;
    }

    auto& engine = InferenceEngine::instance();

    EngineConfig eng_cfg;
    auto init_ret = engine.init(eng_cfg);
    if (!init_ret.ok()) {
        std::cerr << "[ERROR] 引擎初始化失败: "
                  << static_cast<int>(init_ret.error().code) << " "
                  << init_ret.error().message << std::endl;
        return 1;
    }

    auto load_ret = engine.load_model(opts.model);
    if (!load_ret.ok()) {
        std::cerr << "[ERROR] 模型加载失败: "
                  << static_cast<int>(load_ret.error().code) << " "
                  << load_ret.error().message << std::endl;
        return 1;
    }
    ModelHandle handle = load_ret.value();

    // 创建 dummy 输入
    auto input_result = Tensor::create({1, 3, 224, 224}, DType::FLOAT32);
    if (!input_result.ok()) {
        std::cerr << "[ERROR] 创建输入 Tensor 失败" << std::endl;
        return 1;
    }
    Tensor input_tensor = std::move(input_result).value();

    // 预热
    for (int i = 0; i < 3; ++i) {
        (void)engine.infer(handle, input_tensor);
    }

    // 正式计时
    std::vector<double> latencies;
    latencies.reserve(static_cast<std::size_t>(opts.repeats));
    for (int i = 0; i < opts.repeats; ++i) {
        auto t0 = std::chrono::high_resolution_clock::now();
        auto infer_ret = engine.infer(handle, input_tensor);
        auto t1 = std::chrono::high_resolution_clock::now();
        if (!infer_ret.ok()) {
            std::cerr << "[ERROR] 推理失败: "
                      << static_cast<int>(infer_ret.error().code) << " "
                      << infer_ret.error().message << std::endl;
            return 1;
        }
        double ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
        latencies.push_back(ms);
    }

    // 统计
    double sum = std::accumulate(latencies.begin(), latencies.end(), 0.0);
    double mean = sum / static_cast<double>(latencies.size());
    std::vector<double> sorted = latencies;
    std::sort(sorted.begin(), sorted.end());
    double min_lat = sorted.front();
    double max_lat = sorted.back();
    double p50 = sorted[sorted.size() / 2];
    double p90 = sorted[static_cast<size_t>(sorted.size() * 0.9)];
    double p99 = sorted[static_cast<size_t>(sorted.size() * 0.99)];

    std::cout << "========== Profile 结果 ==========" << std::endl;
    std::cout << "模型:       " << opts.model << std::endl;
    std::cout << "重复次数:   " << opts.repeats << std::endl;
    std::cout << "均值:       " << mean << " ms" << std::endl;
    std::cout << "最小值:     " << min_lat << " ms" << std::endl;
    std::cout << "P50:        " << p50 << " ms" << std::endl;
    std::cout << "P90:        " << p90 << " ms" << std::endl;
    std::cout << "P99:        " << p99 << " ms" << std::endl;
    std::cout << "最大值:     " << max_lat << " ms" << std::endl;

    // 输出 JSON（若指定了 -o）
    if (!opts.output.empty()) {
        std::ofstream ofs(opts.output);
        if (ofs) {
            ofs << "{\n"
                 << "  \"model\": \"" << opts.model << "\",\n"
                 << "  \"repeats\": " << opts.repeats << ",\n"
                 << "  \"min_ms\": " << min_lat << ",\n"
                 << "  \"mean_ms\": " << mean << ",\n"
                 << "  \"max_ms\": " << max_lat << ",\n"
                 << "  \"p50_ms\": " << p50 << ",\n"
                 << "  \"p90_ms\": " << p90 << ",\n"
                 << "  \"p99_ms\": " << p99 << "\n"
                 << "}" << std::endl;
            std::cerr << "[INFO] Profile 结果已写入 " << opts.output << std::endl;
        }
    }

    engine.unload_model(handle);
    return 0;
}
