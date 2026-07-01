#pragma once

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

inline std::vector<TestCase>& g_tests() {
    static std::vector<TestCase> tests;
    return tests;
}

struct TestRegistrar {
    TestRegistrar(const std::string& name, std::function<bool()> func) {
        g_tests().push_back({name, func});
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
