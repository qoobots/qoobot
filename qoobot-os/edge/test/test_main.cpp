#include "test_common.h"

int main() {
    std::cout << "qooedge Test Suite v0.1.0" << std::endl << std::endl;

    int passed = 0, failed = 0;
    for (const auto& test : g_tests()) {
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
