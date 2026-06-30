/**
 * test_dependency_resolver.cpp — 依赖解析器单元测试
 */

#include "qoostore/skill_resolver.h"

using namespace qoostore::edge;

std::unique_ptr<SkillResolver> create_test_resolver() {
    auto resolver = createSkillResolver();

    // 注册已安装的技能
    resolver->registerInstalled("com.qoobot.core", "1.0.0");

    return resolver;
}

TEST(resolver_empty_deps) {
    auto resolver = create_test_resolver();
    resolver->registerAvailable("com.test.simple", "1.0.0", {});

    auto result = resolver->resolve("com.test.simple", "1.0.0");
    CHECK(result.success);
    CHECK_EQ(result.install_order.size(), 0u);  // 无依赖，无需额外安装
    return true;
}

TEST(resolver_single_dep) {
    auto resolver = create_test_resolver();
    resolver->registerAvailable("com.qoobot.navigation", "1.0.0", {});
    resolver->registerAvailable("com.qoobot.cleaning", "1.0.0", {
        {"com.qoobot.navigation", ">=1.0.0", false, "Navigation required"}
    });

    auto result = resolver->resolve("com.qoobot.cleaning", "1.0.0");
    CHECK(result.success);
    // 安装顺序：先 navigation 再 cleaning
    CHECK(result.install_order.size() >= 1u);
    return true;
}

TEST(resolver_already_installed_satisfied) {
    auto resolver = create_test_resolver();
    resolver->registerInstalled("com.qoobot.navigation", "1.0.0");

    resolver->registerAvailable("com.qoobot.navigation", "1.0.0", {});
    resolver->registerAvailable("com.qoobot.cleaning", "1.0.0", {
        {"com.qoobot.navigation", ">=1.0.0", false, "Navigation required"}
    });

    auto result = resolver->resolve("com.qoobot.cleaning", "1.0.0");
    CHECK(result.success);
    // 已安装的依赖不需要重新安装
    for (const auto& id : result.install_order) {
        CHECK(id != "com.qoobot.navigation");
    }
    return true;
}

TEST(resolver_missing_required_dep) {
    auto resolver = create_test_resolver();
    resolver->registerAvailable("com.qoobot.cleaning", "1.0.0", {
        {"com.qoobot.missing", ">=1.0.0", false, "Missing dependency"}
    });

    auto result = resolver->resolve("com.qoobot.cleaning", "1.0.0");
    CHECK(result.success == false);
    CHECK(result.missing.size() >= 1u);
    return true;
}

TEST(resolver_optional_missing_ok) {
    auto resolver = create_test_resolver();
    resolver->registerAvailable("com.qoobot.cleaning", "1.0.0", {
        {"com.qoobot.optional_feature", ">=1.0.0", true, "Optional feature"}
    });

    auto result = resolver->resolve("com.qoobot.cleaning", "1.0.0");
    CHECK(result.success);
    CHECK_EQ(result.install_order.size(), 0u);
    return true;
}

TEST(resolver_check_dependencies) {
    auto resolver = create_test_resolver();
    resolver->registerInstalled("com.qoobot.navigation", "1.0.0");
    resolver->registerInstalled("com.qoobot.vision", "1.0.0");

    resolver->registerAvailable("com.qoobot.navigation", "1.0.0", {});
    resolver->registerAvailable("com.qoobot.cleaning", "1.0.0", {
        {"com.qoobot.navigation", ">=1.0.0", false, "Navigation"},
        {"com.qoobot.vision", ">=1.0.0", false, "Vision"}
    });

    CHECK(resolver->checkDependencies("com.qoobot.cleaning"));
    return true;
}

