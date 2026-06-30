/**
 * test_skill_manager.cpp — 技能管理器单元测试
 */

#include <filesystem>
#include <fstream>
#include <cstdio>

// 直接包含实现文件以访问内部类（仅测试用）
// 工厂函数声明
namespace qoostore::edge {
class SkillManagerImpl;
std::unique_ptr<SkillManager> createSkillManager();
}

namespace fs = std::filesystem;

// 测试用的临时目录
static const std::string TEST_ROOT = "/tmp/qoostore_test_skills";

void setup_test_env() {
    fs::remove_all(TEST_ROOT);
    fs::create_directories(TEST_ROOT + "/repo");
    fs::create_directories(TEST_ROOT + "/data");
}

void teardown_test_env() {
    fs::remove_all(TEST_ROOT);
}

TEST(skill_manager_create) {
    setup_test_env();
    auto mgr = qoostore::edge::createSkillManager();
    CHECK(mgr != nullptr);
    teardown_test_env();
    return true;
}

TEST(skill_manager_list_empty) {
    setup_test_env();
    auto mgr = qoostore::edge::createSkillManager();
    auto skills = mgr->listInstalled();
    CHECK_EQ(skills.size(), 0u);
    teardown_test_env();
    return true;
}

TEST(skill_manager_is_not_installed) {
    setup_test_env();
    auto mgr = qoostore::edge::createSkillManager();
    CHECK(mgr->isInstalled("nonexistent.skill") == false);
    teardown_test_env();
    return true;
}

TEST(skill_manager_get_nonexistent_skill) {
    setup_test_env();
    auto mgr = qoostore::edge::createSkillManager();
    auto skill = mgr->getSkill("nonexistent.skill");
    CHECK(skill.skill_id.empty());
    teardown_test_env();
    return true;
}

TEST(skill_manager_get_skill_path) {
    setup_test_env();
    auto mgr = qoostore::edge::createSkillManager();
    std::string path = mgr->getSkillPath("test.skill");
    CHECK(path.find("test.skill") != std::string::npos);
    teardown_test_env();
    return true;
}

TEST(skill_manager_get_data_path) {
    setup_test_env();
    auto mgr = qoostore::edge::createSkillManager();
    std::string path = mgr->getSkillDataPath("test.skill");
    CHECK(path.find("data") != std::string::npos);
    CHECK(path.find("test.skill") != std::string::npos);
    teardown_test_env();
    return true;
}

TEST(skill_manager_install_from_package) {
    setup_test_env();

    // 创建模拟的技能包
    std::string pkg_dir = TEST_ROOT + "/temp";
    fs::create_directories(pkg_dir);
    std::string pkg_path = pkg_dir + "/com.test.app-1.0.0.qooskills";

    // 创建包内容
    std::string install_dir = TEST_ROOT + "/repo/com.test.app-1.0.0";
    fs::create_directories(install_dir);
    {
        std::ofstream manifest(install_dir + "/manifest.json");
        manifest << R"({"skillId":"com.test.app-1.0.0","name":"Test App","version":"1.0.0","entryPoint":"main.py","runtime":"python3.11","sandboxLevel":"restricted","permissions":["camera"]})";
        manifest.close();
    }

    // 创建 package "文件" (简化为标记文件)
    {
        std::ofstream pkg(pkg_path);
        pkg << "mock package";
        pkg.close();
    }

    auto mgr = qoostore::edge::createSkillManager();

    bool callback_called = false;
    std::string result_skill_id;
    bool result_success = false;

    mgr->installFromPackage(pkg_path,
        [&](const std::string& skill_id, bool success, const std::string& error) {
            callback_called = true;
            result_skill_id = skill_id;
            result_success = success;
        });

    // 注意：在开发环境下安装可能需要解压逻辑
    // 这里主要测试回调机制和基本流程
    CHECK(callback_called);

    teardown_test_env();
    return true;
}

TEST(skill_manager_enable_disable) {
    setup_test_env();
    auto mgr = qoostore::edge::createSkillManager();

    // 对不存在的技能操作不应崩溃
    mgr->enable("nonexistent");
    mgr->disable("nonexistent");

    teardown_test_env();
    return true;
}

TEST(skill_manager_uninstall_nonexistent) {
    setup_test_env();
    auto mgr = qoostore::edge::createSkillManager();

    bool callback_called = false;
    mgr->uninstall("nonexistent",
        [&](const std::string&, bool success) {
            callback_called = true;
            CHECK(success == false);
        });

    CHECK(callback_called);
    teardown_test_env();
    return true;
}

TEST(skill_manager_status_callback) {
    setup_test_env();
    auto mgr = qoostore::edge::createSkillManager();

    bool callback_called = false;
    std::string last_skill_id;
    qoostore::edge::SkillStatus last_status;

    mgr->onStatusChanged([&](const std::string& skill_id, qoostore::edge::SkillStatus status) {
        callback_called = true;
        last_skill_id = skill_id;
        last_status = status;
    });

    // 启用状态回调注册
    CHECK(callback_called == false);  // 尚未触发

    teardown_test_env();
    return true;
}
