#include <iostream>
#include <string>
#include <vector>
#include <functional>
#include <chrono>
#include <cmath>

struct TestCase {
    std::string name;
    std::function<bool()> func;
};

static std::vector<TestCase> g_tests;

struct TestRegistrar {
    TestRegistrar(const std::string& name, std::function<bool()> func) {
        g_tests.push_back({name, func});
    }
};

#define TEST(name) \
    static bool test_##name(); \
    static TestRegistrar reg_##name(#name, test_##name); \
    static bool test_##name()

#define CHECK(expr) do { \
    if (!(expr)) { std::cerr << "  FAIL " << #expr << std::endl; return false; } \
} while(0)

#define CHECK_EQ(a, b) do { \
    if ((a) != (b)) { std::cerr << "  FAIL " << #a << " != " << #b << std::endl; return false; } \
} while(0)

#define CHECK_CLOSE(a, b, eps) do { \
    if (std::abs((a) - (b)) > (eps)) { \
        std::cerr << "  FAIL " << #a << " not close to " << #b << std::endl; return false; \
    } \
} while(0)

int main() {
    std::cout << "qooedge Test Suite v0.1.0" << std::endl << std::endl;

    int passed = 0, failed = 0;
    for (const auto& test : g_tests) {
        std::cout << "[RUN ] " << test.name << std::endl;
        try {
            if (test.func()) { std::cout << "[ OK ] " << test.name << std::endl; passed++; }
            else { std::cout << "[FAIL] " << test.name << std::endl; failed++; }
        } catch (const std::exception& e) {
            std::cout << "[EXCP] " << test.name << " - " << e.what() << std::endl;
            failed++;
        }
    }

    std::cout << "\nTotal: " << (passed + failed) << " Passed: " << passed << " Failed: " << failed << std::endl;
    return failed > 0 ? 1 : 0;
}
