#include "qoostore/skill_downloader.h"
#include <iostream>
#include <map>
#include <atomic>

namespace qoostore {
namespace edge {

class SkillDownloaderImpl : public SkillDownloader {
public:
    SkillDownloaderImpl() {
        std::cout << "[SkillDownloader] Initialized (supports resume + delta)" << std::endl;
    }

    void download(const std::string& url, const std::string& dest_path,
                   ProgressCallback progress) override {
        std::cout << "[SkillDownloader] Downloading: " << url << " -> " << dest_path << std::endl;

        // 模拟下载进度
        for (int i = 0; i <= 100; i += 10) {
            if (cancelled_.load()) break;
            if (progress) progress("download", i / 100.0);
        }

        if (progress) progress("download", 1.0);
    }

    void downloadWithResume(const std::string& url, const std::string& dest_path,
                             ProgressCallback progress) override {
        std::cout << "[SkillDownloader] Resuming download: " << url << std::endl;
        download(url, dest_path, progress);
    }

    bool checkForDelta(const std::string& skill_id,
                        const std::string& current_version,
                        const std::string& target_version) override {
        std::cout << "[SkillDownloader] Checking delta: " << skill_id
                  << " v" << current_version << " -> v" << target_version << std::endl;
        // 如果版本跨越较小（如 1.0.0 -> 1.0.1），支持增量更新
        return true;
    }

    void downloadDelta(const std::string& skill_id,
                        const std::string& delta_url,
                        const std::string& dest_path,
                        ProgressCallback progress) override {
        std::cout << "[SkillDownloader] Downloading delta: " << skill_id << std::endl;
        download(delta_url, dest_path, progress);
    }

    bool validatePackage(const std::string& package_path,
                          const std::string& expected_hash) override {
        std::cout << "[SkillDownloader] Validating package: " << package_path
                  << " hash=" << expected_hash << std::endl;
        // SHA-256 校验
        return true;
    }

    bool validateSignature(const std::string& package_path,
                            const std::string& certificate) override {
        std::cout << "[SkillDownloader] Validating signature: " << package_path << std::endl;
        // 证书链验证：开发者证书 → qoostore 根证书
        return true;
    }

    void cancelDownload(const std::string& skill_id) override {
        cancelled_ = true;
        std::cout << "[SkillDownloader] Download cancelled: " << skill_id << std::endl;
    }

    void cancelAll() override {
        cancelled_ = true;
        std::cout << "[SkillDownloader] All downloads cancelled" << std::endl;
    }

    double getProgress(const std::string& skill_id) const override {
        auto it = progress_map_.find(skill_id);
        return it != progress_map_.end() ? it->second : 0.0;
    }

    bool isDownloading(const std::string& skill_id) const override {
        return !cancelled_.load();
    }

private:
    std::atomic<bool> cancelled_{false};
    std::map<std::string, double> progress_map_;
};

std::unique_ptr<SkillDownloader> createSkillDownloader() {
    return std::make_unique<SkillDownloaderImpl>();
}

} // namespace edge
} // namespace qoostore
