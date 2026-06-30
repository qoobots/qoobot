/**
 * test_json_utils.cpp — JSON 工具库单元测试
 */

#include "json_utils.hpp"
#include <cmath>

using namespace qoostore::edge::json;

TEST(json_parse_empty_object) {
    auto v = parse("{}");
    CHECK(v.is_object());
    CHECK_EQ(v.size(), 0u);
    return true;
}

TEST(json_parse_empty_array) {
    auto v = parse("[]");
    CHECK(v.is_array());
    CHECK_EQ(v.size(), 0u);
    return true;
}

TEST(json_parse_simple_object) {
    auto v = parse(R"({"name":"test","version":"1.0.0"})");
    CHECK(v.is_object());
    CHECK_EQ(v["name"].as_string(), "test");
    CHECK_EQ(v["version"].as_string(), "1.0.0");
    return true;
}

TEST(json_parse_nested_object) {
    auto v = parse(R"({"skill":{"name":"test","version":"1.0.0"}})");
    CHECK(v.is_object());
    CHECK(v["skill"].is_object());
    CHECK_EQ(v["skill"]["name"].as_string(), "test");
    CHECK_EQ(v["skill"]["version"].as_string(), "1.0.0");
    return true;
}

TEST(json_parse_array_of_strings) {
    auto v = parse(R"(["camera","microphone","location"])");
    CHECK(v.is_array());
    CHECK_EQ(v.size(), 3u);
    CHECK_EQ(v[0].as_string(), "camera");
    CHECK_EQ(v[1].as_string(), "microphone");
    CHECK_EQ(v[2].as_string(), "location");
    return true;
}

TEST(json_parse_numbers) {
    auto v = parse(R"({"int_val":42,"float_val":3.14,"neg_val":-17})");
    CHECK(v.is_object());
    CHECK_CLOSE(v["int_val"].as_number(), 42.0, 0.001);
    CHECK_CLOSE(v["float_val"].as_number(), 3.14, 0.001);
    CHECK_CLOSE(v["neg_val"].as_number(), -17.0, 0.001);
    CHECK_EQ(v["int_val"].as_int(), 42);
    CHECK_EQ(v["neg_val"].as_int(), -17);
    return true;
}

TEST(json_parse_boolean) {
    auto v = parse(R"({"active":true,"disabled":false})");
    CHECK(v.is_object());
    CHECK(v["active"].as_bool() == true);
    CHECK(v["disabled"].as_bool() == false);
    return true;
}

TEST(json_parse_null) {
    auto v = parse(R"({"data":null})");
    CHECK(v.is_object());
    CHECK(v["data"].is_null());
    return true;
}

TEST(json_parse_unicode_escape) {
    auto v = parse(R"("\u0048\u0065\u006C\u006C\u006F")");  // "Hello"
    CHECK(v.is_string());
    CHECK_EQ(v.as_string(), "Hello");
    return true;
}

TEST(json_dump_object) {
    Value v(Object{});
    v["name"] = "test";
    v["version"] = "1.0.0";
    v["active"] = true;

    std::string result = v.dump();
    CHECK(result.find("\"name\"") != std::string::npos);
    CHECK(result.find("\"test\"") != std::string::npos);
    CHECK(result.find("\"1.0.0\"") != std::string::npos);
    CHECK(result.find("true") != std::string::npos);
    return true;
}

TEST(json_dump_array) {
    Value v(Array{});
    v[0] = "camera";
    v[1] = "microphone";
    v[2] = 42;

    std::string result = v.dump();
    CHECK(result.find("\"camera\"") != std::string::npos);
    CHECK(result.find("\"microphone\"") != std::string::npos);
    CHECK(result.find("42") != std::string::npos);
    return true;
}

TEST(json_dump_pretty) {
    Value v(Object{});
    v["name"] = "test";
    v["items"] = Value(Array{});
    v["items"][0] = "a";
    v["items"][1] = "b";

    std::string result = v.dump(2);
    CHECK(result.find('\n') != std::string::npos);  // 应该包含换行
    return true;
}

TEST(json_get_string_with_default) {
    auto v = parse(R"({"name":"test"})");
    CHECK_EQ(v.get_string("name"), "test");
    CHECK_EQ(v.get_string("missing"), "");
    CHECK_EQ(v.get_string("missing", "default"), "default");
    return true;
}

TEST(json_get_int_with_default) {
    auto v = parse(R"({"count":42})");
    CHECK_EQ(v.get_int("count"), 42);
    CHECK_EQ(v.get_int("missing"), 0);
    CHECK_EQ(v.get_int("missing", 99), 99);
    return true;
}

TEST(json_roundtrip_complex) {
    std::string original = R"({"skillId":"com.test.app","name":"Test App","version":"1.2.3","permissions":["camera","microphone"],"settings":{"maxMemoryMB":512,"maxCPUPercent":30}})";
    auto v = parse(original);
    std::string regenerated = v.dump();
    // 重新解析应该成功
    auto v2 = parse(regenerated);
    CHECK(v2.is_object());
    CHECK_EQ(v2["skillId"].as_string(), "com.test.app");
    CHECK_EQ(v2["settings"]["maxMemoryMB"].as_int(), 512);
    return true;
}

TEST(json_parse_invalid_should_throw) {
    try {
        parse("{invalid json");
        return false;  // 不应该到这里
    } catch (const ParseError&) {
        return true;   // 预期抛出异常
    }
}
