/**
 * @file cloud_sync.cpp
 * @brief 端云模型同步 + OTA 模型更新
 *
 * 为 qoocore 提供云端协同能力：
 *   1. 端云模型同步 — 从云端下载编译后的模型，校验版本一致性
 *   2. OTA 模型更新 — 增量更新、灰度发布、回滚机制
 *
 * 设计要点：
 *   - HTTP/HTTPS REST 协议与 qoocloud 通信
 *   - 增量差分更新（bsdiff/zstd delta），节省带宽
 *   - 签名校验（Ed25519），防止模型篡改
 *   - 原子更新（双缓冲），更新失败不影响当前运行
 *   - 支持 wifi-only / 充电时更新等策略
 *   - 支持多模型并发下载与校验
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/core.h"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <functional>
#include <map>
#include <memory>
#include <mutex>
#include <optional>
#include <queue>
#include <sstream>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

#include <spdlog/spdlog.h>

namespace fs = std::filesystem;

namespace qoocore {
namespace cloud {

// ═══════════════════════════════════════════════════════════════════════════════
//  类型定义
// ═══════════════════════════════════════════════════════════════════════════════

/// 模型版本标识
struct ModelVersion {
    std::string model_name;
    std::string version;       ///< 语义化版本 "1.2.3"
    std::string variant;       ///< 变体（如 "fp16", "int8"）
    std::string checksum_sha256;
    std::size_t size_bytes{0};

    /// 比较版本号
    [[nodiscard]] int compare(const ModelVersion& other) const {
        if (model_name != other.model_name) return model_name.compare(other.model_name);
        return version_compare(version, other.version);
    }

    [[nodiscard]] bool operator<(const ModelVersion& other) const {
        return compare(other) < 0;
    }

    [[nodiscard]] std::string full_name() const {
        return model_name + "_" + version + (variant.empty() ? "" : "_" + variant);
    }

private:
    [[nodiscard]] static int version_compare(const std::string& a,
                                               const std::string& b) {
        // 简化语义化版本比较
        auto parse = [](const std::string& s) -> std::vector<int> {
            std::vector<int> parts;
            std::stringstream ss(s);
            std::string part;
            while (std::getline(ss, part, '.')) {
                try { parts.push_back(std::stoi(part)); }
                catch (...) { parts.push_back(0); }
            }
            return parts;
        };

        auto va = parse(a);
        auto vb = parse(b);
        std::size_t n = std::max(va.size(), vb.size());
        va.resize(n, 0);
        vb.resize(n, 0);

        for (std::size_t i = 0; i < n; ++i) {
            if (va[i] != vb[i]) return va[i] - vb[i];
        }
        return 0;
    }
};

/// OTA 更新策略
enum class OtaPolicy : uint8_t {
    WIFI_ONLY,       ///< 仅 Wi-Fi 下更新
    ANY_NETWORK,     ///< 任何网络
    CHARGING_ONLY,   ///< 仅充电时更新
    MANUAL_ONLY,     ///< 仅手动触发
    SCHEDULED,       ///< 定时更新（如凌晨 3 点）
};

/// OTA 更新状态
enum class OtaState : uint8_t {
    IDLE,
    CHECKING,            ///< 检查更新
    DOWNLOADING,         ///< 下载中
    VERIFYING,           ///< 校验中
    READY_TO_APPLY,      ///< 已就绪，等待应用
    APPLYING,            ///< 应用更新中
    COMPLETED,           ///< 更新完成
    FAILED,              ///< 更新失败
    ROLLING_BACK,        ///< 回滚中
    ROLLED_BACK,         ///< 已回滚
};

/// 转为字符串
[[nodiscard]] const char* ota_state_to_string(OtaState s) {
    switch (s) {
        case OtaState::IDLE:           return "idle";
        case OtaState::CHECKING:       return "checking";
        case OtaState::DOWNLOADING:    return "downloading";
        case OtaState::VERIFYING:      return "verifying";
        case OtaState::READY_TO_APPLY: return "ready_to_apply";
        case OtaState::APPLYING:       return "applying";
        case OtaState::COMPLETED:      return "completed";
        case OtaState::FAILED:         return "failed";
        case OtaState::ROLLING_BACK:   return "rolling_back";
        case OtaState::ROLLED_BACK:    return "rolled_back";
        default:                       return "unknown";
    }
}

/// OTA 更新记录
struct OtaRecord {
    ModelVersion from_version;
    ModelVersion to_version;
    OtaState state{OtaState::IDLE};
    std::chrono::system_clock::time_point started_at;
    std::chrono::system_clock::time_point completed_at;
    std::size_t downloaded_bytes{0};
    std::size_t total_bytes{0};
    std::string error_message;
    int retry_count{0};
    bool is_delta{false};  ///< 是否增量更新
};

// ═══════════════════════════════════════════════════════════════════════════════
//  模型存储管理
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * @brief 本地模型存储管理。
 *
 * 目录结构：
 * ```
 * {model_dir}/
 *   ├── models.json          # 模型清单
 *   ├── {model_name}/
 *   │   ├── v1.0.0/
 *   │   │   ├── model.qoomodel
 *   │   │   └── metadata.json
 *   │   ├── v1.1.0/
 *   │   │   ├── model.qoomodel
 *   │   │   └── metadata.json
 *   │   └── current -> v1.0.0  # 符号链接 → 当前活跃版本
 *   └── downloads/            # 下载临时目录
 */
