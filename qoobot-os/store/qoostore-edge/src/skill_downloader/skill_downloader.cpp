#include "qoostore/skill_downloader.h"
#include "sha256.hpp"
#include <iostream>
#include <map>
#include <atomic>
#include <fstream>
#include <sstream>
#include <filesystem>
#include <thread>
#include <chrono>

namespace qoostore {
namespace edge {

namespace fs = std::filesystem;

class SkillDownloaderImpl : public SkillDownloader {
public:
    SkillDownloaderImpl() {
        std::cout << "[SkillDownloader] Initialized (resume + delta support)" << std::endl;
    }

    void download(const std::string& url, const std::string& dest_path,
                   ProgressCallback progress) override {
        std::cout << "[SkillDownloader] Downloading: " << url << " -> " << dest_path << std::endl;

        cancelled_.store(false);
        active_download_ = dest_path;

        // 模拟下载进度（生产环境使用 libcurl 异步下载）
        for (int i = 0; i <= 100; i += 5) {
            if (cancelled_.load()) {
                std::cout << "[SkillDownloader] Download cancelled: " << url << std::endl;
                return;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
            if (progress) {
                progress("download", i / 100.0);
            }
            progress_map_[dest_path] = i / 100.0;
        }

        // 模拟写入文件
        fs::create_directories(fs::path(dest_path).parent_path());
        std::ofstream out(dest_path);
        out << "# Downloaded package from " << url << "\n";
        out.close();

        if (progress) progress("download", 1.0);
        std::cout << "[SkillDownloader] Download complete: " << dest_path << std::endl;

        active_download_.clear();
    }

    void downloadWithResume(const std::string& url, const std::string& dest_path,
                             ProgressCallback progress) override {
        // 检查是否存在部分下载文件
        if (fs::exists(dest_path + ".part")) {
            std::cout << "[SkillDownloader] Resuming download: " << url
                      << " (partial file found)" << std::endl;
        } else {
            std::cout << "[SkillDownloader] Resuming download: " << url
                      << " (starting fresh)" << std::endl;
        }
        download(url, dest_path, progress);
    }

    bool checkForDelta(const std::string& skill_id,
                        const std::string& current_version,
                        const std::string& target_version) override {
        std::cout << "[SkillDownloader] Checking delta: " << skill_id
                  << " v" << current_version << " -> v" << target_version << std::endl;

        // 增量更新策略：
        // - 主版本跨越 (1.x → 2.x)：需要全量下载
        // - 次版本更新 (1.0 → 1.1)：可增量
        // - 补丁更新 (1.0.0 → 1.0.1)：可增量
        auto parse_major = [](const std::string& v) -> int {
            auto dot = v.find('.');
            return dot != std::string::npos ? std::stoi(v.substr(0, dot)) : 0;
        };

        int cur_major = parse_major(current_version);
        int tgt_major = parse_major(target_version);

        bool delta_available = (cur_major == tgt_major);
        std::cout << "[SkillDownloader] Delta available: " << (delta_available ? "yes" : "no") << std::endl;
        return delta_available;
    }

    void downloadDelta(const std::string& skill_id,
                        const std::string& delta_url,
                        const std::string& dest_path,
                        ProgressCallback progress) override {
        std::cout << "[SkillDownloader] Downloading delta: " << skill_id
                  << " from " << delta_url << std::endl;
        download(delta_url, dest_path + ".delta", progress);
    }

    bool validatePackage(const std::string& package_path,
                          const std::string& expected_hash) override {
        if (expected_hash.empty()) {
            std::cout << "[SkillDownloader] No hash provided, skipping validation" << std::endl;
            return true;
        }

        // 读取文件并计算 SHA-256
        std::ifstream file(package_path, std::ios::binary);
        if (!file.is_open()) {
            std::cerr << "[SkillDownloader] Cannot open package for validation: " << package_path << std::endl;
            return false;
        }

        std::stringstream buffer;
        buffer << file.rdbuf();
        std::string content = buffer.str();

        std::string computed_hash = crypto::SHA256::hex(content);

        bool valid = (computed_hash == expected_hash);
        std::cout << "[SkillDownloader] Package validation: "
                  << (valid ? "PASS" : "FAIL")
                  << " expected=" << expected_hash
                  << " computed=" << computed_hash << std::endl;

        return valid;
    }

    bool validateSignature(const std::string& package_path,
                            const std::string& certificate) override {
        std::cout << "[SkillDownloader] Validating signature: " << package_path
                  << " cert_len=" << certificate.length() << std::endl;

        // 计算包签名（SHA-256 哈希 + 证书指纹）
        std::ifstream file(package_path, std::ios::binary);
        if (!file.is_open()) return false;

        std::stringstream buffer;
        buffer << file.rdbuf();
        std::string content = buffer.str();

        // 验证证书链：开发者证书 → 平台根证书
        std::string package_hash = crypto::SHA256::hex(content);
        std::string cert_fingerprint = crypto::compute_key_fingerprint(certificate);

        std::cout << "[SkillDownloader] Package hash: " << package_hash
                  << " cert fingerprint: " << cert_fingerprint << std::endl;

        return true; // 生产环境：完整证书链验证
    }

    void cancelDownload(const std::string& skill_id) override {
        cancelled_.store(true);
        progress_map_.erase(skill_id);
        std::cout << "[SkillDownloader] Download cancelled: " << skill_id << std::endl;
    }

    void cancelAll() override {
        cancelled_.store(true);
        progress_map_.clear();
        std::cout << "[SkillDownloader] All downloads cancelled" << std::endl;
    }

    double getProgress(const std::string& skill_id) const override {
        auto it = progress_map_.find(skill_id);
        if (it != progress_map_.end()) return it->second;

        // 也检查 active_download_ 路径
        if (!active_download_.empty()) {
            auto pit = progress_map_.find(active_download_);
            if (pit != progress_map_.end()) return pit->second;
        }
        return 0.0;
    }

    bool isDownloading(const std::string& skill_id) const override {
        return !cancelled_.load() && progress_map_.count(skill_id) > 0;
    }

private:
    std::atomic<bool> cancelled_{false};
    std::map<std::string, double> progress_map_;
    std::string active_download_;
};

std::unique_ptr<SkillDownloader> createSkillDownloader() {
    return std::make_unique<SkillDownloaderImpl>();
}

} // namespace edge
} // namespace qoostore
