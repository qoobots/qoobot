/**
 * @file test_compiler.cpp
 * @brief 编译器工具链单元测试
 *
 * 测试 CompilationTarget、SourceFormat、QuantizationConfig 等编译器基础设施。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include <gtest/gtest.h>
#include "qoocore/compiler.h"

using namespace qoocore;

// ── SourceFormat 测试 ─────────────────────────────────────────────────────────
TEST(SourceFormatTest, ToString) {
    EXPECT_STREQ(source_format_to_string(SourceFormat::ONNX), "onnx");
    EXPECT_STREQ(source_format_to_string(SourceFormat::PYTORCH), "pytorch");
    EXPECT_STREQ(source_format_to_string(SourceFormat::TENSORFLOW), "tensorflow");
    EXPECT_STREQ(source_format_to_string(SourceFormat::TFLITE), "tflite");
}

// ── CompilationTarget 测试 ────────────────────────────────────────────────────
TEST(CompilationTargetTest, Default) {
    CompilationTarget target;
    EXPECT_EQ(target.backend, BackendType::AUTO);
    EXPECT_TRUE(target.vendor.empty());
    EXPECT_TRUE(target.chip.empty());
}

TEST(CompilationTargetTest, ToString) {
    CompilationTarget target;
    EXPECT_EQ(target.to_string(), "auto");

    target.backend = BackendType::NPU;
    target.vendor = "qcom";
    target.chip = "sdm8g3";
    EXPECT_EQ(target.to_string(), "npu_qcom_sdm8g3");

    target.backend = BackendType::GPU;
    target.vendor = "nvidia";
    target.chip = "orin";
    EXPECT_EQ(target.to_string(), "gpu_nvidia_orin");

    target.backend = BackendType::CPU;
    EXPECT_EQ(target.to_string(), "cpu_nvidia_orin");
}

// ── QuantizationConfig 测试 ───────────────────────────────────────────────────
TEST(QuantizationConfigTest, Default) {
    QuantizationConfig qc;
    EXPECT_EQ(qc.scheme, QuantizationScheme::NONE);
    EXPECT_EQ(qc.target_dtype, DType::QINT8);
    EXPECT_EQ(qc.calib_size, 100u);
}

TEST(QuantizationConfigTest, INT8Config) {
    QuantizationConfig qc;
    qc.scheme = QuantizationScheme::INT8_PTQ;
    qc.target_dtype = DType::QINT8;
    qc.per_channel = true;
    qc.symmetric = false;

    EXPECT_EQ(qc.scheme, QuantizationScheme::INT8_PTQ);
    EXPECT_TRUE(qc.per_channel);
    EXPECT_FALSE(qc.symmetric);
}

TEST(QuantizationConfigTest, FP16Config) {
    QuantizationConfig qc;
    qc.scheme = QuantizationScheme::FP16;
    qc.target_dtype = DType::FLOAT16;

    EXPECT_EQ(qc.scheme, QuantizationScheme::FP16);
    EXPECT_EQ(qc.target_dtype, DType::FLOAT16);
}

// ── OptimizeConfig 测试 ───────────────────────────────────────────────────────
TEST(OptimizeConfigTest, Default) {
    OptimizeConfig oc;
    EXPECT_EQ(oc.level, 2);
    EXPECT_TRUE(oc.constant_folding);
    EXPECT_TRUE(oc.fuse_bn);
    EXPECT_TRUE(oc.eliminate_dead_branch);
}

TEST(OptimizeConfigTest, Level0) {
    OptimizeConfig oc;
    oc.level = 0;
    oc.constant_folding = false;
    oc.fuse_bn = false;

    EXPECT_EQ(oc.level, 0);
    EXPECT_FALSE(oc.constant_folding);
}

// ── CompilerConfig 测试 ───────────────────────────────────────────────────────
TEST(CompilerConfigTest, Default) {
    CompilerConfig cc;
    EXPECT_EQ(cc.format, SourceFormat::ONNX);
    EXPECT_EQ(cc.target.backend, BackendType::AUTO);
    EXPECT_EQ(cc.optimize.level, 2);
    EXPECT_EQ(cc.quant.scheme, QuantizationScheme::NONE);
}

TEST(CompilerConfigTest, FullConfig) {
    CompilerConfig cc;
    cc.format = SourceFormat::ONNX;
    cc.model_path = "/models/yolo.onnx";
    cc.output_path = "/models/yolo.qoomodel";
    cc.target.backend = BackendType::NPU;
    cc.target.vendor = "qcom";
    cc.target.chip = "sdm8g3";
    cc.optimize.level = 2;
    cc.quant.scheme = QuantizationScheme::INT8_PTQ;
    cc.quant.calib_dir = "/data/calibration";

    EXPECT_EQ(cc.model_path, "/models/yolo.onnx");
    EXPECT_EQ(cc.output_path, "/models/yolo.qoomodel");
    EXPECT_EQ(cc.target.vendor, "qcom");
    EXPECT_EQ(cc.quant.calib_dir, "/data/calibration");
}

// ── CompileResult 测试 ────────────────────────────────────────────────────────
TEST(CompileResultTest, Basic) {
    CompileResult cr;
    cr.success = true;
    cr.output_path = "/out/model.qoomodel";
    cr.input_size_mb = 50.0;
    cr.output_size_mb = 12.5;

    EXPECT_TRUE(cr.success);
    EXPECT_EQ(cr.output_path, "/out/model.qoomodel");
    EXPECT_GT(cr.compression_ratio(), 3.5);  // 50/12.5 = 4.0
}

// ── 编译日志测试 ──────────────────────────────────────────────────────────────
TEST(CompileLogTest, Basic) {
    CompileLog log;
    log.phase = "import";
    log.message = "Loaded ONNX model with 120 ops";
    log.elapsed_ms = 45.2;

    EXPECT_EQ(log.phase, "import");
    EXPECT_EQ(log.message, "Loaded ONNX model with 120 ops");
    EXPECT_NEAR(log.elapsed_ms, 45.2, 0.01);
}
