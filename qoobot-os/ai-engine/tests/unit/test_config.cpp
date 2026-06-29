/**
 * @file test_config.cpp
 * @brief 配置管理单元测试
 *
 * 测试 ConfigValue、ConfigManager 的类型安全访问、文件加载、环境变量等。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include <gtest/gtest.h>
#include "qoocore/config.h"

using namespace qoocore;

// ── ConfigValue 基本类型测试 ──────────────────────────────────────────────────
TEST(ConfigValueTest, BoolType) {
    ConfigValue cv(true);
    EXPECT_TRUE(cv.is_bool());
    EXPECT_FALSE(cv.is_int());
    EXPECT_FALSE(cv.is_string());

    auto result = cv.as_bool();
    ASSERT_TRUE(result.ok());
    EXPECT_TRUE(result.value());
}

TEST(ConfigValueTest, IntType) {
    ConfigValue cv(std::int64_t(42));
    EXPECT_TRUE(cv.is_int());
    EXPECT_EQ(cv.as_int().value(), 42);
    // 可以转为 double
    EXPECT_DOUBLE_EQ(cv.as_double().value(), 42.0);
}

TEST(ConfigValueTest, DoubleType) {
    ConfigValue cv(3.14);
    EXPECT_TRUE(cv.is_double());
    EXPECT_DOUBLE_EQ(cv.as_double().value(), 3.14);
}

TEST(ConfigValueTest, StringType) {
    ConfigValue cv(std::string("hello"));
    EXPECT_TRUE(cv.is_string());
    EXPECT_EQ(cv.as_string().value(), "hello");
}

TEST(ConfigValueTest, NullType) {
    ConfigValue cv;
    EXPECT_TRUE(cv.is_null());
}

TEST(ConfigValueTest, TypeMismatch) {
    ConfigValue cv(std::int64_t(42));
    auto result = cv.as_bool();
    EXPECT_FALSE(result.ok());
}

// ── ConfigValue 类型转换测试 ──────────────────────────────────────────────────
TEST(ConfigValueTest, StringToInt) {
    ConfigValue cv(std::string("12345"));
    auto result = cv.as_int();
    ASSERT_TRUE(result.ok());
    EXPECT_EQ(result.value(), 12345);
}

TEST(ConfigValueTest, StringToDouble) {
    ConfigValue cv(std::string("3.14159"));
    auto result = cv.as_double();
    ASSERT_TRUE(result.ok());
    EXPECT_NEAR(result.value(), 3.14159, 0.00001);
}

TEST(ConfigValueTest, IntToDouble) {
    ConfigValue cv(std::int64_t(100));
    EXPECT_DOUBLE_EQ(cv.as_double().value(), 100.0);
}

TEST(ConfigValueTest, DoubleToInt) {
    ConfigValue cv(3.9);
    EXPECT_EQ(cv.as_int().value(), 3);
}

TEST(ConfigValueTest, BoolToString) {
    ConfigValue cv(true);
    EXPECT_EQ(cv.as_string().value(), "true");
}

TEST(ConfigValueTest, IntToString) {
    ConfigValue cv(std::int64_t(99));
    EXPECT_EQ(cv.as_string().value(), "99");
}

// ── ConfigValue 嵌套对象测试 ──────────────────────────────────────────────────
TEST(ConfigValueTest, NestedObject) {
    ConfigValue root;
    root.set("engine.log_level", ConfigValue(std::string("debug")));
    root.set("engine.max_memory", ConfigValue(std::int64_t(4096)));

    auto log = root.get("engine.log_level");
    ASSERT_TRUE(log.has_value());
    EXPECT_EQ(log->as_string().value(), "debug");

    auto mem = root.get("engine.max_memory");
    ASSERT_TRUE(mem.has_value());
    EXPECT_EQ(mem->as_int().value(), 4096);

    // 不存在的 key
    auto missing = root.get("engine.nonexistent");
    EXPECT_FALSE(missing.has_value());
}

TEST(ConfigValueTest, DotNotationPath) {
    ConfigValue root;
    root.set("a.b.c", ConfigValue(std::int64_t(123)));

    auto val = root.get("a.b.c");
    ASSERT_TRUE(val.has_value());
    EXPECT_EQ(val->as_int().value(), 123);

    // 中间节点
    auto mid = root.get("a");
    ASSERT_TRUE(mid.has_value());
    auto b = mid->get("b");
    ASSERT_TRUE(b.has_value());
    auto c = b->get("c");
    ASSERT_TRUE(c.has_value());
    EXPECT_EQ(c->as_int().value(), 123);
}

// ── ConfigValue YAML 序列化测试 ──────────────────────────────────────────────
TEST(ConfigValueTest, YAMLRoundtrip) {
    std::string yaml = "engine:\n  profiling: true\n  max_memory_mb: 2048\n";
    auto result = ConfigValue::from_yaml(yaml);
    ASSERT_TRUE(result.ok());

    auto profiling = result.value().get("engine.profiling");
    ASSERT_TRUE(profiling.has_value());

    auto memory = result.value().get("engine.max_memory_mb");
    ASSERT_TRUE(memory.has_value());
    EXPECT_EQ(memory->as_int().value(), 2048);
}

TEST(ConfigValueTest, YAMLInvalid) {
    auto result = ConfigValue::from_yaml("invalid: [unclosed");
    EXPECT_FALSE(result.ok());
}

// ── ConfigValue JSON 序列化测试 ──────────────────────────────────────────────
TEST(ConfigValueTest, JSONRoundtrip) {
    std::string json = R"({"name": "test", "value": 42, "flag": true})";
    auto result = ConfigValue::from_json(json);
    ASSERT_TRUE(result.ok());

    auto name = result.value().get("name");
    ASSERT_TRUE(name.has_value());
    EXPECT_EQ(name->as_string().value(), "test");

    auto value = result.value().get("value");
    ASSERT_TRUE(value.has_value());
    EXPECT_EQ(value->as_int().value(), 42);

    auto flag = result.value().get("flag");
    ASSERT_TRUE(flag.has_value());
    EXPECT_TRUE(flag->as_bool().value());
}

TEST(ConfigValueTest, JSONInvalid) {
    auto result = ConfigValue::from_json("{bad json");
    EXPECT_FALSE(result.ok());
}

// ── ConfigManager 单例测试 ────────────────────────────────────────────────────
TEST(ConfigManagerTest, Singleton) {
    ConfigManager& mgr1 = ConfigManager::instance();
    ConfigManager& mgr2 = ConfigManager::instance();
    EXPECT_EQ(&mgr1, &mgr2);
}

TEST(ConfigManagerTest, DefaultValues) {
    ConfigManager& mgr = ConfigManager::instance();

    auto log_level = mgr.get_string("engine.log_level", "info");
    EXPECT_EQ(log_level.value(), "info");

    auto max_mem = mgr.get_int("engine.max_memory_mb", 2048);
    EXPECT_EQ(max_mem.value(), 2048);

    auto profiling = mgr.get_bool("engine.profiling", false);
    EXPECT_FALSE(profiling.value());
}

TEST(ConfigManagerTest, SetAndGet) {
    ConfigManager& mgr = ConfigManager::instance();

    mgr.set("test.key", ConfigValue(std::string("custom_value")));
    auto val = mgr.get_string("test.key", "default");
    EXPECT_EQ(val.value(), "custom_value");

    mgr.set("test.int_key", ConfigValue(std::int64_t(999)));
    auto int_val = mgr.get_int("test.int_key", 0);
    EXPECT_EQ(int_val.value(), 999);

    // 清理
    mgr.set("test.key", ConfigValue());
}

TEST(ConfigManagerTest, GetWithDefault) {
    ConfigManager& mgr = ConfigManager::instance();

    auto missing = mgr.get_bool("nonexistent.key", true);
    EXPECT_TRUE(missing.value());

    auto missing_int = mgr.get_int("nonexistent.int", -1);
    EXPECT_EQ(missing_int.value(), -1);

    auto missing_str = mgr.get_string("nonexistent.str", "fallback");
    EXPECT_EQ(missing_str.value(), "fallback");
}

TEST(ConfigManagerTest, GetWithWrongType) {
    ConfigManager& mgr = ConfigManager::instance();
    mgr.set("num.key", ConfigValue(std::string("not_a_number")));

    auto result = mgr.get_int("num.key", 0);
    EXPECT_EQ(result.value(), 0);  // 返回默认值
}

// ── 便捷宏测试 ────────────────────────────────────────────────────────────────
TEST(ConfigMacroTest, QoocoreGetBool) {
    bool val = QOOCORE_GET_BOOL("engine.profiling");
    EXPECT_FALSE(val);
}

TEST(ConfigMacroTest, QoocoreGetInt) {
    std::int64_t val = QOOCORE_GET_INT("engine.max_memory_mb");
    EXPECT_EQ(val, 2048);
}

TEST(ConfigMacroTest, QoocoreGetString) {
    std::string val = QOOCORE_GET_STRING("engine.log_level");
    EXPECT_EQ(val, "info");
}