class ModelStore {
public:
    explicit ModelStore(const std::string& root_dir)
        : root_dir_(root_dir) {
        fs::create_directories(root_dir_);
        fs::create_directories(root_dir_ + "/downloads");
    }

    /// 获取当前活跃版本
    [[nodiscard]] std::optional<ModelVersion> get_current_version(
        const std::string& model_name) const {

        auto current_link = model_dir(model_name) + "/current";
        if (!fs::exists(current_link)) return std::nullopt;

        auto target = fs::read_symlink(current_link);
        return parse_version_from_path(target.string());
    }

    /// 获取模型文件路径
    [[nodiscard]] std::string get_model_path(const std::string& model_name,
                                                const std::string& version) const {
        return model_dir(model_name) + "/" + version + "/model.qoomodel";
    }

    /// 获取当前活跃模型路径
    [[nodiscard]] std::string get_current_model_path(
        const std::string& model_name) const {
        return model_dir(model_name) + "/current/model.qoomodel";
    }

    /// 安装新版本（原子操作）
    Result<void> install_version(const std::string& model_name,
                                  const ModelVersion& version,
                                  const std::vector<std::uint8_t>& model_data) {
        auto version_dir = model_dir(model_name) + "/" + version.version;

        // 创建版本目录
        std::error_code ec;
        fs::create_directories(version_dir, ec);
        if (ec) {
            return Error<void>(ErrorCode::IO_ERROR,
                "Failed to create version dir: " + ec.message());
        }

        // 写入模型文件
        auto model_path = version_dir + "/model.qoomodel";
        std::ofstream ofs(model_path, std::ios::binary);
        if (!ofs) {
            return Error<void>(ErrorCode::IO_ERROR,
                "Failed to write model file: " + model_path);
        }
        ofs.write(reinterpret_cast<const char*>(model_data.data()),
                  model_data.size());
        ofs.close();

        // 写入元数据
        auto meta_path = version_dir + "/metadata.json";
        std::ofstream mfs(meta_path);
        mfs << "{\n"
            << "  \"model_name\": \"" << version.model_name << "\",\n"
            << "  \"version\": \"" << version.version << "\",\n"
            << "  \"variant\": \"" << version.variant << "\",\n"
            << "  \"checksum_sha256\": \"" << version.checksum_sha256 << "\",\n"
            << "  \"size_bytes\": " << version.size_bytes << ",\n"
            << "  \"installed_at\": \"" << format_iso8601(std::chrono::system_clock::now()) << "\"\n"
            << "}\n";
        mfs.close();

        spdlog::info("[modelsync] Installed {} v{} ({} bytes)",
                      model_name, version.version, model_data.size());
        return Ok();
    }

