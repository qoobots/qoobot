/**
 * @file test_tensor.cpp
 * @brief Tensor 张量单元测试
 *
 * 测试 Tensor 创建、量化/反量化、布局转换、ION 内存等核心功能。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include <gtest/gtest.h>
#include <cstring>
#include "qoocore/tensor.h"

using namespace qoocore;

// ── Tensor 创建测试 ──────────────────────────────────────────────────────────
TEST(TensorTest, CreateSimple) {
    auto result = Tensor::create({1, 3, 64, 64}, DType::FLOAT32);
    ASSERT_TRUE(result.ok());
    Tensor t = std::move(result).value();
    EXPECT_EQ(t.shape().size(), 4u);
    EXPECT_EQ(t.shape()[0], 1);
    EXPECT_EQ(t.shape()[1], 3);
    EXPECT_EQ(t.shape()[2], 64);
    EXPECT_EQ(t.shape()[3], 64);
    EXPECT_EQ(t.dtype(), DType::FLOAT32);
    EXPECT_EQ(t.layout(), TensorLayout::NCHW);
    EXPECT_FALSE(t.empty());
    EXPECT_NE(t.data(), nullptr);
    // FP32: 1*3*64*64*4 = 49152 bytes
    EXPECT_EQ(t.nbytes(), 49152u);
}

TEST(TensorTest, CreateEmptyShape) {
    auto result = Tensor::create({}, DType::FLOAT32);
    EXPECT_FALSE(result.ok());
    EXPECT_EQ(result.error().code, ErrorCode::INVALID_ARGUMENT);
}

TEST(TensorTest, CreateDifferentDtypes) {
    // INT8
    {
        auto r = Tensor::create({10, 10}, DType::INT8);
        ASSERT_TRUE(r.ok());
        Tensor t = std::move(r).value();
        EXPECT_EQ(t.nbytes(), 100u);  // 10*10*1
    }
    // INT4
    {
        auto r = Tensor::create({4, 4}, DType::QINT4);
        ASSERT_TRUE(r.ok());
        Tensor t = std::move(r).value();
        EXPECT_EQ(t.nbytes(), 8u);  // 16/2=8 bytes
    }
    // FLOAT16
    {
        auto r = Tensor::create({2, 3}, DType::FLOAT16);
        ASSERT_TRUE(r.ok());
        Tensor t = std::move(r).value();
        EXPECT_EQ(t.nbytes(), 12u);  // 2*3*2
    }
}

TEST(TensorTest, CreateLargeTensor) {
    // 4K 图像 (1x3x2160x3840)
    auto result = Tensor::create({1, 3, 2160, 3840}, DType::FLOAT32);
    ASSERT_TRUE(result.ok());
    Tensor t = std::move(result).value();
    EXPECT_EQ(t.nbytes(), 1u * 3 * 2160 * 3840 * 4);
}

// ── Tensor 移动语义测试 ──────────────────────────────────────────────────────
TEST(TensorTest, MoveSemantics) {
    auto r1 = Tensor::create({2, 2}, DType::FLOAT32);
    ASSERT_TRUE(r1.ok());
    Tensor t1 = std::move(r1).value();

    float* data = reinterpret_cast<float*>(t1.data());
    data[0] = 1.0f;
    data[1] = 2.0f;

    // 移动构造
    Tensor t2 = std::move(t1);
    EXPECT_TRUE(t1.empty());
    EXPECT_FALSE(t2.empty());
    float* d2 = reinterpret_cast<float*>(t2.data());
    EXPECT_FLOAT_EQ(d2[0], 1.0f);
    EXPECT_FLOAT_EQ(d2[1], 2.0f);

    // 移动赋值
    auto r3 = Tensor::create({3, 3}, DType::FLOAT32);
    ASSERT_TRUE(r3.ok());
    Tensor t3 = std::move(r3).value();
    t3 = std::move(t2);
    EXPECT_TRUE(t2.empty());
    EXPECT_EQ(t3.shape()[0], 2);
    EXPECT_EQ(t3.shape()[1], 2);
}

// ── Tensor 属性测试 ──────────────────────────────────────────────────────────
TEST(TensorTest, Properties) {
    auto r = Tensor::create({4, 8, 16}, DType::INT32, TensorLayout::NHWC);
    ASSERT_TRUE(r.ok());
    Tensor t = std::move(r).value();

    EXPECT_EQ(t.layout(), TensorLayout::NHWC);
    EXPECT_EQ(t.dtype(), DType::INT32);
    EXPECT_FALSE(t.is_ion_memory());
    EXPECT_EQ(t.ion_fd(), -1);
    EXPECT_TRUE(t.owns_data());

    std::string summary = t.summary();
    EXPECT_NE(summary.find("Tensor"), std::string::npos);
    EXPECT_NE(summary.find("int32"), std::string::npos);
    EXPECT_NE(summary.find("NHWC"), std::string::npos);
}

// ── Tensor 数据写入/读取测试 ─────────────────────────────────────────────────
TEST(TensorTest, DataReadWrite) {
    auto r = Tensor::create({2, 2}, DType::FLOAT32);
    ASSERT_TRUE(r.ok());
    Tensor t = std::move(r).value();

    float* data = reinterpret_cast<float*>(t.data());
    data[0] = 1.0f;
    data[1] = 2.0f;
    data[2] = 3.0f;
    data[3] = 4.0f;

    const float* cdata = reinterpret_cast<const float*>(
        static_cast<const Tensor&>(t).data());
    EXPECT_FLOAT_EQ(cdata[0], 1.0f);
    EXPECT_FLOAT_EQ(cdata[3], 4.0f);
}

// ── 量化测试 ──────────────────────────────────────────────────────────────────
TEST(TensorTest, QuantizeINT8PerTensor) {
    auto r = Tensor::create({2, 4}, DType::FLOAT32);
    ASSERT_TRUE(r.ok());
    Tensor t = std::move(r).value();

    // 填充数据
    float* data = reinterpret_cast<float*>(t.data());
    for (int i = 0; i < 8; ++i) data[i] = static_cast<float>(i) - 4.0f;  // [-4, -3, ..., 3]

    QuantParams qp;
    qp.target_dtype = DType::QINT8;
    qp.scales = {0.1f};
    qp.zero_points = {0};
    qp.symmetric = false;

    auto result = t.quantize(qp);
    ASSERT_TRUE(result.ok());

    EXPECT_EQ(t.dtype(), DType::QINT8);
    EXPECT_EQ(t.nbytes(), 8u);  // 8 elements * 1 byte
    EXPECT_TRUE(t.quant().has_value());
}

TEST(TensorTest, QuantizeFP16) {
    auto r = Tensor::create({2, 2}, DType::FLOAT32);
    ASSERT_TRUE(r.ok());
    Tensor t = std::move(r).value();

    float* data = reinterpret_cast<float*>(t.data());
    data[0] = 1.0f; data[1] = 2.0f;
    data[2] = 3.0f; data[3] = 4.0f;

    QuantParams qp;
    qp.target_dtype = DType::FLOAT16;

    auto result = t.quantize(qp);
    ASSERT_TRUE(result.ok());
    EXPECT_EQ(t.dtype(), DType::FLOAT16);
    EXPECT_EQ(t.nbytes(), 8u);  // 4 elements * 2 bytes
}

TEST(TensorTest, QuantizeSymmetrical) {
    auto r = Tensor::create({4}, DType::FLOAT32);
    ASSERT_TRUE(r.ok());
    Tensor t = std::move(r).value();

    float* data = reinterpret_cast<float*>(t.data());
    data[0] = -5.0f; data[1] = 0.0f; data[2] = 2.5f; data[3] = 5.0f;

    QuantParams qp;
    qp.target_dtype = DType::QINT8;
    qp.scales = {0.03937f};  // 5/127
    qp.symmetric = true;

    auto result = t.quantize(qp);
    ASSERT_TRUE(result.ok());
    EXPECT_EQ(t.dtype(), DType::QINT8);
}

TEST(TensorTest, QuantizeInvalidInput) {
    auto r = Tensor::create({4}, DType::INT8);  // 非 FP32
    ASSERT_TRUE(r.ok());
    Tensor t = std::move(r).value();

    QuantParams qp;
    qp.target_dtype = DType::QINT8;
    qp.scales = {0.1f};

    auto result = t.quantize(qp);
    EXPECT_FALSE(result.ok());
    EXPECT_EQ(result.error().code, ErrorCode::INVALID_ARGUMENT);
}

// ── 反量化测试 ────────────────────────────────────────────────────────────────
TEST(TensorTest, DequantizeINT8) {
    auto r = Tensor::create({4}, DType::FLOAT32);
    ASSERT_TRUE(r.ok());
    Tensor t = std::move(r).value();

    float* data = reinterpret_cast<float*>(t.data());
    data[0] = 1.0f; data[1] = 2.0f; data[2] = 3.0f; data[3] = 4.0f;

    QuantParams qp;
    qp.target_dtype = DType::QINT8;
    qp.scales = {0.5f};
    qp.zero_points = {0};

    ASSERT_TRUE(t.quantize(qp).ok());

    auto result = t.dequantize();
    ASSERT_TRUE(result.ok());
    Tensor dt = std::move(result).value();

    EXPECT_EQ(dt.dtype(), DType::FLOAT32);
    float* ddata = reinterpret_cast<float*>(dt.data());
    // 量化值：round([1,2,3,4]/0.5) = [2,4,6,8]
    // 反量化：[2,4,6,8]*0.5 = [1,2,3,4]
    EXPECT_NEAR(ddata[0], 1.0f, 0.6f);
    EXPECT_NEAR(ddata[3], 4.0f, 0.6f);
}

TEST(TensorTest, DequantizeWithoutParams) {
    auto r = Tensor::create({4}, DType::FLOAT32);
    ASSERT_TRUE(r.ok());
    Tensor t = std::move(r).value();

    auto result = t.dequantize();
    EXPECT_FALSE(result.ok());
    EXPECT_EQ(result.error().code, ErrorCode::INVALID_ARGUMENT);
}

// ── 布局转换测试 ──────────────────────────────────────────────────────────────
TEST(TensorTest, ToLayoutNCHWtoNHWC) {
    auto r = Tensor::create({1, 3, 2, 2}, DType::FLOAT32, TensorLayout::NCHW);
    ASSERT_TRUE(r.ok());
    Tensor t = std::move(r).value();

    // NCHW: [n=0,c=0,h=0,w=0]=0, [n=0,c=0,h=0,w=1]=1, ...
    float* data = reinterpret_cast<float*>(t.data());
    for (int i = 0; i < 12; ++i) data[i] = static_cast<float>(i);

    auto result = t.to_layout(TensorLayout::NHWC);
    ASSERT_TRUE(result.ok());
    Tensor nhwc = std::move(result).value();

    EXPECT_EQ(nhwc.layout(), TensorLayout::NHWC);
    EXPECT_EQ(nhwc.shape()[0], 1);
    EXPECT_EQ(nhwc.shape()[1], 2);  // H
    EXPECT_EQ(nhwc.shape()[2], 2);  // W
    EXPECT_EQ(nhwc.shape()[3], 3);  // C
}

TEST(TensorTest, ToLayoutSameLayout) {
    auto r = Tensor::create({1, 3, 2, 2}, DType::FLOAT32, TensorLayout::NCHW);
    ASSERT_TRUE(r.ok());
    Tensor t = std::move(r).value();

    float* data = reinterpret_cast<float*>(t.data());
    for (int i = 0; i < 12; ++i) data[i] = static_cast<float>(i);

    // 相同布局应创建副本
    auto result = t.to_layout(TensorLayout::NCHW);
    ASSERT_TRUE(result.ok());
    Tensor copy = std::move(result).value();
    EXPECT_EQ(copy.layout(), TensorLayout::NCHW);
}

// ── Strides 测试 ──────────────────────────────────────────────────────────────
TEST(StridesTest, FromShape) {
    auto s = Strides::from_shape({1, 3, 640, 640});
    ASSERT_EQ(s.size(), 4u);
    EXPECT_EQ(s[0], 3 * 640 * 640);  // C*H*W
    EXPECT_EQ(s[1], 640 * 640);       // H*W
    EXPECT_EQ(s[2], 640);             // W
    EXPECT_EQ(s[3], 1);
}

TEST(StridesTest, Empty) {
    Strides s;
    EXPECT_TRUE(s.empty());
}

// ── TensorMetadata 测试 ───────────────────────────────────────────────────────
TEST(TensorMetadataTest, NumElements) {
    TensorMetadata meta;
    meta.shape = {1, 3, 224, 224};
    meta.dtype = DType::FLOAT32;
    EXPECT_EQ(meta.num_elements(), 1 * 3 * 224 * 224);
    EXPECT_EQ(meta.bytes_contiguous(), 1u * 3 * 224 * 224 * 4);
    EXPECT_TRUE(meta.valid());
}

TEST(TensorMetadataTest, Invalid) {
    TensorMetadata meta;
    EXPECT_FALSE(meta.valid());
}

// ── QuantParams 测试 ──────────────────────────────────────────────────────────
TEST(QuantParamsTest, Empty) {
    QuantParams qp;
    EXPECT_TRUE(qp.empty());

    qp.scales = {0.1f};
    EXPECT_FALSE(qp.empty());
}

// ── ModelInfo 测试 ────────────────────────────────────────────────────────────
TEST(ModelInfoTest, Basic) {
    ModelInfo info;
    info.name = "test_model";
    info.version = "1.0.0";
    EXPECT_EQ(info.name, "test_model");
    EXPECT_EQ(info.weight_size_bytes, 0u);
}

// ── ProfilingInfo 测试 ────────────────────────────────────────────────────────
TEST(ProfilingInfoTest, Basic) {
    ProfilingInfo info;
    info.total_latency_ms = 10.5;
    info.infer_ms = 8.0;
    EXPECT_DOUBLE_EQ(info.total_latency_ms, 10.5);
    EXPECT_DOUBLE_EQ(info.infer_ms, 8.0);
}
