/**
 * @file main.cpp
 * @brief qoocore CLI 工具入口
 *
 * 用法：
 *   qoocore compile -i model.onnx -o model.qoomodel --backend npu_qnn
 *   qoocore infer -m model.qoomodel -i input.jpg -o output.json
 *   qoocore profile -m model.qoomodel --iterations 100
 *   qoocore list-backends
 *   qoocore info -m model.qoomodel
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include <spdlog/spdlog.h>

#include <memory>
#include <string>

// ── 前向声明：子命令处理函数 ──────────────────────────────────────────
int cmd_compile(int argc, char** argv);
int cmd_infer(int argc, char** argv);
int cmd_profile(int argc, char** argv);
int cmd_list_backends(int argc, char** argv);
int cmd_info(int argc, char** argv);
int cmd_help(const std::string& cmd = "");

// ── 打印版本信息 ──────────────────────────────────────────────────────────
void print_version() {
    spdlog::info("qoocore version {}", QOOCORE_VERSION_STRING);
}

// ── 打印使用帮助 ──────────────────────────────────────────────────────────
void print_usage() {
    spdlog::info(R"(
qoocore — QooBot 端侧 AI 推理引擎 CLI 工具

用法：
  qoocore <command> [options]

命令：
  compile     编译模型（ONNX/Torch → .qoomodel）
  infer       运行推理
  profile      性能剖析
  list        列出可用后端 / 已加载模型
  info        显示模型信息
  help        显示帮助

示例：
  qoocore compile -i yolov11n.onnx -o yolov11n.qoomodel --backend npu_qnn --int8
  qoocore infer -m yolov11n.qoomodel -i image.jpg -o result.json
  qoocore list backends

选项：
  -v, --version   显示版本信息
  -h, --help      显示帮助信息
  --verbose        详细日志
  --quiet          静默模式
)");
}

// ── main ────────────────────────────────────────────────────────────────────
int main(int argc, char** argv) {
    if (argc < 2) {
        print_usage();
        return 1;
    }

    std::string cmd = argv[1];

    // 全局选项
    bool verbose = false;
    bool quiet   = false;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "-v" || arg == "--version") {
            print_version();
            return 0;
        }
        if (arg == "-h" || arg == "--help") {
            print_usage();
            return 0;
        }
        if (arg == "--verbose") verbose = true;
        if (arg == "--quiet")   quiet   = true;
    }

    // 设置日志级别
    if (verbose) spdlog::set_level(spdlog::level::debug);
    if (quiet)   spdlog::set_level(spdlog::level::err);

    // 分发子命令
    if (cmd == "compile")       return cmd_compile(argc - 1, argv + 1);
    if (cmd == "infer")         return cmd_infer(argc - 1, argv + 1);
    if (cmd == "profile")       return cmd_profile(argc - 1, argv + 1);
    if (cmd == "list")          return cmd_list_backends(argc - 1, argv + 1);
    if (cmd == "info")          return cmd_info(argc - 1, argv + 1);
    if (cmd == "help") {
        if (argc > 2) return cmd_help(argv[2]);
        print_usage();
        return 0;
    }

    spdlog::error("Unknown command: '{}'. Use 'qoocore help' for usage.", cmd);
    return 1;
}
