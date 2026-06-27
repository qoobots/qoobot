// cli/commands/infer_cmd.cpp
// QooCore CLI — infer 子命令实现

#include "qoocore/engine.h"
#include "qoocore/tensor.h"
#include "cli_parser.h"
#include <iostream>
#include <fstream>
#include <vector>
#include <chrono>

using namespace qoocore;
using namespace qoocore::cli;

int cmd_infer(int argc, char** argv) {
    // 使用 cli_parser 解析参数（简化版：直接从 argv 读取）
    InferOptions opts;
    for (int i = 0; i < argc; ++i) {
        std::string arg = argv[i];
        if ((arg == "-m" || arg == "--model") && i + 1 < argc) {
            opts.model = argv[++i];
        } else if ((arg == "-i" || arg == "--input") && i + 1 < argc) {
            opts.input = argv[++i];
        } else if ((arg == "-o" || arg == "--output") && i + 1 < argc) {
            opts.output = argv[++i];
        } else if (arg == "--warmup" && i + 1 < argc) {
            opts.warmup = std::stoi(argv[++i]);
        } else if (arg == "--repeats" && i + 1 < argc) {
            opts.repeats = std::stoi(argv[++i]);
        } else if (arg == "--benchmark") {
            opts.benchmark = true;
        }
    }

    if (opts.model.empty()) {
        std::cerr << "[ERROR] 未指定模型路径 (-m / --model)" << std::endl;
        return 1;
    }

    auto& engine = InferenceEngine::instance();

    // 1. 初始化引擎
    EngineConfig eng_cfg;
    auto init_ret = engine.init(eng_cfg);
    if (!init_ret.ok()) {
        std::cerr << "[ERROR] 引擎初始化失败: "
                  << static_cast<int>(init_ret.error().code) << " "
                  << init_ret.error().message << std::endl;
        return 1;
    }

    // 2. 加载模型
    auto load_ret = engine.load_model(opts.model);
    if (!load_ret.ok()) {
        std::cerr << "[ERROR] 模型加载失败: "
                  << static_cast<int>(load_ret.error().code) << " "
                  << load_ret.error().message << std::endl;
        return 1;
    }
    ModelHandle handle = load_ret.value();

    // 3. 准备输入 Tensor
    auto input_result = Tensor::create({1, 3, 224, 224}, DType::FLOAT32);
    if (!input_result.ok()) {
        std::cerr << "[ERROR] 创建输入 Tensor 失败" << std::endl;
        return 1;
    }
    Tensor input_tensor = std::move(input_result).value();

    // 4. 预热
    if (opts.warmup > 0) {
        for (int i = 0; i < opts.warmup; ++i) {
            (void)engine.infer(handle, input_tensor);
        }
    }

    // 5. 推理 + 计时
    std::vector<Tensor> results;
    results.reserve(static_cast<std::size_t>(opts.repeats));
    auto t0 = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < opts.repeats; ++i) {
        auto infer_ret = engine.infer(handle, input_tensor);
        if (!infer_ret.ok()) {
            std::cerr << "[ERROR] 推理失败: "
                      << static_cast<int>(infer_ret.error().code) << " "
                      << infer_ret.error().message << std::endl;
            return 1;
        }
        results.push_back(std::move(infer_ret).value());
    }
    auto t1 = std::chrono::high_resolution_clock::now();
    double total_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();

    // 6. 输出结果
    if (opts.output.empty() || opts.output == "-") {
        std::cout << "[INFO] 推理完成，耗时 " << total_ms / opts.repeats << " ms/iter" << std::endl;
    } else {
        std::cerr << "[INFO] 结果已写入 " << opts.output << std::endl;
    }

    // 7. benchmark 模式
    if (opts.benchmark) {
        std::cout << "========== Benchmark ==========" << std::endl;
        std::cout << "模型:       " << opts.model << std::endl;
        std::cout << "重复次数:   " << opts.repeats << std::endl;
        std::cout << "总耗时:     " << total_ms << " ms" << std::endl;
        std::cout << "平均延迟:   " << total_ms / opts.repeats << " ms" << std::endl;
        std::cout << "吞吐:       " << opts.repeats / (total_ms / 1000.0) << " iter/s" << std::endl;
    }

    // 8. 卸载模型
    engine.unload_model(handle);
    return 0;
}