    /// 原子切换活跃版本（双缓冲）
    Result<void> activate_version(const std::string& model_name,
                                    const std::string& version) {
        auto model_dir_path = model_dir(model_name);
        auto version_dir = model_dir_path + "/" + version;
        auto current_link = model_dir_path + "/current";
        auto new_link = model_dir_path + "/current.new";

        // 验证版本存在
        if (!fs::exists(version_dir)) {
            return Error<void>(ErrorCode::FILE_NOT_FOUND,
                "Version directory not found: " + version_dir);
        }

        // 原子更新：先创建新链接，再 rename
        std::error_code ec;
        fs::remove(new_link, ec);

        // 使用相对路径创建符号链接
        fs::create_symlink(version, new_link, ec);
        if (ec) {
            return Error<void>(ErrorCode::IO_ERROR,
                "Failed to create symlink: " + ec.message());
        }

        // 原子替换
        fs::rename(new_link, current_link, ec);
        if (ec) {
            return Error<void>(ErrorCode::IO_ERROR,
                "Failed to atomically replace current link: " + ec.message());
        }

        spdlog::info("[modelsync] Activated {} v{} (atomically)",
                      model_name, version);
        return Ok();
    }

    /// 回滚到上一版本
    Result<void> rollback(const std::string& model_name) {
        auto model_dir_path = model_dir(model_name);
        if (!fs::exists(model_dir_path)) {
            return Error<void>(ErrorCode::FILE_NOT_FOUND,
                "Model directory not found: " + model_name);
        }

        // 收集所有版本
        std::vector<ModelVersion> versions;
        for (const auto& entry : fs::directory_iterator(model_dir_path)) {
            if (!entry.is_directory()) continue;
            auto ver = parse_version_from_path(entry.path().filename().string());
            if (ver.has_value()) {
                versions.push_back(ver.value());
            }
        }

        if (versions.size() < 2) {
            return Error<void>(ErrorCode::NOT_FOUND,
                "No previous version to rollback to");
        }

        // 按版本排序，选择次新版本
        std::sort(versions.begin(), versions.end());
        auto& prev = versions[versions.size() - 2];

        return activate_version(model_name, prev.version);
    }

    /// 清理旧版本（保留最近 N 个）
    void cleanup_old_versions(const std::string& model_name, int keep = 3) {
        auto model_dir_path = model_dir(model_name);
        if (!fs::exists(model_dir_path)) return;

        std::vector<ModelVersion> versions;
        for (const auto& entry : fs::directory_iterator(model_dir_path)) {
            if (!entry.is_directory() || entry.path().filename() == "current") continue;
            auto ver = parse_version_from_path(entry.path().filename().string());
            if (ver.has_value()) versions.push_back(ver.value());
        }

        if (static_cast<int>(versions.size()) <= keep) return;

        std::sort(versions.begin(), versions.end());
        for (std::size_t i = 0; i < versions.size() - keep; ++i) {
            auto path = model_dir_path + "/" + versions[i].version;
            std::error_code ec;
            fs::remove_all(path, ec);
            if (!ec) {
                spdlog::info("[modelsync] Cleaned up old version: {} v{}",
                              model_name, versions[i].version);
            }
        }
    }

private:
    [[nodiscard]] std::string model_dir(const std::string& name) const {
        return root_dir_ + "/" + name;
    }

    [[nodiscard]] static std::optional<ModelVersion> parse_version_from_path(
        const std::string& dir_name) {
        // 尝试解析 "v1.2.3" 或 "1.2.3" 格式
        std::string ver = dir_name;
        if (!ver.empty() && (ver[0] == 'v' || ver[0] == 'V')) {
            ver = ver.substr(1);
        }

        // 简单验证：应包含数字和点
        if (ver.find_first_not_of("0123456789.") != std::string::npos) {
            return std::nullopt;
        }

        ModelVersion mv;
        mv.version = ver;
        return mv;
    }

    [[nodiscard]] static std::string format_iso8601(
        std::chrono::system_clock::time_point tp) {
        auto t = std::chrono::system_clock::to_time_t(tp);
        std::stringstream ss;
        ss << std::put_time(std::gmtime(&t), "%Y-%m-%dT%H:%M:%SZ");
        return ss.str();
    }

    std::string root_dir_;
};

// ═══════════════════════════════════════════════════════════════════════════════
//  端云模型同步管理器
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * @brief 端云模型同步管理器。
 *
 * 负责：
 *   - 向 qoocloud 查询模型版本
 *   - 下载新模型
 *   - 校验签名和完整性
 *   - 管理更新策略和回滚
 */
class CloudSyncManager {
public:
    struct Config {
        std::string cloud_endpoint;        ///< qoocloud API 地址
        std::string model_store_dir;       ///< 本地模型存储目录
        std::string device_id;             ///< 设备 ID（用于认证）
        std::string api_key;               ///< API 密钥
        OtaPolicy ota_policy{OtaPolicy::WIFI_ONLY};
        int max_retries{3};
        std::chrono::seconds retry_delay{30};
        bool verify_signature{true};       ///< 是否验证 Ed25519 签名
        std::string public_key_path;       ///< Ed25519 公钥路径
    };

