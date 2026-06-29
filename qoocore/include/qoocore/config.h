/**
 * @file config.h
 * @brief 配置管理 — 统一处理 qoocore 的所有配置来源
 *
 * 配置来源优先级（低 → 高）：
 *   1. 内置默认值
 *   2. 系统配置文件（/etc/qoocore/config.yaml）
 *   3. 用户配置文件（~/.qoocore/config.yaml）
 *   4. 环境变量（QOOCORE_*）
 *   5. 程序化设置（EngineConfig / BackendConfig）
 *
 * 支持格式：YAML（主格式）、JSON（兼容）
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#pragma once

#include "core.h"  // 复用 ErrorCode, Result

#include <functional>
#include <memory>
#include <string>
#include <unordered_map>
#include <optional>
#include <vector>

namespace qoocore {

// ─────────────────────────────────────────────────────────────────────────────
//  ConfigValue — 配置值容器（类似 JSON 值）
// ─────────────────────────────────────────────────────────────────────────────
/**
 * @brief 类型安全的配置值，支持嵌套对象。
 *
 * 设计要点：
 *   - 轻量级，栈分配友好
 *   - 支持 .dot.notation 路径访问
 *   - 与 YAML/JSON 自然映射
 */
class ConfigValue {
public:
    enum class Type { NULL_, BOOL, INT64, DOUBLE, STRING, OBJECT, ARRAY };

    ConfigValue() : type_(Type::NULL_) {}
    ConfigValue(bool v)       : type_(Type::BOOL),  bool_val_(v) {}
    ConfigValue(std::int64_t v) : type_(Type::INT64), int_val_(v) {}
    ConfigValue(double v)      : type_(Type::DOUBLE), double_val_(v) {}
    ConfigValue(const std::string& v) : type_(Type::STRING), str_val_(v) {}

    [[nodiscard]] Type type() const noexcept { return type_; }
    [[nodiscard]] bool is_null()  const noexcept { return type_ == Type::NULL_; }
    [[nodiscard]] bool is_bool()  const noexcept { return type_ == Type::BOOL; }
    [[nodiscard]] bool is_int()   const noexcept { return type_ == Type::INT64; }
    [[nodiscard]] bool is_double()const noexcept { return type_ == Type::DOUBLE; }
    [[nodiscard]] bool is_string()const noexcept { return type_ == Type::STRING; }

    [[nodiscard]] Result<bool>        as_bool()  const;
    [[nodiscard]] Result<std::int64_t> as_int()   const;
    [[nodiscard]] Result<double>       as_double()const;
    [[nodiscard]] Result<std::string> as_string()const;

    // 嵌套对象访问（.dot.notation）
    [[nodiscard]] std::optional<ConfigValue> get(const std::string& key) const;
    void set(const std::string& key, ConfigValue value);

    // 序列化
    [[nodiscard]] std::string to_yaml()  const;
    [[nodiscard]] std::string to_json()  const;
    static Result<ConfigValue> from_yaml(const std::string& yaml_str);
    static Result<ConfigValue> from_json(const std::string& json_str);

private:
    Type type_{Type::NULL_};
    bool        bool_val_{false};
    std::int64_t int_val_{0};
    double       double_val_{0.0};
    std::string  str_val_;
    std::unordered_map<std::string, ConfigValue> obj_val_;
    std::vector<ConfigValue> arr_val_;
};

// ─────────────────────────────────────────────────────────────────────────────
//  ConfigManager — 全局配置管理器
// ─────────────────────────────────────────────────────────────────────────────
/**
 * @brief 管理 qoocore 所有配置。
 *
 * 单例，在 InferenceEngine::init() 中自动初始化。
 *
 * 配置文件搜索路径（按优先级，后者覆盖前者）：
 *   - <exe_dir>/qoocore.yaml
 *   - ~/.qoocore/config.yaml
 *   - /etc/qoocore/config.yaml
 *   - 环境变量 QOOCORE_CONFIG
 */
class ConfigManager {
public:
    static ConfigManager& instance();

    // 禁止拷贝
    ConfigManager(const ConfigManager&) = delete;
    ConfigManager& operator=(const ConfigManager&) = delete;

    ~ConfigManager();

    /**
     * @brief 加载配置（搜索默认路径）。
     * @return 加载的配置源路径列表
     */
    Result<std::vector<std::string>> load();

    /**
     * @brief 从指定文件加载配置。
     */
    Result<void> load_file(const std::string& file_path);

    /**
     * @brief 从环境变量加载配置（QOOCORE_*）。
     */
    Result<void> load_env();

    /**
     * @brief 保存当前配置到文件。
     */
    Result<void> save(const std::string& file_path) const;

    // ── 查询 ─────────────────────────────────────────────────────────────
    /**
     * @brief 获取配置值（.dot.notation 路径）。
     * @example get("backend.npu.power_mode") → ConfigValue
     */
    [[nodiscard]] std::optional<ConfigValue> get(const std::string& key) const;

    /**
     * @brief 获取值，带类型转换和默认值。
     */
    Result<bool>        get_bool(const std::string& key, bool default_val = false) const;
    Result<std::int64_t> get_int(const std::string& key, std::int64_t default_val = 0) const;
    Result<double>       get_double(const std::string& key, double default_val = 0.0) const;
    Result<std::string>  get_string(const std::string& key, const std::string& default_val = "") const;

    // ── 修改 ─────────────────────────────────────────────────────────────
    /**
     * @brief 设置配置值（运行时覆盖，不持久化）。
     */
    void set(const std::string& key, ConfigValue value);

    /**
     * @brief 重置为默认值。
     */
    void reset_to_defaults();

    /**
     * @brief 返回完整配置（JSON 字符串，用于诊断）。
     */
    [[nodiscard]] std::string to_json() const;

private:
    ConfigManager();
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

// ─────────────────────────────────────────────────────────────────────────────
//  便捷宏（类似 spdlog 的 SPDLOG_XXX）
// ─────────────────────────────────────────────────────────────────────────────
#define QOOCORE_GET_BOOL(key) \
    qoocore::ConfigManager::instance().get_bool(key).value_or(false)

#define QOOCORE_GET_INT(key) \
    qoocore::ConfigManager::instance().get_int(key).value_or(0)

#define QOOCORE_GET_STRING(key) \
    qoocore::ConfigManager::instance().get_string(key).value_or("")

} // namespace qoocore
