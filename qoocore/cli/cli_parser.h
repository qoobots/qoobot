// cli/cli_parser.h
// QooCore CLI — 命令行参数解析
// 标准：qoocore C++17，Google 风格（.clang-format）

#ifndef QOOCORE_CLI_PARSER_H
#define QOOCORE_CLI_PARSER_H

#include <string>
#include <vector>
#include <optional>
#include <cstddef>

namespace qoocore {
namespace cli {

// ========== 全局选项 ==========
struct GlobalOptions {
    bool        verbose   = false;
    std::string config_path;           // -c / --config
    std::optional<std::string> log_file;
    bool        version   = false;
    bool        help      = false;
};

// ========== 子命令选项 ==========
struct CompileOptions {
    std::string input;                // -i / --input   输入模型路径
    std::string output;               // -o / --output  输出 .qoomodel 路径
    std::string target      = "auto"; // -t / --target  目标后端 (qnn/bpu/rknn/cuda/opencl/cpu/auto)
    std::string quant_mode;            // --quant        量化模式 (int8/int4/fp16/None)
    bool        optimize    = true;    // --no-optimize  是否执行图优化
    size_t      max_batch  = 1;      // --max-batch    最大 batch size
};

struct InferOptions {
    std::string model;                // -m / --model   .qoomodel 路径
    std::string input;                // -i / --input   输入数据（npy/bin/json）
    std::string output;               // -o / --output  输出路径（默认 stdout）
    int         warmup     = 0;      // --warmup       预热次数
    int         repeats    = 1;      // --repeats      重复推理次数
    bool        benchmark  = false;    // --benchmark    打印延迟统计
};

struct ProfileOptions {
    std::string model;                // -m / --model
    std::string output;               // -o / --output  输出 profile JSON 路径
    int         repeats    = 100;     // --repeats
    bool        per_layer  = true;    // --per-layer   逐算子打点
};

struct ListOptions {
    std::string type = "backends";   // backends / models / devices
};

struct InfoOptions {
    std::string target;               // 模型路径 或 "system"
};

// ========== 解析结果 ==========
struct ParsedArgs {
    std::string    subcommand;        // compile / infer / profile / list / info / help
    GlobalOptions  global;
    CompileOptions compile;
    InferOptions   infer;
    ProfileOptions profile;
    ListOptions    list;
    InfoOptions    info;
};

// ========== API ==========
// 解析命令行参数。遇到 --help / 未知参数时抛出 std::invalid_argument。
ParsedArgs parse_args(int argc, char* argv[]);

// 打印帮助信息。subcommand 为空时打印总帮助。
void print_usage(const std::string& subcommand = "");

}  // namespace cli
}  // namespace qoocore

#endif  // QOOCORE_CLI_PARSER_H