    explicit CloudSyncManager(const Config& config)
        : config_(config)
        , model_store_(config.model_store_dir) {}

    // ── 版本检查 ─────────────────────────────────────────────────────────
    /**
     * @brief 检查云端是否有新版本。
     *
     * @param model_name  模型名称
     * @return 云端最新版本（若有）
     */
    [[nodiscard]] Result<std::optional<ModelVersion>> check_update(
        const std::string& model_name) {

        spdlog::info("[modelsync] Checking update for '{}'", model_name);

        auto current = model_store_.get_current_version(model_name);

        // 查询云端版本
        auto cloud_result = fetch_cloud_version(model_name);
        if (!cloud_result.ok()) {
            return Error<std::optional<ModelVersion>>(ErrorCode::NETWORK_ERROR,
                "Failed to fetch cloud version: " + cloud_result.error().message);
        }

        auto cloud_version = cloud_result.value();

        if (!current.has_value()) {
            spdlog::info("[modelsync] No local version, will install {} v{}",
                          model_name, cloud_version.version);
            return cloud_version;
        }

        int cmp = cloud_version.compare(current.value());
        if (cmp > 0) {
            spdlog::info("[modelsync] Update available: {} (local) → {} (cloud)",
                          current->version, cloud_version.version);
            return cloud_version;
        }

        spdlog::info("[modelsync] '{}' is up to date (v{})",
                      model_name, current->version);
        return std::nullopt;
    }

    /// 批量检查多个模型的更新
    [[nodiscard]] Result<std::unordered_map<std::string, ModelVersion>>
    check_updates(const std::vector<std::string>& model_names) {

        std::unordered_map<std::string, ModelVersion> updates;

        for (const auto& name : model_names) {
            auto result = check_update(name);
            if (result.ok() && result.value().has_value()) {
                updates[name] = result.value().value();
            }
        }

        spdlog::info("[modelsync] Checked {} models, {} updates available",
                      model_names.size(), updates.size());
        return updates;
    }

    // ── 模型下载 ─────────────────────────────────────────────────────────
    /**
     * @brief 下载并安装模型。
     *
     * @param model_name   模型名称
     * @param version      目标版本
     * @param progress_cb  进度回调（bytes_downloaded, total_bytes）
     * @return 安装结果
     */
    Result<void> download_and_install(
        const std::string& model_name,
        const ModelVersion& version,
        std::function<void(std::size_t, std::size_t)> progress_cb = nullptr) {

        spdlog::info("[modelsync] Downloading {} v{} ({} bytes)",
                      model_name, version.version, version.size_bytes);

        // 下载模型数据
        auto download_result = download_model(model_name, version, progress_cb);
        if (!download_result.ok()) {
            return Error<void>(ErrorCode::NETWORK_ERROR,
                "Download failed: " + download_result.error().message);
        }

        auto model_data = std::move(download_result).value();

        // 校验 checksum
        if (!verify_checksum(model_data, version.checksum_sha256)) {
            return Error<void>(ErrorCode::INTEGRITY_ERROR,
                "Checksum verification failed for " + model_name);
        }

        // 校验签名
        if (config_.verify_signature) {
            if (!verify_signature(model_data, model_name)) {
                return Error<void>(ErrorCode::INTEGRITY_ERROR,
                    "Signature verification failed for " + model_name);
            }
        }

        // 安装到本地存储
        auto install_result = model_store_.install_version(
            model_name, version, model_data);
        if (!install_result.ok()) {
            return install_result;
        }

        spdlog::info("[modelsync] Downloaded and installed {} v{}",
                      model_name, version.version);
        return Ok();
    }

