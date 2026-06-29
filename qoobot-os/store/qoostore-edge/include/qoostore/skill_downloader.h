#pragma once

#include "skill_types.h"
#include <string>
#include <functional>

namespace qoostore {
namespace edge {

using ProgressCallback = std::function<void(const std::string& skill_id, double progress)>;

/**
 * SkillDownloader — 技能包下载器
 * 支持断点续传、增量更新、完整性校验
 */
class SkillDownloader {
public:
    virtual ~SkillDownloader() = default;

    // 下载
    virtual void download(const std::string& url, const std::string& dest_path,
                           ProgressCallback progress = nullptr) = 0;
    virtual void downloadWithResume(const std::string& url, const std::string& dest_path,
                                     ProgressCallback progress = nullptr) = 0;

    // 增量更新
    virtual bool checkForDelta(const std::string& skill_id,
                                const std::string& current_version,
                                const std::string& target_version) = 0;
    virtual void downloadDelta(const std::string& skill_id,
                                const std::string& delta_url,
                                const std::string& dest_path,
                                ProgressCallback progress = nullptr) = 0;

    // 校验
    virtual bool validatePackage(const std::string& package_path,
                                  const std::string& expected_hash) = 0;
    virtual bool validateSignature(const std::string& package_path,
                                    const std::string& certificate) = 0;

    // 取消
    virtual void cancelDownload(const std::string& skill_id) = 0;
    virtual void cancelAll() = 0;

    // 状态
    virtual double getProgress(const std::string& skill_id) const = 0;
    virtual bool isDownloading(const std::string& skill_id) const = 0;
};

} // namespace edge
} // namespace qoostore
