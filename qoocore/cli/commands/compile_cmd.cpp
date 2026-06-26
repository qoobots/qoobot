/**
 * @file compile_cmd.cpp
 * @brief CLI "compile" 子命令实现
 *
 * 用法：
 *   qoocore compile -i model.onnx -o model.qoomodel --backend npu_qnn --int8
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include <spdlog/spdlog.h>

#include <string>
#include <vector>
#include <cstdint>

// ── compile 命令选项 ────────────────────────────────────────────────
struct CompileOptions {
    std::string input_path;
    std::string output_path;
    std::string backend{"npu_qnn"};
    std::string quant_scheme{"int8_per_tensor"};
    int opt_level{2};
    bool help{false};
    bool verbose{false};
};

// ── 解析命令行参数 ──────────────────────────────────────────────────
static Result<CompileOptions> parse_compile_args(int argc, char** argv) {
    CompileOptions opts;

    for (int i = 0; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "-i" || arg == "--input") {
            if (i + 1 < argc) opts.input_path = argv[++i];
        } else if (arg == "-o" || arg == "--output") {
            if (i + 1 < argc) opts.output_path = argv[++i];
        } else if (arg == "--backend") {
            if (i + 1 < argc) opts.backend = argv[++i];
        } else if (arg == "--quant") {
            if (i + 1 < argc) opts.quant_scheme = argv[++i];
        } else if (arg == "--opt-level") {
            if (i + 1 < argc) opts.opt_level = std::stoi(argv[++i]);
        } else if (arg == "-h" || arg == "--help") {
            opts.help = true;
        } else if (arg == "--verbose" || arg == "-v") {
            opts.verbose = true;
        }
    }

    if (opts.help) {
        print_compile_help();
        return Error(ErrorCode::CANCELLED, "Help displayed");
    }

    if (opts.input_path.empty()) {
        return Error(ErrorCode::INVALID_ARGUMENT,
                     "Missing input file (-i/--input)");
    }
    if (opts.output_path.empty()) {
        // 自动生成输出路径
        opts.output_path = opts.input_path;
        // 替换扩展名
        auto pos = opts.output_path.find_last_of('.');
        if (pos != std::string::npos) {
            opts.output_path = opts.output_path.substr(0, pos);
        }
        opts.output_path += ".qoomodel";
    }

    return opts;
}

// ── 打印帮助 ──────────────────────────────────────────────────────
static void print_compile_help() {
    spdlog::info(R"(
qoocore compile — 编译模型为 .qoomodel 格式

用法：
  qoocore compile -i <input> [-o <output>] [options]

必须参数：
  -i, --input <file>     输入模型文件（.onnx / .pt / .pb）

可选参数：
  -o, --output <file>    输出 .qoomodel 路径（默认：同名 .qoomodel）
  --backend <name>       目标后端（npu_qnn / npu_bpu / npu_rknn / gpu_cuda）
  --quant <scheme>       量化方案（int8_per_tensor / int8_per_channel / int4 / fp16）
  --opt-level <0-3>      优化等级（默认 2）
  --calibration-data <path> 量化校准数据集路径
  --verbose                详细日志
  -h, --help              显示帮助

示例：
  qoocore compile -i yolov11n.onnx -o yolov11n.qoomodel \
      --backend npu_qnn --quant int8_per_tensor
)");
}

// ── compile 命令主函数 ─────────────────────────────────────────────
int cmd_compile(int argc, char** argv) {
    // 1. 解析参数
    auto opts_result = parse_compile_args(argc, argv);
    if (!opts_result.ok()) {
        if (opts_result.error().code == ErrorCode::CANCELLED) {
            return 0;  // Help displayed
        }
        spdlog::error("Failed to parse arguments: [{}] {}",
                       static_cast<int>(opts_result.error().code),
                       opts_result.error().message);
        return 1;
    }
    auto opts = std::move(opts_result.value());

    if (opts.verbose) {
        spdlog::set_level(spdlog::level::debug);
    }

    spdlog::info("QooCore Compiler v{}", QOOCORE_VERSION_STRING);
    spdlog::info("Input:  {}", opts.input_path);
    spdlog::info("Output: {}", opts.output_path);
    spdlog::info("Backend: {}", opts.backend);
    spdlog::info("Quant:   {}", opts.quant_scheme);

    // 2. 创建编译器
    auto compiler = create_compiler(true);  // use MLIR
    if (!compiler) {
        spdlog::error("Failed to create compiler (ONNX Runtime not available?)");
        return 1;
    }

    // 3. 配置编译
    CompilationConfig config;
    config.source_model_path = opts.input_path;
    config.output_path      = opts.output_path;
    config.opt_level       = static_cast<OptimizationLevel>(opts.opt_level);

    if (opts.quant_scheme == "int8_per_tensor") {
        QuantizationConfig qc;
        qc.scheme = QuantizationConfig::Scheme::INT8_PER_TENSOR;
        config.quantization = qc;
    }

    // 4. 执行编译
    spdlog::info("Starting compilation...");
    auto result = compiler->compile(config,
        [](float progress, const std::string& msg) {
            spdlog::info("  [{:.1f}%] {}", progress * 100, msg);
        });

    if (!result.ok()) {
        spdlog::error("Compilation failed: [{}] {}",
                       static_cast<int>(result.error().code),
                       result.error().message);
        return 1;
    }

    auto& r = result.value();
    spdlog::info("✅ Compilation successful!");
    spdlog::info("   Output:  {}", r.output_path);
    spdlog::info("   Size:    {} bytes (original) → {} bytes (compiled)",
                   r.size_info.original_size_bytes,
                   r.size_info.compiled_size_bytes);
    if (r.accuracy_info.top1_accuracy.has_value()) {
        spdlog::info("   Accuracy: Top-1 = {:.3f}",
                       r.accuracy_info.top1_accuracy.value());
    }

    return 0;
}
