/**
 * test_main.cpp — 轻量级测试运行器
 *
 * 无外部测试框架依赖，直接运行所有测试用例。
 */

#include <iostream>
#include <string>
#include <vector>
#include <functional>
#include <chrono>
#include <iomanip>
#include <cstdlib>

struct TestCase {
    std::string name;
    std::function<bool()> func;
};

static std::vector<TestCase> g_tests;

struct TestRegistrar {
    TestRegistrar(const std::string& name, std::function<bool()> func) {
        g_tests.push_back({name, std::move(func)});
    }
};

#define TEST(name) \
    static bool test_##name(); \
    static TestRegistrar reg_##name(#name, test_##name); \
    static bool test_##name()

#define CHECK(expr) do { \
    if (!(expr)) { \
        std::cerr << "  FAIL at " << __FILE__ << ":" << __LINE__ << ": " << #expr << std::endl; \
        return false; \
    } \
} while(0)

#define CHECK_EQ(a, b) do { \
    if ((a) != (b)) { \
        std::cerr << "  FAIL at " << __FILE__ << ":" << __LINE__ << ": " \
                  << #a << " (" << (a) << ") != " << #b << " (" << (b) << ")" << std::endl; \
        return false; \
    } \
} while(0)

#define CHECK_CLOSE(a, b, eps) do { \
    if (std::abs((a) - (b)) > (eps)) { \
        std::cerr << "  FAIL at " << __FILE__ << ":" << __LINE__ << ": " \
                  << #a << " (" << (a) << ") not close to " << #b << " (" << (b) << ")" << std::endl; \
        return false; \
    } \
} while(0)

// 前向声明：各测试文件中的测试用例在这里注册
// （实际用例定义在各自 .cpp 文件中，通过 TEST 宏注册）

int main() {
    std::cout << "╔══════════════════════════════════════════════╗" << std::endl;
    std::cout << "║  qoostore-edge Test Suite v0.2.0             ║" << std::endl;
    std::cout << "╚══════════════════════════════════════════════╝" << std::endl;
    std::cout << std::endl;

    int passed = 0;
    int failed = 0;
    std::vector<std::string> failures;

    auto start_time = std::chrono::steady_clock::now();

    for (const auto& test : g_tests) {
        std::cout << "[RUN ] " << test.name << std::endl;
        auto test_start = std::chrono::steady_clock::now();

        try {
            if (test.func()) {
                auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
                    std::chrono::steady_clock::now() - test_start).count();
                std::cout << "[ OK ] " << test.name << " (" << elapsed << "ms)" << std::endl;
                passed++;
            } else {
                auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
                    std::chrono::steady_clock::now() - test_start).count();
                std::cout << "[FAIL] " << test.name << " (" << elapsed << "ms)" << std::endl;
                failed++;
                failures.push_back(test.name);
            }
        } catch (const std::exception& e) {
            std::cout << "[EXCP] " << test.name << " - " << e.what() << std::endl;
            failed++;
            failures.push_back(test.name);
        } catch (...) {
            std::cout << "[EXCP] " << test.name << " - unknown exception" << std::endl;
            failed++;
            failures.push_back(test.name);
        }
    }

    auto total_time = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - start_time).count();

    std::cout << std::endl;
    std::cout << "══════════════════════════════════════════════" << std::endl;
    std::cout << "  Total:   " << g_tests.size() << std::endl;
    std::cout << "  Passed:  " << passed << std::endl;
    std::cout << "  Failed:  " << failed << std::endl;
    std::cout << "  Time:    " << total_time << "ms" << std::endl;
    std::cout << "══════════════════════════════════════════════" << std::endl;

    if (!failures.empty()) {
        std::cout << "\nFailed tests:" << std::endl;
        for (const auto& name : failures) {
            std::cout << "  - " << name << std::endl;
        }
    }

    return failed > 0 ? 1 : 0;
}
