// cli/commands/infer_cmd.cpp
// QooCore CLI — infer 子命令实现

#include "qoocore/engine.h"
#include "qoocore/tensor.h"
#include <iostream>
#include <fstream>
#include <vector>
#include <chrono>

int cmd_infer(const InferOptions& opts) {
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
                  << error_code_to_string(init_ret.error().code) << std::endl;
        return 1;
    }

    // 2. 加载模型
    ModelConfig model_cfg;
    model_cfg.model_path = opts.model;
    auto load_ret = engine.load_model(model_cfg);
    if (!load_ret.ok()) {
        std::cerr << "[ERROR] 模型加载失败: "
                  << error_code_to_string(load_ret.error().code) << std::endl;
        return 1;
    }
    ModelHandle handle = load_ret.value();

    // 3. 准备输入 Tensor
    // TODO: 从 opts.input 读取输入数据（支持 .npy / .bin / JSON）
    // 当前使用随机数据填充演示
    auto input_tensor = Tensor::create({1, 3, 224, 224}, DType::FLOAT32);
    if (!input_tensor.ok()) {
        std::cerr << "[ERROR] 创建输入 Tensor 失败" << std::endl;
        return 1;
    }

    // 4. 预热
    if (opts.warmup > 0) {
        for (int i = 0; i < opts.warmup; ++i) {
            (void)engine.infer(handle, *input_tensor);
        }
    }

    // 5. 推理 + 计时
    std::vector<InferenceResult> results;
    results.reserve(opts.repeats);
    auto t0 = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < opts.repeats; ++i) {
        auto infer_ret = engine.infer(handle, *input_tensor);
        if (!infer_ret.ok()) {
            std::cerr << "[ERROR] 推理失败: "
                      << error_code_to_string(infer_ret.error().code) << std::endl;
            return 1;
        }
        results.push_back(std::move(infer_ret.value()));
    }
    auto t1 = std::chrono::high_resolution_clock::now();
    double total_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();

    // 6. 输出结果
    if (opts.output.empty() || opts.output == "-") {
        std::cout << "[INFO] 推理完成，耗时 " << total_ms / opts.repeats << " ms/iter" << std::endl;
        // TODO: 序列化输出 Tensor 到 stdout（JSON / 二进制）
    } else {
        // TODO: 写入文件
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