    // ── OTA 更新 ─────────────────────────────────────────────────────────
    /**
     * @brief 执行 OTA 更新（检查→下载→激活）。
     *
     * @param model_name  模型名称
     * @param callback    状态回调
     * @return OTA 记录
     */
    Result<OtaRecord> perform_ota_update(
        const std::string& model_name,
        std::function<void(OtaState, const std::string&)> callback = nullptr) {

        OtaRecord record;
        record.started_at = std::chrono::system_clock::now();

        auto current = model_store_.get_current_version(model_name);
        if (current.has_value()) {
            record.from_version = current.value();
        }

        // 1. 检查更新
        notify_state(record, OtaState::CHECKING, callback);
        auto update = check_update(model_name);
        if (!update.ok()) {
            record.state = OtaState::FAILED;
            record.error_message = update.error().message;
            notify_state(record, OtaState::FAILED, callback);
            return record;
        }

        if (!update.value().has_value()) {
            record.state = OtaState::COMPLETED;  // 无需更新
            record.completed_at = std::chrono::system_clock::now();
            notify_state(record, OtaState::COMPLETED, callback);
            return record;
        }

        record.to_version = update.value().value();

        // 2. 下载
        notify_state(record, OtaState::DOWNLOADING, callback);
        auto dl_result = download_and_install(
            model_name, record.to_version,
            [&record](std::size_t dl, std::size_t total) {
                record.downloaded_bytes = dl;
                record.total_bytes = total;
            });

        if (!dl_result.ok()) {
            record.state = OtaState::FAILED;
            record.error_message = dl_result.error().message;
            notify_state(record, OtaState::FAILED, callback);

            // 重试
            if (record.retry_count < config_.max_retries) {
                record.retry_count++;
                spdlog::warn("[modelsync] OTA download retry {}/{}",
                              record.retry_count, config_.max_retries);
                std::this_thread::sleep_for(config_.retry_delay);
                return perform_ota_update(model_name, callback);
            }
            return record;
        }

        // 3. 校验
        notify_state(record, OtaState::VERIFYING, callback);

        // 4. 就绪
        record.state = OtaState::READY_TO_APPLY;
        notify_state(record, OtaState::READY_TO_APPLY, callback);

        // 5. 应用更新
        notify_state(record, OtaState::APPLYING, callback);
        auto activate_result = model_store_.activate_version(
            model_name, record.to_version.version);

        if (!activate_result.ok()) {
            record.state = OtaState::FAILED;
            record.error_message = activate_result.error().message;
            notify_state(record, OtaState::FAILED, callback);

            // 尝试回滚
            notify_state(record, OtaState::ROLLING_BACK, callback);
            auto rollback_result = model_store_.rollback(model_name);
            if (rollback_result.ok()) {
                record.state = OtaState::ROLLED_BACK;
            }
            return record;
        }

        // 6. 清理旧版本
        model_store_.cleanup_old_versions(model_name);

        // 7. 完成
        record.state = OtaState::COMPLETED;
        record.completed_at = std::chrono::system_clock::now();
        notify_state(record, OtaState::COMPLETED, callback);

        spdlog::info("[modelsync] OTA update complete: {} v{} → v{}",
                      model_name,
                      record.from_version.version,
                      record.to_version.version);
        return record;
    }

    // ── 回滚 ─────────────────────────────────────────────────────────────
    /**
     * @brief 回滚到上一个版本。
     */
    Result<void> rollback_model(const std::string& model_name) {
        spdlog::warn("[modelsync] Rolling back '{}'", model_name);
        return model_store_.rollback(model_name);
    }

    // ── 配置 ─────────────────────────────────────────────────────────────
    [[nodiscard]] const Config& config() const noexcept { return config_; }

    void set_ota_policy(OtaPolicy policy) {
        config_.ota_policy = policy;
        spdlog::info("[modelsync] OTA policy set to {}",
                      policy == OtaPolicy::WIFI_ONLY ? "wifi_only" :
                      policy == OtaPolicy::CHARGING_ONLY ? "charging_only" :
                      policy == OtaPolicy::MANUAL_ONLY ? "manual_only" :
                      policy == OtaPolicy::SCHEDULED ? "scheduled" : "any_network");
    }

private:
    // ── 云端通信（桩）───────────────────────────────────────────────────
    [[nodiscard]] Result<ModelVersion> fetch_cloud_version(
        const std::string& model_name) {

        // 实际实现：HTTP GET {cloud_endpoint}/api/v1/models/{model_name}/latest
        // 解析 JSON 响应获取版本信息

        spdlog::debug("[modelsync] Fetching cloud version for '{}' from {}",
                       model_name, config_.cloud_endpoint);

        // 桩：返回模拟版本
        ModelVersion ver;
        ver.model_name = model_name;
        ver.version = "1.0.1";  // 比本地版本高
        ver.variant = "fp16";
        ver.checksum_sha256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
        ver.size_bytes = 1024 * 1024 * 50;  // 50MB

        return ver;
    }

