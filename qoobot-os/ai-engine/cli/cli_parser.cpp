// cli/cli_parser.cpp
// QooCore CLI — 命令行参数解析实现

#include "cli_parser.h"
#include <iostream>
#include <string>
#include <cstring>
#include <stdexcept>

namespace qoocore {
namespace cli {

static bool str_eq(const char* a, const char* b) { return std::strcmp(a, b) == 0; }
static bool str_starts_with(const char* s, const char* prefix) {
    return std::strncmp(s, prefix, std::strlen(prefix)) == 0;
}

ParsedArgs parse_args(int argc, char* argv[]) {
    ParsedArgs args;
    int i = 1;  // argv[0] 为程序名

    // 第一阶段：全局选项 + 子命令
    while (i < argc) {
        const char* arg = argv[i];

        if (str_eq(arg, "--verbose") || str_eq(arg, "-v")) {
            args.global.verbose = true;
        } else if (str_eq(arg, "-c") || str_eq(arg, "--config")) {
            if (++i >= argc) throw std::invalid_argument("缺少 --config 参数");
            args.global.config_path = argv[i];
        } else if (str_eq(arg, "--log-file")) {
            if (++i >= argc) throw std::invalid_argument("缺少 --log-file 参数");
            args.global.log_file = argv[i];
        } else if (str_eq(arg, "--version")) {
            args.global.version = true;
        } else if (str_eq(arg, "--help") || str_eq(arg, "-h")) {
            args.global.help = true;
        } else if (str_eq(arg, "compile") || str_eq(arg, "infer") ||
                   str_eq(arg, "profile") || str_eq(arg, "list") ||
                   str_eq(arg, "info") || str_eq(arg, "help")) {
            args.subcommand = arg;
            ++i;
            break;  // 剩余参数交给子命令解析
        } else if (arg[0] == '-') {
            throw std::invalid_argument(std::string("未知全局选项: ") + arg);
        } else {
            // 无子命令直接跟位置参数，视为模型路径（兼容老用法）
            args.subcommand = "infer";
            break;
        }
        ++i;
    }

    // 第二阶段：子命令参数
    while (i < argc) {
        const char* arg = argv[i];
        auto& sc = args.subcommand;

        if (sc == "compile") {
            if      (str_eq(arg, "-i") || str_eq(arg, "--input"))    { if(++i>=argc) throw std::invalid_argument("缺少 --input");  args.compile.input  = argv[i]; }
            else if (str_eq(arg, "-o") || str_eq(arg, "--output"))   { if(++i>=argc) throw std::invalid_argument("缺少 --output"); args.compile.output = argv[i]; }
            else if (str_eq(arg, "-t") || str_eq(arg, "--target"))   { if(++i>=argc) throw std::invalid_argument("缺少 --target");  args.compile.target = argv[i]; }
            else if (str_starts_with(arg, "--quant="))               { args.compile.quant_mode = arg + 8; }
            else if (str_eq(arg, "--no-optimize"))                    { args.compile.optimize = false; }
            else throw std::invalid_argument(std::string("未知 compile 选项: ") + arg);
        } else if (sc == "infer") {
            if      (str_eq(arg, "-m") || str_eq(arg, "--model"))    { if(++i>=argc) throw std::invalid_argument("缺少 --model");  args.infer.model  = argv[i]; }
            else if (str_eq(arg, "-i") || str_eq(arg, "--input"))    { if(++i>=argc) throw std::invalid_argument("缺少 --input");  args.infer.input  = argv[i]; }
            else if (str_eq(arg, "-o") || str_eq(arg, "--output"))   { if(++i>=argc) throw std::invalid_argument("缺少 --output"); args.infer.output = argv[i]; }
            else if (str_eq(arg, "--warmup"))                         { if(++i>=argc) throw std::invalid_argument("缺少 --warmup"); args.infer.warmup  = std::stoi(argv[i]); }
            else if (str_eq(arg, "--repeats"))                        { if(++i>=argc) throw std::invalid_argument("缺少 --repeats");args.infer.repeats = std::stoi(argv[i]); }
            else if (str_eq(arg, "--benchmark"))                      { args.infer.benchmark = true; }
            else throw std::invalid_argument(std::string("未知 infer 选项: ") + arg);
        } else if (sc == "profile") {
            if      (str_eq(arg, "-m") || str_eq(arg, "--model"))    { if(++i>=argc) throw std::invalid_argument("缺少 --model");  args.profile.model  = argv[i]; }
            else if (str_eq(arg, "-o") || str_eq(arg, "--output"))   { if(++i>=argc) throw std::invalid_argument("缺少 --output"); args.profile.output = argv[i]; }
            else if (str_eq(arg, "--repeats"))                        { if(++i>=argc) throw std::invalid_argument("缺少 --repeats");args.profile.repeats = std::stoi(argv[i]); }
            else throw std::invalid_argument(std::string("未知 profile 选项: ") + arg);
        } else if (sc == "list") {
            if (str_eq(arg, "--type"))                               { if(++i>=argc) throw std::invalid_argument("缺少 --type");   args.list.type = argv[i]; }
            else throw std::invalid_argument(std::string("未知 list 选项: ") + arg);
        } else if (sc == "info") {
            if (i + 1 < argc && argv[i][0] != '-')                 { args.info.target = argv[i]; }
            else throw std::invalid_argument(std::string("未知 info 参数: ") + arg);
        }
        ++i;
    }

    // 后置校验
    if (args.global.help || args.subcommand.empty()) {
        args.subcommand = "help";
    }
    return args;
}

void print_usage(const std::string& subcommand) {
    if (subcommand.empty() || subcommand == "help") {
        std::cout <<
            "QooCore CLI — 端侧 AI 推理引擎命令行工具\n"
            "用法: qoocore-cli [全局选项] <子命令> [选项...]\n"
            "\n全局选项:\n"
            "  -v, --verbose           详细日志\n"
            "  -c, --config <path>     指定配置文件\n"
            "  --log-file <path>       日志文件路径\n"
            "  --version                输出版本信息\n"
            "  -h, --help              显示帮助\n"
            "\n子命令:\n"
            "  compile   编译模型为 .qoomodel\n"
            "  infer     执行模型推理\n"
            "  profile   性能剖析\n"
            "  list      列出后端/模型/设备\n"
            "  info      显示模型或系统信息\n"
            "\n示例:\n"
            "  qoocore-cli compile -i model.onnx -o model.qoomodel -t qnn\n"
            "  qoocore-cli infer -m model.qoomodel -i input.bin --benchmark\n"
            << std::endl;
        return;
    }
    // 子命令帮助省略——各 cmd_xxx 函数自行打印
}

}  // namespace cli
}  // namespace qoocore
