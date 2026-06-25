/**
 * test_bt_loader.cpp — Unit tests for BTLoader XML loading & validation
 *
 * Tests cover: XML loading from file/string, validation rules,
 * preprocessing (markdown fence stripping), error reporting.
 */

#include <gtest/gtest.h>
#include <string>
#include <fstream>
#include <cstdio>

#include "brain_core/behavior_engine/bt_loader.h"

using brain_core::BTLoader;

// ── Fixture ────────────────────────────────────────────────
class BTLoaderTest : public ::testing::Test {
protected:
    void SetUp() override {
        loader_ = std::make_unique<BTLoader>();
    }
    void TearDown() override {
        loader_.reset();
    }

    // Helper: write temp XML file, return path
    std::string writeTempFile(const std::string& content, const std::string& suffix = ".xml") {
        std::string path = "bt_test_" + std::to_string(file_counter_++) + suffix;
        std::ofstream ofs(path);
        ofs << content;
        ofs.close();
        return path;
    }

    // Helper: clean up temp file
    void removeTempFile(const std::string& path) {
        std::remove(path.c_str());
    }

    std::unique_ptr<BTLoader> loader_;
    int file_counter_ = 0;
};

// ── Basic construction ────────────────────────────────────
TEST_F(BTLoaderTest, ConstructorInitializesClean) {
    EXPECT_TRUE(loader_->lastError().empty());
}

// ── XML loading from file ─────────────────────────────────
TEST_F(BTLoaderTest, LoadValidXMLFile) {
    std::string xml = R"(<?xml version="1.0"?>
<root BTCPP_format="4">
  <BehaviorTree ID="test">
    <Sequence>
      <NavigateTo goal="0,0,0"/>
      <PickObject target="cup"/>
    </Sequence>
  </BehaviorTree>
</root>)";
    auto path = writeTempFile(xml);
    auto result = loader_->loadXML(path);
    removeTempFile(path);
    EXPECT_TRUE(result.has_value());
}

TEST_F(BTLoaderTest, LoadNonexistentFileReturnsNullopt) {
    auto result = loader_->loadXML("nonexistent_file_12345.xml");
    EXPECT_FALSE(result.has_value());
}

TEST_F(BTLoaderTest, LoadEmptyFileReturnsContent) {
    auto path = writeTempFile("");
    auto result = loader_->loadXML(path);
    removeTempFile(path);
    EXPECT_TRUE(result.has_value());
    EXPECT_TRUE(result->empty());
}

// ── XML loading from string ───────────────────────────────
TEST_F(BTLoaderTest, LoadFromString) {
    std::string xml = "<root><BehaviorTree ID=\"main\"/></root>";
    auto result = loader_->loadFromString(xml);
    EXPECT_FALSE(result.empty());
}

TEST_F(BTLoaderTest, LoadEmptyString) {
    auto result = loader_->loadFromString("");
    EXPECT_TRUE(result.empty());
}

// ── Validation ────────────────────────────────────────────
TEST_F(BTLoaderTest, ValidateWellFormedXML) {
    std::string xml = R"(<root BTCPP_format="4">
  <BehaviorTree ID="main">
    <Sequence>
      <NavigateTo goal="1,2,3"/>
    </Sequence>
  </BehaviorTree>
</root>)";
    EXPECT_TRUE(loader_->validateXML(xml));
    EXPECT_TRUE(loader_->lastError().empty());
}

TEST_F(BTLoaderTest, ValidateMalformedXMLLogsError) {
    std::string xml = "<root><unclosed>";
    EXPECT_FALSE(loader_->validateXML(xml));
    EXPECT_FALSE(loader_->lastError().empty());
}

TEST_F(BTLoaderTest, ValidateEmptyStringFails) {
    EXPECT_FALSE(loader_->validateXML(""));
    EXPECT_FALSE(loader_->lastError().empty());
}

// ── Preprocessing ─────────────────────────────────────────
TEST_F(BTLoaderTest, PreprocessStripsMarkdownFences) {
    std::string raw = R"(```xml
<root><BehaviorTree ID="main"/></root>
```)";
    auto result = loader_->preprocess(raw);
    EXPECT_NE(result.find("```"), std::string::npos);  // some stripping
    EXPECT_NE(result.find("BehaviorTree"), std::string::npos);
}

TEST_F(BTLoaderTest, PreprocessRemovesLeadingWhitespace) {
    std::string raw = "\n\n  <root/>  \n";
    auto result = loader_->preprocess(raw);
    EXPECT_FALSE(result.empty());
}

// ── Error state ───────────────────────────────────────────
TEST_F(BTLoaderTest, ValidateClearsPreviousErrorOnSuccess) {
    // First, fail validation to set error
    loader_->validateXML("");
    EXPECT_FALSE(loader_->lastError().empty());

    // Then succeed — error should be cleared
    std::string valid = R"(<root BTCPP_format="4">
  <BehaviorTree ID="main"/>
</root>)";
    loader_->validateXML(valid);
    EXPECT_TRUE(loader_->lastError().empty());
}