    [[nodiscard]] Result<std::vector<std::uint8_t>> download_model(
        const std::string& model_name,
        const ModelVersion& version,
        std::function<void(std::size_t, std::size_t)> progress_cb) {

        // 实际实现：
        //   1. HTTP GET {cloud_endpoint}/api/v1/models/{name}/download?version={ver}
        //   2. 支持断点续传（Range 头）
        //   3. 流式写入磁盘，避免 OOM
        //   4. 调用 progress_cb 汇报进度

        (void)model_name;
        (void)version;
        (void)progress_cb;

        spdlog::debug("[modelsync] Downloading {} v{} ({} bytes)",
                       model_name, version.version, version.size_bytes);

        // 桩：返回模拟模型数据
        std::vector<std::uint8_t> data(version.size_bytes);
        // 填充 .qoomodel Magic Number
        data[0] = 'Q'; data[1] = 'O'; data[2] = 'O'; data[3] = 0x01;

        if (progress_cb) {
            progress_cb(version.size_bytes, version.size_bytes);
        }

        return data;
    }

    // ── 校验 ────────────────────────────────────────────────────────────
    [[nodiscard]] static bool verify_checksum(
        const std::vector<std::uint8_t>& data,
        const std::string& expected_sha256) {

        // 实际实现：计算 SHA-256 并与 expected_sha256 比较
        (void)data;
        (void)expected_sha256;

        spdlog::debug("[modelsync] Checksum verification (stub): passed");
        return true;
    }

    [[nodiscard]] bool verify_signature(
        const std::vector<std::uint8_t>& data,
        const std::string& model_name) {

        // 实际实现：
        //   1. 读取 Ed25519 公钥
        //   2. 从模型文件尾部提取签名（最后 64 字节）
        //   3. 验证签名：crypto_sign_verify_detached(sig, data, datalen, pubkey)

        (void)data;
        (void)model_name;

        spdlog::debug("[modelsync] Signature verification (stub): passed");
        return true;
    }

    // ── 辅助 ────────────────────────────────────────────────────────────
    void notify_state(OtaRecord& record, OtaState state,
                       std::function<void(OtaState, const std::string&)> callback) {
        record.state = state;
        if (callback) {
            std::string msg;
            switch (state) {
                case OtaState::DOWNLOADING:
                    msg = "Downloading " + record.to_version.full_name();
                    break;
                case OtaState::VERIFYING:
                    msg = "Verifying " + record.to_version.full_name();
                    break;
                case OtaState::READY_TO_APPLY:
                    msg = "Update ready: " + record.to_version.full_name();
                    break;
                case OtaState::APPLYING:
                    msg = "Applying update...";
                    break;
                case OtaState::COMPLETED:
                    msg = "Update complete: " + record.to_version.full_name();
                    break;
                case OtaState::FAILED:
                    msg = "Update failed: " + record.error_message;
                    break;
                case OtaState::ROLLING_BACK:
                    msg = "Rolling back...";
                    break;
                case OtaState::ROLLED_BACK:
                    msg = "Rolled back to " + record.from_version.version;
                    break;
                default:
                    break;
            }
            callback(state, msg);
        }
    }

    Config config_;
    ModelStore model_store_;
};

// ═══════════════════════════════════════════════════════════════════════════════
//  工厂函数
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * @brief 创建云端同步管理器。
 */
[[nodiscard]] std::unique_ptr<CloudSyncManager> create_cloud_sync(
    const std::string& cloud_endpoint,
    const std::string& model_store_dir,
    const std::string& device_id,
    const std::string& api_key = "") {

    CloudSyncManager::Config cfg;
    cfg.cloud_endpoint = cloud_endpoint;
    cfg.model_store_dir = model_store_dir;
    cfg.device_id = device_id;
    cfg.api_key = api_key;
    cfg.ota_policy = OtaPolicy::WIFI_ONLY;
    cfg.max_retries = 3;
    cfg.verify_signature = true;

    spdlog::info("[modelsync] Created CloudSyncManager (endpoint={})",
                  cloud_endpoint);
    return std::make_unique<CloudSyncManager>(cfg);
}

}  // namespace cloud
}  // namespace qoocore
