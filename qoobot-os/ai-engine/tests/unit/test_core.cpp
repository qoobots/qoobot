/**
 * @file test_core.cpp
 * @brief qoocore 核心类型单元测试
 *
 * 测试 Result<T>、ErrorCode、DType、TensorLayout 等核心类型。
 *
 * 运行：./build/tests/test_core
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include <gtest/gtest.h>

#include "qoocore/core.h"

// ── ErrorCode 测试 ───────────────────────────────────────────────────────
TEST(ErrorCodeTest, OkIsZero) {
    EXPECT_EQ(static_cast<int>(qoocore::ErrorCode::OK), 0);
}

TEST(ErrorCodeTest, ErrorCodeValues) {
    EXPECT_NE(qoocore::ErrorCode::FILE_NOT_FOUND,
              qoocore::ErrorCode::INVALID_MODEL);
}

// ── DType 工具函数测试 ───────────────────────────────────────────────────
TEST(DTypeTest, IsFloating) {
    EXPECT_TRUE(qoocore::is_floating(qoocore::DType::FLOAT32));
    EXPECT_TRUE(qoocore::is_floating(qoocore::DType::FLOAT16));
    EXPECT_TRUE(qoocore::is_floating(qoocore::DType::BFLOAT16));
    EXPECT_FALSE(qoocore::is_floating(qoocore::DType::INT8));
    EXPECT_FALSE(qoocore::is_floating(qoocore::DType::BOOL));
}

TEST(DTypeTest, IsInteger) {
    EXPECT_TRUE(qoocore::is_integer(qoocore::DType::INT32));
    EXPECT_TRUE(qoocore::is_integer(qoocore::DType::INT8));
    EXPECT_TRUE(qoocore::is_integer(qoocore::DType::UINT8));
    EXPECT_FALSE(qoocore::is_integer(qoocore::DType::FLOAT32));
}

TEST(DTypeTest, IsQuantized) {
    EXPECT_TRUE(qoocore::is_quantized(qoocore::DType::QINT8));
    EXPECT_TRUE(qoocore::is_quantized(qoocore::DType::QINT4));
    EXPECT_FALSE(qoocore::is_quantized(qoocore::DType::INT8));
}

TEST(DTypeTest, DTypeBytes) {
    EXPECT_EQ(qoocore::dtype_bytes(qoocore::DType::FLOAT32), 4);
    EXPECT_EQ(qoocore::dtype_bytes(qoocore::DType::FLOAT16), 2);
    EXPECT_EQ(qoocore::dtype_bytes(qoocore::DType::INT8),   1);
    EXPECT_EQ(qoocore::dtype_bytes(qoocore::DType::UINT8),  1);
    EXPECT_EQ(qoocore::dtype_bytes(qoocore::DType::BOOL),   1);
    // INT4 返回 0（需特殊处理）
    EXPECT_EQ(qoocore::dtype_bytes(qoocore::DType::QINT4), 0);
}

TEST(DTypeTest, DTypeToString) {
    EXPECT_STREQ(qoocore::dtype_to_string(qoocore::DType::FLOAT32), "float32");
    EXPECT_STREQ(qoocore::dtype_to_string(qoocore::DType::INT8),    "int8");
    EXPECT_STREQ(qoocore::dtype_to_string(qoocore::DType::QINT8),  "qint8");
}

// ── TensorLayout 测试 ──────────────────────────────────────────────────────
TEST(TensorLayoutTest, LayoutToString) {
    EXPECT_STREQ(qoocore::layout_to_string(qoocore::TensorLayout::NCHW), "NCHW");
    EXPECT_STREQ(qoocore::layout_to_string(qoocore::TensorLayout::NHWC), "NHWC");
}

// ── BackendType 测试 ──────────────────────────────────────────────────────
TEST(BackendTypeTest, BackendToString) {
    EXPECT_STREQ(qoocore::backend_to_string(qoocore::BackendType::NPU), "npu");
    EXPECT_STREQ(qoocore::backend_to_string(qoocore::BackendType::GPU), "gpu");
    EXPECT_STREQ(qoocore::backend_to_string(qoocore::BackendType::CPU), "cpu");
    EXPECT_STREQ(qoocore::backend_to_string(qoocore::BackendType::AUTO), "auto");
}

// ── Result<T> 测试 ───────────────────────────────────────────────────────
TEST(ResultTest, OkValue) {
    qoocore::Result<int> r(42);
    EXPECT_TRUE(r.ok());
    EXPECT_EQ(r.value(), 42);
}

TEST(ResultTest, ErrorValue) {
    qoocore::Result<int> r(qoocore::ErrorCode::INVALID_ARGUMENT, "test error");
    EXPECT_FALSE(r.ok());
    EXPECT_EQ(r.error().code, qoocore::ErrorCode::INVALID_ARGUMENT);
    EXPECT_EQ(r.error().message, "test error");
}

TEST(ResultTest, MoveSemantics) {
    qoocore::Result<std::string> r(std::string("hello"));
    EXPECT_TRUE(r.ok());

    // 移动后原对象不再持有值
    qoocore::Result<std::string> r2 = std::move(r);
    EXPECT_TRUE(r2.ok());
    EXPECT_EQ(r2.value(), "hello");
}

// ── Version 测试 ─────────────────────────────────────────────────────────
TEST(VersionTest, Comparison) {
    qoocore::Version v1_0_0{1, 0, 0};
    qoocore::Version v0_1_0{0, 1, 0};
    qoocore::Version v1_0_1{1, 0, 1};

    EXPECT_TRUE(v1_0_0 >= v0_1_0);
    EXPECT_TRUE(v1_0_1 >= v1_0_0);
    EXPECT_FALSE(v0_1_0 >= v1_0_0);
}

// ── 主函数 ─────────────────────────────────────────────────────────────────
int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
