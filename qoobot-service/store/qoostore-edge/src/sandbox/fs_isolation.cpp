/**
 * fs_isolation.cpp — 文件系统隔离
 * 使用 OverlayFS 实现文件系统隔离：
 *   - lowerdir: 只读系统层 (/opt/qoo/system)
 *   - upperdir: 可写层 (/data/qoostore/sandboxes/{skill_id}/upper)
 *   - workdir: OverlayFS 工作目录
 *   - merged: 合并后的挂载点
 */
#include "qoostore/skill_types.h"
#include <iostream>
#include <filesystem>
#include <fstream>
#include <vector>
#include <string>
#include <sys/mount.h>
#include <sys/stat.h>
#include <unistd.h>

namespace qoostore::edge {

namespace fs = std::filesystem;

class FileSystemIsolation {
public:
    struct FsIsolationConfig {
        std::string skill_id;
        std::string sandbox_root;       // /var/run/qoostore/sandboxes/{skill_id}
        std::string lower_dir;          // 只读系统层
        std::string upper_dir;          // 可写层
        std::string work_dir;           // OverlayFS work dir
        std::string merged_dir;         // 合并挂载点
        std::vector<std::string> readonly_paths;   // 额外只读路径
        std::vector<std::string> writable_paths;   // 可写路径
        std::vector<std::string> hidden_paths;     // 完全隐藏的路径
    };

    explicit FileSystemIsolation(const FsIsolationConfig& config)
        : config_(config) {}

    /**
     * 设置文件系统隔离
     * 1. 创建必要的目录结构
     * 2. 挂载 OverlayFS
     * 3. 绑定挂载可写路径
     */
    bool setup() {
        std::cout << "[FsIsolation] Setting up filesystem isolation for: " << config_.skill_id << std::endl;

        // 创建目录结构
        if (!createDirectories()) {
            std::cerr << "[FsIsolation] Failed to create directories" << std::endl;
            return false;
        }

        // 挂载 OverlayFS
        if (!mountOverlayFS()) {
            std::cerr << "[FsIsolation] Failed to mount OverlayFS" << std::endl;
            return false;
        }

        // 绑定挂载可写路径
        for (const auto& path : config_.writable_paths) {
            if (!bindMount(path, config_.merged_dir + path)) {
                std::cerr << "[FsIsolation] Failed to bind mount: " << path << std::endl;
            }
        }

        std::cout << "[FsIsolation] Filesystem isolation ready" << std::endl;
        return true;
    }

    /**
     * 拆除文件系统隔离
     */
    bool teardown() {
        std::cout << "[FsIsolation] Tearing down filesystem isolation" << std::endl;

        // 卸载 merged 目录
        if (!unmount(config_.merged_dir)) {
            std::cerr << "[FsIsolation] Failed to unmount: " << config_.merged_dir << std::endl;
        }

        // 清理目录
        try {
            fs::remove_all(config_.sandbox_root);
        } catch (const std::exception& e) {
            std::cerr << "[FsIsolation] Cleanup error: " << e.what() << std::endl;
            return false;
        }

        return true;
    }

private:
    FsIsolationConfig config_;

    bool createDirectories() {
        try {
            fs::create_directories(config_.sandbox_root);
            fs::create_directories(config_.lower_dir);
            fs::create_directories(config_.upper_dir);
            fs::create_directories(config_.work_dir);
            fs::create_directories(config_.merged_dir);
            return true;
        } catch (const std::exception& e) {
            std::cerr << "[FsIsolation] Directory creation failed: " << e.what() << std::endl;
            return false;
        }
    }

    /**
     * 挂载 OverlayFS
     * mount -t overlay overlay -o lowerdir={lower},upperdir={upper},workdir={work} {merged}
     */
    bool mountOverlayFS() {
        std::string options = "lowerdir=" + config_.lower_dir
                            + ",upperdir=" + config_.upper_dir
                            + ",workdir=" + config_.work_dir;

        std::cout << "[FsIsolation] Mounting OverlayFS: " << options << " -> " << config_.merged_dir << std::endl;

        // 实际系统调用
        if (mount("overlay", config_.merged_dir.c_str(), "overlay", 0, options.c_str()) != 0) {
            perror("[FsIsolation] mount overlay failed");
            return false;
        }

        return true;
    }

    /**
     * 绑定挂载
     */
    bool bindMount(const std::string& source, const std::string& target) {
        // 确保目标目录存在
        fs::create_directories(target);

        if (mount(source.c_str(), target.c_str(), nullptr, MS_BIND, nullptr) != 0) {
            perror(("[FsIsolation] bind mount failed: " + source + " -> " + target).c_str());
            return false;
        }

        // 重新挂载为只读（如果需要）
        if (std::find(config_.readonly_paths.begin(), config_.readonly_paths.end(), source)
            != config_.readonly_paths.end()) {
            mount(nullptr, target.c_str(), nullptr, MS_REMOUNT | MS_RDONLY | MS_BIND, nullptr);
        }

        return true;
    }

    /**
     * 卸载文件系统
     */
    bool unmount(const std::string& path) {
        if (umount(path.c_str()) != 0) {
            // 尝试 lazy unmount
            if (umount2(path.c_str(), MNT_DETACH) != 0) {
                perror(("[FsIsolation] unmount failed: " + path).c_str());
                return false;
            }
        }
        return true;
    }
};

std::unique_ptr<FileSystemIsolation> createFileSystemIsolation(
        const FileSystemIsolation::FsIsolationConfig& config) {
    return std::make_unique<FileSystemIsolation>(config);
}

} // namespace qoostore::edge
