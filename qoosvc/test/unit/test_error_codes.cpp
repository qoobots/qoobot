#include <gtest/gtest.h>
#include "qoosvc/common/error_codes.h"

using namespace qoosvc;

TEST(ErrorCodesTest, OkIsZero) {
    EXPECT_EQ(static_cast<int>(ErrorCode::OK), 0);
}

TEST(ErrorCodesTest, MessageForOk) {
    EXPECT_EQ(error_code_message(ErrorCode::OK), "Success");
}

TEST(ErrorCodesTest, MessageForUnknown) {
    EXPECT_EQ(error_code_message(ErrorCode::UNKNOWN), "Unknown error");
}

TEST(ErrorCodesTest, MessageForVoiceWakeWordNotFound) {
    EXPECT_EQ(error_code_message(ErrorCode::VOICE_WAKE_WORD_NOT_FOUND), "Wake word not found");
}

TEST(ErrorCodesTest, MessageForNavNoPath) {
    EXPECT_EQ(error_code_message(ErrorCode::NAV_NO_PATH), "No path found");
}

TEST(ErrorCodesTest, MessageForDiagPostFailed) {
    EXPECT_EQ(error_code_message(ErrorCode::DIAG_POST_FAILED), "POST self-test failed");
}

TEST(ErrorCodesTest, DistinctRanges) {
    // General: 100-199
    EXPECT_GE(static_cast<int>(ErrorCode::UNKNOWN), 100);
    EXPECT_LT(static_cast<int>(ErrorCode::UNKNOWN), 200);

    // Voice: 200-299
    EXPECT_GE(static_cast<int>(ErrorCode::VOICE_WAKE_WORD_NOT_FOUND), 200);
    EXPECT_LT(static_cast<int>(ErrorCode::VOICE_WAKE_WORD_NOT_FOUND), 300);

    // Navigation: 300-399
    EXPECT_GE(static_cast<int>(ErrorCode::NAV_NO_PATH), 300);
    EXPECT_LT(static_cast<int>(ErrorCode::NAV_NO_PATH), 400);

    // Spatial: 400-499
    EXPECT_GE(static_cast<int>(ErrorCode::SPATIAL_MAP_NOT_LOADED), 400);
    EXPECT_LT(static_cast<int>(ErrorCode::SPATIAL_MAP_NOT_LOADED), 500);

    // Diagnostics: 500-599
    EXPECT_GE(static_cast<int>(ErrorCode::DIAG_POST_FAILED), 500);
    EXPECT_LT(static_cast<int>(ErrorCode::DIAG_POST_FAILED), 600);

    // HMI: 600-699
    EXPECT_GE(static_cast<int>(ErrorCode::HMI_LED_FAULT), 600);
    EXPECT_LT(static_cast<int>(ErrorCode::HMI_LED_FAULT), 700);

    // Charging: 700-799
    EXPECT_GE(static_cast<int>(ErrorCode::CHARGE_DOCK_NOT_FOUND), 700);
    EXPECT_LT(static_cast<int>(ErrorCode::CHARGE_DOCK_NOT_FOUND), 800);

    // People: 800-899
    EXPECT_GE(static_cast<int>(ErrorCode::PEOPLE_FACE_NOT_RECOGNIZED), 800);
    EXPECT_LT(static_cast<int>(ErrorCode::PEOPLE_FACE_NOT_RECOGNIZED), 900);

    // Multi-robot: 900-999
    EXPECT_GE(static_cast<int>(ErrorCode::MR_DISCOVERY_FAILED), 900);
    EXPECT_LT(static_cast<int>(ErrorCode::MR_DISCOVERY_FAILED), 1000);
}