TEST(resolver_check_dependencies_missing) {
    auto resolver = create_test_resolver();
    resolver->registerInstalled("com.qoobot.navigation", "1.0.0");

    resolver->registerAvailable("com.qoobot.cleaning", "1.0.0", {
        {"com.qoobot.navigation", ">=1.0.0", false, "Navigation"},
        {"com.qoobot.missing", ">=1.0.0", false, "Missing"}
    });

    CHECK(resolver->checkDependencies("com.qoobot.cleaning") == false);
    return true;
}

TEST(resolver_transitive_deps) {
    auto resolver = create_test_resolver();
    resolver->registerAvailable("com.qoobot.base", "1.0.0", {});
    resolver->registerAvailable("com.qoobot.navigation", "1.0.0", {
        {"com.qoobot.base", ">=1.0.0", false, "Base library"}
    });
    resolver->registerAvailable("com.qoobot.cleaning", "1.0.0", {
        {"com.qoobot.navigation", ">=1.0.0", false, "Navigation"},
        {"com.qoobot.base", ">=1.0.0", false, "Base library"}
    });

    auto deps = resolver->getTransitiveDeps("com.qoobot.cleaning");
    CHECK(deps.size() >= 2u);
    return true;
}

TEST(resolver_no_cycles_simple) {
    auto resolver = create_test_resolver();
    resolver->registerAvailable("com.test.a", "1.0.0", {});
    resolver->registerAvailable("com.test.b", "1.0.0", {
        {"com.test.a", ">=1.0.0", false, "Depends on A"}
    });

    auto cycles = resolver->detectCycles();
    CHECK_EQ(cycles.size(), 0u);
    return true;
}

TEST(resolver_version_satisfies) {
    auto resolver = create_test_resolver();
    resolver->registerInstalled("com.qoobot.lib", "1.2.0");

    resolver->registerAvailable("com.qoobot.lib", "1.2.0", {});
    resolver->registerAvailable("com.qoobot.app", "1.0.0", {
        {"com.qoobot.lib", ">=1.0.0", false, "Library >= 1.0.0"}
    });

    CHECK(resolver->checkDependencies("com.qoobot.app"));
    return true;
}

TEST(resolver_version_not_satisfies) {
    auto resolver = create_test_resolver();
    resolver->registerInstalled("com.qoobot.lib", "0.9.0");

    resolver->registerAvailable("com.qoobot.lib", "0.9.0", {});
    resolver->registerAvailable("com.qoobot.app", "1.0.0", {
        {"com.qoobot.lib", ">=1.0.0", false, "Library >= 1.0.0"}
    });

    CHECK(resolver->checkDependencies("com.qoobot.app") == false);
    return true;
}

TEST(resolver_install_order_topological) {
    auto resolver = create_test_resolver();
    resolver->registerAvailable("com.qoobot.layer3", "1.0.0", {});
    resolver->registerAvailable("com.qoobot.layer2", "1.0.0", {
        {"com.qoobot.layer3", ">=1.0.0", false, "Layer 3"}
    });
    resolver->registerAvailable("com.qoobot.layer1", "1.0.0", {
        {"com.qoobot.layer2", ">=1.0.0", false, "Layer 2"},
        {"com.qoobot.layer3", ">=1.0.0", false, "Layer 3"}
    });

    auto result = resolver->resolve("com.qoobot.layer1", "1.0.0");
    CHECK(result.success);

    // 验证拓扑顺序：layer3 和 layer2 应该在 layer1 之前
    int layer3_pos = -1, layer2_pos = -1, layer1_pos = -1;
    for (size_t i = 0; i < result.install_order.size(); i++) {
        if (result.install_order[i] == "com.qoobot.layer3") layer3_pos = static_cast<int>(i);
        if (result.install_order[i] == "com.qoobot.layer2") layer2_pos = static_cast<int>(i);
        if (result.install_order[i] == "com.qoobot.layer1") layer1_pos = static_cast<int>(i);
    }

    // 依赖关系：layer3 和 layer2 在 layer1 之前
    CHECK(layer3_pos < layer1_pos);
    CHECK(layer2_pos < layer1_pos);

    return true;
}
